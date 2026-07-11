"""Regression tests for fail-closed Stripe subscription cancellation.

``POST /api/v1/subscriptions/{id}/cancel`` must never report success while
Stripe still has the subscription active: a swallowed Stripe error would
leave the customer being billed behind a locally "cancelled" status.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.models import Subscription, SubscriptionStatus, Team


async def _login(client: AsyncClient, email: str, password: str = "Pass123!@") -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email},
    )
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    return response.json()["access_token"]


async def _create_team_owner(client: AsyncClient, email: str, slug: str) -> tuple[str, str]:
    token = await _login(client, email)
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=headers
    ) as c:
        response = await c.post("/api/v1/teams", json={"name": f"Team {slug}", "slug": slug})
    assert response.status_code == 201, response.text
    return token, response.json()["id"]


async def _attach_stripe_subscription(db_session, team_id: str) -> Subscription:
    subscription = Subscription(
        plan_name="pro",
        status=SubscriptionStatus.ACTIVE,
        stripe_subscription_id="sub_test_123",
    )
    db_session.add(subscription)
    await db_session.commit()
    await db_session.refresh(subscription)
    team = await db_session.get(Team, team_id)
    team.subscription_id = subscription.id
    await db_session.commit()
    return subscription


@pytest.mark.anyio
async def test_cancel_fails_closed_when_stripe_rejects(client, db_session, monkeypatch):
    """Stripe error => HTTP 502 and the local subscription stays ACTIVE."""
    import stripe

    token, team_id = await _create_team_owner(client, "cancel-fail@example.com", "cancel-fail-team")
    subscription = await _attach_stripe_subscription(db_session, team_id)

    def _reject(*args, **kwargs):
        raise RuntimeError("stripe unreachable")

    monkeypatch.setattr(stripe.Subscription, "modify", _reject)
    monkeypatch.setattr(stripe.Subscription, "delete", _reject)

    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=headers
    ) as c:
        response = await c.post(f"/api/v1/subscriptions/{subscription.id}/cancel")

    assert response.status_code == 502

    await db_session.refresh(subscription)
    assert subscription.status == SubscriptionStatus.ACTIVE


@pytest.mark.anyio
async def test_cancel_succeeds_when_stripe_accepts(client, db_session, monkeypatch):
    """Stripe accepting the cancellation lets the local cancel proceed."""
    import stripe

    token, team_id = await _create_team_owner(client, "cancel-ok@example.com", "cancel-ok-team")
    subscription = await _attach_stripe_subscription(db_session, team_id)

    calls: list[tuple] = []

    def _accept(*args, **kwargs):
        calls.append((args, kwargs))
        return {"id": "sub_test_123"}

    monkeypatch.setattr(stripe.Subscription, "modify", _accept)

    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=headers
    ) as c:
        response = await c.post(f"/api/v1/subscriptions/{subscription.id}/cancel")

    assert response.status_code == 200, response.text
    assert calls, "Stripe cancellation must actually be attempted"
