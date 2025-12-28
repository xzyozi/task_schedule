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
from sqlalchemy.orm import Session, joinedload

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

def execute_shell_job(job_id: str, task_params: dict, db: Optional[Session] = None, workflow_run_id: Optional[int] = None) -> Dict[str, Any]:
    
    db_session = db if db else next(database.get_db())
    local_session = not db

    try:
        log_entry = None
        try:
            params = schemas.ShellJobParams.model_validate(task_params)
            log_entry = _log_job_start(db_session, job_id, params.command, workflow_run_id=workflow_run_id)
            
            command_list = shlex.split(params.command)

            result = _execute_subprocess(
                command_to_run=command_list,
                cwd=params.cwd,
                env=params.env
            )
            _log_job_end(log_entry, **result)
            db_session.commit()
            return result
        except ValidationError as e:
            logger.error(f"Invalid parameters for shell job '{job_id}': {e}")
            result = {"stdout": "", "stderr": str(e), "exit_code": 1, "return_value": None}
            if log_entry: _log_job_end(log_entry, **{k: v for k, v in result.items() if k != 'return_value'})
            db_session.commit()
            return result
        except Exception as e:
            logger.error(f"Error in execute_shell_job for job '{job_id}': {e}", exc_info=True)
            result = {"stdout": "", "stderr": traceback.format_exc(), "exit_code": 1, "return_value": None}
            if log_entry: _log_job_end(log_entry, **{k: v for k, v in result.items() if k != 'return_value'})
            db_session.commit()
            return result
    finally:
        if local_session:
            db_session.close()

def execute_python_job(job_id: str, task_params: dict, db: Optional[Session] = None, workflow_run_id: Optional[int] = None) -> Dict[str, Any]:
    
    db_session = db if db else next(database.get_db())
    local_session = not db

    try:
        log_entry = None
        try:
            params = schemas.PythonJobParams.model_validate(task_params)
            target_func_path = f"{params.module}:{params.function}"
            log_entry = _log_job_start(db_session, job_id, target_func_path, workflow_run_id=workflow_run_id)

            try:
                payload = json.dumps({'args': params.args, 'kwargs': params.kwargs})
                encoded_payload = base64.b64encode(payload.encode('utf-8')).decode('utf-8')
            except (TypeError, OverflowError) as e:
                err_msg = f"Failed to serialize arguments for Python job: {e}. Arguments must be JSON-serializable."
                result = {"stdout": "", "stderr": err_msg, "exit_code": 1, "return_value": None}
                if log_entry:
                    _log_job_end(log_entry, **{k: v for k, v in result.items() if k != 'return_value'})
                db_session.commit()
                return result

            wrapper_path = Path(__file__).parent.joinpath("python_job_wrapper.py")
            command_to_run = [
                sys.executable, 
                str(wrapper_path), 
                target_func_path, 
                encoded_payload
            ]

            result = _execute_subprocess(command_to_run=command_to_run)
            
            return_value = None
            if result["exit_code"] == 0 and result["stdout"]:
                try:
                    output_data = json.loads(result["stdout"])
                    return_value = output_data.get("return_value")
                except json.JSONDecodeError:
                    pass
            
            result["return_value"] = return_value
            
            _log_job_end(log_entry, **{k: v for k, v in result.items() if k != 'return_value'})
            db_session.commit()
            return result
            
        except ValidationError as e:
            logger.error(f"Invalid parameters for python job '{job_id}': {e}")
            result = {"stdout": "", "stderr": str(e), "exit_code": 1, "return_value": None}
            if log_entry: _log_job_end(log_entry, **{k: v for k, v in result.items() if k != 'return_value'})
            db_session.commit()
            return result
        except Exception as e:
            logger.error(f"Error in execute_python_job for job '{job_id}': {e}", exc_info=True)
            result = {"stdout": "", "stderr": traceback.format_exc(), "exit_code": 1, "return_value": None}
            if log_entry: _log_job_end(log_entry, **{k: v for k, v in result.items() if k != 'return_value'})
            db_session.commit()
            return result
    finally:
        if local_session:
            db_session.close()

