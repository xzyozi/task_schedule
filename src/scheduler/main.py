from typing import Generator, List, Optional
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, status
from apscheduler.jobstores.base import JobLookupError
from sqlalchemy.orm import Session

from scheduler.database import SessionLocal # Changed import
from .models import JobDefinition, JobConfig, ErrorResponse # Added ErrorResponse
from .scheduler import scheduler 

app = FastAPI(title="Resilient Task Scheduler API")

# Pydantic model for APScheduler Job information
class JobInfo(JobConfig):
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

@app.get("/jobs", response_model=List[JobConfig], tags=["Job Definitions"])
def read_jobs(db: Session = Depends(get_db)):
    jobs = db.query(JobDefinition).all()
    return [JobConfig.model_validate(job) for job in jobs]

@app.post(
    "/jobs",
    response_model=JobConfig,
    status_code=status.HTTP_201_CREATED,
    tags=["Job Definitions"],
    responses={
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "Conflict: Job with this ID already exists"}
    }
)
def create_job(job: JobConfig, db: Session = Depends(get_db)):
    db_job = db.query(JobDefinition).filter(JobDefinition.id == job.id).first()
    if db_job:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job with this ID already exists"
        )
    
    # Map JobConfig Pydantic model to JobDefinition SQLAlchemy model
    trigger_config = job.trigger.copy()
    trigger_type = trigger_config.pop('type')

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
    return JobConfig.model_validate(db_job)

@app.get(
    "/jobs/{job_id}",
    response_model=JobConfig,
    tags=["Job Definitions"],
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Not Found: Job not found"}
    }
)
def read_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobDefinition).filter(JobDefinition.id == job_id).first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    return JobConfig.model_validate(job)

@app.put(
    "/jobs/{job_id}",
    response_model=JobConfig,
    tags=["Job Definitions"],
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Not Found: Job not found"}
    }
)
def update_job(job_id: str, job: JobConfig, db: Session = Depends(get_db)):
    db_job = db.query(JobDefinition).filter(JobDefinition.id == job_id).first()
    if db_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Update fields
    db_job.func = job.func
    
    trigger_config = job.trigger.copy()
    db_job.trigger_type = trigger_config.pop('type')
    db_job.trigger_config = trigger_config

    db_job.args = job.args
    db_job.kwargs = job.kwargs
    db_job.max_instances = job.max_instances
    db_job.coalesce = job.coalesce
    db_job.misfire_grace_time = job.misfire_grace_time

    db.commit()
    db.refresh(db_job)
    return JobConfig.model_validate(db_job)

@app.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Job Definitions"],
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Not Found: Job not found"}
    }
)
def delete_job(job_id: str, db: Session = Depends(get_db)):
    db_job = db.query(JobDefinition).filter(JobDefinition.id == job_id).first()
    if db_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    db.delete(db_job)
    db.commit()
    return


# --- Scheduler Control Endpoints (APScheduler Instance) ---

@app.get("/scheduler/jobs", response_model=List[JobInfo], tags=["Scheduler Control"])
def get_scheduled_jobs():
    jobs = scheduler.get_jobs()
    return [
        JobInfo(
            id=job.id,
            func=job.func.__module__ + ":" + job.func.__name__ if hasattr(job.func, '__module__') and hasattr(job.func, '__name__') else str(job.func),
            trigger=job.trigger.args, # This might need more careful mapping depending on trigger type
            args=list(job.args),
            kwargs=job.kwargs,
            max_instances=job.max_instances,
            coalesce=job.coalesce,
            misfire_grace_time=job.misfire_grace_time,
            next_run_time=job.next_run_time
        ) for job in jobs
    ]

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



