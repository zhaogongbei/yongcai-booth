"""Regression tests for subscription team-access authorization.

Covers ``GET /api/v1/subscriptions/{id}`` which reads ``subscription.team.id``
to resolve the owning team. ``Subscription.team`` is configured
``lazy="joined"`` so this access must not trigger an async lazy-load
(``MissingGreenlet``) under a real async SQLAlchemy driver, and the route
must enforce team membership.
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
    """Register a user, log in, and create a team (caller becomes team owner)."""
    token = await _login(client, email)
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        response = await c.post("/api/v1/teams", json={"name": f"Team {slug}", "slug": slug})
    assert response.status_code == 201, response.text
    return token, response.json()["id"]


async def _attach_subscription(db_session, team_id: str) -> Subscription:
    subscription = Subscription(plan_name="pro", status=SubscriptionStatus.ACTIVE)
    db_session.add(subscription)
    await db_session.commit()
    await db_session.refresh(subscription)
    team = await db_session.get(Team, team_id)
    team.subscription_id = subscription.id
    await db_session.commit()
    return subscription


@pytest.mark.anyio
async def test_member_can_read_subscription(client, db_session):
    """Owner of the team owning the subscription can read it (200)."""
    token, team_id = await _create_team_owner(client, "sub-owner@example.com", "sub-owner-team")
    subscription = await _attach_subscription(db_session, team_id)

    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        response = await c.get(f"/api/v1/subscriptions/{subscription.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(subscription.id)


@pytest.mark.anyio
async def test_non_member_cannot_read_subscription(client, db_session):
    """A user authenticated but NOT a member of the owning team is denied (403)."""
    _, team_id = await _create_team_owner(client, "sub-owner-2@example.com", "sub-owner-team-2")
    subscription = await _attach_subscription(db_session, team_id)

    # Different user, never added to the owner's team.
    other_token = await _login(client, "sub-other-2@example.com")
    headers = {"Authorization": f"Bearer {other_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        response = await c.get(f"/api/v1/subscriptions/{subscription.id}")

    assert response.status_code == 403
