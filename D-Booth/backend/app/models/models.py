from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text, Enum as SQLEnum, Numeric, JSON, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.core.database import Base
from app.models.types import GUID


# Enums
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    OWNER = "owner"
    MEMBER = "member"


class EventStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PrintJobStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PRINTING = "printing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"


class PropCategory(str, enum.Enum):
    HOLIDAY = "节日"
    WEDDING = "婚礼"
    BIRTHDAY = "生日"
    ANIMAL = "动物"
    GLASSES = "眼镜"
    HAT = "帽子"
    BEARD = "胡须"
    CUSTOM = "自定义"


class BoothStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"


# Trigger enums
class TriggerType(str, enum.Enum):
    SESSION_START = "session_start"
    COUNTDOWN_START = "countdown_start"
    CAPTURE_START = "capture_start"
    FILE_DOWNLOAD = "file_download"
    PROCESSING_START = "processing_start"
    SHARING_SCREEN = "sharing_screen"
    SESSION_END = "session_end"
    PRINTING = "printing"


class TriggerAction(str, enum.Enum):
    HTTP_CALLBACK = "http_callback"   # POST到URL
    APP_EXECUTE = "app_execute"       # 执行本地程序


# Base model with common fields
class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# User Model
class User(Base, TimestampMixin):
    __tablename__ = "users"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Relationships
    team_members = relationship("TeamMember", back_populates="user", lazy="selectin")
    events = relationship("Event", back_populates="creator", lazy="selectin")


# Team Model
class Team(Base, TimestampMixin):
    __tablename__ = "teams"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True)
    description = Column(Text)
    subscription_id = Column(GUID(), ForeignKey("subscriptions.id"))
    
    # Relationships
    members = relationship("TeamMember", back_populates="team", lazy="selectin")
    events = relationship("Event", back_populates="team", lazy="selectin")
    templates = relationship("Template", back_populates="team", lazy="selectin")
    subscription = relationship("Subscription", back_populates="team", lazy="joined")


# TeamMember Model
class TeamMember(Base, TimestampMixin):
    __tablename__ = "team_members"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    team_id = Column(GUID(), ForeignKey("teams.id"), nullable=False)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.MEMBER)
    
    # Indexes
    __table_args__ = (
        UniqueConstraint('team_id', 'user_id', name='uq_team_member_team_user'),
        Index('ix_team_member_team_id', 'team_id'),
        Index('ix_team_member_user_id', 'user_id'),
    )
    
    # Relationships — use selectin/joined; never rely on default lazy="select"
    # which raises MissingGreenlet in async sessions.
    team = relationship("Team", back_populates="members", lazy="selectin")
    user = relationship("User", back_populates="team_members", lazy="selectin")


# Signature Model
class Signature(Base, TimestampMixin):
    __tablename__ = "signatures"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    session_id = Column(GUID(), ForeignKey("photo_sessions.id"), nullable=False)
    signature_url = Column(String(500), nullable=False)

    # Relationships
    session = relationship("PhotoSession", back_populates="signatures")


# SurveyQuestion - used as JSON column in Survey model
class SurveyQuestion:
    """Survey question structure stored as JSON"""
    def __init__(self, id: str, type: str, text: str, required: bool = True,
                 options: list = None, order: int = 0):
        self.id = id
        self.type = type
        self.text = text
        self.required = required
        self.options = options or []
        self.order = order


# Survey Model
class Survey(Base, TimestampMixin):
    __tablename__ = "surveys"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    event_id = Column(GUID(), ForeignKey("events.id"), nullable=False, unique=True)
    enabled = Column(Boolean, default=True)
    title = Column(String(255), default="问卷调查")
    questions = Column(JSON, default=list)

    # Relationships
    event = relationship("Event", lazy="joined")


# SurveyResponse Model
class SurveyResponse(Base, TimestampMixin):
    __tablename__ = "survey_responses"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    event_id = Column(GUID(), ForeignKey("events.id"), nullable=False)
    session_id = Column(GUID(), ForeignKey("photo_sessions.id"), nullable=False)
    answers = Column(JSON, default=dict)


# Disclaimer Model
class Disclaimer(Base, TimestampMixin):
    __tablename__ = "disclaimers"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    event_id = Column(GUID(), ForeignKey("events.id"), nullable=False, unique=True)
    enabled = Column(Boolean, default=True)
    title = Column(String(255), default="免责声明")
    text = Column(Text, default="")
    require_signature = Column(Boolean, default=False)

    # Relationships
    event = relationship("Event", lazy="joined")


# DisclaimerAcceptance Model
class DisclaimerAcceptance(Base, TimestampMixin):
    __tablename__ = "disclaimer_acceptances"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    event_id = Column(GUID(), ForeignKey("events.id"), nullable=False)
    session_id = Column(GUID(), ForeignKey("photo_sessions.id"), nullable=False)


