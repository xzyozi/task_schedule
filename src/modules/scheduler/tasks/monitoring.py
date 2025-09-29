import requests
from datetime import datetime
from core.database import SessionLocal
from modules.scheduler.models import ProcessExecutionLog
import logging

def check_api_status(api_endpoint: str, timeout_seconds: int, job_id: str = None):
    """
    Checks the health of an API endpoint.
    This function is intended to be called by the scheduler.
    The job_id is passed by the wrapper for logging context.
    """
    logging.info(f"Checking API status for job '{job_id}' at {api_endpoint}")
    try:
        response = requests.get(api_endpoint, timeout=timeout_seconds)
        response.raise_for_status()
        return f"API is healthy. Status code: {response.status_code}"
    except requests.exceptions.RequestException as e:
        logging.error(f"API health check failed for job '{job_id}': {e}")
        # Re-raise the exception so the wrapper can catch it and log it as a failure.
        raise
