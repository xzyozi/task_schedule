import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from typing import List, Optional, Dict, Any
# from pathlib import Path # No longer needed for PROJECT_ROOT calculation

from jinja2 import Environment, FileSystemLoader

from util import logger_util
from util.config_util import PROJECT_ROOT, config # Import config as well
from util import time_util # For send_task_failure_notification

logger = logger_util.get_logger(__name__)

# Configure Jinja2 environment
# TEMPLATE_DIR now uses the imported PROJECT_ROOT
TEMPLATE_DIR = PROJECT_ROOT / "src" / "templates" / "emails"
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True) # autoescape for security

def send_email_task(
    to_email: str,
    subject: str,
    template_name: Optional[str] = None,
    template_context: Optional[Dict[str, Any]] = None,
    body: Optional[str] = None,
    body_type: str = "plain",
    image_paths: Optional[List[str]] = None,
    job_id: Optional[str] = None,
    workflow_run_id: Optional[str] = None
):
    """
    汎用的なメール送信タスク。Jinja2テンプレートまたは直接指定された本文を使用します。
    環境変数 EMAIL_SENDER_PASSWORD からパスワードを取得します。
    送信元アカウント、SMTPサーバー、ポートは config_util から取得します。
    """
    logger.info(f"Attempting to send email for job_id: {job_id}, workflow_run_id: {workflow_run_id}")

    # --- Parameter Validation ---
    if not to_email:
        logger.error("送信先メールアドレス (to_email) が指定されていません。")
        raise ValueError("Recipient email (to_email) is mandatory.")
    if not subject:
        logger.error("メール件名 (subject) が指定されていません。")
        raise ValueError("Email subject is mandatory.")
    # --- End Parameter Validation ---

    sender_account = config.email_sender_account
    smtp_server = config.email_smtp_server
    smtp_port = config.email_smtp_port

    # --- Configuration Validation ---
    if not sender_account:
        logger.error("メール送信元アカウントが設定されていません。config.yamlのemail.sender_accountを確認してください。")
        raise ValueError("Email sender account is not configured in config.yaml or environment variable.")
    if not smtp_server:
        logger.error("SMTPサーバーが設定されていません。config.yamlのemail.smtp_serverを確認してください。")
        raise ValueError("SMTP server is not configured in config.yaml or environment variable.")
    if not smtp_port:
        logger.error("SMTPポートが設定されていません。config.yamlのemail.smtp_portを確認してください。")
        raise ValueError("SMTP port is not configured in config.yaml or environment variable.")
    # --- End Configuration Validation ---

    sender_password = os.getenv('EMAIL_SENDER_PASSWORD')
    if not sender_password:
        logger.error("EMAIL_SENDER_PASSWORD 環境変数が設定されていません。メール送信をスキップします。")
        raise ValueError("EMAIL_SENDER_PASSWORD environment variable is not set.")

    # Determine email body: use template if template_name is provided, otherwise use direct body
    if template_name:
        try:
            template = env.get_template(template_name)
            body_type = "html" # Ensure body_type is html if a template is used
            rendered_body = template.render(template_context or {})
        except Exception as e:
            logger.error(f"Jinja2テンプレートのレンダリング中にエラーが発生しました ({template_name}): {e}")
            raise
    elif body:
        rendered_body = body
    else:
        logger.error("メール本文またはテンプレートが指定されていません。")
        raise ValueError("Email body or template must be provided.")

    message = MIMEMultipart()
    message["From"] = sender_account
    message["To"] = to_email
    message["Subject"] = subject

    message.attach(MIMEText(rendered_body, body_type))

    if image_paths:
        for i, image_path in enumerate(image_paths):
            if not image_path:
                continue
            try:
                file_ext = os.path.splitext(image_path)[1].lower()
                ext = file_ext[1:]
                with open(image_path, "rb") as img_file:
                    img = MIMEImage(img_file.read(), _subtype=f'{ext}')
                    img.add_header("Content-ID", f"<image_{i}>")
                    message.attach(img)
            except FileNotFoundError:
                logger.warning(f"添付ファイルが見つかりません: {image_path}")
            except Exception as e:
                logger.error(f"添付ファイルの処理中にエラーが発生しました {image_path}: {e}")

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            server.login(sender_account, sender_password)
            server.sendmail(sender_account, to_email, message.as_string())
        logger.info(f"メールが正常に送信されました。To: {to_email}, Subject: {subject}")
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP認証エラー: ユーザー名またはパスワードが正しくありません。{e}")
        raise
    except smtplib.SMTPConnectError as e:
        logger.error(f"SMTP接続エラー: サーバーへの接続に失敗しました。{e}")
        raise
    except smtplib.SMTPException as e:
        logger.error(f"SMTPエラーが発生しました: {e}")
        raise
    except Exception as e:
        logger.error(f"メール送信中に予期せぬエラーが発生しました: {e}")
        raise

