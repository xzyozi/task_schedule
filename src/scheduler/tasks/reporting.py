import logging

def send_daily_report(email: str, template_name: str, include_projections: bool, **kwargs):
    logging.info(
        f"Sending daily report to {email} using template {template_name}. "
        f"Projections included: {include_projections}"
    )
    print("--- Daily report task executed ---")
