from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import aiosmtplib
except ImportError:
    aiosmtplib = None
    logger.warning("aiosmtplib is not installed, email service unavailable")

class EmailService:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL or self.smtp_user

    async def send_photo_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        photo_urls: List[str],
        share_url: str,
        event_name: str = "",
        date: str = ""
    ) -> bool:
        if aiosmtplib is None:
            logger.warning("aiosmtplib is not installed, cannot send email")
            return False

        if not all([self.smtp_host, self.smtp_port, self.smtp_user, self.smtp_password]):
            logger.warning("SMTP configuration incomplete, cannot send email")
            return False

        try:
            # 构建HTML内容
            photos_html = ""
            for url in photo_urls:
                photos_html += f'<img src="{url}" style="max-width: 100%; margin-bottom: 20px; border-radius: 8px;" />\n'

            html_content = html_body.format(
                photo_url=photo_urls[0] if photo_urls else "",
                share_url=share_url,
                event_name=event_name,
                date=date,
                photos=photos_html
            )

            # 创建邮件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email

            part = MIMEText(html_content, "html")
            msg.attach(part)

            # 发送邮件
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                use_tls=settings.SMTP_USE_TLS,
                timeout=10
            )

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

email_service = EmailService()
