"""Metrics collection system for performance tracking"""
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
import logging

from app.core.logging import get_logger, safe_log

logger = get_logger(__name__)


class MetricsCollector:
    """Collector for metrics during processing"""
    
    def __init__(self, request_id: Optional[str] = None):
        """
        Initialize metrics collector.
        
        Args:
            request_id: Optional request ID for tracking
        """
        self.request_id = request_id
        self.start_time = time.time()
        self.metrics = {
            "request_id": request_id,
            "start_time": datetime.utcnow().isoformat(),
            "steps": {},
            "field_success": {},
            "memory_usage": [],
            "llm_costs": [],
            "errors": []
        }
    
    def start_step(self, step_name: str):
        """Start timing a processing step"""
        self.metrics["steps"][step_name] = {
            "start_time": time.time(),
            "end_time": None,
            "duration": None
        }
    
    def end_step(self, step_name: str):
        """End timing a processing step"""
        if step_name in self.metrics["steps"]:
            step = self.metrics["steps"][step_name]
            step["end_time"] = time.time()
            step["duration"] = step["end_time"] - step["start_time"]
    
    def record_field_success(self, field_name: str, success: bool, confidence: Optional[float] = None):
        """
        Record field extraction success.
        
        Args:
            field_name: Name of the field
            success: Whether extraction was successful
            confidence: Confidence score if available
        """
        if field_name not in self.metrics["field_success"]:
            self.metrics["field_success"][field_name] = {
                "success": success,
                "confidence": confidence,
                "attempts": 1
            }
        else:
            self.metrics["field_success"][field_name]["attempts"] += 1
            if success:
                self.metrics["field_success"][field_name]["success"] = True
                if confidence is not None:
                    self.metrics["field_success"][field_name]["confidence"] = confidence
    
    def record_memory_usage(self, memory_info: Dict[str, Any]):
        """
        Record memory usage snapshot.
        
        Args:
            memory_info: Dictionary with memory usage info
        """
        self.metrics["memory_usage"].append({
            "timestamp": datetime.utcnow().isoformat(),
            **memory_info
        })
    
    def record_llm_cost(self, model: str, tokens_input: int, tokens_output: int, cost_per_1k_input: float = 0.0, cost_per_1k_output: float = 0.0):
        """
        Record LLM API cost estimate.
        
        Args:
            model: Model name
            tokens_input: Input tokens
            tokens_output: Output tokens
            cost_per_1k_input: Cost per 1k input tokens
            cost_per_1k_output: Cost per 1k output tokens
        """
        cost = (tokens_input / 1000 * cost_per_1k_input) + (tokens_output / 1000 * cost_per_1k_output)
        self.metrics["llm_costs"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "model": model,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "cost": cost
        })
    
    def record_error(self, error_type: str, error_message: str, step: Optional[str] = None):
        """
        Record an error.
        
        Args:
            error_type: Type of error
            error_message: Error message
            step: Processing step where error occurred
        """
        self.metrics["errors"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "step": step
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get metrics summary.
        
        Returns:
            Dictionary with summary metrics
        """
        total_duration = time.time() - self.start_time
        
        # Calculate success rate
        total_fields = len(self.metrics["field_success"])
        successful_fields = sum(1 for f in self.metrics["field_success"].values() if f["success"])
        success_rate = (successful_fields / total_fields * 100) if total_fields > 0 else 0
        
        # Calculate average confidence
        confidences = [f["confidence"] for f in self.metrics["field_success"].values() if f.get("confidence") is not None]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Total LLM cost
        total_llm_cost = sum(c["cost"] for c in self.metrics["llm_costs"])
        
        # Peak memory usage
        peak_memory = None
        if self.metrics["memory_usage"]:
            peak_memory = max(m["rss_mb"] for m in self.metrics["memory_usage"] if "rss_mb" in m)
        
        return {
            "request_id": self.request_id,
            "total_duration": total_duration,
            "total_duration_formatted": f"{total_duration:.2f}s",
            "steps": {
                name: {
                    "duration": step.get("duration"),
                    "duration_formatted": f"{step.get('duration', 0):.2f}s" if step.get("duration") else None
                }
                for name, step in self.metrics["steps"].items()
            },
            "field_extraction": {
                "total_fields": total_fields,
                "successful_fields": successful_fields,
                "success_rate": round(success_rate, 2),
                "average_confidence": round(avg_confidence, 2)
            },
            "memory": {
                "peak_memory_mb": round(peak_memory, 2) if peak_memory else None,
                "snapshots_count": len(self.metrics["memory_usage"])
            },
            "llm_costs": {
                "total_cost": round(total_llm_cost, 4),
                "requests_count": len(self.metrics["llm_costs"])
            },
            "errors": {
                "count": len(self.metrics["errors"]),
                "errors": self.metrics["errors"]
            }
        }
    
    def get_full_metrics(self) -> Dict[str, Any]:
        """
        Get full metrics data.
        
        Returns:
            Complete metrics dictionary
        """
        self.metrics["end_time"] = datetime.utcnow().isoformat()
        self.metrics["total_duration"] = time.time() - self.start_time
        return self.metrics
    
    def log_summary(self):
        """Log metrics summary"""
        summary = self.get_summary()
        safe_log(
            logger,
            logging.INFO,
            "Processing metrics summary",
            **summary
        )


