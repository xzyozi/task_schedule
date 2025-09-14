import time
import logging

from .database import init_db
import sys
import time
import logging

from .database import init_db
from .loader import sync_jobs_from_db, seed_db_from_yaml
from .scheduler import start_scheduler, scheduler

def main():
    """The main entry point for the scheduler service."""
    # Initialize the database first, as both seeding and running need it.
    init_db()

    # Check for command-line arguments
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'seed':
        config_path = "jobs.yaml"
        seed_db_from_yaml(config_path)
        return  # Exit after seeding

    # --- Default execution: start the scheduler ---
    start_scheduler()

    # Perform an initial sync on startup
    logging.info("Performing initial job sync...")
    try:
        sync_jobs_from_db()
    except Exception as e:
        logging.critical(f"Initial job sync failed: {e}", exc_info=True)
        # For now, we'll log it as critical and continue.

    # Schedule the sync function to run periodically
    scheduler.add_job(
        sync_jobs_from_db,
        "interval",
        seconds=60,  # This can be made configurable
        id="internal_db_sync",
        replace_existing=True,
    )
    logging.info("Scheduled periodic job sync every 60 seconds.")

    print("Scheduler started. Press Ctrl+C to exit.")

    try:
        # Keep the main thread alive
        while scheduler.running:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Scheduler stopped by user.")
        # The shutdown hook registered in start_scheduler will handle cleanup
        pass

if __name__ == "__main__":
    main()
