from datetime import datetime
from .logger_util import setup_logging, get_logger

LOGGER_DATEFORMAT = "%Y%m%d"
nowtime = datetime.now()
formatted_now = nowtime.strftime(LOGGER_DATEFORMAT)

# Setup the logging configuration once
setup_logging(
    log_file_path=f"./log/{formatted_now}.log",
    console_level=20, # INFO
    file_level=10 # DEBUG
)

# Get the pre-configured logger instance
logger = get_logger(name="task_scheduler")

