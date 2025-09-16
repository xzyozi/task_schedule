import logging
import os
from logging.handlers import RotatingFileHandler

_logger_initialized = False

def setup_logging(log_file_path="app.log", console_level=logging.INFO, file_level=logging.DEBUG):
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
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

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
    root_logger.addHandler(file_handler)

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
