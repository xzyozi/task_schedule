import logging
import datetime

logger = logging.getLogger(__name__)

def print_current_time():
    """Prints the current time to the console."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Sample job executed at: {now}")
