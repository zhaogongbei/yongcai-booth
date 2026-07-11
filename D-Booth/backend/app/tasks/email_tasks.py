import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from app.celery_app import celery_app
from app.core.config import settings
from app.core.logging import logger


class EmailService:
    """Email service for sending emails via SMTP"""

    @staticmethod
    def send_email(
        to: str | List[str], subject: str, html_content: str, text_content: str = None
    ) -> bool:
        """Send email via SMTP.

        Returns False only when SMTP is not configured (a deliberate skip).
        A configured-but-failing send raises, so Celery tasks can retry
        instead of silently reporting success.
        """

        if not settings.SMTP_HOST or not settings.SMTP_USER:
            logger.warning("SMTP not configured, skipping email")
            return False

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to if isinstance(to, str) else ", ".join(to)

        # Add text and HTML parts
        if text_content:
            msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        # Send email — exceptions propagate so the caller can retry.
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email sent successfully to {to}")
        return True


@celery_app.task(bind=True, max_retries=3)
def send_welcome_email(self, user_email: str, user_name: str):
    """Send welcome email to new user"""
    try:
        subject = f"Welcome to {settings.APP_NAME}!"

        html_content = f"""
        <html>
            <body>
                <h1>Welcome to {settings.APP_NAME}!</h1>
                <p>Hi {user_name},</p>
                <p>Thank you for signing up. We're excited to have you on board!</p>
                <p>Get started by creating your first event.</p>
                <br>
                <p>Best regards,<br>The {settings.APP_NAME} Team</p>
            </body>
        </html>
        """

        text_content = f"""
        Welcome to {settings.APP_NAME}!
        
        Hi {user_name},
        
        Thank you for signing up. We're excited to have you on board!
        Get started by creating your first event.
        
        Best regards,
        The {settings.APP_NAME} Team
        """

        sent = EmailService.send_email(user_email, subject, html_content, text_content)

        return {"status": "sent" if sent else "skipped", "to": user_email}

    except Exception as e:
        logger.error(f"Failed to send welcome email to {user_email}: {e}")
        raise self.retry(exc=e, countdown=300)


@celery_app.task(bind=True, max_retries=3)
def send_password_reset_email(self, user_email: str, reset_token: str):
    """Send password reset email"""
    try:
        subject = f"Password Reset - {settings.APP_NAME}"

        reset_url = f"https://app.aibooth.com/reset-password?token={reset_token}"

        html_content = f"""
        <html>
            <body>
                <h1>Password Reset Request</h1>
                <p>You requested to reset your password.</p>
                <p>Click the link below to reset your password:</p>
                <p><a href="{reset_url}">Reset Password</a></p>
                <p>This link will expire in 1 hour.</p>
                <p>If you didn't request this, please ignore this email.</p>
                <br>
                <p>Best regards,<br>The {settings.APP_NAME} Team</p>
            </body>
        </html>
        """

        text_content = f"""
        Password Reset Request
        
        You requested to reset your password.
        
        Copy and paste this link to reset your password:
        {reset_url}
        
        This link will expire in 1 hour.
        
        If you didn't request this, please ignore this email.
        
        Best regards,
        The {settings.APP_NAME} Team
        """

        sent = EmailService.send_email(user_email, subject, html_content, text_content)

        return {"status": "sent" if sent else "skipped", "to": user_email}

    except Exception as e:
        logger.error(f"Failed to send password reset email to {user_email}: {e}")
        raise self.retry(exc=e, countdown=300)


@celery_app.task(bind=True, max_retries=3)
def send_event_invitation_email(self, user_email: str, event_name: str, event_url: str):
    """Send event invitation email"""
    try:
        subject = f"You're invited to {event_name}"

        html_content = f"""
        <html>
            <body>
                <h1>You're Invited!</h1>
                <p>You've been invited to join the event: <strong>{event_name}</strong></p>
                <p>Click the link below to view event details:</p>
                <p><a href="{event_url}">View Event</a></p>
                <br>
                <p>Best regards,<br>The {settings.APP_NAME} Team</p>
            </body>
        </html>
        """

        text_content = f"""
        You're Invited!
        
        You've been invited to join the event: {event_name}
        
        View event details:
        {event_url}
        
        Best regards,
        The {settings.APP_NAME} Team
        """

        sent = EmailService.send_email(user_email, subject, html_content, text_content)

        return {"status": "sent" if sent else "skipped", "to": user_email}

    except Exception as e:
        logger.error(f"Failed to send invitation email to {user_email}: {e}")
        raise self.retry(exc=e, countdown=300)


@celery_app.task(bind=True, max_retries=3)
def send_photo_share_email(self, user_email: str, photo_url: str, sender_name: str):
    """Send photo share notification email"""
    try:
        subject = f"{sender_name} shared a photo with you"

        html_content = f"""
        <html>
            <body>
                <h1>New Photo Shared!</h1>
                <p>{sender_name} shared a photo with you.</p>
                <p><img src="{photo_url}" style="max-width: 600px; height: auto;"></p>
                <p><a href="{photo_url}">View Full Size</a></p>
                <br>
                <p>Best regards,<br>The {settings.APP_NAME} Team</p>
            </body>
        </html>
        """

        text_content = f"""
        New Photo Shared!
        
        {sender_name} shared a photo with you.
        
        View photo: {photo_url}
        
        Best regards,
        The {settings.APP_NAME} Team
        """

        sent = EmailService.send_email(user_email, subject, html_content, text_content)

        return {"status": "sent" if sent else "skipped", "to": user_email}

    except Exception as e:
        logger.error(f"Failed to send photo share email to {user_email}: {e}")
        raise self.retry(exc=e, countdown=300)
