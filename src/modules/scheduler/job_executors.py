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

def _split_shell_command(command: str) -> list:
    """
    シェルコマンド文字列をトークンに分割する。

    標準の shlex.split() (posix=True) は POSIX シェル文法でパースするため、
    Windows パスの区切り文字 '\\' をエスケープ文字として解釈し、パスを破壊してしまう
    (例: 'C:\\Users\\test' -> 'C:Userstest')。
    このプロジェクトはWindows専用のため、posix=False で分割してバックスラッシュを
    保持し、その後に残る引用符(") のみを手動で除去する。
    """
    parts = shlex.split(command, posix=False)
    cleaned = []
    for part in parts:
        if len(part) >= 2 and part[0] == part[-1] and part[0] in ('"', "'"):
            cleaned.append(part[1:-1])
        else:
            cleaned.append(part)
    return cleaned

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
        absolute_cwd = config.resolve_sandboxed_path(cwd)
        if absolute_cwd is None:
            logger.error(f"Rejected CWD outside of sandbox (work_dir): '{cwd}'")
            return {"stdout": "", "stderr": f"Invalid cwd: '{cwd}' resolves outside of the sandboxed work directory.", "exit_code": 1}
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
            
            command_list = _split_shell_command(params.command)

            result = _execute_subprocess(
                command_to_run=command_list,
                cwd=params.cwd,
                env=params.env
            )
            if result['exit_code'] == 0:
                logger.info(f"Shell job '{job_id}' completed successfully. Output:\n{result['stdout']}")

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
            module = task_params.get('module')
            function = task_params.get('function')
            
            if not module or not function:
                raise ValueError("'module' and 'function' are required for Python jobs.")

            target_func_path = f"{module}:{function}"
            log_entry = _log_job_start(db_session, job_id, target_func_path, workflow_run_id=workflow_run_id)

            # Collect all non-standard params to be passed to the task function.
            func_kwargs = {k: v for k, v in task_params.items() if k not in ['task_type', 'module', 'function', 'args']}

            # Defensively handle cases where params might be incorrectly nested under a 'kwargs' key from the UI/DB.
            if len(func_kwargs) == 1 and 'kwargs' in func_kwargs and isinstance(func_kwargs.get('kwargs'), dict):
                func_kwargs = func_kwargs['kwargs']

            # For tasks decorated with @task, we expect all parameters to be passed
            # in a single dictionary argument named 'params'.
            payload_kwargs = {'params': func_kwargs}
            
            try:
                payload = json.dumps({'args': task_params.get('args', []), 'kwargs': payload_kwargs})
                encoded_payload = base64.b64encode(payload.encode('utf-8')).decode('utf-8')
            except (TypeError, OverflowError) as e:
                err_msg = f"Failed to serialize arguments for Python job: {e}. Arguments must be JSON-serializable."
                result = {"stdout": "", "stderr": err_msg, "exit_code": 1, "return_value": None}
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
            final_stdout = result["stdout"]  # Default to raw stdout

            if result["exit_code"] == 0 and result["stdout"]:
                try:
                    # The wrapper script outputs a JSON with 'return_value'
                    output_data = json.loads(result["stdout"])
                    return_value = output_data.get("return_value")
                    # For logging and DB storage, use the cleaner, unescaped return value.
                    # Coerce to string just in case the return value isn't a string itself.
                    final_stdout = str(return_value) if return_value is not None else ""
                except json.JSONDecodeError:
                    # Output wasn't JSON, so the raw stdout is the only thing we have.
                    pass
            
            result["return_value"] = return_value

            # Log the "real" output for the user to see
            if result["exit_code"] == 0:
                logger.info(f"Python job '{job_id}' completed successfully. Output:\n{final_stdout}")
            
            _log_job_end(log_entry, exit_code=result['exit_code'], stdout=final_stdout, stderr=result['stderr'])
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

# --- Workflow Executor ---
# Note: ステップ間の動的な変数受け渡し・テンプレート機能はスコープ外としている。
# ワークフローは「登録されたジョブ(shell/python/email)を順番に実行し、失敗したら止まる」
# という単純な直列実行のみを提供する。

def run_workflow(workflow_id: int, job_id: str = None):
    db = next(database.get_db())
    workflow_run = None
    workflow = None  # Initialize workflow to None
    final_status = 'COMPLETED'  # Assume success initially

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
        )
        db.add(workflow_run)
        db.commit()
        db.refresh(workflow_run)
        
        steps = sorted(workflow.steps, key=lambda s: s.step_order)

        for i, step in enumerate(steps):
            logger.info(f"Executing step {i+1}/{len(steps)}: '{step.name}' for workflow '{workflow_name}'")
            step_job_id = f"{workflow_name}_{step.step_order}_{step.name}"
            
            try:
                task_type = step.task_parameters.get('task_type')
                
                step_result = None
                if task_type == 'python':
                    step_result = execute_python_job(job_id=step_job_id, task_params=step.task_parameters, db=db, workflow_run_id=workflow_run.id)
                elif task_type == 'shell':
                    step_result = execute_shell_job(job_id=step_job_id, task_params=step.task_parameters, db=db, workflow_run_id=workflow_run.id)
                elif task_type == 'email':
                    step_result = execute_email_job(job_id=step_job_id, task_params=step.task_parameters, db=db, workflow_run_id=workflow_run.id)
                else:
                    logger.error(f"Unknown step task_type: {task_type} for step '{step.name}'")
                    final_status = 'FAILED'
                    break

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
        workflow_name = workflow.name if workflow else f"ID {workflow_id}"
        logger.error(f"A critical error occurred during workflow execution for '{workflow_name}': {e}", exc_info=True)
        final_status = 'FAILED'
    
    finally:
        if workflow_run:
            workflow_run.status = final_status
            workflow_run.end_time = time_util.get_current_utc_time()
            db.commit()
        
        workflow_name = workflow.name if workflow else f"ID {workflow_id}"
        logger.info(f"Workflow '{workflow_name}' finished with status {final_status}.")
        
        db.close()
