from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.database import get_db
from modules.scheduler import schemas, service
from util import logger_util

logger = logger_util.get_logger(__name__)

router = APIRouter(prefix="/api")

@router.get("/dashboard/summary", response_model=schemas.DashboardSummary, tags=["Dashboard"], summary="Get Dashboard Summary", description="Provides a high-level summary of job statuses.")
def get_dashboard_summary(db: Session = Depends(get_db)):
    try:
        return service.get_dashboard_summary(db)
    except Exception as e:
        logger.error(f"Error fetching dashboard summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard summary")

@router.get("/logs", response_model=List[schemas.ProcessExecutionLogInfo], tags=["Dashboard"], summary="Get Execution Logs", description="Retrieves a paginated list of job execution logs.")
def get_execution_logs(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=200), db: Session = Depends(get_db)):
    try:
        return service.get_execution_logs(db, skip=skip, limit=limit)
    except Exception as e:
        logger.error(f"Error fetching execution logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch execution logs")

@router.get("/timeline-items", response_model=List[schemas.TimelineItem], tags=["Dashboard"], summary="Get Timeline Data", description="Provides data for the job execution timeline, including scheduled and historical runs.")
def get_timeline_data(db: Session = Depends(get_db)):
    try:
        return service.get_timeline_data(db)
    except Exception as e:
        logger.error(f"Error fetching timeline data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/unified-jobs", response_model=List[schemas.UnifiedJobItem], tags=["Dashboard"])
def get_unified_jobs(db: Session = Depends(get_db)):
    """
    Retrieves a unified list of all jobs and workflows.
    """
    try:
        return service.get_unified_jobs_list(db)
    except Exception as e:
        logger.error(f"Error fetching unified jobs list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch unified jobs list")
