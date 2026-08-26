from typing import Any, Dict, List

from apscheduler.jobstores.base import JobLookupError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from modules.scheduler import scheduler_instance, schemas, service
from util import logger_util, time_util

logger = logger_util.get_logger(__name__)

router = APIRouter()


@router.get("/scheduler/jobs", response_model=List[schemas.Job], tags=["Scheduler Control"])
def get_scheduled_jobs(db: Session = Depends(get_db)) -> List[schemas.Job]:
    try:
        return service.get_scheduled_jobs_info(db)
    except Exception as e:
        logger.error(f"Error fetching scheduled jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch scheduled jobs")


@router.post("/scheduler/jobs/{job_id}/pause", tags=["Scheduler Control"])
def pause_scheduled_job(job_id: str) -> Dict[str, str]:
    try:
        scheduler_instance.scheduler.pause_job(job_id)
        return {"message": f"Job '{job_id}' paused successfully."}
    except JobLookupError:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")


@router.post("/scheduler/jobs/{job_id}/resume", tags=["Scheduler Control"])
def resume_scheduled_job(job_id: str) -> Dict[str, str]:
    try:
        scheduler_instance.scheduler.resume_job(job_id)
        return {"message": f"Job '{job_id}' resumed successfully."}
    except JobLookupError:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")


@router.post("/scheduler/jobs/{job_id}/run", tags=["Scheduler Control"])
def run_scheduled_job_immediately(job_id: str) -> Dict[str, str]:
    try:
        scheduler_instance.scheduler.modify_job(job_id, next_run_time=time_util.get_current_utc_time())
        return {"message": f"Job '{job_id}' scheduled for immediate execution."}
    except JobLookupError:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")


@router.post("/scheduler/jobs/bulk/pause", tags=["Scheduler Control"])
def pause_bulk_scheduled_jobs(payload: schemas.BulkJobUpdate) -> Dict[str, Any]:
    if not payload.job_ids:
        raise HTTPException(status_code=400, detail="No job IDs provided")
    try:
        result = service.pause_bulk_scheduled_jobs(payload.job_ids)
        if result["failed"]:
            return {"message": "Partial success", "paused": result["paused"], "failed": result["failed"]}
        return {"message": "All selected jobs paused successfully."}
    except Exception as e:
        logger.error(f"Error during bulk pause of jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to pause jobs")


@router.post("/scheduler/jobs/bulk/resume", tags=["Scheduler Control"])
def resume_bulk_scheduled_jobs(payload: schemas.BulkJobUpdate) -> Dict[str, Any]:
    if not payload.job_ids:
        raise HTTPException(status_code=400, detail="No job IDs provided")
    try:
        result = service.resume_bulk_scheduled_jobs(payload.job_ids)
        if result["failed"]:
            return {"message": "Partial success", "resumed": result["resumed"], "failed": result["failed"]}
        return {"message": "All selected jobs resumed successfully."}
    except Exception as e:
        logger.error(f"Error during bulk resume of jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to resume jobs")