# Event Model
class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    team_id = Column(GUID(), ForeignKey("teams.id"), nullable=False)
    creator_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    event_type = Column(String(50))
    status = Column(SQLEnum(EventStatus), default=EventStatus.DRAFT)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    venue_name = Column(String(255))
    venue_address = Column(Text)
    settings = Column(JSON)

    # Indexes
    __table_args__ = (
        Index('ix_event_team_status', 'team_id', 'status'),
        Index('ix_event_creator_id', 'creator_id'),
    )

    # Relationships
    team = relationship("Team", back_populates="events", lazy="joined")
    creator = relationship("User", back_populates="events", lazy="joined")
    photos = relationship("Photo", back_populates="event", lazy="selectin")
    sessions = relationship("PhotoSession", back_populates="event", lazy="selectin")
    survey = relationship("Survey", back_populates="event", lazy="joined", uselist=False)
    disclaimer = relationship("Disclaimer", back_populates="event", lazy="joined", uselist=False)


# Template Model
class Template(Base, TimestampMixin):
    __tablename__ = "templates"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    team_id = Column(GUID(), ForeignKey("teams.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    size = Column(String(50))
    canvas_width = Column(Numeric)
    canvas_height = Column(Numeric)
    layers = Column(JSON)
    thumbnail_url = Column(String(500))
    is_public = Column(Boolean, default=False)
    
    # Relationships
    team = relationship("Team", back_populates="templates", lazy="selectin")


# PhotoSession Model
class PhotoSession(Base, TimestampMixin):
    __tablename__ = "photo_sessions"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    event_id = Column(GUID(), ForeignKey("events.id"), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    event = relationship("Event", back_populates="sessions", lazy="joined")
    photos = relationship("Photo", back_populates="session", lazy="selectin")
    signatures = relationship("Signature", back_populates="session", lazy="selectin")


# Photo Model
class Photo(Base, TimestampMixin):
    __tablename__ = "photos"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    event_id = Column(GUID(), ForeignKey("events.id"), nullable=False)
    session_id = Column(GUID(), ForeignKey("photo_sessions.id"))
    original_url = Column(String(500), nullable=False)
    processed_url = Column(String(500))
    thumbnail_url = Column(String(500))
    file_size = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    metadata_ = Column("metadata", JSON)
    
    # Indexes
    __table_args__ = (
        Index('ix_photo_event_id', 'event_id'),
        Index('ix_photo_session_id', 'session_id'),
    )
    
    # Relationships
    event = relationship("Event", back_populates="photos", lazy="joined")
    session = relationship("PhotoSession", back_populates="photos", lazy="joined")
    print_jobs = relationship("PrintJob", back_populates="photo", lazy="selectin")
    shares = relationship("Share", back_populates="photo", lazy="selectin")


# PrintJob Model
class PrintJob(Base, TimestampMixin):
    __tablename__ = "print_jobs"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    photo_id = Column(GUID(), ForeignKey("photos.id"), nullable=False)
    printer_name = Column(String(255))
    copies = Column(Integer, default=1)
    status = Column(SQLEnum(PrintJobStatus), default=PrintJobStatus.PENDING)
    error_message = Column(Text)
    printed_at = Column(DateTime(timezone=True))
    
    # Indexes
    __table_args__ = (
        Index('ix_print_job_photo_id', 'photo_id'),
        Index('ix_print_job_status', 'status'),
    )
    
    # Relationships
    photo = relationship("Photo", back_populates="print_jobs", lazy="selectin")


# Share Model
class Share(Base, TimestampMixin):
    __tablename__ = "shares"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    photo_id = Column(GUID(), ForeignKey("photos.id"), nullable=False)
    channel = Column(String(50), nullable=False)
    recipient = Column(String(255))
    short_code = Column(String(20), unique=True, index=True)
    full_url = Column(String(500))
    view_count = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True))
    
    # Relationships
    photo = relationship("Photo", back_populates="shares", lazy="selectin")


# AITask Model
class AITask(Base, TimestampMixin):
    __tablename__ = "ai_tasks"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    team_id = Column(GUID(), ForeignKey("teams.id"), nullable=False)
    workflow = Column(String(50), nullable=False)
    provider = Column(String(50), nullable=False)
    prompt = Column(Text, nullable=False)
    parameters = Column(JSON)
    status = Column(String(50), default="pending")
    progress = Column(Numeric, default=0)
    result_url = Column(String(500))
    error_message = Column(Text)
    estimated_cost = Column(Numeric)
    actual_cost = Column(Numeric)


# AnalyticsEvent Model
class AnalyticsEvent(Base, TimestampMixin):
    __tablename__ = "analytics_events"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    team_id = Column(GUID(), ForeignKey("teams.id"), nullable=False)
    event_id = Column(GUID(), ForeignKey("events.id"))
    event_type = Column(String(50), nullable=False)
    properties = Column(JSON)
    user_id = Column(GUID())
    session_id = Column(String(255))


# Subscription Model
class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    plan_name = Column(String(100), nullable=False)
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    stripe_subscription_id = Column(String(255), unique=True)
    stripe_customer_id = Column(String(255))
    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))
    cancel_at_period_end = Column(Boolean, default=False)

    # Relationships
    team = relationship("Team", back_populates="subscription", uselist=False)


