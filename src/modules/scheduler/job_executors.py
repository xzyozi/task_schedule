import os
import re
import subprocess
import traceback
import json
import base64
import sys
from importlib import import_module
from pathlib import Path
from typing import Dict, Any, Optional, Union

from sqlalchemy.orm import Session

from util import logger_util, time_util
from util.config_util import config
from datetime import datetime
import uuid
from core import database
from . import models

logger = logger_util.get_logger(__name__)

def _execute_subprocess(command_to_run: Union[list, str], use_shell: bool, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None, run_in_background: bool = False) -> Dict[str, Any]:
    if isinstance(command_to_run, list):
        log_command = ' '.join(command_to_run)
    else:
        log_command = command_to_run

    absolute_cwd = None
    if cwd:
        path_obj = Path(cwd)
        if path_obj.is_absolute():
            absolute_cwd = path_obj
        else:
            absolute_cwd = config.scheduler_work_dir.joinpath(cwd).resolve()
        absolute_cwd.mkdir(parents=True, exist_ok=True)

    logger.info(f"Executing: {log_command}" + (f" in {absolute_cwd}" if absolute_cwd else ""))

    try:
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        # When use_shell=True, command_to_run should be a string.
        # When use_shell=False, it should be a list of arguments.
        proc_input = command_to_run

        if run_in_background:
            logger.info(f"Executing in background: {log_command}")
            subprocess.Popen(proc_input, shell=use_shell, cwd=absolute_cwd, env=process_env)
            return {"stdout": "Process launched in background.", "stderr": "", "exit_code": 0}
        else:
            process = subprocess.run(
                proc_input, capture_output=True, text=True, check=False, shell=use_shell, cwd=absolute_cwd, env=process_env
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
        cmd_name = command_to_run[0] if isinstance(command_to_run, list) else command_to_run.split()[0]
        logger.error(f"Command not found: {cmd_name}", exc_info=True)
        return {"stdout": "", "stderr": f"Command not found: {cmd_name}", "exit_code": 127}
    except Exception as e:
        logger.error(f"Error executing command '{log_command}': {e}", exc_info=True)
        return {"stdout": "", "stderr": str(e), "exit_code": 1}


def execute_command_job(**kwargs):
    job_id = kwargs.get('job_id')
    db = next(database.get_db())
    try:
        # This function now manages its own transaction entirely.
        _execute_command_job_impl(db=db, **kwargs)
        db.commit()
    except Exception as e:
        logger.error(f"Error in execute_command_job for job '{job_id}': {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()

def _execute_command_job_impl(db: Session, **kwargs):
    job_id = kwargs.get('job_id')
    job_type = kwargs.get('job_type')
    command_list = kwargs.get('command', [])
    
    executable_command = []
    use_shell = False
    if job_type == 'powershell':
        # PowerShellは引数をリストで受け取るため、そのまま
        executable_command = ['powershell', '-Command'] + command_list
    elif job_type == 'cmd':
        # cmdはshell=Trueで実行されるため、単一の文字列として渡す
        executable_command = command_list[0] if command_list else "" # command_listは単一要素のリストを想定
        use_shell = True
    elif job_type == 'shell':
        # shellはshell=Trueで実行されるため、単一の文字列として渡す
        executable_command = command_list[0] if command_list else "" # command_listは単一要素のリストを想定
        use_shell = True
    else:
        raise ValueError(f"Unknown command job type: {job_type}")

    command_str = ' '.join(command_list)
    log_entry = models.ProcessExecutionLog(
        id=str(uuid.uuid4()),
        job_id=job_id,
        workflow_run_id=kwargs.get('workflow_run_id'),
        command=command_str,
        start_time=time_util.get_current_utc_time(),
        status='RUNNING'
    )
    db.add(log_entry)
    db.flush()

    result = _execute_subprocess(
        command_to_run=executable_command,
        use_shell=use_shell,
        cwd=kwargs.get('cwd'),
        env=kwargs.get('env'),
        run_in_background=kwargs.get('run_in_background', False)
    )

    log_entry.end_time = time_util.get_current_utc_time()
    log_entry.exit_code = result.get('exit_code')
    log_entry.stdout = result.get('stdout')
    log_entry.stderr = result.get('stderr')
    log_entry.status = 'COMPLETED' if log_entry.exit_code == 0 else 'FAILED'
    db.add(log_entry)

def _resolve_func_path(func_path: str):
    if ':' in func_path:
        module_path, func_name = func_path.rsplit(':', 1)
    else:
        module_path, func_name = func_path.rsplit('.', 1)
    module = import_module(module_path)
    return getattr(module, func_name)

def execute_python_job(**kwargs):
    job_id = kwargs.get('job_id')
    db = next(database.get_db())
    try:
        # This function now manages its own transaction entirely.
        _execute_python_job_impl(db=db, **kwargs)
        db.commit()
    except Exception as e:
        logger.error(f"Error in execute_python_job for job '{job_id}': {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()

def _execute_python_job_impl(db: Session, **kwargs):
    job_id = kwargs.get('job_id')
    target_func_path = kwargs.get('target_func_path')
    target_args = kwargs.get('target_args', [])
    target_kwargs = kwargs.get('target_kwargs', {})

    if 'job_id' not in target_kwargs:
        target_kwargs['job_id'] = job_id

    log_entry = models.ProcessExecutionLog(
        id=str(uuid.uuid4()),
        job_id=job_id,
        workflow_run_id=kwargs.get('workflow_run_id'),
        command=target_func_path,
        start_time=time_util.get_current_utc_time(),
        status='RUNNING'
    )
    db.add(log_entry)
    db.flush()

    try:
        # Ensure the path is in the 'module:function' format for the wrapper
        if ':' not in target_func_path and '.' in target_func_path:
            parts = target_func_path.rsplit('.', 1)
            target_func_path_for_wrapper = ':'.join(parts)
        else:
            target_func_path_for_wrapper = target_func_path

        payload = json.dumps({'args': target_args, 'kwargs': target_kwargs})
        encoded_payload = base64.b64encode(payload.encode('utf-8')).decode('utf-8')
    except (TypeError, OverflowError) as e:
        log_entry.end_time = time_util.get_current_utc_time()
        log_entry.exit_code = 1
        log_entry.stderr = f"Failed to serialize arguments for Python job: {e}\nArguments must be JSON-serializable."
        log_entry.status = 'FAILED'
        db.add(log_entry)
        return

    # Get the path to the wrapper script, assuming it's in the same directory
    wrapper_path = Path(__file__).parent.joinpath("python_job_wrapper.py")

    command_to_run = [
        sys.executable, 
        str(wrapper_path), 
        target_func_path_for_wrapper, 
        encoded_payload
    ]

    result = _execute_subprocess(
        command_to_run=command_to_run,
        use_shell=False,
        cwd=kwargs.get('cwd'),
        env=kwargs.get('env')
    )

    log_entry.end_time = time_util.get_current_utc_time()
    log_entry.exit_code = result.get('exit_code')
    log_entry.stdout = result.get('stdout')
    log_entry.stderr = result.get('stderr')
    log_entry.status = 'COMPLETED' if log_entry.exit_code == 0 else 'FAILED'
    db.add(log_entry)

def run_workflow(workflow_id: int, job_id: str = None, run_params: Optional[dict] = None):
    db = next(database.get_db())
    try:
        workflow = db.query(models.Workflow).filter(models.Workflow.id == workflow_id).first()
        if not workflow:
            logger.error(f"Workflow with id {workflow_id} not found.")
            return

        # --- CWD Generation and Security Check ---
        workflow_name = workflow.name
        # Sanitize workflow_name to prevent path traversal
        if ".." in workflow_name or "/" in workflow_name or "\"" in workflow_name:
            logger.error(f"Invalid workflow name for use as directory: {workflow_name}")
            # TODO: Optionally, update workflow_run status to FAILED
            return
        
        base_dir = os.path.join(os.path.expanduser('~'), '.task_scheduler')
        workflow_cwd = os.path.join(base_dir, workflow_name)
        os.makedirs(workflow_cwd, exist_ok=True)
        logger.info(f"Working directory for workflow '{workflow_name}' is {workflow_cwd}")
        # --- End CWD Generation ---
        
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
            
            kwargs_for_executor = {
                'job_id': f"{workflow_name}_{step.name}",
                'workflow_run_id': workflow_run_id,
            }

            # --- Parameter Substitution ---
            substituted_target = step.target
            if run_params:
                # 正規表現でマッチした部分を直接置換する
                # {{ params.変数名 }} の形式にマッチし、変数名部分をキャプチャ
                substituted_target = re.sub(
                    r"\{\{\s*params\.([a-zA-Z0-9_]+)\s*\}\}",
                    lambda match: str(run_params.get(match.group(1), match.group(0))), # マッチした変数名でrun_paramsから値を取得、なければ元のプレースホルダーを維持
                    substituted_target
                )
            # --- End Parameter Substitution ---

            if step.job_type == 'python':
                kwargs_for_executor['target_func_path'] = substituted_target
                kwargs_for_executor['target_args'] = step.args or []
                kwargs_for_executor['target_kwargs'] = step.kwargs or {}
                execute_python_job(**kwargs_for_executor)
            elif step.job_type in ['cmd', 'powershell', 'shell']:
                kwargs_for_executor['job_type'] = step.job_type
                kwargs_for_executor['command'] = [substituted_target] # 単一要素のリストとして渡す

                # Combine step kwargs with the mandatory workflow_cwd
                step_kwargs = step.kwargs or {}
                step_kwargs['cwd'] = workflow_cwd  # Always use the workflow's CWD

                kwargs_for_executor['cwd'] = step_kwargs.get('cwd')
                kwargs_for_executor['env'] = step_kwargs.get('env')
                kwargs_for_executor['run_in_background'] = step.run_in_background
                execute_command_job(**kwargs_for_executor)
            else:
                raise ValueError(f"Unknown step job_type: {step.job_type}")

            temp_db = next(database.get_db())
            try:
                last_log = temp_db.query(models.ProcessExecutionLog).filter(
                    models.ProcessExecutionLog.job_id == kwargs_for_executor['job_id']
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
        # Final update
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