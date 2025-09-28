import os
import subprocess
import shlex
from typing import List, Dict, Any, Optional
from util import logger_util

logger = logger_util.get_logger(__name__)

def execute_shell_command(command: str, *args, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
    """
    Executes a shell command and captures its output.

    Args:
        command: The shell command to execute.
        *args: Positional arguments to pass to the command.
        cwd: The working directory for the command.
        env: A dictionary of environment variables to set for the command.
        **kwargs: Other keyword arguments, passed as --key value pairs.

    Returns:
        A dictionary containing stdout, stderr, and exit_code.
    """
    full_command = [command] + [str(arg) for arg in args]
    # For kwargs, we pass them as --key value, skipping internal ones.
    for k, v in kwargs.items():
        if k in ['job_id', 'cwd', 'env']: # also skip cwd and env from being passed as args
            continue
        full_command.append(f"--{k}")
        full_command.append(str(v))

    log_command = ' '.join(full_command)
    logger.info(f"Executing shell command: {log_command}" + (f" in {cwd}" if cwd else ""))

    try:
        # Prepare the environment for the subprocess
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        process = subprocess.run(
            full_command,
            capture_output=True,
            text=True,  # Capture stdout/stderr as text
            check=False,  # Do not raise an exception for non-zero exit codes
            cwd=cwd,      # Set the working directory
            env=process_env # Set the environment variables
        )

        stdout = process.stdout.strip()
        stderr = process.stderr.strip()
        exit_code = process.returncode

        if exit_code != 0:
            logger.error(f"Shell command '{log_command}' failed with exit code {exit_code}.\nCWD: {cwd}\nSTDOUT: {stdout}\nSTDERR: {stderr}")
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
        error_msg = f"Permission denied to execute command '{command}' or access CWD '{cwd}'."
        logger.error(error_msg, exc_info=True)
        return {"stdout": "", "stderr": error_msg, "exit_code": 126} # 126 is common for command cannot execute
    except Exception as e:
        logger.error(f"Error executing shell command '{log_command}': {e}", exc_info=True)
        return {"stdout": "", "stderr": str(e), "exit_code": 1}
