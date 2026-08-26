from datetime import datetime, timedelta, timezone
import importlib
import inspect
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from apscheduler.jobstores.base import JobLookupError
from sqlalchemy.orm import Session, joinedload

from core.crud import CRUDBase
from util import logger_util
from util.config_util import config

from . import models, scheduler_instance, schemas

logger = logger_util.get_logger(__name__)


class JobDefinitionCRUD(CRUDBase[models.JobDefinition, schemas.JobCreate, schemas.JobUpdate]):
    pass


job_definition_service = JobDefinitionCRUD(models.JobDefinition)


class WorkflowCRUD(CRUDBase[models.Workflow, schemas.WorkflowCreate, schemas.Workflow]):
    def get_by_name(self, db: Session, *, name: str) -> Optional[models.Workflow]:
        return db.query(self.model).filter(self.model.name == name).first()

    def create_with_steps(self, db: Session, *, obj_in: schemas.WorkflowCreate) -> models.Workflow:
        """
        Create a new workflow and its associated steps.
        """
        workflow_data = obj_in.model_dump(exclude={"steps"})
        db_workflow = self.model(**workflow_data)
        db.add(db_workflow)
        db.commit()
        db.refresh(db_workflow)

        for step_in in obj_in.steps:
            # Extract task_parameters from the Pydantic schema
            task_parameters_data = step_in.task_parameters.model_dump()

            step_data = step_in.model_dump(exclude={"task_parameters"})
            # Add the task_parameters dictionary to the step_data
            step_data["task_parameters"] = task_parameters_data

            db_step = models.WorkflowStep(**step_data, workflow_id=db_workflow.id)
            db.add(db_step)

        db.commit()
        db.refresh(db_workflow)
        return db_workflow

    def update_with_steps(
        self, db: Session, *, db_obj: models.Workflow, obj_in: schemas.WorkflowCreate
    ) -> models.Workflow:
        """
        Update a workflow and its steps.
        """
        # Update workflow fields
        if obj_in.name != db_obj.name:
            existing = self.get_by_name(db, name=obj_in.name)
            if existing and existing.id != db_obj.id:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=409, detail=f"Workflow with name '{obj_in.name}' already exists."
                )
            db_obj.name = obj_in.name

        update_data = obj_in.model_dump(exclude={"steps", "name"})
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        # Delete old steps
        for step in db_obj.steps:
            db.delete(step)

        # Create new steps
        for step_in in obj_in.steps:
            # Extract task_parameters from the Pydantic schema
            task_parameters_data = step_in.task_parameters.model_dump()

            step_data = step_in.model_dump(exclude={"task_parameters"})
            # Add the task_parameters dictionary to the step_data
            step_data["task_parameters"] = task_parameters_data

            db_step = models.WorkflowStep(**step_data, workflow_id=db_obj.id)
            db.add(db_step)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, id: int) -> Optional[models.Workflow]:
        """
        Get a workflow by ID, including its steps.
        """
        # steps と runs を結合ロードするように修正
        return (
            db.query(self.model)
            .options(joinedload(self.model.steps), joinedload(self.model.runs))
            .filter(self.model.id == id)
            .first()
        )


workflow_service = WorkflowCRUD(models.Workflow)


