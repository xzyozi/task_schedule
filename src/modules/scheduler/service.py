import os
from pathlib import Path
from sqlalchemy.orm import Session, joinedload
from core.crud import CRUDBase
from . import models, schemas, scheduler_instance
from typing import List, Dict
from datetime import datetime, timedelta, timezone
from util import logger_util
from util.config_util import config
from apscheduler.jobstores.base import JobLookupError

logger = logger_util.get_logger(__name__)

class JobDefinitionCRUD(CRUDBase[models.JobDefinition, schemas.JobConfig, schemas.JobConfig]):
    def create_from_config(self, db: Session, *, job_in: schemas.JobConfig) -> models.JobDefinition:
        """
        Creates a JobDefinition in the database from a JobConfig Pydantic schema.
        """
        trigger_dict = job_in.trigger.model_dump()
        trigger_type = trigger_dict.pop('type')
        
        db_obj = self.model(
            id=job_in.id,
            func=job_in.func,
            description=job_in.description,
            is_enabled=job_in.is_enabled,
            job_type=job_in.job_type,
            trigger_type=trigger_type,
            trigger_config=trigger_dict,
            args=job_in.args,
            kwargs=job_in.kwargs,
            cwd=job_in.cwd,
            env=job_in.env,
            max_instances=job_in.max_instances,
            coalesce=job_in.coalesce,
            misfire_grace_time=job_in.misfire_grace_time,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_from_config(self, db: Session, *, db_obj: models.JobDefinition, job_in: schemas.JobConfig) -> models.JobDefinition:
        """
        Updates a JobDefinition in the database from a JobConfig Pydantic schema.
        """
        update_data = job_in.model_dump(exclude_unset=True, exclude={'id'})

        if 'trigger' in update_data:
            trigger_dict = update_data.pop('trigger')
            db_obj.trigger_type = trigger_dict.get('type')
            trigger_dict.pop('type', None)
            db_obj.trigger_config = trigger_dict
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

job_definition_service = JobDefinitionCRUD(models.JobDefinition)

class WorkflowCRUD(CRUDBase[models.Workflow, schemas.WorkflowCreate, schemas.Workflow]):
    def create_with_steps(self, db: Session, *, obj_in: schemas.WorkflowCreate) -> models.Workflow:
        """
        Create a new workflow and its associated steps.
        """
        workflow_data = obj_in.model_dump(exclude={'steps'})
        db_workflow = self.model(**workflow_data)
        db.add(db_workflow)
        db.commit()
        db.refresh(db_workflow)

        for step_in in obj_in.steps:
            step_data = step_in.model_dump()
            db_step = models.WorkflowStep(**step_data, workflow_id=db_workflow.id)
            db.add(db_step)
        
        db.commit()
        db.refresh(db_workflow)
        return db_workflow

    def update_with_steps(self, db: Session, *, db_obj: models.Workflow, obj_in: schemas.WorkflowCreate) -> models.Workflow:
        """
        Update a workflow and its steps.
        """
        # Update workflow fields
        update_data = obj_in.model_dump(exclude={'steps', 'name'}) # name is not updatable
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        # Delete old steps
        for step in db_obj.steps:
            db.delete(step)
        
        # Create new steps
        for step_in in obj_in.steps:
            step_data = step_in.model_dump()
            db_step = models.WorkflowStep(**step_data, workflow_id=db_obj.id)
            db.add(db_step)
            
        db.commit()
        db.refresh(db_obj)
        return db_obj

workflow_service = WorkflowCRUD(models.Workflow)

def get_dashboard_summary(db: Session) -> schemas.DashboardSummary:
    """
    Retrieves a summary of job statuses for the dashboard.
    """
    total_jobs = len(scheduler_instance.scheduler.get_jobs())
    running_jobs = db.query(models.ProcessExecutionLog).filter(models.ProcessExecutionLog.status == 'RUNNING').count()
    successful_runs = db.query(models.ProcessExecutionLog).filter(models.ProcessExecutionLog.status == 'COMPLETED').count()
    failed_runs = db.query(models.ProcessExecutionLog).filter(models.ProcessExecutionLog.status == 'FAILED').count()
    return schemas.DashboardSummary(
        total_jobs=total_jobs,
        running_jobs=running_jobs,
        successful_runs=successful_runs,
        failed_runs=failed_runs
    )

def get_timeline_data(db: Session) -> List[schemas.TimelineItem]:
    """
    Provides data for the job execution timeline, including scheduled and historical runs.
    """
    timeline_items: List[schemas.TimelineItem] = []
    workflows_by_id = {wf.id: wf for wf in db.query(models.Workflow).all()}
    
    scheduled_jobs = scheduler_instance.scheduler.get_jobs()
    for job in scheduled_jobs:
        if job.next_run_time:
            start_time_aware = job.next_run_time.replace(tzinfo=timezone.utc) if job.next_run_time.tzinfo is None else job.next_run_time
            
            content = job.id
            group = job.id

            if job.id.startswith('workflow_'):
                try:
                    workflow_id = int(job.id.split('_')[1])
                    workflow = workflows_by_id.get(workflow_id)
                    if workflow:
                        content = workflow.name
                        group = f"workflow_{workflow.id}"
                except (IndexError, ValueError):
                    pass # Keep default content if parsing fails
            
            timeline_items.append(schemas.TimelineItem(
                id=f"scheduled-{job.id}-{start_time_aware.isoformat()}",
                content=f"{content} (Scheduled)", start=start_time_aware, status="scheduled", group=group
            ))

    # Eagerly load related data to avoid N+1 query problem.
    recent_logs = (db.query(models.ProcessExecutionLog)
        .options(joinedload(models.ProcessExecutionLog.workflow_run).joinedload(models.WorkflowRun.workflow).joinedload(models.Workflow.steps))
        .filter(models.ProcessExecutionLog.start_time >= datetime.now(timezone.utc) - timedelta(days=7))
        .order_by(models.ProcessExecutionLog.start_time.asc()).all())

    for log in recent_logs:
        item_status = log.status.lower()
        start = log.start_time.replace(tzinfo=timezone.utc) if log.start_time.tzinfo is None else log.start_time
        end = None
        if log.end_time:
            end = log.end_time.replace(tzinfo=timezone.utc) if log.end_time.tzinfo is None else log.end_time
        elif item_status == 'running':
            end = datetime.now(timezone.utc)
        
        content = log.job_id
        group = log.job_id
        if log.workflow_run_id and log.workflow_run and log.workflow_run.workflow:
            group = f"workflow_{log.workflow_run.workflow.id}"
            try:
                # The job_id for a workflow step is synthetic, e.g., "workflow_1_step_2"
                # We parse it to find the step details.
                step_id_str = log.job_id.split('_step_')[-1]
                step_id = int(step_id_str)
                step = next((s for s in log.workflow_run.workflow.steps if s.id == step_id), None)
                if step:
                    content = f"{log.workflow_run.workflow.name}.{step.name}"
                else:
                    # Fallback if step not found (should not happen)
                    content = f"{log.workflow_run.workflow.name}.?"
            except (IndexError, ValueError):
                 content = f"WF Run #{log.workflow_run_id}" # Fallback

        timeline_items.append(schemas.TimelineItem(
            id=f"log-{log.id}", content=content,
            start=start, end=end, status=item_status, group=group
        ))

    timeline_items.sort(key=lambda item: item.start)
    return timeline_items


def get_execution_logs(db: Session, skip: int = 0, limit: int = 100) -> List[models.ProcessExecutionLog]:
    """
    Retrieves a paginated list of job execution logs.
    """
    return db.query(models.ProcessExecutionLog).order_by(models.ProcessExecutionLog.start_time.desc()).offset(skip).limit(limit).all()

def get_job_execution_history(db: Session, job_id: str) -> List[models.ProcessExecutionLog]:
    """
    Retrieves the execution history for a specific job.
    """
    return db.query(models.ProcessExecutionLog).filter(models.ProcessExecutionLog.job_id == job_id).order_by(models.ProcessExecutionLog.start_time.desc()).all()

def get_scheduled_jobs_info() -> List[schemas.JobInfo]:
    """
    Retrieves a list of currently scheduled jobs with formatted trigger information.
    """
    jobs = scheduler_instance.scheduler.get_jobs()
    job_infos = []
    for job in jobs:
        if job.id.startswith('workflow_'):
            continue
        try:
            trigger_dict = {"type": "unknown"}
            trigger_class_name = job.trigger.__class__.__name__.lower()
            if "cron" in trigger_class_name:
                trigger_dict["type"] = "cron"
                for field in job.trigger.fields:
                    trigger_dict[field.name] = str(field)
            elif "interval" in trigger_class_name:
                trigger_dict["type"] = "interval"
                td = job.trigger.interval
                trigger_dict['weeks'] = td.days // 7
                trigger_dict['days'] = td.days % 7
                trigger_dict['hours'] = td.seconds // 3600
                trigger_dict['minutes'] = (td.seconds // 60) % 60
                trigger_dict['seconds'] = td.seconds % 60
            func_repr = job.func
            if not isinstance(func_repr, str):
                func_repr = f"{job.func.__module__}:{job.func.__name__}"
            job_info = schemas.JobInfo(
                id=job.id, func=func_repr, trigger=trigger_dict, args=list(job.args),
                kwargs=job.kwargs, max_instances=job.max_instances, coalesce=job.coalesce,
                misfire_grace_time=job.misfire_grace_time, next_run_time=job.next_run_time
            )
            job_infos.append(job_info)
        except Exception as e:
            logger.error(f"Error processing job '{job.id}' for API response: {e}", exc_info=True)
    return job_infos

def delete_bulk_jobs(db: Session, job_ids: List[str]) -> int:
    """
    Deletes a list of job definitions from the database.
    Returns the number of jobs successfully deleted.
    """
    deleted_count = 0
    for job_id in job_ids:
        if job_definition_service.remove(db, id=job_id):
            deleted_count += 1
    return deleted_count

def pause_bulk_scheduled_jobs(job_ids: List[str]) -> Dict[str, list]:
    """
    Pauses a list of scheduled jobs.
    Returns a dictionary with lists of successfully paused and failed job IDs.
    """
    paused_ids = []
    failed_ids = {}
    for job_id in job_ids:
        try:
            scheduler_instance.scheduler.pause_job(job_id)
            paused_ids.append(job_id)
        except JobLookupError:
            failed_ids[job_id] = "Not Found"
    return {"paused": paused_ids, "failed": failed_ids}


def resume_bulk_scheduled_jobs(job_ids: List[str]) -> Dict[str, list]:
    """
    Resumes a list of scheduled jobs.
    Returns a dictionary with lists of successfully resumed and failed job IDs.
    """
    resumed_ids = []
    failed_ids = {}
    for job_id in job_ids:
        try:
            scheduler_instance.scheduler.resume_job(job_id)
            resumed_ids.append(job_id)
        except JobLookupError:
            failed_ids[job_id] = "Not Found"
    return {"resumed": resumed_ids, "failed": failed_ids}

def list_subdirectories(relative_path: str = "") -> List[str]:
    """
    Lists subdirectories within the scheduler's work_dir for autocompletion.
    """
    work_dir = config.scheduler_work_dir
    
    # Prevent directory traversal attacks
    if ".." in relative_path:
        return []

    scan_path = work_dir.joinpath(relative_path).resolve()

    # Security check: ensure the path to scan is within the work_dir sandbox
    if work_dir not in scan_path.parents and scan_path != work_dir:
        return []

    if not scan_path.is_dir():
        return []

    try:
        return [entry.name for entry in os.scandir(scan_path) if entry.is_dir()]
    except OSError:
        return []