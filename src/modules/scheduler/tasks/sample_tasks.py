import logging

from util import time_util

from ..task_utils import task

logger = logging.getLogger(__name__)


@task(name="Print Current Time", description="Logs the current UTC time.")
def print_current_time(**kwargs: object) -> None:
    """Logs the current UTC time."""
    now = time_util.get_current_utc_time().strftime("%Y-%m-%d %H:%M:%S UTC")
    logger.info(f"Sample job executed at: {now}")
    print(f"Sample job executed at: {now}")


@task(name="Simple Echo", description="Prints the provided message to the log.")
def echo(message: str = "No message provided") -> None:
    """Prints a message."""
    logger.info(f"Echo: {message}")
    print(f"Echo: {message}")


@task(enabled=False, name="Disabled Task Example")
def disabled_task() -> None:
    """This task is disabled and should not appear in the UI."""
    logger.info("This should not run from the UI.")
    print("This should not run from the UI.")
