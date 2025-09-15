import sys
import time
import logging

import uvicorn

from .database import init_db
from .loader import sync_jobs_from_db, seed_db_from_yaml
from .scheduler import start_scheduler, scheduler
from .main import app # Import the FastAPI app

def main():
    """The main entry point for the scheduler service."""
    # Initialize the database first, as both seeding and running need it.
    init_db()

    # Check for command-line arguments
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'seed':
        config_path = "jobs.yaml"
        seed_db_from_yaml(config_path)
        return  # Exit after seeding

    # --- Default execution: start the scheduler and API ---
    start_scheduler()

    # Perform an initial sync on startup
    logging.info("Performing initial job sync...")
    try:
        sync_jobs_from_db()
    except Exception as e:
        logging.critical(f"Initial job sync failed: {e}", exc_info=True)

    # Schedule the sync function to run periodically
    scheduler.add_job(
        sync_jobs_from_db,
        "interval",
        seconds=60,  # This can be made configurable
        id="internal_db_sync",
        replace_existing=True,
    )
    logging.info("Scheduled periodic job sync every 60 seconds.")

    print("Scheduler and API started. Press Ctrl+C to exit.")

    # Start the FastAPI application using uvicorn
    # This call is blocking and will keep the main thread alive
    uvicorn.run(app, host="0.0.0.0", port=8000)

    # The atexit.register(shutdown_scheduler) in scheduler.py will handle cleanup
    # when the process exits (e.g., on Ctrl+C)
