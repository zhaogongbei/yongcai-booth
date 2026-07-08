from __future__ import annotations

import asyncio
import hashlib
import hmac
import ipaddress
import json
import secrets
import socket
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.models import TriggerAction, TriggerConfig, TriggerLog, TriggerType
from app.repositories.trigger_repository import TriggerConfigRepository, TriggerLogRepository
from app.schemas.trigger import TriggerConfigCreate, TriggerConfigUpdate
from app.services.base_service import BaseService, BusinessRuleError, ValidationError


class TriggerService(BaseService[TriggerConfig, TriggerConfigCreate, TriggerConfigUpdate]):
    """
    Service for executing event-driven triggers.

    This service manages trigger configurations and execution logs,
    supporting HTTP callbacks only. Local application execution is intentionally
    disabled for SaaS safety.
    """

    ALLOWED_ACTION_TYPES = {TriggerAction.HTTP_CALLBACK}

    def __init__(self, db: AsyncSession):
        self.config_repo = TriggerConfigRepository(db)
        self.log_repo = TriggerLogRepository(db)
        super().__init__(self.config_repo, db)

    @classmethod
    def _validate_action_type(cls, action_type: TriggerAction) -> None:
        if action_type not in cls.ALLOWED_ACTION_TYPES:
            raise ValidationError("Only HTTP callback triggers are supported")

    @staticmethod
    def _is_forbidden_callback_ip(address: str) -> bool:
        ip = ipaddress.ip_address(address)
        return any(
            (
                ip.is_private,
                ip.is_loopback,
                ip.is_link_local,
                ip.is_multicast,
                ip.is_reserved,
                ip.is_unspecified,
            )
        )

    @classmethod
    def _validate_http_callback_target(cls, target: str) -> None:
        parsed = urlparse(target)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValidationError("HTTP callback target must be an absolute HTTP(S) URL")

        hostname = parsed.hostname.strip().lower()
        if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".localhost"):
            raise ValidationError("HTTP callback target must not point to localhost")

        try:
            if cls._is_forbidden_callback_ip(hostname):
                raise ValidationError(
                    "HTTP callback target must not point to private network addresses"
                )
        except ValueError:
            try:
                resolved = socket.getaddrinfo(
                    hostname, parsed.port or None, type=socket.SOCK_STREAM
                )
            except socket.gaierror as exc:
                raise ValidationError("HTTP callback target host cannot be resolved") from exc

            for result in resolved:
                ip_address = result[4][0]
                if cls._is_forbidden_callback_ip(ip_address):
                    raise ValidationError(
                        "HTTP callback target must not resolve to private network addresses"
                    )

    @classmethod
    def _validate_config_data(cls, cfg_data: Dict[str, Any]) -> None:
        try:
            action_type = TriggerAction(cfg_data.get("action_type"))
        except ValueError as exc:
            raise ValidationError("Invalid action_type") from exc

        cls._validate_action_type(action_type)
        target = cfg_data.get("target")
        if not target:
            raise ValidationError("Trigger target cannot be empty")
        if action_type == TriggerAction.HTTP_CALLBACK:
            cls._validate_http_callback_target(str(target))

        timeout = cfg_data.get("timeout", 10)
        retry = cfg_data.get("retry", 3)
        if not isinstance(timeout, int) or not isinstance(retry, int):
            raise ValidationError("Timeout and retry must be integers")
        if timeout <= 0:
            raise ValidationError("Timeout must be greater than 0")
        if retry < 1:
            raise ValidationError("Retry count must be at least 1")

    async def validate_create(self, obj_in: TriggerConfigCreate) -> None:
        """
        Validate trigger configuration before creation.

        Args:
            obj_in: Trigger configuration to validate

        Raises:
            ValidationError: If configuration is invalid
            BusinessRuleError: If business rules are violated
        """
        self._validate_action_type(obj_in.action_type)
        if not obj_in.target:
            raise ValidationError("Trigger target cannot be empty")

        if obj_in.action_type == TriggerAction.HTTP_CALLBACK:
            self._validate_http_callback_target(obj_in.target)

        if obj_in.timeout <= 0:
            raise ValidationError("Timeout must be greater than 0")

        if obj_in.retry < 1:
            raise ValidationError("Retry count must be at least 1")

    async def validate_update(self, existing: TriggerConfig, obj_in: TriggerConfigUpdate) -> None:
        """
        Validate trigger configuration before update.

        Args:
            existing: Current trigger configuration
            obj_in: Update data

        Raises:
            ValidationError: If update data is invalid
        """
        if obj_in.target is not None:
            if not obj_in.target:
                raise ValidationError("Trigger target cannot be empty")

            action_type = obj_in.action_type or existing.action_type
            self._validate_action_type(action_type)
            if action_type == TriggerAction.HTTP_CALLBACK:
                self._validate_http_callback_target(obj_in.target)

        if obj_in.timeout is not None and obj_in.timeout <= 0:
            raise ValidationError("Timeout must be greater than 0")

        if obj_in.retry is not None and obj_in.retry < 1:
            raise ValidationError("Retry count must be at least 1")

    async def execute_triggers(
        self, event_type: Union[TriggerType, str], context: Dict[str, Any]
    ) -> List[TriggerLog]:
        """
        Execute all enabled triggers matching the event_type.

        Args:
            event_type: TriggerType enum value or string matching a TriggerType
            context: Dictionary with event data (e.g. {"session_id": "...", "event_id": "..."})

        Returns:
            List of TriggerLog entries recording each execution

        Raises:
            ValidationError: If context is invalid
        """
        event_id_str = context.get("event_id")
        if not event_id_str:
            logger.warning(
                f"No event_id in trigger context, skipping trigger execution for {event_type}"
            )
            return []

        try:
            event_id = UUID(str(event_id_str))
            event_type_enum = (
                event_type if isinstance(event_type, TriggerType) else TriggerType(event_type)
            )
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid trigger params: {e}")
            return []

        configs = await self.config_repo.get_by_event_and_type(event_id, event_type_enum)
        if not configs:
            return []

        tasks = []
        for config in configs:
            tasks.append(self._execute_single_trigger(config, event_type_enum, context))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        logs = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Trigger execution failed: {result}")
            elif result is not None:
                logs.append(result)

        return logs

    async def _execute_single_trigger(
        self, config: TriggerConfig, event_type: TriggerType, context: Dict[str, Any]
    ) -> Optional[TriggerLog]:
        """
        Execute a single trigger with retry logic.

        Args:
            config: Trigger configuration to execute
            event_type: Type of event that triggered execution
            context: Event context data

        Returns:
            TriggerLog entry recording the execution result
        """
        start_time = int(time.time() * 1000)
        attempt = 0
        max_attempts = config.retry
        last_error = None
        last_status = None

        for attempt in range(1, max_attempts + 1):
            try:
                if config.action_type == TriggerAction.HTTP_CALLBACK:
                    last_status, last_error = await self._execute_url_callback(config, context)
                elif config.action_type == TriggerAction.APP_EXECUTE:
                    last_error = "Local app execution triggers are disabled"
                    last_status = -1
                else:
                    last_error = f"Unknown action type: {config.action_type}"
                    last_status = -1

                if last_error is None:
                    break  # Success, no need to retry
            except Exception as e:
                last_error = str(e)
                last_status = -1

            if attempt < max_attempts:
                backoff = 2 ** (attempt - 1)  # 1, 2, 4 seconds
                await asyncio.sleep(backoff)

        duration_ms = int(time.time() * 1000) - start_time
        success = last_error is None

        log_entry = await self.log_repo.create(
            {
                "id": uuid4(),
                "trigger_id": config.id,
                "event_id": config.event_id,
                "event_type": event_type,
                "success": success,
                "response_status": last_status,
                "response_data": last_error if last_error else ("OK" if success else None),
                "duration_ms": duration_ms,
                "attempt_count": attempt,
            }
        )

        if not success:
            logger.warning(
                f"Trigger {event_type.value} -> {config.target} failed after {attempt} attempts: {last_error}"
            )

        return log_entry

    async def _execute_url_callback(self, config: TriggerConfig, context: Dict[str, Any]) -> tuple:
        """
        HTTP POST to configured URL.

        Args:
            config: Trigger configuration with target URL
            context: Event context to send as payload

        Returns:
            Tuple of (status_code, error_message) - error_message is None on success
        """
        self._validate_http_callback_target(config.target)
        payload = self._build_payload(config, context)
        timeout = httpx.Timeout(config.timeout)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    config.target,
                    json=payload,
                    headers={"Content-Type": "application/json", "User-Agent": "AI-Booth/1.0"},
                )
                if response.is_success or response.status_code < 500:
                    return response.status_code, None
                return response.status_code, f"HTTP {response.status_code}: {response.text[:500]}"
        except httpx.TimeoutException:
            return None, f"Request timeout after {config.timeout}s"
        except httpx.ConnectError:
            return None, f"Connection refused: {config.target}"
        except Exception as e:
            return None, str(e)

    def _build_payload(self, config: TriggerConfig, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build the payload by merging template with context.

        Args:
            config: Trigger configuration with optional payload template
            context: Event context data

        Returns:
            Complete payload dictionary
        """
        payload = {
            "event_type": (
                config.event_type.value
                if hasattr(config.event_type, "value")
                else str(config.event_type)
            ),
            "timestamp": int(time.time()),
        }
        if config.payload_template:
            payload.update(config.payload_template)
        payload.update(context)
        return payload

    async def test_trigger(self, config: TriggerConfig) -> TriggerLog:
        """
        Test a single trigger with a dummy context.

        Args:
            config: Trigger configuration to test

        Returns:
            TriggerLog entry with test execution results
        """
        context = {
            "test": True,
            "timestamp": int(time.time()),
        }
        return await self._execute_single_trigger(config, config.event_type, context)

    async def get_configs(self, event_id: UUID) -> List[TriggerConfig]:
        """
        Get all trigger configs for an event.

        Args:
            event_id: Event UUID

        Returns:
            List of trigger configurations
        """
        return await self.config_repo.get_by_event_id(event_id)

    async def update_config(
        self, event_id: UUID, configs: List[Dict[str, Any]]
    ) -> List[TriggerConfig]:
        """
        Replace all trigger configs for an event.

        Args:
            event_id: Event UUID
            configs: List of trigger configuration dictionaries

        Returns:
            List of created trigger configurations

        Raises:
            ValidationError: If configuration data is invalid
        """
        if not isinstance(configs, list):
            raise ValidationError("Configs must be a list")

        for cfg_data in configs:
            self._validate_config_data(cfg_data)

        existing = await self.config_repo.get_by_event_id(event_id)
        for cfg in existing:
            await self.config_repo.delete(cfg.id)

        created = []
        for cfg_data in configs:
            create_data = dict(cfg_data)
            create_data["id"] = uuid4()
            create_data["event_id"] = event_id
            cfg = await self.config_repo.create(create_data)
            created.append(cfg)

        return created

    async def get_logs(self, event_id: UUID, skip: int = 0, limit: int = 100) -> List[TriggerLog]:
        """
        Get trigger execution logs for an event.

        Args:
            event_id: Event UUID
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            List of trigger execution logs
        """
        return await self.log_repo.get_by_event_id(event_id, skip, limit)


class WebhookService:
    """
    Service for dispatching outgoing webhooks.

    This service manages webhook configurations and dispatches
    HTTP callbacks with signature verification.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        from app.repositories.webhook_repository import WebhookLogRepository, WebhookRepository

        self.webhook_repo = WebhookRepository(db)
        self.log_repo = WebhookLogRepository(db)

    @staticmethod
    def compute_signature(payload_bytes: bytes, secret: str) -> str:
        """
        Compute HMAC-SHA256 signature for webhook verification.

        Args:
            payload_bytes: Raw payload bytes
            secret: Shared secret key

        Returns:
            Hex-encoded signature string
        """
        return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    async def dispatch(self, event_type: str, payload: Dict[str, Any], team_id: UUID) -> None:
        """
        Find matching webhooks, generate signature, POST, and log.

        Args:
            event_type: Type of event to dispatch
            payload: Event payload data
            team_id: Team UUID
        """
        webhooks = await self.webhook_repo.get_by_event_type(team_id, event_type)
        if not webhooks:
            return

        tasks = []
        for webhook in webhooks:
            if event_type in (webhook.events or []):
                tasks.append(self._dispatch_single(webhook, event_type, payload))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _dispatch_single(self, webhook, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Dispatch to a single webhook with retry.

        Args:
            webhook: Webhook configuration
            event_type: Event type being dispatched
            payload: Event payload data
        """
        from app.models.models import Webhook

        start_time = int(time.time() * 1000)
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = self.compute_signature(payload_bytes, webhook.secret)
        attempt = 0
        max_attempts = 3
        last_error = None
        last_status = None

        for attempt in range(1, max_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.post(
                        webhook.url,
                        content=payload_bytes,
                        headers={
                            "Content-Type": "application/json",
                            "X-Webhook-Signature": signature,
                            "User-Agent": "AI-Booth-Webhook/1.0",
                        },
                    )
                    if response.is_success:
                        last_status = response.status_code
                        last_error = None
                        break
                    last_status = response.status_code
                    last_error = f"HTTP {response.status_code}: {response.text[:500]}"
            except Exception as e:
                last_error = str(e)
                last_status = None

            if attempt < max_attempts:
                backoff = 2 ** (attempt - 1)
                await asyncio.sleep(backoff)

        duration_ms = int(time.time() * 1000) - start_time
        success = last_error is None

        await self.log_repo.create(
            {
                "id": uuid4(),
                "webhook_id": webhook.id,
                "event_type": event_type,
                "payload": payload,
                "success": success,
                "response_status": last_status,
                "response_data": last_error if last_error else ("OK" if success else None),
                "duration_ms": duration_ms,
                "attempt_count": attempt,
                "signature": signature,
            }
        )

        if not success:
            logger.warning(f"Webhook {webhook.url} failed after {attempt} attempts: {last_error}")

    async def create_webhook(self, data: Dict[str, Any]):
        """
        Create a webhook.

        Args:
            data: Webhook configuration data

        Returns:
            Created webhook instance
        """
        from app.models.models import Webhook

        data["id"] = uuid4()
        if "secret" not in data:
            data["secret"] = secrets.token_hex(32)
        return await self.webhook_repo.create(data)

    async def get_webhooks(self, team_id: UUID) -> List:
        """
        Get all webhooks for a team.

        Args:
            team_id: Team UUID

        Returns:
            List of webhook configurations
        """
        return await self.webhook_repo.get_by_team_id(team_id)

    async def delete_webhook(self, webhook_id: UUID) -> bool:
        """
        Delete a webhook.

        Args:
            webhook_id: Webhook UUID

        Returns:
            True if deleted, False if not found
        """
        return await self.webhook_repo.delete(webhook_id)

    async def get_webhook_logs(self, webhook_id: UUID, skip: int = 0, limit: int = 100) -> List:
        """
        Get webhook dispatch logs.

        Args:
            webhook_id: Webhook UUID
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            List of webhook execution logs
        """
        return await self.log_repo.get_by_webhook_id(webhook_id, skip, limit)
