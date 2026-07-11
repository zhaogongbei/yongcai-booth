"""Regression tests for R2 public URL construction and email fail-closed behavior.

Covers two production-only fail modes found in the services sweep:

- Stored object URLs must be built from the configured public base
  (pub-*.r2.dev / custom domain), not the S3 API endpoint which does not
  serve anonymous GETs.
- A configured-but-failing SMTP send must raise (so Celery retries) rather
  than silently returning success.
"""

import pytest

from app.services.storage_service import R2StorageService
from app.tasks import email_tasks


def test_public_url_uses_configured_public_base(monkeypatch):
    monkeypatch.setattr(
        email_tasks.settings, "R2_PUBLIC_URL", "https://pub-abc.r2.dev", raising=False
    )
    from app.services import storage_service

    monkeypatch.setattr(
        storage_service.settings, "R2_PUBLIC_URL", "https://pub-abc.r2.dev", raising=False
    )

    url = R2StorageService._public_url("photos/abc.jpg")

    assert url == "https://pub-abc.r2.dev/photos/abc.jpg"


def test_public_url_falls_back_to_endpoint_when_public_base_absent(monkeypatch):
    from app.services import storage_service

    monkeypatch.setattr(storage_service.settings, "R2_PUBLIC_URL", "", raising=False)
    monkeypatch.setattr(
        storage_service.settings,
        "R2_ENDPOINT_URL",
        "https://acc.r2.cloudflarestorage.com",
        raising=False,
    )
    monkeypatch.setattr(storage_service.settings, "R2_BUCKET_NAME", "bucket", raising=False)

    url = R2StorageService._public_url("photos/abc.jpg")

    assert url == "https://acc.r2.cloudflarestorage.com/bucket/photos/abc.jpg"


def test_object_key_extracted_from_public_url(monkeypatch):
    from app.services import storage_service

    monkeypatch.setattr(
        storage_service.settings, "R2_PUBLIC_URL", "https://pub-abc.r2.dev", raising=False
    )
    service = R2StorageService()

    key = service._object_key_from_url("https://pub-abc.r2.dev/props/xyz.png")

    assert key == "props/xyz.png"


def test_send_email_returns_false_when_smtp_not_configured(monkeypatch):
    monkeypatch.setattr(email_tasks.settings, "SMTP_HOST", "", raising=False)
    monkeypatch.setattr(email_tasks.settings, "SMTP_USER", "", raising=False)

    result = email_tasks.EmailService.send_email("to@example.com", "subj", "<p>hi</p>")

    assert result is False


def test_send_email_raises_when_configured_send_fails(monkeypatch):
    monkeypatch.setattr(email_tasks.settings, "SMTP_HOST", "smtp.example.com", raising=False)
    monkeypatch.setattr(email_tasks.settings, "SMTP_USER", "user@example.com", raising=False)
    monkeypatch.setattr(email_tasks.settings, "SMTP_PASSWORD", "secret", raising=False)

    def _boom(*args, **kwargs):
        raise OSError("smtp unreachable")

    monkeypatch.setattr(email_tasks.smtplib, "SMTP", _boom)

    with pytest.raises(OSError):
        email_tasks.EmailService.send_email("to@example.com", "subj", "<p>hi</p>")
