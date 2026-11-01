from fastapi import APIRouter
import time

router = APIRouter()

from ..services.cloud_llm import get_llm_status

START_TIME = time.time()

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": "Smart Question Paper Generator",
        "version": "1.0.0",
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "llm": get_llm_status()
    }

@router.get("/llm/status")
def llm_status_check():
    return get_llm_status()
