import asyncio
import logging
import re
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException
except ImportError:
    Client = None
    TwilioRestException = Exception
    logger.warning("twilio is not installed, SMS service unavailable")

class SMSService:
    def __init__(self):
        self.account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
        self.auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
        self.from_number = getattr(settings, "TWILIO_FROM_NUMBER", None)
        self.client = None

        if Client and all([self.account_sid, self.auth_token, self.from_number]):
            try:
                self.client = Client(self.account_sid, self.auth_token)
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {str(e)}")

    def _validate_phone_number(self, phone_number: str, country_code: str = "+86") -> bool:
        """简单验证手机号格式"""
        cleaned_number = re.sub(r'\D', '', phone_number)
        if country_code == "+86":
            return len(cleaned_number) == 11 and cleaned_number.startswith('1')
        # 其他国家号码简单验证
        return len(cleaned_number) >= 8 and len(cleaned_number) <= 15

    async def send_photo_sms(
        self,
        to_phone: str,
        message: str,
        share_url: str,
        country_code: str = "+86"
    ) -> bool:
        if not self.client:
            logger.warning("Twilio not configured, cannot send SMS")
            return False

        if not self._validate_phone_number(to_phone, country_code):
            logger.warning(f"Invalid phone number: {to_phone}")
            return False

        try:
            full_message = f"{message}\n{share_url}"
            full_to = f"{country_code}{to_phone.lstrip('+')}"

            # 使用run_in_executor包装同步Twilio调用，防止阻塞事件循环
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.messages.create(
                    body=full_message,
                    from_=self.from_number,
                    to=full_to
                )
            )

            logger.info(f"SMS sent successfully to {full_to}")
            return True

        except TwilioRestException as e:
            logger.error(f"Twilio API error when sending SMS: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_phone}: {str(e)}")
            return False

sms_service = SMSService()