def execute_email_job(job_id: str, task_params: dict, db: Optional[Session] = None, workflow_run_id: Optional[int] = None) -> Dict[str, Any]:

    db_session = db if db else next(database.get_db())
    local_session = not db

    try:
        log_entry = None
        try:
            params = schemas.EmailJobParams.model_validate(task_params)
            log_command = f"send_email to:{params.to_email} subject:{params.subject}"
            log_entry = _log_job_start(db_session, job_id, log_command, workflow_run_id=workflow_run_id)
            
            try:
                email_kwargs = params.model_dump()
                email_kwargs.pop('task_type', None)
                email_kwargs['job_id'] = job_id
                email_tasks.send_email_task(**email_kwargs)
                result = {"stdout": "Email sent successfully.", "stderr": "", "exit_code": 0, "return_value": None}
                _log_job_end(log_entry, **{k: v for k, v in result.items() if k != 'return_value'})
            except Exception as e:
                logger.error(f"Email sending failed for job '{job_id}': {e}", exc_info=True)
                result = {"stdout": "", "stderr": traceback.format_exc(), "exit_code": 1, "return_value": None}
                _log_job_end(log_entry, **{k: v for k, v in result.items() if k != 'return_value'})
                
            db_session.commit()
            return result
        except ValidationError as e:
            logger.error(f"Invalid parameters for email job '{job_id}': {e}")
            result = {"stdout": "", "stderr": str(e), "exit_code": 1, "return_value": None}
            if log_entry: _log_job_end(log_entry, **{k: v for k, v in result.items() if k != 'return_value'})
            db_session.commit()
            return result
        except Exception as e:
            logger.error(f"Error in execute_email_job for job '{job_id}': {e}", exc_info=True)
            result = {"stdout": "", "stderr": traceback.format_exc(), "exit_code": 1, "return_value": None}
            if log_entry: _log_job_end(log_entry, **{k: v for k, v in result.items() if k != 'return_value'})
            db_session.commit()
            return result
    finally:
        if local_session:
            db_session.close()

# --- Workflow Context and Templating ---

def _render_template(data: Any, context: Dict[str, Any]) -> Any:
    """Recursively renders templates in a nested data structure."""
    if isinstance(data, dict):
        return {k: _render_template(v, context) for k, v in data.items()}
    elif isinstance(data, list):
        return [_render_template(i, context) for i in data]
    elif isinstance(data, str):
        # Find all {{ context.variable }} placeholders
        placeholders = re.findall(r"\{\{\s*context\.(\w+)\s*\}\}", data)
        if not placeholders:
            return data
        
        rendered_str = data
        for var_name in placeholders:
            if var_name not in context:
                raise KeyError(f"Variable '{var_name}' not found in workflow context.")
            
            # Simple replacement for now. If the string is ONLY the placeholder,
            # we can replace it with the raw type. Otherwise, we coerce to string.
            placeholder_full = f"{{{{ context.{var_name} }}}}"
            if rendered_str == placeholder_full:
                return context[var_name] # Replace with raw type
            
            rendered_str = rendered_str.replace(placeholder_full, str(context[var_name]))
        return rendered_str
    else:
        return data

# --- Workflow Executor (Updated) ---

