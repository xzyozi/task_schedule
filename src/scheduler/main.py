from contextlib import asynccontextmanager
from typing import Generator, List, Optional
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.jobstores.base import JobLookupError
from sqlalchemy.orm import Session
from pydantic import BaseModel

# --- App Imports ---
from scheduler import database
from .models import JobDefinition, JobConfig, ErrorResponse, ProcessExecutionLog
from .scheduler import scheduler, start_scheduler, shutdown_scheduler
from .loader import load_and_validate_jobs, apply_job_config, start_config_watcher, sync_jobs_from_db
from util import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("Application startup...")
    
    # 1. Initialize Database
    database.init_db()
    
    # 2. Start Scheduler
    start_scheduler()

    # 3. Load jobs from YAML and sync with DB
    config_path = "jobs.yaml"
    logger.info(f"Loading initial job configurations from {config_path}...")
    initial_jobs = load_and_validate_jobs(config_path)
    if initial_jobs:
        apply_job_config(scheduler, initial_jobs)
        logger.info("Initial job configurations applied.")
    else:
        logger.warning("No initial job configurations loaded from YAML.")

    # 4. Start file watcher
    logger.info(f"Starting file watcher for {config_path}...")
    watcher = start_config_watcher(scheduler, config_path)
    
    # 5. Perform initial DB sync
    logger.info("Performing initial job sync...")
    try:
        sync_jobs_from_db()
    except Exception as e:
        logger.critical(f"Initial job sync failed: {e}", exc_info=True)

    # 6. Schedule periodic DB sync
    scheduler.add_job(
        sync_jobs_from_db,
        "interval",
        seconds=60,
        id="internal_db_sync",
        replace_existing=True,
    )
    logger.info("Scheduled periodic job sync every 60 seconds.")

    yield # Application is running

    # --- Shutdown ---
    logger.info("Application shutdown...")
    if watcher:
        watcher.stop()
        watcher.join()
        logger.info("File watcher stopped.")
    shutdown_scheduler()

app = FastAPI(title="Resilient Task Scheduler API", lifespan=lifespan)

# CORS Middleware
origins = [
    "http://localhost:5012",
    "http://127.0.0.1:5012",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic model for APScheduler Job information
class JobInfo(JobConfig):
    next_run_time: Optional[datetime] = None
    # Add other relevant fields from APScheduler Job object if needed

# Dependency to get DB session
def get_db() -> Generator[Session, None, None]:
    if database.SessionLocal is None:
        raise RuntimeError("Database is not initialized. SessionLocal is None.")
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Resilient Task Scheduler API!"}


# --- Dashboard Endpoints ---

class DashboardSummary(BaseModel):
    total_jobs: int
    running_jobs: int
    successful_runs: int
    failed_runs: int

@app.get("/api/dashboard/summary", response_model=DashboardSummary, tags=["Dashboard"])
def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    Provides a summary of job statuses for the dashboard.
    """
    try:
        total_jobs = db.query(JobDefinition).count()
        
        # Note: This is a simplified aggregation. For large datasets, more efficient queries would be needed.
        running_jobs = db.query(ProcessExecutionLog).filter(ProcessExecutionLog.status == 'RUNNING').count()
        successful_runs = db.query(ProcessExecutionLog).filter(ProcessExecutionLog.status == 'COMPLETED').count()
        failed_runs = db.query(ProcessExecutionLog).filter(ProcessExecutionLog.status == 'FAILED').count()

        return DashboardSummary(
            total_jobs=total_jobs,
            running_jobs=running_jobs,
            successful_runs=successful_runs,
            failed_runs=failed_runs,
        )
    except Exception as e:
        logger.error(f"Error fetching dashboard summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard summary data."
        )

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
        logger.warning(f"Attempted to create job with existing ID: {job.id}")
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
    logger.info(f"Job '{job.id}' created successfully.")
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
        logger.warning(f"Attempted to read non-existent job: {job_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    logger.info(f"Job '{job_id}' read successfully.")
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
        logger.warning(f"Attempted to update non-existent job: {job_id}")
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
    logger.info(f"Job '{job_id}' updated successfully.")
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
        logger.warning(f"Attempted to delete non-existent job: {job_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    db.delete(db_job)
    db.commit()
    logger.info(f"Job '{job_id}' deleted successfully.")
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
        logger.info(f"Job '{job_id}' paused successfully.")
        return {"message": f"Job '{job_id}' paused successfully."}
    except JobLookupError:
        logger.warning(f"Attempted to pause non-existent job: '{job_id}'")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred while pausing job '{job_id}': {e}", exc_info=True)
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
        logger.info(f"Job '{job_id}' resumed successfully.")
        return {"message": f"Job '{job_id}' resumed successfully."}
    except JobLookupError:
        logger.warning(f"Attempted to resume non-existent job: '{job_id}'")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred while resuming job '{job_id}': {e}", exc_info=True)
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
        logger.info(f"Job '{job_id}' scheduled for immediate execution.")
        return {"message": f"Job '{job_id}' scheduled for immediate execution."}
    except JobLookupError:
        logger.warning(f"Attempted to run non-existent job immediately: '{job_id}'")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred while triggering job '{job_id}' for immediate execution: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while triggering job '{job_id}' for immediate execution: {e}"
        )



