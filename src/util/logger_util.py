import logging
import os
import copy
import sys
from logging.handlers import RotatingFileHandler

_logger_initialized = False

class ColoredFormatter(logging.Formatter):
    """ANSIカラー対応のフォーマッター"""
    COLORS = {
        "DEBUG": "\033[0;36m",  # CYAN
        # "NOTICE": "\033[1;34m",  # LIGHT BLUE
        "INFO": "\033[0;32m",  # GREEN
        # "ALERT": "\033[0;35m",  # PURPLE
        "WARNING": "\033[0;33m",  # YELLOW
        "ERROR": "\033[0;31m",  # RED
        "CRITICAL": "\033[0;37;41m",  # WHITE ON RED
        "RESET": "\033[0m",  # RESET COLOR
    }

    def format(self, record):
        colored_record = copy.copy(record)
        levelname = colored_record.levelname
        seq = self.COLORS.get(levelname, self.COLORS["RESET"])
        colored_record.levelname = f"{seq}{levelname}{self.COLORS['RESET']}"
        return super().format(colored_record)

def setup_logging(log_file_path="app.log", 
                  use_colors=True, 
                  console_level=logging.INFO, 
                  file_level=logging.DEBUG):
    """
    Configures a logger that outputs to both console and a rotating file.
    This function should ideally be called once at the application's entry point.
    """
    global _logger_initialized
    if _logger_initialized:
        return

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Set root logger to DEBUG to capture all messages

    # Clear existing handlers to prevent duplicate logs if called multiple times in a session
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console Handler
    log_format = "[%(filename)s:%(lineno)d %(funcName)s]%(asctime)s[%(levelname)s] - %(message)s"
    date_format = "%H:%M:%S"

    # 標準出力のハンドラー
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = ColoredFormatter(log_format, datefmt=date_format) if use_colors else logging.Formatter(log_format, datefmt=date_format)
    stream_handler.setFormatter(formatter)

    root_logger.addHandler(stream_handler)

    # Ensure the log directory exists before creating the file handler
    log_dir = os.path.dirname(log_file_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
        # We can't use logger.info here yet, as the logger is not fully set up.
        # print(f"Created log directory: {log_dir}") # For debugging if needed

    # File Handler (rotating)
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=1024 * 1024 * 5,  # 5 MB
        backupCount=5
    )
    file_handler.setLevel(file_level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    # root_logger.addHandler(file_handler)

    # Set specific loggers for libraries that might be too verbose
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    logging.getLogger('watchdog').setLevel(logging.WARNING)

    _logger_initialized = True

    # Now that logging is set up, get a logger for logger_util itself
    logger = get_logger(__name__)
    
    logger.info("Logging initialized.")

def get_logger(name):
    """
    Returns a named logger. Assumes setup_logging has been called.
    """
    return logging.getLogger(name)

# Example usage (can be removed if only used via import)
if __name__ == "__main__":
    setup_logging(log_file_path="test_app.log", console_level=logging.DEBUG, file_level=logging.DEBUG)
    logger = get_logger(__name__)
    logger.debug("This is a debug message from example.")
    logger.info("This is an info message from example.")
    logger.warning("This is a warning message from example.")
    logger.error("This is an error message from example.")
    logger.critical("This is a critical message from example.")

    another_logger = get_logger("my_module")
    another_logger.info("This is an info message from 'my_module'.")
