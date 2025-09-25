import subprocess
import shlex
from typing import List, Dict, Any, Optional
from util import logger_util

logger = logger_util.get_logger(__name__)

def execute_shell_command(command: str, args: Optional[List[Any]] = None, kwargs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Executes a shell command and captures its output.

    Args:
        command: The shell command to execute.
        args: Positional arguments to pass to the command.
        kwargs: Keyword arguments (not typically used for shell commands, but included for consistency).

    Returns:
        A dictionary containing stdout, stderr, and exit_code.
    """
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    full_command = [command] + [str(arg) for arg in args]
    # For kwargs, we might want to pass them as --key value or similar, but for generic shell commands,
    # it's often simpler to expect them to be handled within the script itself or passed as args.
    # For now, we'll just pass them as additional arguments if they exist.
    for k, v in kwargs.items():
        full_command.append(f"--{k}")
        full_command.append(str(v))

    logger.info(f"Executing shell command: {' '.join(full_command)}")

    try:
        # Using shlex.split for robust command parsing, especially if command itself contains spaces
        # However, if command is just the executable and args are separate, direct list is better.
        # For now, assuming command is the executable and args are separate.
        process = subprocess.run(
            full_command,
            capture_output=True,
            text=True,  # Capture stdout/stderr as text
            check=False  # Do not raise an exception for non-zero exit codes
        )

        stdout = process.stdout.strip()
        stderr = process.stderr.strip()
        exit_code = process.returncode

        if exit_code != 0:
            logger.error(f"Shell command '{' '.join(full_command)}' failed with exit code {exit_code}.\nSTDOUT: {stdout}\nSTDERR: {stderr}")
        else:
            logger.info(f"Shell command '{' '.join(full_command)}' completed successfully.\nSTDOUT: {stdout}\nSTDERR: {stderr}")

        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code
        }
    except FileNotFoundError:
        logger.error(f"Command not found: {command}", exc_info=True)
        return {"stdout": "", "stderr": f"Command not found: {command}", "exit_code": 127}
    except Exception as e:
        logger.error(f"Error executing shell command '{' '.join(full_command)}': {e}", exc_info=True)
        return {"stdout": "", "stderr": str(e), "exit_code": 1}
