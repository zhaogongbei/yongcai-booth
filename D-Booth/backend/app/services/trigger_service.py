from __future__ import annotations

import asyncio
import json
import time
import hashlib
import hmac
import secrets
from typing import List, Optional, Union
from uuid import UUID, uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.trigger_repository import TriggerConfigRepository, TriggerLogRepository
from app.models.models import TriggerConfig, TriggerLog, TriggerType, TriggerAction
from app.core.logging import logger


class TriggerService:
    """Service for executing event-driven triggers"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.config_repo = TriggerConfigRepository(db)
        self.log_repo = TriggerLogRepository(db)

    async def execute_triggers(self, event_type: Union[TriggerType, str], context: dict) -> List[TriggerLog]:
        """Execute all enabled triggers matching the event_type

        Args:
            event_type: TriggerType enum value or string matching a TriggerType
            context: Dictionary with event data (e.g. {"session_id": "...", "event_id": "..."})

        Returns:
            List of TriggerLog entries recording each execution
        """
        event_id_str = context.get("event_id")
        if not event_id_str:
            logger.warning(f"No event_id in trigger context, skipping trigger execution for {event_type}")
            return []

        try:
            event_id = UUID(str(event_id_str))
            event_type_enum = event_type if isinstance(event_type, TriggerType) else TriggerType(event_type)
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

    async def _execute_single_trigger(self, config: TriggerConfig, event_type: TriggerType, context: dict) -> Optional[TriggerLog]:
        """Execute a single trigger with retry logic"""
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
                    last_status, last_error = await self._execute_app_trigger(config, context)
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

        log_entry = await self.log_repo.create({
            "id": uuid4(),
            "trigger_id": config.id,
            "event_id": config.event_id,
            "event_type": event_type,
            "success": success,
            "response_status": last_status,
            "response_data": last_error if last_error else ("OK" if success else None),
            "duration_ms": duration_ms,
            "attempt_count": attempt,
        })

        if not success:
            logger.warning(
                f"Trigger {event_type.value} -> {config.target} failed after {attempt} attempts: {last_error}"
            )

        return log_entry

    async def _execute_url_callback(self, config: TriggerConfig, context: dict) -> tuple:
        """HTTP POST to configured URL

        Returns:
            (status_code, error_message) - error_message is None on success
        """
        payload = self._build_payload(config, context)
        timeout = httpx.Timeout(config.timeout)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    config.target,
                    json=payload,
                    headers={"Content-Type": "application/json", "User-Agent": "AI-Booth/1.0"}
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

    async def _execute_app_trigger(self, config: TriggerConfig, context: dict) -> tuple:
        """Execute a local executable/script

        Returns:
            (exit_code, error_message) - error_message is None on success
        """
        payload_json = json.dumps(self._build_payload(config, context))

        try:
            process = await asyncio.create_subprocess_exec(
                config.target,
                "--payload", payload_json,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=config.timeout)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return None, f"App execution timeout after {config.timeout}s"

            if process.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace")[:500] if stderr else f"Exit code {process.returncode}"
                return process.returncode, error_msg

            return process.returncode, None
        except FileNotFoundError:
            return None, f"Executable not found: {config.target}"
        except Exception as e:
            return None, str(e)

    def _build_payload(self, config: TriggerConfig, context: dict) -> dict:
        """Build the payload by merging template with context"""
        payload = {
            "event_type": config.event_type.value if hasattr(config.event_type, "value") else str(config.event_type),
            "timestamp": int(time.time()),
        }
        if config.payload_template:
            payload.update(config.payload_template)
        payload.update(context)
        return payload

    async def test_trigger(self, config: TriggerConfig) -> TriggerLog:
        """Test a single trigger with a dummy context"""
        context = {
            "test": True,
            "timestamp": int(time.time()),
        }
        return await self._execute_single_trigger(config, config.event_type, context)

    async def get_configs(self, event_id: UUID) -> List[TriggerConfig]:
        """Get all trigger configs for an event"""
        return await self.config_repo.get_by_event_id(event_id)

    async def update_config(self, event_id: UUID, configs: List[dict]) -> List[TriggerConfig]:
        """Replace all trigger configs for an event"""
        existing = await self.config_repo.get_by_event_id(event_id)
        for cfg in existing:
            await self.config_repo.delete(cfg.id)

        created = []
        for cfg_data in configs:
            cfg_data["id"] = uuid4()
            cfg_data["event_id"] = event_id
            cfg = await self.config_repo.create(cfg_data)
            created.append(cfg)

        return created

    async def get_logs(self, event_id: UUID, skip: int = 0, limit: int = 100) -> List[TriggerLog]:
        """Get trigger execution logs for an event"""
        return await self.log_repo.get_by_event_id(event_id, skip, limit)


class WebhookService:
    """Service for dispatching outgoing webhooks"""

    def __init__(self, db: AsyncSession):
        self.db = db
        from app.repositories.webhook_repository import WebhookRepository, WebhookLogRepository
        self.webhook_repo = WebhookRepository(db)
        self.log_repo = WebhookLogRepository(db)

    @staticmethod
    def compute_signature(payload_bytes: bytes, secret: str) -> str:
        """Compute HMAC-SHA256 signature"""
        return hmac.new(
            secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

    async def dispatch(self, event_type: str, payload: dict, team_id: UUID) -> None:
        """Find matching webhooks, generate signature, POST, and log"""
        webhooks = await self.webhook_repo.get_by_event_type(team_id, event_type)
        if not webhooks:
            return

        tasks = []
        for webhook in webhooks:
            if event_type in (webhook.events or []):
                tasks.append(self._dispatch_single(webhook, event_type, payload))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _dispatch_single(self, webhook, event_type: str, payload: dict) -> None:
        """Dispatch to a single webhook with retry"""
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
                        }
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

        await self.log_repo.create({
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
        })

        if not success:
            logger.warning(f"Webhook {webhook.url} failed after {attempt} attempts: {last_error}")

    async def create_webhook(self, data: dict) -> Webhook:
        """Create a webhook"""
        from app.models.models import Webhook
        data["id"] = uuid4()
        if "secret" not in data:
            data["secret"] = secrets.token_hex(32)
        return await self.webhook_repo.create(data)

    async def get_webhooks(self, team_id: UUID) -> list:
        """Get all webhooks for a team"""
        return await self.webhook_repo.get_by_team_id(team_id)

    async def delete_webhook(self, webhook_id: UUID) -> bool:
        """Delete a webhook"""
        return await self.webhook_repo.delete(webhook_id)

    async def get_webhook_logs(self, webhook_id: UUID, skip: int = 0, limit: int = 100) -> list:
        """Get webhook dispatch logs"""
        return await self.log_repo.get_by_webhook_id(webhook_id, skip, limit)
