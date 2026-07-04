from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import AliasChoices, BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_team_member, get_current_active_user, get_db
from app.models.models import User
from app.services.email_service import email_service
from app.services.event_service import EventService
from app.services.sms_service import sms_service

router = APIRouter()


# Schemas
class WiFiSettings(BaseModel):
    ssid: str = ""
    password: str = ""
    encryption: str = "WPA2"


class SMTPSettings(BaseModel):
    host: str = ""
    port: int = 587
    user: str = ""
    password: str = ""
    from_email: EmailStr = "noreply@aibooth.app"
    use_tls: bool = True


class TwilioSettings(BaseModel):
    account_sid: str = ""
    auth_token: str = ""
    from_number: str = ""


class TemplateSettings(BaseModel):
    email_subject: str = "Your photo from {event_name}"
    email_body: str = """
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1>Hi there!</h1>
            <p>Thank you for participating in {event_name} on {date}.</p>
            <p>Your photo is ready:</p>
            {photos}
            <p><a href="{share_url}" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View and download all your photos</a></p>
            <p>We hope you had a great time!</p>
        </body>
    </html>
    """
    sms_message: str = "Hi! Your photo from {event_name} is ready: {share_url}"


class ShareSettings(BaseModel):
    enabled_channels: list[str] = ["qr", "email", "sms", "whatsapp"]
    wifi: WiFiSettings = WiFiSettings()
    smtp: SMTPSettings = SMTPSettings()
    twilio: TwilioSettings = TwilioSettings()
    templates: TemplateSettings = TemplateSettings()
    whatsapp_number: str = Field(
        default="",
        validation_alias=AliasChoices("whatsapp_number", "whatssapp_number"),
    )


class ShareSettingsResponse(ShareSettings):
    event_id: UUID


class TestEmailRequest(BaseModel):
    to_email: EmailStr
    event_id: UUID
    photo_urls: list[str] = Field(default_factory=list)
    share_url: str


class TestSMSRequest(BaseModel):
    to_phone: str
    event_id: UUID
    share_url: str
    country_code: str = "+86"


def normalize_share_settings(raw_settings: dict) -> dict:
    share_settings = dict(raw_settings)
    if "whatsapp_number" not in share_settings and "whatssapp_number" in share_settings:
        share_settings["whatsapp_number"] = share_settings.pop("whatssapp_number")
    return ShareSettings.model_validate(share_settings).model_dump()


@router.get("/settings/sharing/{event_id}", response_model=ShareSettingsResponse)
async def get_share_settings(
    event_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取活动的分享配置"""
    event_service = EventService(db)
    event = await event_service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    await check_team_member(event.team_id, current_user, db)

    # 从event.settings中获取分享配置，不存在则返回默认值
    settings = event.settings or {}
    share_settings = normalize_share_settings(settings.get("sharing", ShareSettings().model_dump()))

    return {"event_id": event_id, **share_settings}


@router.put("/settings/sharing/{event_id}", response_model=ShareSettingsResponse)
async def update_share_settings(
    event_id: UUID,
    settings: ShareSettings,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """更新活动的分享配置"""
    event_service = EventService(db)
    event = await event_service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    await check_team_member(event.team_id, current_user, db)

    # 更新配置
    event_settings = event.settings or {}
    event_settings["sharing"] = settings.model_dump()
    event.settings = event_settings

    await event_service.update_event(event_id, {"settings": event_settings})

    return {"event_id": event_id, **settings.model_dump()}


@router.post("/shares/email/test", status_code=status.HTTP_200_OK)
async def test_email_send(
    request: TestEmailRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """测试邮件发送"""
    event_service = EventService(db)
    event = await event_service.get_event(request.event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    await check_team_member(event.team_id, current_user, db)

    # 获取分享配置
    settings = event.settings or {}
    share_settings = normalize_share_settings(settings.get("sharing", ShareSettings().model_dump()))
    templates = share_settings.get("templates", TemplateSettings().model_dump())

    # 发送测试邮件
    success = await email_service.send_photo_email(
        to_email=request.to_email,
        subject=templates["email_subject"].format(event_name=event.name),
        html_body=templates["email_body"],
        photo_urls=request.photo_urls,
        share_url=request.share_url,
        event_name=event.name,
        date=event.start_date.strftime("%Y-%m-%d"),
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test email. Please check your SMTP configuration.",
        )

    return {"status": "success", "message": "Test email sent successfully"}


@router.post("/shares/sms/test", status_code=status.HTTP_200_OK)
async def test_sms_send(
    request: TestSMSRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """测试SMS发送"""
    event_service = EventService(db)
    event = await event_service.get_event(request.event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    await check_team_member(event.team_id, current_user, db)

    # 获取分享配置
    settings = event.settings or {}
    share_settings = normalize_share_settings(settings.get("sharing", ShareSettings().model_dump()))
    templates = share_settings.get("templates", TemplateSettings().model_dump())

    message = templates["sms_message"].format(event_name=event.name, share_url=request.share_url)

    success = await sms_service.send_photo_sms(
        to_phone=request.to_phone,
        message=message,
        share_url=request.share_url,
        country_code=request.country_code,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test SMS. Please check your Twilio configuration.",
        )

    return {"status": "success", "message": "Test SMS sent successfully"}
