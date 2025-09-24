import logging

def send_daily_report(email: str, **kwargs):
    logging.info(f"Sending daily report to {email}.")