# Helper function for task failure notification
def send_task_failure_notification(
    task_id: str,
    error_message: str,
    error_details: Optional[str] = None,
    recipient_email: str = "admin@example.com", # Default recipient
    log_url: Optional[str] = None,
    job_id: Optional[str] = None,
    workflow_run_id: Optional[str] = None
):
    """
    タスク失敗時に管理者へ通知メールを送信するヘルパー関数。
    """
    # --- Parameter Validation ---
    if not task_id:
        logger.error("タスクID (task_id) が指定されていません。")
        raise ValueError("Task ID (task_id) is mandatory.")
    if not error_message:
        logger.error("エラーメッセージ (error_message) が指定されていません。")
        raise ValueError("Error message (error_message) is mandatory.")
    # --- End Parameter Validation ---

    subject = f"【アラート】タスク失敗: {task_id}"
    template_context = {
        "main_message": f"タスク '{task_id}' が失敗しました。詳細を確認してください。",
        "details": {
            "タスクID": task_id,
            "実行時刻": time_util.get_current_utc_time().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "ステータス": "FAILED"
        },
        "error_message": error_message,
        "error_details": error_details,
        "call_to_action_url": log_url,
        "call_to_action_text": "ログを確認" if log_url else None,
        "recipient_name": "管理者" # テンプレート内の挨拶用
    }

    send_email_task(
        to_email=recipient_email,
        subject=subject,
        template_name="notification_email.html",
        template_context=template_context,
        job_id=job_id,
        workflow_run_id=workflow_run_id
    )

# UI/jobs.yaml のタスク定義を簡素化するための新しいヘルパー関数
def send_notification_email(
    subject: str,
    main_message: str,
    to_email: str = "admin@example.com", # Default recipient
    details: Optional[Dict[str, str]] = None,
    error_message: Optional[str] = None,
    error_details: Optional[str] = None,
    call_to_action_url: Optional[str] = None,
    call_to_action_text: Optional[str] = None,
    recipient_name: Optional[str] = None, # For template greeting
    image_paths: Optional[List[str]] = None,
    **kwargs # Catch any extra arguments passed by the scheduler (e.g., job_id, workflow_run_id)
):
    """
    汎用的な通知メールを送信するヘルパー関数。
    notification_email.html テンプレートを使用し、共通のメール設定を適用します。
    """
    template_context = {
        "main_message": main_message,
        "details": details,
        "error_message": error_message,
        "error_details": error_details,
        "call_to_action_url": call_to_action_url,
        "call_to_action_text": call_to_action_text,
        "recipient_name": recipient_name,
        # Add any other common context variables here
    }

    send_email_task(
        to_email=to_email,
        subject=subject,
        template_name="notification_email.html",
        template_context=template_context,
        image_paths=image_paths,
        job_id=kwargs.get('job_id'),
        workflow_run_id=kwargs.get('workflow_run_id')
    )
