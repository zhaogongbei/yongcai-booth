import pytest
from httpx import AsyncClient

from app.services.printer_driver_service import PrinterDriverService


@pytest.mark.anyio
async def test_cancel_print_job_driver_failure_returns_400(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    async def fail_cancel(printer_name: str, job_id: int) -> bool:
        return False

    monkeypatch.setattr(PrinterDriverService, "cancel_print_job", fail_cancel)

    response = await client.delete("/api/v1/printers/Booth%20Printer/queue/42")

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Failed to cancel print job"


@pytest.mark.anyio
async def test_print_test_page_driver_failure_returns_400(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    async def fail_test_page(printer_name: str) -> bool:
        return False

    monkeypatch.setattr(PrinterDriverService, "print_test_page", fail_test_page)

    response = await client.post("/api/v1/printers/Booth%20Printer/test-page")

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Failed to print test page"


@pytest.mark.anyio
async def test_save_calibration_reports_not_implemented(client: AsyncClient):
    response = await client.put(
        "/api/v1/printers/Booth%20Printer/calibration",
        json={
            "scale": 1.0,
            "offset_x": 0,
            "offset_y": 0,
            "rotation": 0,
        },
    )

    assert response.status_code == 501
    assert response.json()["error"]["message"] == (
        "Printer calibration persistence is not implemented"
    )