def run_workflow(workflow_id: int, job_id: str = None):
    db = next(database.get_db())
    workflow_run = None
    try:
        workflow = db.query(models.Workflow).options(joinedload(models.Workflow.steps)).filter(models.Workflow.id == workflow_id).first()
        if not workflow:
            logger.error(f"Workflow with id {workflow_id} not found.")
            return

        workflow_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', workflow.name)
        
        logger.info(f"Starting workflow '{workflow.name}' (ID: {workflow.id})")
        workflow_run = models.WorkflowRun(
            workflow_id=workflow.id,
            status='RUNNING',
            context={} # Start with an empty context
        )
        db.add(workflow_run)
        db.commit()
        db.refresh(workflow_run)
        
        context = {}
        final_status = 'COMPLETED'
        steps = sorted(workflow.steps, key=lambda s: s.step_order)

        for i, step in enumerate(steps):
            logger.info(f"Executing step {i+1}/{len(steps)}: '{step.name}' for workflow '{workflow_name}'")
            step_job_id = f"{workflow_name}_{step.step_order}_{step.name}"
            
            try:
                rendered_params = _render_template(step.task_parameters, context)
                task_type = rendered_params.get('task_type')
                
                step_result = None
                if task_type == 'python':
                    step_result = execute_python_job(job_id=step_job_id, task_params=rendered_params, db=db, workflow_run_id=workflow_run.id)
                elif task_type == 'shell':
                    step_result = execute_shell_job(job_id=step_job_id, task_params=rendered_params, db=db, workflow_run_id=workflow_run.id)
                elif task_type == 'email':
                    step_result = execute_email_job(job_id=step_job_id, task_params=rendered_params, db=db, workflow_run_id=workflow_run.id)
                else:
                    logger.error(f"Unknown step task_type: {task_type} for step '{step.name}'")
                    final_status = 'FAILED'
                    break
                
                # Capture output if requested
                if step.output_variable_name:
                    output_value = None
                    if task_type == 'python':
                        output_value = step_result.get('return_value')
                    elif task_type == 'shell':
                        output_value = step_result.get('stdout')
                    
                    if output_value is not None:
                        context[step.output_variable_name] = output_value
                        # Persist context after each step
                        workflow_run.context = context
                        db.commit()

                if step_result.get('exit_code', 1) != 0:
                    if step.on_failure == 'stop':
                        logger.error(f"Workflow '{workflow_name}' stopping due to failed step '{step.name}'.")
                        final_status = 'FAILED'
                        break
            
            except Exception as e:
                logger.error(f"An unhandled error occurred during step '{step.name}': {e}", exc_info=True)
                final_status = 'FAILED'
                # Log this as a failed step execution
                fail_log = _log_job_start(db, step_job_id, "Workflow Step Execution", workflow_run.id)
                _log_job_end(fail_log, exit_code=1, stderr=traceback.format_exc())
                db.commit()
                break
    
    except Exception as e:
        logger.error(f"A critical error occurred during workflow execution for '{workflow.name}': {e}", exc_info=True)
        final_status = 'FAILED'
    
    finally:
        if workflow_run:
            workflow_run.status = final_status
            workflow_run.end_time = time_util.get_current_utc_time()
            db.commit()
            logger.info(f"Workflow '{workflow.name}' finished with status {final_status}.")
        
        db.close()


def execute_python_job(job_id: str, task_params: dict, db: Optional[Session] = None, workflow_run_id: Optional[int] = None) -> Dict[str, Any]:
    
    db_session = db if db else next(database.get_db())
    local_session = not db

    try:
        log_entry = None
        try:
            params = schemas.PythonJobParams.model_validate(task_params)
            target_func_path = f"{params.module}:{params.function}"
            log_entry = _log_job_start(db_session, job_id, target_func_path, workflow_run_id=workflow_run_id)

            try:
                payload = json.dumps({'args': params.args, 'kwargs': params.kwargs})
                encoded_payload = base64.b64encode(payload.encode('utf-8')).decode('utf-8')
            except (TypeError, OverflowError) as e:
                err_msg = f"Failed to serialize arguments for Python job: {e}. Arguments must be JSON-serializable."
                result = {"stdout": "", "stderr": err_msg, "exit_code": 1, "return_value": None}
                if log_entry:
                    _log_job_end(log_entry, **{k: v for k, v in result.items() if k != 'return_value'})
                db_session.commit()
                return result

            wrapper_path = Path(__file__).parent.joinpath("python_job_wrapper.py")
            command_to_run = [
                sys.executable, 
                str(wrapper_path), 
                target_func_path, 
                encoded_payload
            ]

            result = _execute_subprocess(command_to_run=command_to_run)
            
            return_value = None
            if result["exit_code"] == 0 and result["stdout"]:
                try:
                    output_data = json.loads(result["stdout"])
                    return_value = output_data.get("return_value")
                except json.JSONDecodeError:
                    pass
            
            result["return_value"] = return_value
            
            _log_job_end(log_entry, **{k: v for k, v in result.items() if k != 'return_value'})
            db_session.commit()
            return result
            
        except ValidationError as e:
            logger.error(f"Invalid parameters for python job '{job_id}': {e}")
            result = {"stdout": "", "stderr": str(e), "exit_code": 1, "return_value": None}
            if log_entry: _log_job_end(log_entry, **{k: v for k, v in result.items() if k != 'return_value'})
            db_session.commit()
            return result
        except Exception as e:
            logger.error(f"Error in execute_python_job for job '{job_id}': {e}", exc_info=True)
            result = {"stdout": "", "stderr": traceback.format_exc(), "exit_code": 1, "return_value": None}
            if log_entry: _log_job_end(log_entry, **{k: v for k, v in result.items() if k != 'return_value'})
            db_session.commit()
            return result
    finally:
        if local_session:
            db_session.close()

