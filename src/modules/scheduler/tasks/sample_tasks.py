import logging
import datetime

logger = logging.getLogger(__name__)

def print_current_time(**kwargs):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Sample job executed at: {now}")
