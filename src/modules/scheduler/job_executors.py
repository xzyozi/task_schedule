import os
import subprocess
from typing import Dict, Any, Optional
from util import logger_util
from util.config_util import config
from datetime import datetime
import uuid
from core import database
from . import models

logger = logger_util.get_logger(__name__)

def execute_shell_command(command: list, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
    """
    Executes a shell command and captures its output.

    Args:
        command: The shell command to execute as a list of strings.
        cwd: The relative path from the work_dir to use as the working directory.
        env: A dictionary of environment variables to set for the command.
        **kwargs: Other keyword arguments (ignored).

    Returns:
        A dictionary containing stdout, stderr, and exit_code.
    """
    full_command = command
    log_command = ' '.join(full_command)
    
    absolute_cwd = None
    if cwd:
        # Resolve the relative CWD path against the sandboxed work directory
        absolute_cwd = config.scheduler_work_dir.joinpath(cwd).resolve()
        # Create the directory if it doesn't exist
        absolute_cwd.mkdir(parents=True, exist_ok=True)

    logger.info(f"Executing shell command: {log_command}" + (f" in {absolute_cwd}" if absolute_cwd else ""))

    try:
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        process = subprocess.run(
            log_command, # Pass the command as a string
            capture_output=True,
            text=True,
            check=False,
            shell=True, # Execute through the shell
            cwd=absolute_cwd, # Use the resolved absolute path
            env=process_env
        )

        stdout = process.stdout.strip()
        stderr = process.stderr.strip()
        exit_code = process.returncode

        if exit_code != 0:
            logger.error(f"Shell command '{log_command}' failed with exit code {exit_code}.\nCWD: {absolute_cwd}\nSTDOUT: {stdout}\nSTDERR: {stderr}")
        else:
            logger.info(f"Shell command '{log_command}' completed successfully.\nSTDOUT: {stdout}")

        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code
        }
    except FileNotFoundError:
        logger.error(f"Command not found: {command[0]}", exc_info=True)
        return {"stdout": "", "stderr": f"Command not found: {command[0]}", "exit_code": 127}
    except PermissionError:
        error_msg = f"Permission denied to execute command '{command[0]}' or access CWD '{absolute_cwd}'."
        logger.error(error_msg, exc_info=True)
        return {"stdout": "", "stderr": error_msg, "exit_code": 126}
    except Exception as e:
        logger.error(f"Error executing shell command '{log_command}': {e}", exc_info=True)
        return {"stdout": "", "stderr": str(e), "exit_code": 1}

def logged_shell_command(**kwargs):
    """
    Wrapper for execute_shell_command that logs the execution details
    to the ProcessExecutionLog table.
    """
    job_id = kwargs.get('job_id')
    command_list = kwargs.get('command', [])
    command_str = ' '.join(command_list)

    db = next(database.get_db())
    log_entry = None
    try:
        # Create a unique ID for the log entry
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
        # Still proceed to execute the command
    finally:
        db.close()

    # Execute the actual command
    result = execute_shell_command(**kwargs)

    # Update the log entry with the result
    if log_entry:
        db = next(database.get_db())
        try:
            # Re-attach the object to the new session if it was detached
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