"""Metrics export endpoint"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional
import logging

from app.core.logging import get_logger, safe_log

logger = get_logger(__name__)

router = APIRouter()

# In-memory storage for metrics (in production, use Redis or database)
_metrics_storage = {}


@router.get("/metrics/{request_id}")
async def get_metrics(request_id: str) -> JSONResponse:
    """
    Get metrics for a specific request.
    
    Args:
        request_id: Request ID to get metrics for
        
    Returns:
        JSON response with metrics data
    """
    try:
        if request_id not in _metrics_storage:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": "error",
                    "error": {
                        "code": "METRICS_NOT_FOUND",
                        "message": f"Metrics not found for request_id: {request_id}"
                    }
                }
            )
        
        metrics = _metrics_storage[request_id]
        
        safe_log(
            logger,
            logging.INFO,
            "Metrics retrieved",
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "data": metrics
            }
        )
        
    except Exception as e:
        safe_log(
            logger,
            logging.ERROR,
            "Error retrieving metrics",
            request_id=request_id,
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown error"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving metrics: {str(e) if e else 'Unknown error'}"
        )


@router.get("/metrics")
async def list_metrics(limit: Optional[int] = 100) -> JSONResponse:
    """
    List all available metrics.
    
    Args:
        limit: Maximum number of metrics to return
        
    Returns:
        JSON response with list of metrics
    """
    try:
        # Get recent metrics
        metrics_list = list(_metrics_storage.values())[-limit:]
        
        safe_log(
            logger,
            logging.INFO,
            "Metrics list retrieved",
            count=len(metrics_list)
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "data": {
                    "metrics": metrics_list,
                    "total": len(_metrics_storage)
                }
            }
        )
        
    except Exception as e:
        safe_log(
            logger,
            logging.ERROR,
            "Error listing metrics",
            error_type=type(e).__name__,
            error_message=str(e) if e else "Unknown error"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing metrics: {str(e) if e else 'Unknown error'}"
        )


def store_metrics(request_id: str, metrics: dict):
    """
    Store metrics for a request.
    
    Args:
        request_id: Request ID
        metrics: Metrics data to store
    """
    _metrics_storage[request_id] = metrics
    
    # Limit storage size (keep last 1000 requests)
    if len(_metrics_storage) > 1000:
        # Remove oldest entries
        oldest_keys = sorted(_metrics_storage.keys())[:-1000]
        for key in oldest_keys:
            del _metrics_storage[key]