# Prop Model
class Prop(Base, TimestampMixin):
    __tablename__ = "props"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    team_id = Column(GUID(), ForeignKey("teams.id"), nullable=True)
    name = Column(String(255), nullable=False)
    category = Column(SQLEnum(PropCategory), nullable=False)
    image_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=False)
    is_public = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)
    tags = Column(JSON, default=list)

    # Indexes
    __table_args__ = (
        Index('ix_prop_team_id', 'team_id'),
        Index('ix_prop_category', 'category'),
        Index('ix_prop_is_public', 'is_public'),
    )

    # Relationships
    team = relationship("Team", lazy="joined")


# Booth Model
class Booth(Base, TimestampMixin):
    __tablename__ = "booths"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    team_id = Column(GUID(), ForeignKey("teams.id"), nullable=False)
    name = Column(String(255), nullable=False)
    device_id = Column(String(255), unique=True, index=True, nullable=False)
    status = Column(SQLEnum(BoothStatus), default=BoothStatus.OFFLINE)
    version = Column(String(50))
    last_heartbeat = Column(DateTime(timezone=True))
    ip_address = Column(String(50))
    os_info = Column(String(255))
    current_event_id = Column(GUID(), ForeignKey("events.id"), nullable=True)
    config_hash = Column(String(64))  # SHA256 hash of current configuration

    # Indexes
    __table_args__ = (
        Index('ix_booth_team_id', 'team_id'),
        Index('ix_booth_device_id', 'device_id'),
        Index('ix_booth_status', 'status'),
    )

    # Relationships
    team = relationship("Team", lazy="joined")
    current_event = relationship("Event", lazy="joined")


# Trigger Configuration Model
class TriggerConfig(Base, TimestampMixin):
    __tablename__ = "trigger_configs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    event_id = Column(GUID(), ForeignKey("events.id"), nullable=False)
    event_type = Column(SQLEnum(TriggerType), nullable=False)
    enabled = Column(Boolean, default=False)
    action_type = Column(SQLEnum(TriggerAction), nullable=False)
    target = Column(String(500), nullable=False)  # URL或可执行文件路径
    payload_template = Column(JSON, default=dict)  # 自定义payload
    timeout = Column(Integer, default=10)
    retry = Column(Integer, default=3)

    # Relationships
    event = relationship("Event", lazy="joined")

    # Indexes
    __table_args__ = (
        Index('ix_trigger_config_event_id', 'event_id'),
        Index('ix_trigger_config_event_type', 'event_type'),
    )


# Trigger Log Model
class TriggerLog(Base, TimestampMixin):
    __tablename__ = "trigger_logs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    trigger_id = Column(GUID(), ForeignKey("trigger_configs.id"), nullable=False)
    event_id = Column(GUID(), ForeignKey("events.id"), nullable=False)
    event_type = Column(SQLEnum(TriggerType), nullable=False)
    success = Column(Boolean, nullable=False)
    response_status = Column(Integer)  # HTTP status code or exit code
    response_data = Column(Text)  # Response content or error message
    duration_ms = Column(Integer)  # Execution time in milliseconds
    attempt_count = Column(Integer, default=1)

    # Relationships
    trigger = relationship("TriggerConfig", lazy="joined")
    event = relationship("Event", lazy="joined")

    # Indexes
    __table_args__ = (
        Index('ix_trigger_log_event_id', 'event_id'),
        Index('ix_trigger_log_trigger_id', 'trigger_id'),
        Index('ix_trigger_log_event_type', 'event_type'),
    )


# Webhook Model
class Webhook(Base, TimestampMixin):
    __tablename__ = "webhooks"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    team_id = Column(GUID(), ForeignKey("teams.id"), nullable=False)
    url = Column(String(500), nullable=False)
    events = Column(JSON, default=list)  # ["photo.created", "print.completed", ...]
    secret = Column(String(255), nullable=False)  # HMAC签名密钥
    enabled = Column(Boolean, default=True)

    # Relationships
    team = relationship("Team", lazy="joined")

    # Indexes
    __table_args__ = (
        Index('ix_webhook_team_id', 'team_id'),
        Index('ix_webhook_enabled', 'enabled'),
    )


# Webhook Log Model
class WebhookLog(Base, TimestampMixin):
    __tablename__ = "webhook_logs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    webhook_id = Column(GUID(), ForeignKey("webhooks.id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    payload = Column(JSON, default=dict)
    success = Column(Boolean, nullable=False)
    response_status = Column(Integer)
    response_data = Column(Text)
    duration_ms = Column(Integer)
    attempt_count = Column(Integer, default=1)
    signature = Column(String(255))

    # Relationships
    webhook = relationship("Webhook", lazy="joined")

    # Indexes
    __table_args__ = (
        Index('ix_webhook_log_webhook_id', 'webhook_id'),
        Index('ix_webhook_log_event_type', 'event_type'),
    )
