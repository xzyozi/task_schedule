import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from typing import List, Optional

from util import logger_util

logger = logger_util.get_logger(__name__)

def send_email_task(
    to_email: str,
    subject: str,
    body: str,
    sender_account: str,
    smtp_server: str,
    smtp_port: int,
    body_type: str = "plain",
    image_paths: Optional[List[str]] = None,
    job_id: Optional[str] = None, # Added for scheduler context
    workflow_run_id: Optional[str] = None # Added for scheduler context
):
    """
    汎用的なメール送信タスク。
    環境変数 EMAIL_SENDER_PASSWORD からパスワードを取得します。
    """
    logger.info(f"Attempting to send email for job_id: {job_id}, workflow_run_id: {workflow_run_id}")

    sender_password = os.getenv('EMAIL_SENDER_PASSWORD')
    if not sender_password:
        logger.error("EMAIL_SENDER_PASSWORD 環境変数が設定されていません。メール送信をスキップします。")
        raise ValueError("EMAIL_SENDER_PASSWORD environment variable is not set.")

    message = MIMEMultipart()
    message["From"] = sender_account
    message["To"] = to_email
    message["Subject"] = subject

    message.attach(MIMEText(body, body_type))

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
        # STARTTLS を使用したセキュアな接続
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
