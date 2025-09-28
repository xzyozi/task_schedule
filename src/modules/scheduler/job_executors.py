import os
import subprocess
from typing import Dict, Any, Optional
from util import logger_util
from util.config_util import config

logger = logger_util.get_logger(__name__)

def execute_shell_command(command: str, *args, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
    """
    Executes a shell command and captures its output.

    Args:
        command: The shell command to execute.
        *args: Positional arguments to pass to the command.
        cwd: The relative path from the work_dir to use as the working directory.
        env: A dictionary of environment variables to set for the command.
        **kwargs: Other keyword arguments, passed as --key value pairs.

    Returns:
        A dictionary containing stdout, stderr, and exit_code.
    """
    full_command = [command] + [str(arg) for arg in args]
    for k, v in kwargs.items():
        if k in ['job_id', 'cwd', 'env']:
            continue
        full_command.append(f"--{k}")
        full_command.append(str(v))

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
            full_command,
            capture_output=True,
            text=True,
            check=False,
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
        logger.error(f"Command not found: {command}", exc_info=True)
        return {"stdout": "", "stderr": f"Command not found: {command}", "exit_code": 127}
    except PermissionError:
        error_msg = f"Permission denied to execute command '{command}' or access CWD '{absolute_cwd}'."
        logger.error(error_msg, exc_info=True)
        return {"stdout": "", "stderr": error_msg, "exit_code": 126}
    except Exception as e:
        logger.error(f"Error executing shell command '{log_command}': {e}", exc_info=True)
        return {"stdout": "", "stderr": str(e), "exit_code": 1}
