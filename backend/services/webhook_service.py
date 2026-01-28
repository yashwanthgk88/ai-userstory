import hashlib
import hmac
import json
import logging
from datetime import datetime
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.webhook import Webhook

logger = logging.getLogger(__name__)


def _sign_payload(payload: dict, secret: str) -> str:
    body = json.dumps(payload, sort_keys=True, default=str)
    return "sha256=" + hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


async def fire_webhooks(project_id: UUID, event_type: str, data: dict, db: AsyncSession):
    """Fire all active webhooks for a project that match the event type."""
    result = await db.execute(
        select(Webhook).where(Webhook.project_id == project_id, Webhook.is_active == True)
    )
    webhooks = result.scalars().all()

    for wh in webhooks:
        if event_type not in (wh.event_types or []):
            continue

        payload = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }
        signature = _sign_payload(payload, wh.secret)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    wh.url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Signature-256": signature,
                        "X-SecureReq-Event": event_type,
                    },
                )
            wh.last_triggered_at = datetime.utcnow()
            logger.info("Webhook fired: %s -> %s", event_type, wh.url)
        except Exception as e:
            logger.error("Webhook delivery failed (%s): %s", wh.url, e)

    await db.commit()