def create_job_from_schema(db: Session, *, job_in: schemas.JobCreate) -> Optional[models.JobDefinition]:
    """
    Creates a JobDefinition in the database from the new JobCreate Pydantic schema.
    """
    # Check for ID conflict if an ID is provided
    if hasattr(job_in, "id") and job_in.id and job_definition_service.get(db, id=job_in.id):
        logger.warning(f"Job with ID '{job_in.id}' already exists.")
        return None

    # Separate trigger and task parameter models
    trigger_dict = job_in.trigger.model_dump()
    trigger_type = trigger_dict.pop("type")

    task_params_dict = job_in.task_parameters.model_dump()
    task_type = task_params_dict.pop("task_type")

    # Generate a unique ID for the job if not provided
    job_id = getattr(job_in, "id", None) or uuid.uuid4().hex[:12]

    db_obj = models.JobDefinition(
        id=job_id,
        name=job_in.name,
        description=job_in.description,
        is_enabled=job_in.is_enabled,
        task_type=task_type,
        task_parameters=task_params_dict,
        trigger_type=trigger_type,
        trigger_config=trigger_dict,
        max_instances=job_in.max_instances,
        coalesce=job_in.coalesce,
        misfire_grace_time=job_in.misfire_grace_time,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_job_from_schema(
    db: Session, *, db_obj: models.JobDefinition, job_in: schemas.JobUpdate
) -> models.JobDefinition:
    """
    Updates a JobDefinition in the database from the new JobUpdate Pydantic schema.
    """
    update_data = job_in.model_dump(exclude_unset=True)

    if "trigger" in update_data and update_data["trigger"] is not None:
        trigger_dict = update_data.pop("trigger")
        db_obj.trigger_type = trigger_dict.get("type")
        trigger_dict.pop("type", None)
        db_obj.trigger_config = trigger_dict

    if "task_parameters" in update_data and update_data["task_parameters"] is not None:
        task_params_dict = update_data.pop("task_parameters")
        db_obj.task_type = task_params_dict.get("task_type")
        task_params_dict.pop("task_type", None)
        db_obj.task_parameters = task_params_dict

    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_workflow_enabled_status(db: Session, workflow_id: int, is_enabled: bool) -> Optional[models.Workflow]:
    """
    Updates the is_enabled status of a workflow.
    """
    workflow = workflow_service.get(db, id=workflow_id)
    if workflow:
        workflow.is_enabled = is_enabled
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
    return workflow


def get_dashboard_summary(db: Session) -> schemas.DashboardSummary:
    """
    Retrieves a summary of job statuses for the dashboard.
    """
    total_job_defs = db.query(models.JobDefinition).count()
    total_workflows = db.query(models.Workflow).count()
    total_jobs = total_job_defs + total_workflows

    running_jobs = db.query(models.ProcessExecutionLog).filter(models.ProcessExecutionLog.status == "RUNNING").count()
    successful_runs = (
        db.query(models.ProcessExecutionLog).filter(models.ProcessExecutionLog.status == "COMPLETED").count()
    )
    failed_runs = db.query(models.ProcessExecutionLog).filter(models.ProcessExecutionLog.status == "FAILED").count()
    return schemas.DashboardSummary(
        total_jobs=total_jobs, running_jobs=running_jobs, successful_runs=successful_runs, failed_runs=failed_runs
    )


def get_timeline_data(db: Session) -> List[schemas.TimelineItem]:
    """
    Provides data for the job execution timeline.
    - Scheduled jobs and workflows are shown as points.
    - Executed workflow runs are shown as single ranges.
    - Executed regular jobs (not part of a workflow) are shown as ranges.
    - Individual workflow steps are NOT shown.
    """

    def _make_aware(dt: Optional[datetime]) -> Optional[datetime]:
        if dt and dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _make_aware_required(dt: Optional[datetime]) -> datetime:
        """start_time等、DBのserver_defaultにより常に値が入る前提のカラム用。"""
        aware = _make_aware(dt)
        if aware is None:
            raise ValueError("Expected a non-null datetime value.")
        return aware

    timeline_items: List[schemas.TimelineItem] = []
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    # Part 1: Scheduled Jobs & Workflows
    workflows_by_id = {wf.id: wf for wf in db.query(models.Workflow).all()}
    scheduled_jobs = scheduler_instance.scheduler.get_jobs()
    for job in scheduled_jobs:
        if job.next_run_time:
            start_time_aware = _make_aware_required(job.next_run_time)
            content = job.id
            group = job.id
            item_id = f"scheduled-{job.id}"

            if job.id.startswith("workflow_"):
                try:
                    workflow_id = int(job.id.split("_")[1])
                    workflow = workflows_by_id.get(workflow_id)
                    if workflow:
                        content = workflow.name
                        group = f"workflow_{workflow.id}"
                except (IndexError, ValueError):
                    pass

            timeline_items.append(
                schemas.TimelineItem(
                    id=f"{item_id}-{start_time_aware.isoformat()}",
                    content=f"{content} (Scheduled)",
                    start=start_time_aware,
                    status="scheduled",
                    group=group,
                )
            )

    # Part 2: Executed Workflow Runs
    recent_workflow_runs = (
        db.query(models.WorkflowRun)
        .options(joinedload(models.WorkflowRun.workflow))
        .filter(models.WorkflowRun.start_time >= seven_days_ago)
        .all()
    )

    for run in recent_workflow_runs:
        timeline_items.append(
            schemas.TimelineItem(
                id=f"wf_run-{run.id}",
                content=run.workflow.name if run.workflow else f"Workflow {run.workflow_id} (deleted)",
                start=_make_aware_required(run.start_time),
                end=_make_aware(run.end_time) or (now if run.status == "RUNNING" else None),
                status=run.status.lower(),
                group=f"workflow_{run.workflow_id}",
            )
        )

    # Part 3: Executed Regular Jobs (non-workflow)
    recent_job_logs = (
        db.query(models.ProcessExecutionLog)
        .filter(
            models.ProcessExecutionLog.workflow_run_id.is_(None),
            models.ProcessExecutionLog.start_time >= seven_days_ago,
        )
        .all()
    )

    for log in recent_job_logs:
        # Redundant check to ensure steps are not shown, in case of data inconsistency
        if log.job_id and "_step_" in log.job_id:
            continue
        timeline_items.append(
            schemas.TimelineItem(
                id=f"log-{log.id}",
                content=log.job_id or f"log-{log.id}",
                start=_make_aware_required(log.start_time),
                end=_make_aware(log.end_time) or (now if log.status == "RUNNING" else None),
                status=log.status.lower(),
                group=log.job_id,
            )
        )

    timeline_items.sort(key=lambda item: item.start)
    return timeline_items


def get_execution_logs(db: Session, skip: int = 0, limit: int = 100) -> List[models.ProcessExecutionLog]:
    """
    Retrieves a paginated list of job execution logs.
    """
    return (
        db.query(models.ProcessExecutionLog)
        .order_by(models.ProcessExecutionLog.start_time.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_job_execution_history(db: Session, job_id: str) -> List[models.ProcessExecutionLog]:
    """
    Retrieves the execution history for a specific job.
    """
    return (
        db.query(models.ProcessExecutionLog)
        .filter(models.ProcessExecutionLog.job_id == job_id)
        .order_by(models.ProcessExecutionLog.start_time.desc())
        .all()
    )


def get_scheduled_jobs_info(db: Session) -> List[schemas.Job]:
    """
    Retrieves a list of currently scheduled jobs, combining scheduler info
    with database definitions to return the full `schemas.Job` model.
    """
    scheduled_jobs = scheduler_instance.scheduler.get_jobs()
    job_ids = [job.id for job in scheduled_jobs if not job.id.startswith("workflow_")]

    if not job_ids:
        return []

    # Fetch corresponding job definitions from the database
    job_defs = db.query(models.JobDefinition).filter(models.JobDefinition.id.in_(job_ids)).all()
    job_defs_map = {job_def.id: job_def for job_def in job_defs}

    job_infos = []
    for job in scheduled_jobs:
        if job.id in job_defs_map:
            db_job = job_defs_map[job.id]

            # Use the Pydantic model's validator to construct the base object
            # The validator `assemble_from_db_model` in `schemas.py` handles the transformation
            job_model = schemas.Job.model_validate(db_job)

            # Add the dynamic next_run_time from the scheduler
            job_model.next_run_time = job.next_run_time

            job_infos.append(job_model)

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


def pause_bulk_scheduled_jobs(job_ids: List[str]) -> Dict[str, Any]:
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


def resume_bulk_scheduled_jobs(job_ids: List[str]) -> Dict[str, Any]:
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
    # config.resolve_sandboxed_path が resolve() 後に work_dir 配下であることを
    # 検証するため、'..' の文字列チェックだけでなく Windows のドライブ相対パス
    # (例: 'D:temp') によるサンドボックス回避も防げる。
    scan_path = config.resolve_sandboxed_path(relative_path)

    if scan_path is None:
        return []

    if not scan_path.is_dir():
        return []

    try:
        return [entry.name for entry in os.scandir(scan_path) if entry.is_dir()]
    except OSError:
        return []


def get_unified_jobs_list(db: Session) -> List[schemas.UnifiedJobItem]:
    """
    Retrieves a unified list of all jobs and workflows for dashboard display.
    """
    unified_list = []

    # Get all scheduled jobs from APScheduler
    scheduled_jobs = {job.id: job for job in scheduler_instance.scheduler.get_jobs()}

    # 1. Process Job Definitions
    jobs_in_db = db.query(models.JobDefinition).all()
    for job_def in jobs_in_db:
        job_id = job_def.id
        status = "disabled"  # Default to disabled
        next_run = None

        if job_def.is_enabled:
            # Only if the job is enabled in the DB can it have an active status
            if job_id in scheduled_jobs:
                scheduled_job = scheduled_jobs[job_id]
                next_run = scheduled_job.next_run_time
                status = "paused" if scheduled_job.next_run_time is None else "enabled"
            else:
                # If it's enabled in DB but not in scheduler, it's effectively disabled
                # from a control perspective.
                status = "disabled"

        trigger_str = f"{job_def.trigger_type}: "
        if job_def.trigger_type == "cron":
            cron_fields = ["minute", "hour", "day", "month", "day_of_week"]
            parts = []
            for field in cron_fields:
                value = job_def.trigger_config.get(field)
                parts.append(str(value) if value is not None else "*")
            trigger_str += " ".join(parts)
        elif job_def.trigger_type == "interval":
            parts = []
            for unit in ["weeks", "days", "hours", "minutes", "seconds"]:
                if job_def.trigger_config.get(unit, 0) > 0:
                    parts.append(f"{job_def.trigger_config[unit]}{unit[0]}")
            trigger_str += " ".join(parts)

        unified_list.append(
            schemas.UnifiedJobItem(
                id=job_id,
                type="job",
                name=job_def.name or job_def.id,
                description=job_def.description,
                is_enabled=job_def.is_enabled,
                schedule=trigger_str,
                next_run_time=next_run,
                status=status,
            )
        )

    # 2. Process Workflows
    workflows_in_db = db.query(models.Workflow).all()
    for workflow in workflows_in_db:
        job_id = f"workflow_{workflow.id}"
        status = "disabled"  # Default to disabled
        next_run = None

        if workflow.is_enabled:
            # Only if the workflow is enabled in the DB can it have an active status
            if job_id in scheduled_jobs:
                scheduled_job = scheduled_jobs[job_id]
                next_run = scheduled_job.next_run_time
                status = "paused" if scheduled_job.next_run_time is None else "enabled"
            else:
                # If enabled in DB but not scheduled (e.g. no cron string), it's effectively disabled.
                status = "disabled"

        unified_list.append(
            schemas.UnifiedJobItem(
                id=str(workflow.id),
                type="workflow",
                name=workflow.name,
                description=workflow.description,
                is_enabled=workflow.is_enabled,
                schedule=workflow.schedule or "Not Scheduled",
                next_run_time=next_run,
                status=status,
            )
        )

    return unified_list


def run_workflow_immediately(db: Session, workflow_id: int) -> Dict[str, str]:
    """
    Schedules a one-off, immediate execution of a workflow.
    """
    scheduler_instance.scheduler.add_job(
        "modules.scheduler.job_executors:run_workflow", kwargs={"workflow_id": workflow_id}
    )
    return {"message": "Workflow scheduled for immediate execution."}


def get_available_tasks() -> List[schemas.AvailableTask]:
    """
    Scans for available tasks and returns a structured list with their parameters,
    controlled by decorators and application configuration.
    """
    logger.info("--- Starting task discovery ---")
    tasks: List[schemas.AvailableTask] = []

    # Part 1: Discover Python tasks from the 'tasks' directory
    try:
        tasks_dir = Path(__file__).parent.joinpath("tasks")
        logger.info(f"Scanning for Python tasks in: {tasks_dir}")

        found_files = list(tasks_dir.glob("*.py"))
        logger.info(f"Found {len(found_files)} Python files to inspect: {[f.name for f in found_files]}")

        for file_path in found_files:
            if file_path.name.startswith("__"):
                logger.info(f"Skipping file: {file_path.name}")
                continue

            module_name = f"modules.scheduler.tasks.{file_path.stem}"
            logger.info(f"Inspecting module: {module_name}")
            try:
                module = importlib.import_module(module_name)
                for name, func in inspect.getmembers(module, inspect.isfunction):
                    if not hasattr(func, "_task_meta"):
                        continue

                    logger.info(f"Found potential task '{name}' in {module_name}")
                    meta = func._task_meta
                    if not meta.get("enabled", False):
                        logger.warning(f"Task '{name}' is defined but not enabled. Skipping.")
                        continue

                    sig = inspect.signature(func)
                    docstring = inspect.getdoc(func) or ""

                    description = meta.get("description") or (docstring.strip().splitlines()[0] if docstring else "")
                    display_name = meta.get("name") or name.replace("_", " ").title()

                    parameters = []
                    for param in sig.parameters.values():
                        if param.name in ("self", "cls", "db", "db_session", "job_id", "workflow_run_id", "kwargs"):
                            continue

                        param_type = "Any"
                        if param.annotation is not inspect.Parameter.empty:
                            # Heuristic to differentiate between standard types (int, str) and
                            # typing types (List, Literal)
                            if hasattr(param.annotation, "__origin__"):  # Catches List, Dict, Literal, Union etc.
                                param_type_str = str(param.annotation).replace("typing.", "")
                                if "Union[" in param_type_str and "NoneType" in param_type_str:
                                    main_type = param_type_str.replace("Union[", "").replace(", NoneType]", "")
                                    param_type_str = f"Optional[{main_type}]"
                                param_type = param_type_str
                            else:  # Likely a primitive type
                                param_type = param.annotation.__name__

                        parameters.append(
                            schemas.AvailableTaskParameter(
                                name=param.name,
                                type=param_type,
                                required=param.default is inspect.Parameter.empty,
                                label=param.name.replace("_", " ").title(),
                            )
                        )

                    task_id = f"python:{module_name}:{name}"
                    tasks.append(
                        schemas.AvailableTask(
                            id=task_id,
                            name=display_name,
                            task_type="python",
                            module=module_name,
                            function=name,
                            description=description,
                            parameters=parameters,
                        )
                    )
                    logger.info(f"Successfully added task '{display_name}' with id '{task_id}'")

            except Exception as e:
                logger.error(f"Error inspecting module {module_name} for tasks: {e}", exc_info=True)
        logger.info("--- Finished Python task discovery ---")
    except Exception as e:
        logger.critical(f"A critical error occurred during Python task discovery phase: {e}", exc_info=True)

    # Part 2: Add built-in tasks based on UI configuration
    try:
        logger.info("--- Discovering built-in tasks from config ---")
        ui_config = config.task_ui_config

        # Shell Task
        logger.info("Processing Shell task from config...")
        shell_config = ui_config.get("shell", {})
        if shell_config.get("enabled", False):
            shell_params = [schemas.AvailableTaskParameter(**param) for param in shell_config.get("parameters", [])]
            tasks.append(
                schemas.AvailableTask(
                    id="shell",
                    name="Shell Command",
                    task_type="shell",
                    description="Executes a shell command or script.",
                    parameters=shell_params,
                )
            )
            logger.info("Successfully added Shell task.")
        else:
            logger.warning("Shell task is disabled in config.")

        # Email Task
        logger.info("Processing Email task from config...")
        email_config = ui_config.get("email", {})
        if email_config.get("enabled", False):
            email_params = [schemas.AvailableTaskParameter(**param) for param in email_config.get("parameters", [])]
            tasks.append(
                schemas.AvailableTask(
                    id="email",
                    name="Send Email",
                    task_type="email",
                    description="Sends an email notification.",
                    parameters=email_params,
                )
            )
            logger.info("Successfully added Email task.")
        else:
            logger.warning("Email task is disabled in config.")
        logger.info("--- Finished built-in task discovery ---")
    except Exception as e:
        logger.critical(f"A critical error occurred during built-in task discovery phase: {e}", exc_info=True)

    logger.info(f"--- Task discovery finished. Total tasks found: {len(tasks)} ---")

    try:
        sorted_tasks = sorted(tasks, key=lambda t: t.name)
        logger.info(f"Final task list: {[t.name for t in sorted_tasks]}")
        return sorted_tasks
    except Exception as e:
        logger.critical(f"A critical error occurred during final task sorting: {e}", exc_info=True)
        # Return unsorted if sorting fails, to still provide tasks to the user
        return tasks
