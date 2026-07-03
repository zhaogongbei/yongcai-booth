from decimal import Decimal
import sys
from types import SimpleNamespace

import pytest

from app.models.models import Team
from app.schemas.ai_task import AITaskCreate
from app.services.ai_service import AIService


@pytest.mark.anyio
async def test_create_task_schedules_generation_with_prompt_and_provider(db_session, monkeypatch):
    team = Team(name="AI Team", slug="ai-team")
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)

    calls = []
    fake_ai_tasks = SimpleNamespace(
        generate_ai_image=SimpleNamespace(delay=lambda *args: calls.append(args))
    )
    monkeypatch.setitem(sys.modules, "app.tasks.ai_tasks", fake_ai_tasks)

    service = AIService(db_session)
    task = await service.create_task(
        AITaskCreate(
            team_id=team.id,
            workflow="scene_generation",
            provider="openai",
            prompt="generate a booth scene",
        )
    )

    assert len(calls) == 1
    assert calls[0][0] == str(task.id)
    assert "Generate a realistic photo booth scene" in calls[0][1]
    assert "<<<USER_REQUEST>>>\ngenerate a booth scene\n<<</USER_REQUEST>>>" in calls[0][1]
    assert calls[0][2] == "openai"
    assert "Generate a realistic photo booth scene" in task.prompt
    assert task.status == "pending"
    assert task.estimated_cost == Decimal("0.20")


@pytest.mark.anyio
async def test_create_task_rejects_unsupported_workflow(db_session):
    team = Team(name="AI Invalid Workflow Team", slug="ai-invalid-workflow-team")
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)

    service = AIService(db_session)

    with pytest.raises(ValueError, match="Unsupported AI workflow"):
        await service.create_task(
            AITaskCreate(
                team_id=team.id,
                workflow="freeform_shell",
                provider="openai",
                prompt="do anything",
            )
        )


@pytest.mark.anyio
async def test_create_task_rejects_unsupported_provider(db_session):
    team = Team(name="AI Invalid Provider Team", slug="ai-invalid-provider-team")
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)

    service = AIService(db_session)

    with pytest.raises(ValueError, match="Unsupported AI provider"):
        await service.create_task(
            AITaskCreate(
                team_id=team.id,
                workflow="scene_generation",
                provider="replicate",
                prompt="generate a booth scene",
            )
        )


@pytest.mark.anyio
async def test_complete_task_writes_zero_actual_cost_and_clears_error(db_session, monkeypatch):
    team = Team(name="AI Team", slug="ai-team")
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)

    fake_ai_tasks = SimpleNamespace(
        generate_ai_image=SimpleNamespace(delay=lambda *args: None)
    )
    monkeypatch.setitem(sys.modules, "app.tasks.ai_tasks", fake_ai_tasks)

    service = AIService(db_session)
    task = await service.create_task(
        AITaskCreate(
            team_id=team.id,
            workflow="scene_generation",
            provider="openai",
            prompt="generate a booth scene",
        )
    )

    task.error_message = "previous error"
    await db_session.commit()

    completed = await service.complete_task(
        task.id,
        "https://example.com/result.png",
        Decimal("0"),
    )

    assert completed is not None
    assert completed.status == "completed"
    assert completed.progress == Decimal("100")
    assert completed.result_url == "https://example.com/result.png"
    assert completed.actual_cost == Decimal("0")
    assert completed.error_message is None
