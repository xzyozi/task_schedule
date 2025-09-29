import os
import subprocess
import traceback
from importlib import import_module
from typing import Dict, Any, Optional
from util import logger_util
from util.config_util import config
from datetime import datetime
import uuid
from core import database
from . import models

logger = logger_util.get_logger(__name__)

def _execute_subprocess(command_to_run: list, use_shell: bool, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Internal helper to execute a command as a subprocess.
    """
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

        # When shell=True, pass a string. Otherwise, pass a list.
        proc_input = log_command if use_shell else command_to_run

        process = subprocess.run(
            proc_input,
            capture_output=True,
            text=True,
            check=False,
            shell=use_shell,
            cwd=absolute_cwd,
            env=process_env
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


def execute_command_job(**kwargs):
    """
    A wrapper for executing command-based jobs (shell, cmd, powershell)
    that logs the execution details to the ProcessExecutionLog table.
    This is the main entry point for command jobs.
    """
    job_id = kwargs.get('job_id')
    job_type = kwargs.get('job_type')
    command_list = kwargs.get('command', [])
    
    # Prepare the command and execution options based on job_type
    executable_command = []
    use_shell = False
    
    if job_type == 'powershell':
        # For PowerShell, we execute the powershell executable with the command.
        # `shell=False` is safer here.
        executable_command = ['powershell', '-Command'] + command_list
        use_shell = False
    elif job_type == 'cmd':
        # For cmd, we need `shell=True` to use built-ins.
        # The command will be passed as a string.
        executable_command = command_list
        use_shell = True
    elif job_type == 'shell': # For Linux/macOS
        # For Linux/macOS, `shell=True` will use the default shell (e.g., /bin/sh)
        executable_command = command_list
        use_shell = True
    else:
        logger.error(f"Attempted to execute unknown command job type: {job_type}")
        return

    command_str = ' '.join(command_list)
    db = next(database.get_db())
    log_entry = None
    try:
        log_id = str(uuid.uuid4())
        log_entry = models.ProcessExecutionLog(
            id=log_id,
            job_id=job_id,
            command=command_str,
            start_time=datetime.now(),
            status='RUNNING'
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
    except Exception as e:
        logger.error(f"Failed to create initial log entry for job {job_id}: {e}")
        db.rollback()
    finally:
        db.close()

    # Execute the actual command
    result = _execute_subprocess(
        command_to_run=executable_command,
        use_shell=use_shell,
        cwd=kwargs.get('cwd'),
        env=kwargs.get('env')
    )

    # Update the log entry with the result
    if log_entry:
        db = next(database.get_db())
        try:
            log_entry = db.query(models.ProcessExecutionLog).filter_by(id=log_entry.id).one()
            log_entry.end_time = datetime.now()
            log_entry.exit_code = result.get('exit_code')
            log_entry.stdout = result.get('stdout')
            log_entry.stderr = result.get('stderr')
            log_entry.status = 'COMPLETED' if log_entry.exit_code == 0 else 'FAILED'
            db.commit()
        except Exception as e:
            logger.error(f"Failed to update log entry {log_entry.id} for job {job_id}: {e}")
            db.rollback()
        finally:
            db.close()

    return result

def _resolve_func_path(func_path: str):
    """Helper to resolve a function path like 'module.submodule:function_name'."""
    if ':' in func_path:
        module_path, func_name = func_path.rsplit(':', 1)
    else:
        module_path, func_name = func_path.rsplit('.', 1)
    module = import_module(module_path)
    return getattr(module, func_name)

def execute_python_job(**kwargs):
    """
    A wrapper for executing Python functions that logs the execution details
    to the ProcessExecutionLog table.
    """
    job_id = kwargs.get('job_id')
    target_func_path = kwargs.get('target_func_path')
    target_args = kwargs.get('target_args', [])
    target_kwargs = kwargs.get('target_kwargs', {})

    # Inject job_id into the target function's kwargs if it's not already there
    if 'job_id' not in target_kwargs:
        target_kwargs['job_id'] = job_id

    db = next(database.get_db())
    log_entry = None
    try:
        log_id = str(uuid.uuid4())
        log_entry = models.ProcessExecutionLog(
            id=log_id,
            job_id=job_id,
            command=target_func_path,
            start_time=datetime.now(),
            status='RUNNING'
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
    except Exception as e:
        logger.error(f"Failed to create initial log entry for job {job_id}: {e}")
        db.rollback()
    finally:
        db.close()

    result = None
    stdout = ""
    stderr = ""
    exit_code = 0
    status = 'COMPLETED'

    try:
        if not target_func_path or (':' not in target_func_path and '.' not in target_func_path):
            raise ValueError(f"Invalid function path format: '{target_func_path}'. It must be in 'module.submodule:function' format.")
        target_func = _resolve_func_path(target_func_path)
        result = target_func(*target_args, **target_kwargs)
        stdout = str(result) if result is not None else ""
        logger.info(f"Python job '{job_id}' ({target_func_path}) executed successfully.")
    except Exception as e:
        logger.error(f"Error executing python job '{job_id}' ({target_func_path}): {e}", exc_info=True)
        exit_code = 1
        status = 'FAILED'
        stderr = traceback.format_exc()

    if log_entry:
        db = next(database.get_db())
        try:
            log_entry = db.query(models.ProcessExecutionLog).filter_by(id=log_entry.id).one()
            log_entry.end_time = datetime.now()
            log_entry.exit_code = exit_code
            log_entry.stdout = stdout
            log_entry.stderr = stderr
            log_entry.status = status
            db.commit()
        except Exception as e:
            logger.error(f"Failed to update log entry {log_entry.id} for job {job_id}: {e}")
            db.rollback()
        finally:
            db.close()

    return result

def run_workflow(workflow_id: int, job_id: str = None):
    """
    The main entry point for executing a workflow.
    This function is called by an APScheduler job.
    """
    db = next(database.get_db())
    workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
    
    if not workflow:
        logger.error(f"Workflow with id {workflow_id} not found for job {job_id}.")
        db.close()
        return

    workflow_run = models.WorkflowRun(workflow_id=workflow.id, status='RUNNING')
    db.add(workflow_run)
    db.commit()
    db.refresh(workflow_run)
    
    logger.info(f"Starting workflow '{workflow.name}' (run_id: {workflow_run.id})")

    try:
        steps = sorted(workflow.steps, key=lambda s: s.step_order)

        for i, step in enumerate(steps):
            workflow_run.current_step = i + 1
            db.commit()

            logger.info(f"Executing step {i+1}/{len(steps)}: '{step.name}'")

            kwargs_for_executor = {
                'job_id': f"workflow_{workflow.id}_step_{step.id}",
                'workflow_run_id': workflow_run.id,
            }

            if step.job_type == 'python':
                kwargs_for_executor['target_func_path'] = step.target
                kwargs_for_executor['target_args'] = step.args or []
                kwargs_for_executor['target_kwargs'] = step.kwargs or {}
                execute_python_job(**kwargs_for_executor)
            
            elif step.job_type in ['cmd', 'powershell', 'shell']:
                kwargs_for_executor['job_type'] = step.job_type
                kwargs_for_executor['command'] = step.target.split()
                if step.kwargs:
                    kwargs_for_executor['cwd'] = step.kwargs.get('cwd')
                    kwargs_for_executor['env'] = step.kwargs.get('env')
                execute_command_job(**kwargs_for_executor)
            
            else:
                raise ValueError(f"Unknown step job_type: {step.job_type}")

            db.refresh(workflow_run)
            last_log = db.query(models.ProcessExecutionLog).filter(
                models.ProcessExecutionLog.workflow_run_id == workflow_run.id
            ).order_by(models.ProcessExecutionLog.start_time.desc()).first()

            if last_log and last_log.status == 'FAILED':
                if step.on_failure == 'stop':
                    logger.error(f"Workflow '{workflow.name}' stopped due to failed step '{step.name}'.")
                    workflow_run.status = 'FAILED'
                    db.commit()
                    return

        workflow_run.status = 'COMPLETED'
        logger.info(f"Workflow '{workflow.name}' (run_id: {workflow_run.id}) completed successfully.")

    except Exception as e:
        logger.error(f"An unexpected error occurred in workflow '{workflow.name}': {e}", exc_info=True)
        workflow_run.status = 'FAILED'
    finally:
        workflow_run.end_time = datetime.now()
        db.commit()
        db.close()
