import logging
from ..task_utils import task

# @task(name="Send Daily Report", description="Generates and sends a daily report.")
def send_daily_report(email: str, **kwargs):
    logging.info(f"Sending daily report to {email}.")
