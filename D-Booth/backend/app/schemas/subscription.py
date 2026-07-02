from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.models import SubscriptionStatus


# Base Subscription Schema
class SubscriptionBase(BaseModel):
    plan_name: str = Field(..., max_length=100)


# Subscription Create Schema
class SubscriptionCreate(SubscriptionBase):
    stripe_subscription_id: Optional[str] = Field(None, max_length=255)
    stripe_customer_id: Optional[str] = Field(None, max_length=255)


# Subscription Update Schema
class SubscriptionUpdate(BaseModel):
    status: Optional[SubscriptionStatus] = None
    plan_name: Optional[str] = Field(None, max_length=100)
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: Optional[bool] = None


# Subscription Response Schema
class SubscriptionResponse(SubscriptionBase):
    id: UUID
    status: SubscriptionStatus
    stripe_subscription_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Subscription Plan Schema
class SubscriptionPlan(BaseModel):
    id: str
    name: str
    price: float
    currency: str = "usd"
    interval: str = "month"  # "month", "year"
    features: list[str] = []
    limits: dict[str, Optional[int]] = {}


# Checkout Session Request
class CheckoutSessionRequest(BaseModel):
    plan_id: str
    team_id: UUID
    success_url: str
    cancel_url: str


# Checkout Session Response
class CheckoutSessionResponse(BaseModel):
    session_id: str
    checkout_url: str


# Subscription Usage Schema
class SubscriptionUsage(BaseModel):
    team_id: UUID
    plan_name: str
    current_period_start: datetime
    current_period_end: datetime
    usage: dict[str, int] = {}
    limits: dict[str, Optional[int]] = {}
    is_overused: bool = False


# Stripe Webhook Event Schema
class StripeWebhookEvent(BaseModel):
    type: str
    data: dict
