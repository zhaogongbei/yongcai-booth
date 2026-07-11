from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect

from app.models.models import (
    DisclaimerAcceptance,
    Event,
    EventStatus,
    Photo,
    PrintJob,
    Share,
    Signature,
    SurveyResponse,
    Team,
    TeamMember,
    User,
    UserRole,
)
from app.schemas.share import ShareCreate
from app.services.analytics_service import AnalyticsService
from app.services.event_service import EventService
from app.services.share_service import ShareService


def test_leaf_record_relationships_break_recursive_eager_loading() -> None:
    relationship_boundaries = {
        Signature: ("session",),
        SurveyResponse: ("event", "session", "survey"),
        DisclaimerAcceptance: ("event", "session", "disclaimer"),
        Share: ("photo",),
    }

    for model, relationship_names in relationship_boundaries.items():
        relationships = inspect(model).relationships
        for relationship_name in relationship_names:
            assert relationships[relationship_name].lazy == "noload"


@pytest.mark.anyio
async def test_create_share_sets_default_expiration(db_session):
    user = User(
        email="share-owner@example.com",
        hashed_password="not-used",
        full_name="Share Owner",
    )
    db_session.add(user)
    await db_session.flush()

    team = Team(name="Share Runtime Team", slug="share-runtime-team")
    db_session.add(team)
    await db_session.flush()

    db_session.add(TeamMember(team_id=team.id, user_id=user.id, role=UserRole.OWNER))
    event = Event(
        team_id=team.id,
        creator_id=user.id,
        name="Share Runtime Event",
        start_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    db_session.add(event)
    await db_session.flush()

    photo = Photo(
        event_id=event.id,
        original_url="https://example.com/photo.jpg",
        file_size=1234,
        width=100,
        height=100,
    )
    db_session.add(photo)
    await db_session.commit()

    share = await ShareService(db_session).create_share(
        ShareCreate(photo_id=photo.id, channel="link")
    )

    assert share.expires_at is not None
    expires_at = share.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    assert expires_at > datetime.now(timezone.utc)
    assert share.full_url.endswith(f"/s/{share.short_code}")


@pytest.mark.anyio
async def test_photo_stats_aggregates_without_runtime_error(db_session):
    user = User(
        email="analytics-owner@example.com",
        hashed_password="not-used",
        full_name="Analytics Owner",
    )
    db_session.add(user)
    await db_session.flush()

    team = Team(name="Analytics Runtime Team", slug="analytics-runtime-team")
    db_session.add(team)
    await db_session.flush()

    db_session.add(TeamMember(team_id=team.id, user_id=user.id, role=UserRole.OWNER))
    event = Event(
        team_id=team.id,
        creator_id=user.id,
        name="Analytics Runtime Event",
        start_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    db_session.add(event)
    await db_session.flush()

    db_session.add_all(
        [
            Photo(
                event_id=event.id,
                original_url="https://example.com/photo-1.jpg",
                file_size=100,
                width=100,
                height=100,
            ),
            Photo(
                event_id=event.id,
                original_url="https://example.com/photo-2.jpg",
                file_size=250,
                width=100,
                height=100,
            ),
        ]
    )
    await db_session.commit()

    stats = await AnalyticsService(db_session).get_photo_stats(
        team.id,
        datetime(2026, 7, 1, tzinfo=timezone.utc),
        datetime(2026, 7, 3, tzinfo=timezone.utc),
    )

    assert stats["team_id"] == str(team.id)
    assert stats["total_photos"] == 2
    assert stats["total_size_bytes"] == 350
    assert stats["total_events"] == 1


@pytest.mark.anyio
async def test_analytics_overview_includes_business_metrics(db_session):
    user = User(
        email="overview-owner@example.com",
        hashed_password="not-used",
        full_name="Overview Owner",
    )
    db_session.add(user)
    await db_session.flush()

    team = Team(name="Overview Team", slug="overview-team")
    db_session.add(team)
    await db_session.flush()

    db_session.add(TeamMember(team_id=team.id, user_id=user.id, role=UserRole.OWNER))
    event = Event(
        team_id=team.id,
        creator_id=user.id,
        name="Overview Event",
        status=EventStatus.ACTIVE,
        start_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    db_session.add(event)
    await db_session.flush()

    photo_one = Photo(
        event_id=event.id,
        original_url="https://example.com/photo-1.jpg",
        file_size=100,
        width=100,
        height=100,
    )
    photo_two = Photo(
        event_id=event.id,
        original_url="https://example.com/photo-2.jpg",
        file_size=250,
        width=100,
        height=100,
    )
    db_session.add_all([photo_one, photo_two])
    await db_session.flush()

    db_session.add(PrintJob(photo_id=photo_one.id, copies=1))
    db_session.add(Share(photo_id=photo_two.id, channel="link", short_code="ovr123"))
    await db_session.commit()

    overview = await AnalyticsService(db_session).get_overview(
        team.id,
        datetime(2026, 7, 1, tzinfo=timezone.utc),
        datetime(2026, 7, 3, tzinfo=timezone.utc),
    )

    assert overview["total_photos"] == 2
    assert overview["total_prints"] == 1
    assert overview["total_shares"] == 1
    assert overview["active_events"] == 1
    assert overview["storage_used"] == 350
    assert overview["estimated_revenue"] == 0


@pytest.mark.anyio
async def test_event_statistics_counts_prints_and_shares(db_session):
    user = User(
        email="event-stats-owner@example.com",
        hashed_password="not-used",
        full_name="Event Stats Owner",
    )
    db_session.add(user)
    await db_session.flush()

    team = Team(name="Event Stats Team", slug="event-stats-team")
    db_session.add(team)
    await db_session.flush()

    db_session.add(TeamMember(team_id=team.id, user_id=user.id, role=UserRole.OWNER))
    event = Event(
        team_id=team.id,
        creator_id=user.id,
        name="Event Stats Event",
        start_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    db_session.add(event)
    await db_session.flush()

    photo = Photo(
        event_id=event.id,
        original_url="https://example.com/event-stats-photo.jpg",
        file_size=100,
        width=100,
        height=100,
    )
    db_session.add(photo)
    await db_session.flush()

    db_session.add(PrintJob(photo_id=photo.id, copies=1))
    db_session.add(Share(photo_id=photo.id, channel="link", short_code="evt123"))
    await db_session.commit()

    stats = await EventService(db_session).get_event_statistics(event.id)

    assert stats.total_photos == 1
    assert stats.total_prints == 1
    assert stats.total_shares == 1
