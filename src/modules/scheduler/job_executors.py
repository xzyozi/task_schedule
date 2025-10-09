import os
import re
import subprocess
import traceback
import json
import base64
import sys
import uuid
import shlex
from pathlib import Path
from typing import Dict, Any, Optional

from pydantic import ValidationError
from sqlalchemy.orm import Session

from util import logger_util, time_util
from util.config_util import config
from core import database
from . import models, schemas
from .tasks import email_tasks

logger = logger_util.get_logger(__name__)

# --- Utility Functions ---

def _log_job_start(db: Session, job_id: str, command: str, workflow_run_id: Optional[int] = None) -> models.ProcessExecutionLog:
    """Creates and returns a new log entry for a job start."""
    log_entry = models.ProcessExecutionLog(
        id=str(uuid.uuid4()),
        job_id=job_id,
        workflow_run_id=workflow_run_id,
        command=command,
        start_time=time_util.get_current_utc_time(),
        status='RUNNING'
    )
    db.add(log_entry)
    db.flush()
    return log_entry

def _log_job_end(log_entry: models.ProcessExecutionLog, exit_code: int, stdout: str = "", stderr: str = ""):
    """Updates a log entry with the job's final status and output."""
    log_entry.end_time = time_util.get_current_utc_time()
    log_entry.exit_code = exit_code
    log_entry.stdout = stdout
    log_entry.stderr = stderr
    log_entry.status = 'COMPLETED' if exit_code == 0 else 'FAILED'

def _execute_subprocess(
    command_to_run: list,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    run_in_background: bool = False
) -> Dict[str, Any]:
    """Executes a command in a subprocess, handling path resolution and logging."""
    log_command = ' '.join(command_to_run)
    
    absolute_cwd = None
    if cwd:
        absolute_cwd = config.scheduler_work_dir.joinpath(cwd).resolve()
        absolute_cwd.mkdir(parents=True, exist_ok=True)

    logger.info(f"Executing: {log_command}" + (f" in {absolute_cwd}" if absolute_cwd else ""))

    try:
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        if run_in_background:
            logger.info(f"Executing in background: {log_command}")
            subprocess.Popen(command_to_run, shell=False, cwd=absolute_cwd, env=process_env)
            return {"stdout": "Process launched in background.", "stderr": "", "exit_code": 0}
        
        process = subprocess.run(
            command_to_run, capture_output=True, text=True, check=False, shell=False, cwd=absolute_cwd, env=process_env
        )
        stdout = process.stdout.strip()
        stderr = process.stderr.strip()
        exit_code = process.returncode
        
        if exit_code != 0:
            logger.error(f"Command '{log_command}' failed with exit code {exit_code}.\nCWD: {absolute_cwd}\nSTDOUT: {stdout}\nSTDERR: {stderr}")
        else:
            logger.info(f"Command '{log_command}' completed successfully.\nSTDOUT: {stdout}")
            
        return {"stdout": stdout, "stderr": stderr, "exit_code": exit_code}

    except FileNotFoundError:
        cmd_name = command_to_run[0]
        logger.error(f"Command not found: {cmd_name}", exc_info=True)
        return {"stdout": "", "stderr": f"Command not found: {cmd_name}", "exit_code": 127}
    except Exception as e:
        logger.error(f"Error executing command '{log_command}': {e}", exc_info=True)
        return {"stdout": "", "stderr": str(e), "exit_code": 1}

# --- New Job Executors ---

def execute_shell_job(job_id: str, task_params: dict):
    db = next(database.get_db())
    log_entry = None
    try:
        params = schemas.ShellJobParams.model_validate(task_params)
        log_entry = _log_job_start(db, job_id, params.command)
        
        command_list = shlex.split(params.command)

        result = _execute_subprocess(
            command_to_run=command_list,
            cwd=params.cwd,
            env=params.env
        )
        _log_job_end(log_entry, **result)
        db.commit()
    except ValidationError as e:
        logger.error(f"Invalid parameters for shell job '{job_id}': {e}")
        if log_entry: _log_job_end(log_entry, exit_code=1, stderr=str(e))
        db.commit()
    except Exception as e:
        logger.error(f"Error in execute_shell_job for job '{job_id}': {e}", exc_info=True)
        if log_entry: _log_job_end(log_entry, exit_code=1, stderr=traceback.format_exc())
        db.commit()
    finally:
        db.close()

def execute_python_job(job_id: str, task_params: dict):
    db = next(database.get_db())
    log_entry = None
    try:
        params = schemas.PythonJobParams.model_validate(task_params)
        target_func_path = f"{params.module}:{params.function}"
        log_entry = _log_job_start(db, job_id, target_func_path)

        try:
            payload = json.dumps({'args': params.args, 'kwargs': params.kwargs})
            encoded_payload = base64.b64encode(payload.encode('utf-8')).decode('utf-8')
        except (TypeError, OverflowError) as e:
            err_msg = f"Failed to serialize arguments for Python job: {e}. Arguments must be JSON-serializable."
            _log_job_end(log_entry, exit_code=1, stderr=err_msg)
            db.commit()
            return

        wrapper_path = Path(__file__).parent.joinpath("python_job_wrapper.py")
        command_to_run = [
            sys.executable, 
            str(wrapper_path), 
            target_func_path, 
            encoded_payload
        ]

        result = _execute_subprocess(command_to_run=command_to_run)
        
        _log_job_end(log_entry, **result)
        db.commit()
    except ValidationError as e:
        logger.error(f"Invalid parameters for python job '{job_id}': {e}")
        if log_entry: _log_job_end(log_entry, exit_code=1, stderr=str(e))
        db.commit()
    except Exception as e:
        logger.error(f"Error in execute_python_job for job '{job_id}': {e}", exc_info=True)
        if log_entry: _log_job_end(log_entry, exit_code=1, stderr=traceback.format_exc())
        db.commit()
    finally:
        db.close()