def execute_email_job(job_id: str, task_params: dict, db: Session, workflow_run_id: Optional[int] = None) -> Dict[str, Any]:
    log_entry = None
    try:
        params = schemas.EmailJobParams.model_validate(task_params)
        log_command = f"send_email to:{params.to_email} subject:{params.subject}"
        log_entry = _log_job_start(db, job_id, log_command, workflow_run_id=workflow_run_id)
        
        try:
            email_kwargs = params.model_dump()
            email_kwargs.pop('task_type', None)
            email_kwargs['job_id'] = job_id
            email_tasks.send_email_task(**email_kwargs)
            result = {"stdout": "Email sent successfully.", "stderr": "", "exit_code": 0}
            _log_job_end(log_entry, **result)
        except Exception as e:
            logger.error(f"Email sending failed for job '{job_id}': {e}", exc_info=True)
            result = {"stdout": "", "stderr": traceback.format_exc(), "exit_code": 1}
            _log_job_end(log_entry, **result)
            
        db.commit()
        return result
    except ValidationError as e:
        logger.error(f"Invalid parameters for email job '{job_id}': {e}")
        result = {"stdout": "", "stderr": str(e), "exit_code": 1}
        if log_entry: _log_job_end(log_entry, **result)
        db.commit()
        return result
    except Exception as e:
        logger.error(f"Error in execute_email_job for job '{job_id}': {e}", exc_info=True)
        result = {"stdout": "", "stderr": traceback.format_exc(), "exit_code": 1}
        if log_entry: _log_job_end(log_entry, **result)
        db.commit()
        return result

# --- Workflow Executor (Updated) ---

def run_workflow(workflow_id: int, job_id: str = None):
    db = next(database.get_db())
    workflow_run_id = None
    try:
        workflow = db.query(models.Workflow).options(joinedload(models.Workflow.steps)).filter(models.Workflow.id == workflow_id).first()
        if not workflow:
            logger.error(f"Workflow with id {workflow_id} not found.")
            return

        workflow_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', workflow.name)
        base_dir = config.scheduler_work_dir
        workflow_cwd = base_dir.joinpath(workflow_name).resolve()
        workflow_cwd.mkdir(parents=True, exist_ok=True)
        logger.info(f"Working directory for workflow '{workflow_name}' is {workflow_cwd}")
        
        logger.info(f"Starting workflow '{workflow.name}' (ID: {workflow.id})")
        workflow_run = models.WorkflowRun(
            workflow_id=workflow.id,
            status='RUNNING'
        )
        db.add(workflow_run)
        db.commit()
        db.refresh(workflow_run)
        workflow_run_id = workflow_run.id
        steps = sorted(workflow.steps, key=lambda s: s.step_order)

    finally:
        if db.is_active:
            db.close()

    final_status = 'COMPLETED'
    try:
        for i, step in enumerate(steps):
            logger.info(f"Executing step {i+1}/{len(steps)}: '{step.name}' for workflow '{workflow_name}'")
            
            step_job_id = f"{workflow_name}_{step.step_order}_{step.name}"
            
            task_params = step.task_parameters
            task_type = task_params.get('task_type')

            if task_type == 'python':
                execute_python_job(job_id=step_job_id, task_params=task_params, workflow_run_id=workflow_run_id)
            elif task_type == 'shell':
                if 'cwd' not in task_params or not task_params['cwd']:
                    task_params['cwd'] = str(workflow_cwd.relative_to(config.scheduler_work_dir))
                execute_shell_job(job_id=step_job_id, task_params=task_params, workflow_run_id=workflow_run_id)
            elif task_type == 'email':
                execute_email_job(job_id=step_job_id, task_params=task_params, workflow_run_id=workflow_run_id)
            else:
                logger.error(f"Unknown step task_type: {task_type} for step '{step.name}'")
                final_status = 'FAILED'
                break 

            temp_db = next(database.get_db())
            try:
                last_log = temp_db.query(models.ProcessExecutionLog).filter(
                    models.ProcessExecutionLog.job_id == step_job_id,
                    models.ProcessExecutionLog.workflow_run_id == workflow_run_id
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
        if workflow_run_id:
            final_db = next(database.get_db())
            try:
                workflow_run_to_update = final_db.query(models.WorkflowRun).filter(models.WorkflowRun.id == workflow_run_id).first()
                if workflow_run_to_update:
                    workflow_run_to_update.status = final_status
                    workflow_run_to_update.end_time = time_util.get_current_utc_time()
                    final_db.commit()
                logger.info(f"Workflow '{workflow_name}' finished with status {final_status}.")
            finally:
                final_db.close()