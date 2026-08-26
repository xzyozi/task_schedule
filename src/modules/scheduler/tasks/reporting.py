import logging
from typing import Any


# @task(name="Send Daily Report", description="Generates and sends a daily report.")
def send_daily_report(email: str, **kwargs: Any) -> None:
    logging.info(f"Sending daily report to {email}.")
