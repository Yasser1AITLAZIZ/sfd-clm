"""Performance tracking context manager"""
import time
from typing import Optional
from contextlib import contextmanager

from app.utils.metrics import MetricsCollector


@contextmanager
def track_performance(metrics_collector: Optional[MetricsCollector], step_name: str):
    """
    Context manager for tracking performance of a processing step.
    
    Args:
        metrics_collector: MetricsCollector instance (optional)
        step_name: Name of the processing step
        
    Example:
        with track_performance(metrics, "ocr_processing"):
            # Do OCR processing
            pass
    """
    if metrics_collector:
        metrics_collector.start_step(step_name)
    
    start_time = time.time()
    try:
        yield
    finally:
        if metrics_collector:
            metrics_collector.end_step(step_name)
        duration = time.time() - start_time
        if not metrics_collector:
            # Log directly if no collector
            print(f"⏱️ [{step_name}] Duration: {duration:.2f}s")


