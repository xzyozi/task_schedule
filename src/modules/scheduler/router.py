import json, os
import platform
from typing import List
import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.orm import Session
from apscheduler.jobstores.base import JobLookupError

from core.database import get_db
from modules.scheduler import models, schemas, loader
from modules.scheduler.service import job_definition_service
from modules.scheduler import scheduler_instance, service
from util import logger_util, config_util

logger = logger_util.get_logger(__name__)

router = APIRouter(prefix="/api")

#
# --- System Endpoints ---
#
@router.get("/system/os", tags=["System"], summary="Get OS Information")
def get_os_info():
    """Returns the operating system type (e.g., 'Windows', 'Linux')."""
    return {"os_type": platform.system()}

#
# --- Dashboard Endpoints ---
#
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

@router.get("/timeline/data", response_model=List[schemas.TimelineItem], tags=["Dashboard"], summary="Get Timeline Data", description="Provides data for the job execution timeline, including scheduled and historical runs.")
def get_timeline_data(db: Session = Depends(get_db)):
    try:
        return service.get_timeline_data(db)
    except Exception as e:
        logger.error(f"Error fetching timeline data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

#
# --- Filesystem Endpoints ---
#
@router.get("/filesystem/list-dirs", response_model=List[str], tags=["Filesystem"], summary="List Subdirectories in Work Directory")
def list_work_dir_subdirectories(path: str = Query("", description="The relative path within the work directory to scan.")):
    """
    Lists subdirectories within the configured scheduler work_dir.
    This is useful for providing autocompletion for the 'cwd' field in a UI.
    """
    try:
        return service.list_subdirectories(relative_path=path)
    except Exception as e:
        logger.error(f"Error listing subdirectories for path '{path}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list directories")

# --- Job Definition Endpoints ---
#
@router.get("/jobs", response_model=List[schemas.JobConfig], tags=["Job Definitions"], summary="List All Job Definitions")
def read_jobs(db: Session = Depends(get_db), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    jobs = job_definition_service.get_multi(db, skip=skip, limit=limit)
    return [schemas.JobConfig.model_validate(job) for job in jobs]

@router.post("/jobs", response_model=schemas.JobConfig, status_code=status.HTTP_201_CREATED, tags=["Job Definitions"], summary="Create a New Job Definition")
def create_job(job_in: schemas.JobConfig, db: Session = Depends(get_db)):
    if job_definition_service.get(db, id=job_in.id):
        raise HTTPException(status_code=409, detail="Job with this ID already exists")
    db_job = job_definition_service.create_from_config(db, job_in=job_in)
    loader.sync_jobs_from_db()
    return schemas.JobConfig.model_validate(db_job)

@router.get("/jobs/{job_id}", response_model=schemas.JobConfig, tags=["Job Definitions"])
def read_job(job_id: str, db: Session = Depends(get_db)):
    db_job = job_definition_service.get(db, id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return schemas.JobConfig.model_validate(db_job)

@router.put("/jobs/{job_id}", response_model=schemas.JobConfig, tags=["Job Definitions"])
def update_job(job_id: str, job_in: schemas.JobConfig, db: Session = Depends(get_db)):
    db_job = job_definition_service.get(db, id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    db_job = job_definition_service.update_from_config(db, db_obj=db_job, job_in=job_in)
    loader.sync_jobs_from_db()
    return schemas.JobConfig.model_validate(db_job)

@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Job Definitions"])
def delete_job(job_id: str, db: Session = Depends(get_db)):
    db_job = job_definition_service.remove(db, id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    loader.sync_jobs_from_db()
    return

# --- Workflow Definition Endpoints ---

@router.post("/workflows", response_model=schemas.Workflow, status_code=status.HTTP_201_CREATED, tags=["Workflow Definitions"])
def create_workflow(workflow_in: schemas.WorkflowCreate, db: Session = Depends(get_db)):
    db_workflow = service.workflow_service.create_with_steps(db, obj_in=workflow_in)
    # TODO: Schedule the workflow with APScheduler
    return db_workflow

@router.get("/workflows", response_model=List[schemas.Workflow], tags=["Workflow Definitions"])
def read_workflows(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    workflows = service.workflow_service.get_multi(db, skip=skip, limit=limit)
    return workflows

@router.get("/workflows/{workflow_id}", response_model=schemas.Workflow, tags=["Workflow Definitions"])
def read_workflow(workflow_id: int, db: Session = Depends(get_db)):
    db_workflow = service.workflow_service.get(db, id=workflow_id)
    if db_workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return db_workflow

@router.put("/workflows/{workflow_id}", response_model=schemas.Workflow, tags=["Workflow Definitions"])
def update_workflow(workflow_id: int, workflow_in: schemas.WorkflowCreate, db: Session = Depends(get_db)):
    db_workflow = service.workflow_service.get(db, id=workflow_id)
    if db_workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db_workflow = service.workflow_service.update_with_steps(db, db_obj=db_workflow, obj_in=workflow_in)
    # TODO: Update the schedule in APScheduler
    return db_workflow

@router.delete("/workflows/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Workflow Definitions"])
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    db_workflow = service.workflow_service.remove(db, id=workflow_id)
    if db_workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    # TODO: Remove the job from APScheduler
    return

# --- Scheduler Control Endpoints ---
@router.get("/scheduler/jobs", response_model=List[schemas.JobInfo], tags=["Scheduler Control"])
def get_scheduled_jobs():
    try:
        return service.get_scheduled_jobs_info()
    except Exception as e:
        logger.error(f"Error fetching scheduled jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch scheduled jobs")

# --- job edit Endpoints ---

@router.post("/scheduler/jobs/{job_id}/pause", tags=["Scheduler Control"])
def pause_scheduled_job(job_id: str):
    try:
        scheduler_instance.scheduler.pause_job(job_id)
        return {"message": f"Job '{job_id}' paused successfully."}
    except JobLookupError:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

@router.post("/scheduler/jobs/{job_id}/resume", tags=["Scheduler Control"])
def resume_scheduled_job(job_id: str):
    try:
        scheduler_instance.scheduler.resume_job(job_id)
        return {"message": f"Job '{job_id}' resumed successfully."}
    except JobLookupError:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

@router.post("/scheduler/jobs/{job_id}/run", tags=["Scheduler Control"])
def run_scheduled_job_immediately(job_id: str):
    try:
        scheduler_instance.scheduler.modify_job(job_id, next_run_time=datetime.now())
        return {"message": f"Job '{job_id}' scheduled for immediate execution."}
    except JobLookupError:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")


@router.put("/jobs/{job_id}", response_model=schemas.JobConfig, tags=["Job Definitions"])
def update_job(job_id: str, job_in: schemas.JobConfig, db: Session = Depends(get_db)):
    db_job = job_definition_service.get(db, id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    db_job = job_definition_service.update_from_config(db, db_obj=db_job, job_in=job_in)
    loader.sync_jobs_from_db()
    return schemas.JobConfig.model_validate(db_job)

@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Job Definitions"])
def delete_job(job_id: str, db: Session = Depends(get_db)):
    db_job = job_definition_service.remove(db, id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    loader.sync_jobs_from_db()
    return

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

@router.post("/scheduler/jobs/bulk/pause", tags=["Scheduler Control"])
def pause_bulk_scheduled_jobs(payload: schemas.BulkJobUpdate):
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
def resume_bulk_scheduled_jobs(payload: schemas.BulkJobUpdate):
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

@router.get("/jobs/{job_id}/history", response_model=List[schemas.ProcessExecutionLogInfo], tags=["Job Details"])
def get_job_execution_history(job_id: str, db: Session = Depends(get_db)):
    try:
        return service.get_job_execution_history(db, job_id=job_id)
    except Exception as e:
        logger.error(f"Error fetching job execution history for job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch job execution history")




@router.get("/jobs_yaml", tags=["Configuration"])
def get_jobs_yaml_content():
    try:
        content = config_util.read_jobs_yaml_content()
        return {"content": content}
    except FileNotFoundError as e:
        logger.error(f"Error reading jobs.yaml: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error reading jobs.yaml: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to read jobs.yaml")

@router.get("/settings/notifications", tags=["Settings"])
def get_notification_settings():
    try:
        settings = config_util.get_notification_settings()
        return settings
    except IOError as e:
        logger.error(f"Error reading notification settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to read notification settings: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while reading notification settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while reading notification settings.")

@router.post("/settings/notifications", tags=["Settings"])
def update_notification_settings(email_recipients: str = "", webhook_url: str = ""):
    settings = {
        "email_recipients": email_recipients,
        "webhook_url": webhook_url
    }
    try:
        config_util.update_notification_settings(settings)
        return {"message": "Notification settings updated successfully."}
    except IOError as e:
        logger.error(f"Error writing notification settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update notification settings: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while writing notification settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while updating notification settings.")
