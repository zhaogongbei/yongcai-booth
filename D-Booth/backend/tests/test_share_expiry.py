"""Regression tests for public share-code expiry enforcement.

``GET /api/v1/shares/code/{short_code}`` is a public, unauthenticated
endpoint. Expiry must be enforced on the read path itself (fail closed) —
the hourly Celery cleanup task is best-effort and must never be the only
gate keeping expired guest-photo links inaccessible.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.models import Event, Photo, Share, Team, TeamMember, User, UserRole


async def _create_share(db_session, *, short_code: str, expires_at) -> Share:
    user = User(
        email=f"{short_code}@example.com",
        hashed_password="not-used",
        full_name="Share Owner",
    )
    db_session.add(user)
    await db_session.flush()

    team = Team(name=f"Team {short_code}", slug=f"team-{short_code}")
    db_session.add(team)
    await db_session.flush()

    db_session.add(TeamMember(team_id=team.id, user_id=user.id, role=UserRole.OWNER))
    event = Event(
        team_id=team.id,
        creator_id=user.id,
        name="Share Expiry Event",
        start_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    db_session.add(event)
    await db_session.flush()

    photo = Photo(event_id=event.id, original_url="/uploads/share-expiry.jpg")
    db_session.add(photo)
    await db_session.flush()

    share = Share(
        photo_id=photo.id,
        channel="link",
        short_code=short_code,
        full_url=f"https://aibooth.app/s/{short_code}",
        expires_at=expires_at,
    )
    db_session.add(share)
    await db_session.commit()
    await db_session.refresh(share)
    return share


@pytest.mark.anyio
async def test_expired_share_code_returns_404(client, db_session):
    """An expired share code must be treated as absent on the public endpoint."""
    await _create_share(
        db_session,
        short_code="expired01",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    response = await client.get("/api/v1/shares/code/expired01")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_active_share_code_is_served(client, db_session):
    """A share code with a future expiry stays publicly readable."""
    share = await _create_share(
        db_session,
        short_code="active01",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    response = await client.get("/api/v1/shares/code/active01")

    assert response.status_code == 200
    assert response.json()["id"] == str(share.id)


@pytest.mark.anyio
async def test_share_code_without_expiry_is_served(client, db_session):
    """A share without expires_at is permanent and stays readable."""
    share = await _create_share(db_session, short_code="forever01", expires_at=None)

    response = await client.get("/api/v1/shares/code/forever01")

    assert response.status_code == 200
    assert response.json()["id"] == str(share.id)