def execute_email_job(job_id: str, task_params: dict):
    db = next(database.get_db())
    log_entry = None
    try:
        params = schemas.EmailJobParams.model_validate(task_params)
        log_command = f"send_email to:{params.to_email} subject:{params.subject}"
        log_entry = _log_job_start(db, job_id, log_command)
        
        try:
            email_kwargs = params.model_dump()
            email_kwargs.pop('task_type', None)
            email_kwargs['job_id'] = job_id
            email_tasks.send_email_task(**email_kwargs)
            _log_job_end(log_entry, exit_code=0, stdout="Email sent successfully.")
        except Exception as e:
            logger.error(f"Email sending failed for job '{job_id}': {e}", exc_info=True)
            _log_job_end(log_entry, exit_code=1, stderr=traceback.format_exc())
            
        db.commit()
    except ValidationError as e:
        logger.error(f"Invalid parameters for email job '{job_id}': {e}")
        if log_entry: _log_job_end(log_entry, exit_code=1, stderr=str(e))
        db.commit()
    except Exception as e:
        logger.error(f"Error in execute_email_job for job '{job_id}': {e}", exc_info=True)
        if log_entry: _log_job_end(log_entry, exit_code=1, stderr=traceback.format_exc())
        db.commit()
    finally:
        db.close()

# --- Workflow Executor (Updated) ---

def run_workflow(workflow_id: int, job_id: str = None, run_params: Optional[dict] = None):
    db = next(database.get_db())
    try:
        workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
        if not workflow:
            logger.error(f"Workflow with id {workflow_id} not found.")
            return

        workflow_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', workflow.name)
        base_dir = config.scheduler_work_dir
        workflow_cwd = base_dir.joinpath(workflow_name).resolve()
        workflow_cwd.mkdir(parents=True, exist_ok=True)
        logger.info(f"Working directory for workflow '{workflow_name}' is {workflow_cwd}")
        
        logger.info(f"Starting workflow '{workflow.name}' (ID: {workflow.id}) with params: {run_params}")
        workflow_run = models.WorkflowRun(
            workflow_id=workflow.id,
            status='RUNNING',
            params_val=run_params
        )
        db.add(workflow_run)
        db.commit()
        workflow_run_id = workflow_run.id
        steps = sorted(workflow.steps, key=lambda s: s.step_order)

    finally:
        db.close()

    final_status = 'COMPLETED'
    try:
        for i, step in enumerate(steps):
            logger.info(f"Executing step {i+1}/{len(steps)}: '{step.name}' for workflow '{workflow_name}'")
            
            step_job_id = f"{workflow_name}_{step.step_order}_{step.name}"
            
            substituted_target = step.target
            if run_params:
                substituted_target = re.sub(
                    r"{{\s*params\.([a-zA-Z0-9_]+)\s*}}",
                    lambda match: str(run_params.get(match.group(1), match.group(0))),
                    substituted_target
                )

            if step.job_type == 'python':
                module, function = substituted_target.split(':', 1)
                task_params = {
                    'task_type': 'python',
                    'module': module,
                    'function': function,
                    'args': step.args or [],
                    'kwargs': step.kwargs or {}
                }
                execute_python_job(job_id=step_job_id, task_params=task_params)

            elif step.job_type == 'shell':
                task_params = {
                    'task_type': 'shell',
                    'command': substituted_target,
                    'cwd': str(workflow_cwd.relative_to(config.scheduler_work_dir)),
                    'env': (step.kwargs or {}).get('env')
                }
                execute_shell_job(job_id=step_job_id, task_params=task_params)
            else:
                logger.error(f"Unknown step job_type: {step.job_type} for step '{step.name}'")
                continue

            temp_db = next(database.get_db())
            try:
                last_log = temp_db.query(models.ProcessExecutionLog).filter(
                    models.ProcessExecutionLog.job_id == step_job_id
                ).order_by(models.ProcessExecutionLog.start_time.desc()).first()

                if last_log and last_log.status == 'FAILED':
                    if step.on_failure == 'stop':
                        logger.error(f"Workflow '{workflow_name}' stopping due to failed step '{step.name}'.")
                        final_status = 'FAILED'
                        break
            finally:
                temp_db.close()
    
    except Exception as e:
        logger.error(f"An unhandled error occurred during workflow execution for '{workflow_name}': {e}", exc_info=True)
        final_status = 'FAILED'
    
    finally:
        final_db = next(database.get_db())
        try:
            workflow_run = final_db.query(models.WorkflowRun).filter(models.WorkflowRun.id == workflow_run_id).first()
            if workflow_run:
                workflow_run.status = final_status
                workflow_run.end_time = time_util.get_current_utc_time()
                final_db.commit()
            logger.info(f"Workflow '{workflow_name}' finished with status {final_status}.")
        finally:
            final_db.close()