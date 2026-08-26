from typing import List

from apscheduler.jobstores.base import JobLookupError
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from core.database import get_db
from modules.scheduler import loader, scheduler_instance, schemas, service
from modules.scheduler.service import job_definition_service
from util import logger_util

logger = logger_util.get_logger(__name__)

router = APIRouter()


@router.get(
    "/available-tasks",
    response_model=List[schemas.AvailableTask],
    tags=["Job Definitions"],
    summary="List Available Tasks",
)
def get_available_tasks():
    """
    Returns a list of all available task types (Python, Shell, etc.)
    that can be used to create jobs, including their parameters.
    """
    try:
        return service.get_available_tasks()
    except Exception as e:
        logger.error(f"Error fetching available tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch available tasks")


def _get_next_run_time(job_id: str):
    """Safely retrieves the next run time for a job."""
    job = scheduler_instance.scheduler.get_job(job_id)
    return job.next_run_time if job else None


@router.get("/jobs", response_model=List[schemas.JobOut], tags=["Job Definitions"], summary="List All Job Definitions")
def read_jobs(db: Session = Depends(get_db), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    jobs = job_definition_service.get_multi(db, skip=skip, limit=limit)

    results = []
    for job in jobs:
        job_out = schemas.JobOut.model_validate(job)
        job_out.next_run_time = _get_next_run_time(job.id)
        results.append(job_out)
    return results


@router.post(
    "/jobs",
    response_model=schemas.JobOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Job Definitions"],
    summary="Create a New Job Definition",
)
def create_job(job_in: schemas.JobCreate, db: Session = Depends(get_db)):
    """
    Creates a new job definition in the database and adds it to the scheduler.
    The input is validated against the `JobCreate` schema, which uses a discriminated
    union to validate `task_parameters` based on `task_type`.
    """
    db_job = service.create_job_from_schema(db, job_in=job_in)
    if not db_job:
        raise HTTPException(status_code=409, detail="Job with this ID might already exist or creation failed.")
    loader.sync_jobs_from_db()

    # We return the hydrated JobOut model for consistency, even on creation
    job_out = schemas.JobOut.model_validate(db_job)
    job_out.next_run_time = _get_next_run_time(db_job.id)
    return job_out


@router.get("/jobs/{job_id}", response_model=schemas.JobOut, tags=["Job Definitions"])
def read_job(job_id: str, db: Session = Depends(get_db)):
    db_job = job_definition_service.get(db, id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    job_out = schemas.JobOut.model_validate(db_job)
    job_out.next_run_time = _get_next_run_time(db_job.id)
    return job_out


@router.put("/jobs/{job_id}", response_model=schemas.JobOut, tags=["Job Definitions"])
def update_job(job_id: str, job_in: schemas.JobUpdate, db: Session = Depends(get_db)):
    db_job = job_definition_service.get(db, id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    db_job = service.update_job_from_schema(db, db_obj=db_job, job_in=job_in)
    loader.sync_jobs_from_db()

    job_out = schemas.JobOut.model_validate(db_job)
    job_out.next_run_time = _get_next_run_time(db_job.id)
    return job_out


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Job Definitions"])
def delete_job(job_id: str, db: Session = Depends(get_db)):
    db_job = job_definition_service.remove(db, id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        scheduler_instance.scheduler.remove_job(job_id)
        logger.info(f"Removed job '{job_id}' from scheduler.")
    except JobLookupError:
        logger.warning(f"Job '{job_id}' was not found in the scheduler for removal, but was deleted from the database.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/jobs/bulk/delete", status_code=status.HTTP_200_OK, tags=["Job Definitions"])
def delete_bulk_jobs(payload: schemas.BulkJobUpdate, db: Session = Depends(get_db)):
    job_ids = payload.job_ids
    if not job_ids:
        raise HTTPException(status_code=400, detail="No job IDs provided")

    try:
        deleted_count = service.delete_bulk_jobs(db, job_ids=job_ids)
        if deleted_count > 0:
            loader.sync_jobs_from_db()
        return {"message": f"Successfully deleted {deleted_count} jobs."}
    except Exception as e:
        logger.error(f"Error during bulk deletion of jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete jobs")


@router.get("/jobs/{job_id}/history", response_model=List[schemas.ProcessExecutionLogInfo], tags=["Job Details"])
def get_job_execution_history(job_id: str, db: Session = Depends(get_db)):
    try:
        return service.get_job_execution_history(db, job_id=job_id)
    except Exception as e:
        logger.error(f"Error fetching job execution history for job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch job execution history")
