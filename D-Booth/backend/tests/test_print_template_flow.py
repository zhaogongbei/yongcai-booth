import base64
from datetime import datetime, timezone
from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import select

from app.api.v1 import print_jobs as print_jobs_api
from app.models.models import (
    Event,
    Photo,
    PhotoSession,
    PrintJob,
    PrintJobStatus,
    Team,
    TeamMember,
    Template,
    User,
    UserRole,
)
from app.services.print_service import PrintService
from app.services.printer_driver_service import PrinterDriverService


def _image_data_url(color: str) -> str:
    image = Image.new("RGB", (24, 24), color)
    buf = BytesIO()
    image.save(buf, format="JPEG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


async def _create_user_team_event(db_session, email: str = "print-owner@example.com"):
    user = User(email=email, hashed_password="not-used", full_name="Print Owner")
    db_session.add(user)
    await db_session.flush()

    team = Team(name=f"Team {email}", slug=email.replace("@", "-").replace(".", "-"))
    db_session.add(team)
    await db_session.flush()

    db_session.add(TeamMember(team_id=team.id, user_id=user.id, role=UserRole.OWNER))
    event = Event(
        team_id=team.id,
        creator_id=user.id,
        name="Print Template Event",
        start_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    db_session.add(event)
    await db_session.flush()
    return user, team, event


def _template_layers() -> dict:
    return {
        "id": "layout-test",
        "name": "Two Up",
        "paperSize": {"width": 25.4, "height": 25.4},
        "resolution": 100,
        "orientation": "portrait",
        "background": {"type": "color", "value": "#ffffff"},
        "elements": [
            {
                "id": "photo-1",
                "type": "photo",
                "x": 0,
                "y": 0,
                "width": 50,
                "height": 100,
                "rotation": 0,
                "opacity": 1,
                "zIndex": 1,
                "locked": False,
                "visible": True,
                "props": {"photoNumber": 1, "cropMode": "fill", "borderRadius": 0},
            },
            {
                "id": "photo-2",
                "type": "photo",
                "x": 50,
                "y": 0,
                "width": 50,
                "height": 100,
                "rotation": 0,
                "opacity": 1,
                "zIndex": 2,
                "locked": False,
                "visible": True,
                "props": {"photoNumber": 2, "cropMode": "fill", "borderRadius": 0},
            },
        ],
    }


@pytest.mark.anyio
async def test_execute_print_job_renders_selected_template(db_session, monkeypatch):
    _, team, event = await _create_user_team_event(db_session)
    session = PhotoSession(event_id=event.id)
    db_session.add(session)
    await db_session.flush()

    first = Photo(event_id=event.id, session_id=session.id, original_url=_image_data_url("red"))
    second = Photo(event_id=event.id, session_id=session.id, original_url=_image_data_url("blue"))
    template = Template(team_id=team.id, name="Two Up", layers=_template_layers())
    db_session.add_all([first, second, template])
    await db_session.flush()

    job = PrintJob(
        photo_id=first.id, template_id=template.id, printer_name="Booth Printer", copies=1
    )
    db_session.add(job)
    await db_session.commit()

    printed = {}

    async def ready(_printer_name):
        return "ready"

    async def capture_file(printer_name, file_path, copies=1):
        printed["printer_name"] = printer_name
        printed["copies"] = copies
        with open(file_path, "rb") as f:
            printed["bytes"] = f.read()
        return True

    monkeypatch.setattr(PrinterDriverService, "get_printer_status", ready)
    monkeypatch.setattr(PrinterDriverService, "print_file", capture_file)

    result = await PrintService(db_session).execute_print_job(job.id)
    refreshed = await db_session.get(PrintJob, job.id)
    assert result is True, refreshed.error_message if refreshed else "print job missing"

    rendered = Image.open(BytesIO(printed["bytes"]))
    assert rendered.size == (100, 100)
    assert rendered.getpixel((25, 50))[0] > rendered.getpixel((25, 50))[2]
    assert rendered.getpixel((75, 50))[2] > rendered.getpixel((75, 50))[0]

    assert refreshed.status == PrintJobStatus.COMPLETED


@pytest.mark.anyio
async def test_execute_print_job_fails_when_no_printer_available(db_session, monkeypatch):
    _, _, event = await _create_user_team_event(db_session, "print-no-printer@example.com")
    photo = Photo(event_id=event.id, original_url=_image_data_url("red"))
    db_session.add(photo)
    await db_session.flush()
    job = PrintJob(photo_id=photo.id, copies=1)
    db_session.add(job)
    await db_session.commit()

    async def no_printers():
        return []

    monkeypatch.setattr(PrinterDriverService, "discover_printers", no_printers)

    result = await PrintService(db_session).execute_print_job(job.id)
    refreshed = await db_session.get(PrintJob, job.id)

    assert result is False
    assert refreshed.status == PrintJobStatus.FAILED
    assert refreshed.error_message == "No available printer found"


@pytest.mark.anyio
async def test_execute_print_job_fails_when_printer_not_ready(db_session, monkeypatch):
    _, _, event = await _create_user_team_event(db_session, "print-offline@example.com")
    photo = Photo(event_id=event.id, original_url=_image_data_url("red"))
    db_session.add(photo)
    await db_session.flush()
    job = PrintJob(photo_id=photo.id, printer_name="Offline Printer", copies=1)
    db_session.add(job)
    await db_session.commit()

    async def offline(_printer_name):
        return "offline"

    monkeypatch.setattr(PrinterDriverService, "get_printer_status", offline)

    result = await PrintService(db_session).execute_print_job(job.id)
    refreshed = await db_session.get(PrintJob, job.id)

    assert result is False
    assert refreshed.status == PrintJobStatus.FAILED
    assert "not available" in refreshed.error_message


@pytest.mark.anyio
async def test_execute_print_job_is_claimed_once(db_session, monkeypatch):
    """A job already advanced past PENDING/QUEUED cannot be re-claimed and reprinted."""
    _, _, event = await _create_user_team_event(db_session, "print-claim@example.com")
    photo = Photo(event_id=event.id, original_url=_image_data_url("red"))
    db_session.add(photo)
    await db_session.flush()
    job = PrintJob(photo_id=photo.id, printer_name="Booth Printer", copies=1)
    db_session.add(job)
    await db_session.commit()

    print_calls = {"count": 0}

    async def ready(_printer_name):
        return "ready"

    async def count_print(printer_name, file_path, copies=1):
        print_calls["count"] += 1
        return True

    monkeypatch.setattr(PrinterDriverService, "get_printer_status", ready)
    monkeypatch.setattr(PrinterDriverService, "print_file", count_print)

    service = PrintService(db_session)
    first = await service.execute_print_job(job.id)
    # A second execution of the same (now COMPLETED) job must not print again.
    second = await service.execute_print_job(job.id)

    refreshed = await db_session.get(PrintJob, job.id)
    assert first is True
    assert second is False
    assert print_calls["count"] == 1
    assert refreshed.status == PrintJobStatus.COMPLETED


@pytest.mark.anyio
async def test_start_printing_claim_is_compare_and_swap(db_session):
    """claim_for_printing only succeeds from PENDING/QUEUED, and only once."""
    _, _, event = await _create_user_team_event(db_session, "print-cas@example.com")
    photo = Photo(event_id=event.id, original_url=_image_data_url("red"))
    db_session.add(photo)
    await db_session.flush()
    job = PrintJob(photo_id=photo.id, printer_name="Booth Printer", copies=1)
    db_session.add(job)
    await db_session.commit()

    service = PrintService(db_session)
    claimed = await service.start_printing(job.id)
    reclaimed = await service.start_printing(job.id)

    assert claimed is not None
    assert claimed.status == PrintJobStatus.PRINTING
    assert reclaimed is None


@pytest.mark.anyio
async def test_create_print_job_accepts_same_team_template(
    authenticated_client, db_session, monkeypatch
):
    user = (
        await db_session.execute(select(User).where(User.email == "test@example.com"))
    ).scalar_one()
    team = Team(name="Print API Team", slug="print-api-team")
    db_session.add(team)
    await db_session.flush()
    db_session.add(TeamMember(team_id=team.id, user_id=user.id, role=UserRole.OWNER))
    event = Event(
        team_id=team.id,
        creator_id=user.id,
        name="Print API Event",
        start_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    db_session.add(event)
    await db_session.flush()
    session = PhotoSession(event_id=event.id)
    db_session.add(session)
    await db_session.flush()
    photo = Photo(event_id=event.id, session_id=session.id, original_url=_image_data_url("red"))
    second_photo = Photo(
        event_id=event.id, session_id=session.id, original_url=_image_data_url("blue")
    )
    template = Template(team_id=team.id, name="Two Up", layers=_template_layers())
    db_session.add_all([photo, second_photo, template])
    await db_session.commit()

    async def noop(_job_id):
        return None

    monkeypatch.setattr(print_jobs_api, "_execute_print_job_background", noop)

    response = await authenticated_client.post(
        "/api/v1/print-jobs",
        json={"photo_id": str(photo.id), "template_id": str(template.id), "copies": 1},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "queued"
    assert body["template_id"] == str(template.id)


@pytest.mark.anyio
async def test_create_print_job_rejects_template_when_session_has_too_few_photos(
    authenticated_client, db_session, monkeypatch
):
    user = (
        await db_session.execute(select(User).where(User.email == "test@example.com"))
    ).scalar_one()
    team = Team(name="Print Missing Photo Team", slug="print-missing-photo-team")
    db_session.add(team)
    await db_session.flush()
    db_session.add(TeamMember(team_id=team.id, user_id=user.id, role=UserRole.OWNER))
    event = Event(
        team_id=team.id,
        creator_id=user.id,
        name="Print Missing Photo Event",
        start_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    db_session.add(event)
    await db_session.flush()
    session = PhotoSession(event_id=event.id)
    db_session.add(session)
    await db_session.flush()
    photo = Photo(event_id=event.id, session_id=session.id, original_url=_image_data_url("red"))
    template = Template(team_id=team.id, name="Two Up", layers=_template_layers())
    db_session.add_all([photo, template])
    await db_session.commit()

    async def noop(_job_id):
        return None

    monkeypatch.setattr(print_jobs_api, "_execute_print_job_background", noop)

    response = await authenticated_client.post(
        "/api/v1/print-jobs",
        json={"photo_id": str(photo.id), "template_id": str(template.id), "copies": 1},
    )

    assert response.status_code == 400
    assert "requires 2 photos" in response.text


@pytest.mark.anyio
async def test_create_print_job_rejects_cross_team_template(
    authenticated_client, db_session, monkeypatch
):
    user = (
        await db_session.execute(select(User).where(User.email == "test@example.com"))
    ).scalar_one()
    team = Team(name="Photo Team", slug="photo-team")
    other_team = Team(name="Template Team", slug="template-team")
    db_session.add_all([team, other_team])
    await db_session.flush()
    db_session.add_all(
        [
            TeamMember(team_id=team.id, user_id=user.id, role=UserRole.OWNER),
            TeamMember(team_id=other_team.id, user_id=user.id, role=UserRole.OWNER),
        ]
    )
    event = Event(
        team_id=team.id,
        creator_id=user.id,
        name="Photo Team Event",
        start_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    db_session.add(event)
    await db_session.flush()
    photo = Photo(event_id=event.id, original_url=_image_data_url("red"))
    template = Template(team_id=other_team.id, name="Wrong Team", layers=_template_layers())
    db_session.add_all([photo, template])
    await db_session.commit()

    async def noop(_job_id):
        return None

    monkeypatch.setattr(print_jobs_api, "_execute_print_job_background", noop)

    response = await authenticated_client.post(
        "/api/v1/print-jobs",
        json={"photo_id": str(photo.id), "template_id": str(template.id), "copies": 1},
    )

    assert response.status_code == 400
    assert "same team" in str(response.json())
