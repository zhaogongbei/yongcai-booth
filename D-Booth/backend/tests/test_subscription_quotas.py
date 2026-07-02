from datetime import datetime, timedelta, timezone

import pytest

from app.models.models import AITask, Photo, Team, User
from app.schemas.ai_task import AITaskCreate
from app.schemas.event import EventCreate
from app.services.ai_service import AIService
from app.services.event_service import EventService
from app.services.subscription_service import SubscriptionService


async def _create_team(db_session, slug: str = "quota-team"):
    from app.models.models import TeamMember, UserRole

    user = User(
        email=f"{slug}@example.com",
        hashed_password="not-used",
        is_active=True,
    )
    team = Team(name="Quota Team", slug=slug)
    db_session.add_all([user, team])
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(team)

    # Add user as team member (owner)
    team_member = TeamMember(
        team_id=team.id,
        user_id=user.id,
        role=UserRole.OWNER
    )
    db_session.add(team_member)
    await db_session.commit()

    return user, team


def _event_create(team_id):
    start = datetime.now(timezone.utc) + timedelta(days=1)
    return EventCreate(
        team_id=team_id,
        name="Quota Event",
        start_date=start,
        end_date=start + timedelta(hours=2),
    )


@pytest.mark.anyio
async def test_free_plan_blocks_second_event(db_session):
    user, team = await _create_team(db_session, "event-quota")
    service = EventService(db_session)

    event = await service.create_event(_event_create(team.id), user.id)

    assert event.team_id == team.id
    with pytest.raises(ValueError, match="Event quota exceeded"):
        await service.create_event(_event_create(team.id), user.id)


@pytest.mark.anyio
async def test_free_plan_blocks_photo_after_event_limit(db_session):
    user, team = await _create_team(db_session, "photo-quota")
    event = await EventService(db_session).create_event(_event_create(team.id), user.id)

    db_session.add_all(
        [
            Photo(
                event_id=event.id,
                original_url=f"https://example.com/photo-{index}.jpg",
            )
            for index in range(50)
        ]
    )
    await db_session.commit()

    service = SubscriptionService(db_session)
    with pytest.raises(ValueError, match="Photo quota exceeded"):
        await service.ensure_can_upload_photo(team.id, event.id)


@pytest.mark.anyio
async def test_free_plan_blocks_ai_task_after_monthly_limit(db_session):
    _, team = await _create_team(db_session, "ai-quota")
    db_session.add_all(
        [
            AITask(
                team_id=team.id,
                workflow="scene_generation",
                provider="openai",
                prompt=f"prompt {index}",
            )
            for index in range(10)
        ]
    )
    await db_session.commit()

    service = AIService(db_session)
    with pytest.raises(ValueError, match="AI credit quota exceeded"):
        await service.create_task(
            AITaskCreate(
                team_id=team.id,
                workflow="scene_generation",
                provider="openai",
                prompt="one more prompt",
            )
        )
