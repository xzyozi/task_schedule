import requests
from datetime import datetime
from scheduler.database import SessionLocal
from scheduler.models import ProcessExecutionLog
import logging


def check_api_status(api_endpoint: str, timeout_seconds: int, job_id: str = None):
    """
    Checks the status of an API endpoint and logs the result to the database.
    The `job_id` is injected by our custom loader.
    """
    logging.info(
        f"Checking API status for job '{job_id}' at {api_endpoint} with a timeout of {timeout_seconds}s."
    )
    
    final_status = "UNKNOWN"
    try:
        with SessionLocal() as db:
            start_time = datetime.now()
            
            # Create a preliminary log entry to mark the job as RUNNING
            log_entry = ProcessExecutionLog(
                id=f"{job_id}-{start_time.isoformat()}",
                job_id=job_id,
                command=f"requests.get('{api_endpoint}')",
                start_time=start_time,
                status='RUNNING'
            )
            db.add(log_entry)
            db.commit()

            try:
                response = requests.get(api_endpoint, timeout=timeout_seconds)
                response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
                
                log_entry.status = 'COMPLETED'
                log_entry.exit_code = response.status_code
                log_entry.stdout = response.text[:4000]

            except requests.exceptions.RequestException as e:
                log_entry.status = 'FAILED'
                log_entry.exit_code = e.response.status_code if e.response is not None else -1
                log_entry.stderr = str(e)
            
            log_entry.end_time = datetime.now()
            final_status = log_entry.status # Capture status before db.commit()
            db.commit() # Commit the final state of log_entry
            
        # Log the final status AFTER the 'with' block, but still within the outer try
        logging.info(f"API status check for job '{job_id}' finished with status: {final_status}")

    except Exception as e:
        logging.error(f"An unexpected error occurred in check_api_status for job '{job_id}': {e}", exc_info=True)
        final_status = "ERROR_IN_TASK_LOGIC"
        logging.info(f"API status check for job '{job_id}' finished with status: {final_status}")

