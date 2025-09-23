import requests
from datetime import datetime
from core.database import SessionLocal
from modules.scheduler.models import ProcessExecutionLog
import logging

def check_api_status(api_endpoint: str, timeout_seconds: int, job_id: str = None):
    logging.info(f"Checking API status for job '{job_id}' at {api_endpoint}")
    try:
        with SessionLocal() as db:
            start_time = datetime.now()
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
                response.raise_for_status()
                log_entry.status = 'COMPLETED'
                log_entry.exit_code = response.status_code
                log_entry.stdout = response.text[:4000]
            except requests.exceptions.RequestException as e:
                log_entry.status = 'FAILED'
                log_entry.exit_code = e.response.status_code if e.response is not None else -1
                log_entry.stderr = str(e)
            log_entry.end_time = datetime.now()
            db.commit()
    except Exception as e:
        logging.error(f"Error in check_api_status for job '{job_id}': {e}", exc_info=True)
