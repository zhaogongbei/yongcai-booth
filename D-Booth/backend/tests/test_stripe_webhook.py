import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.anyio
async def test_stripe_webhook_requires_configured_secret(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "")

    response = await client.post(
        "/api/v1/subscriptions/webhooks/stripe",
        content=b'{"type":"customer.subscription.updated","data":{"object":{}}}',
        headers={"stripe-signature": "t=1,v1=fake"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["message"] == "Stripe webhook secret is not configured"
