import logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

from typing import Generator, List, Optional, Union
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, status
from apscheduler.jobstores.base import JobLookupError
from apscheduler.triggers.cron import CronTrigger as APSCronTrigger
from apscheduler.triggers.interval import IntervalTrigger as APSIntervalTrigger
from sqlalchemy.orm import Session

from scheduler.database import SessionLocal
from .models import (
    JobDefinition,
    JobConfigApi,
    ErrorResponse,
    CronTrigger,
    IntervalTrigger,
)
from .scheduler import scheduler

app = FastAPI(title="Resilient Task Scheduler API")


# Pydantic model for APScheduler Job information
class JobInfo(JobConfigApi):
    next_run_time: Optional[datetime] = None
    # Add other relevant fields from APScheduler Job object if needed


# Dependency to get DB session
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Resilient Task Scheduler API!"}


# --- Job Definition Management Endpoints (Database) ---


@app.get("/jobs", response_model=List[JobConfigApi], tags=["Job Definitions"])
def read_jobs(db: Session = Depends(get_db)):
    jobs = db.query(JobDefinition).all()
    return [JobConfigApi.model_validate(job) for job in jobs]


@app.post(
    "/jobs",
    response_model=JobConfigApi,
    status_code=status.HTTP_201_CREATED,
    tags=["Job Definitions"],
    responses={
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "Conflict: Job with this ID already exists",
        }
    },
)
def create_job(job: JobConfigApi, db: Session = Depends(get_db)):
    db_job = db.query(JobDefinition).filter(JobDefinition.id == job.id).first()
    if db_job:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job with this ID already exists",
        )

    # Map JobConfigApi Pydantic model to JobDefinition SQLAlchemy model
    trigger_config = job.trigger.model_dump()
    trigger_type = trigger_config.pop("type")

    db_job = JobDefinition(
        id=job.id,
        func=job.func,
        trigger_type=trigger_type,
        trigger_config=trigger_config,
        args=job.args,
        kwargs=job.kwargs,
        max_instances=job.max_instances,
        coalesce=job.coalesce,
        misfire_grace_time=job.misfire_grace_time,
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return JobConfigApi.model_validate(db_job)


@app.get(
    "/jobs/{job_id}",
    response_model=JobConfigApi,
    tags=["Job Definitions"],
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Not Found: Job not found",
        }
    },
)
def read_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobDefinition).filter(JobDefinition.id == job_id).first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return JobConfigApi.model_validate(job)


@app.put(
    "/jobs/{job_id}",
    response_model=JobConfigApi,
    tags=["Job Definitions"],
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Not Found: Job not found",
        }
    },
)
def update_job(job_id: str, job: JobConfigApi, db: Session = Depends(get_db)):
    db_job = db.query(JobDefinition).filter(JobDefinition.id == job_id).first()
    if db_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )

    # Update fields
    db_job.func = job.func

    trigger_config = job.trigger.model_dump()
    db_job.trigger_type = trigger_config.pop("type")
    db_job.trigger_config = trigger_config

    db_job.args = job.args
    db_job.kwargs = job.kwargs
    db_job.max_instances = job.max_instances
    db_job.coalesce = job.coalesce
    db_job.misfire_grace_time = job.misfire_grace_time

    db.commit()
    db.refresh(db_job)
    return JobConfigApi.model_validate(db_job)


@app.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Job Definitions"],
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Not Found: Job not found",
        }
    },
)
def delete_job(job_id: str, db: Session = Depends(get_db)):
    db_job = db.query(JobDefinition).filter(JobDefinition.id == job_id).first()
    if db_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )

    db.delete(db_job)
    db.commit()
    return


# --- Scheduler Control Endpoints (APScheduler Instance) ---


def _convert_trigger_to_pydantic(
    trigger,
) -> Optional[Union[CronTrigger, IntervalTrigger]]:
    """Converts an APScheduler trigger to a Pydantic model."""
    if isinstance(trigger, APSCronTrigger):
        return CronTrigger(
            type="cron",
            year=str(trigger.fields[0]),
            month=str(trigger.fields[1]),
            day=str(trigger.fields[2]),
            week=str(trigger.fields[3]),
            day_of_week=str(trigger.fields[4]),
            hour=str(trigger.fields[5]),
            minute=str(trigger.fields[6]),
            second=str(trigger.fields[7]),
            timezone=str(trigger.timezone),
        )
    elif isinstance(trigger, APSIntervalTrigger):
        total_seconds = trigger.interval.total_seconds()
        return IntervalTrigger(
            type="interval",
            weeks=int(total_seconds / (7 * 24 * 3600)),
            days=int((total_seconds % (7 * 24 * 3600)) / (24 * 3600)),
            hours=int((total_seconds % (24 * 3600)) / 3600),
            minutes=int((total_seconds % 3600) / 60),
            seconds=int(total_seconds % 60),
            timezone=str(trigger.timezone),
        )
    logging.warning(f"Unsupported trigger type: {type(trigger).__name__}")
    return None


@app.get("/scheduler/jobs", response_model=List[JobInfo], tags=["Scheduler Control"])
def get_scheduled_jobs():
    """Retrieves a list of currently scheduled jobs from the APScheduler instance."""
    jobs = scheduler.get_jobs()
    job_infos = []
    for job in jobs:
        trigger_model = _convert_trigger_to_pydantic(job.trigger)
        if not trigger_model:
            logging.warning(
                f"Skipping job '{job.id}' due to unsupported trigger type '{type(job.trigger).__name__}'."
            )
            continue

        # Ensure 'func' is represented as a string path 'module:function'
        if hasattr(job.func, "__module__") and hasattr(job.func, "__name__"):
            func_str = f"{job.func.__module__}.{job.func.__name__}"
        else:
            func_str = str(job.func)

        job_infos.append(
            JobInfo(
                id=job.id,
                func=func_str,
                trigger=trigger_model,
                args=list(job.args),
                kwargs=job.kwargs,
                max_instances=job.max_instances,
                coalesce=job.coalesce,
                misfire_grace_time=job.misfire_grace_time,
                next_run_time=job.next_run_time,
            )
        )
    return job_infos

@app.post(
    "/scheduler/jobs/{job_id}/pause",
    tags=["Scheduler Control"],
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Not Found: Job not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)
def pause_scheduled_job(job_id: str):
    try:
        scheduler.pause_job(job_id)
        return {"message": f"Job '{job_id}' paused successfully."}
    except JobLookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while pausing job '{job_id}': {e}"
        )

@app.post(
    "/scheduler/jobs/{job_id}/resume",
    tags=["Scheduler Control"],
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Not Found: Job not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)
def resume_scheduled_job(job_id: str):
    try:
        scheduler.resume_job(job_id)
        return {"message": f"Job '{job_id}' resumed successfully."}
    except JobLookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while resuming job '{job_id}': {e}"
        )

@app.post(
    "/scheduler/jobs/{job_id}/run",
    tags=["Scheduler Control"],
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Not Found: Job not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)
def run_scheduled_job_immediately(job_id: str):
    try:
        # This is the recommended way to trigger a job immediately in APScheduler
        # It respects max_instances and other job settings
        scheduler.modify_job(job_id, next_run_time=datetime.now())
        return {"message": f"Job '{job_id}' scheduled for immediate execution."}
    except JobLookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while triggering job '{job_id}': {e}"
        )
