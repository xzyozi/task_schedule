import logging
import datetime
from util import time_util

logger = logging.getLogger(__name__)

def print_current_time(**kwargs):
    now = time_util.get_current_utc_time().strftime("%Y-%m-%d %H:%M:%S UTC")
    logger.info(f"Sample job executed at: {now}")