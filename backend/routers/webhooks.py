from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from database import get_db
from models.user import User
from models.project import Project
from models.webhook import Webhook
from schemas.webhook import WebhookCreate, WebhookResponse
from core.security import get_current_user

router = APIRouter(tags=["webhooks"])

VALID_EVENTS = {"analysis.completed", "analysis.failed", "bulk_analysis.completed"}


async def _verify_project(project_id: UUID, user: User, db: AsyncSession):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")


@router.post("/projects/{project_id}/webhooks", response_model=WebhookResponse, status_code=201)
async def create_webhook(project_id: UUID, req: WebhookCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify_project(project_id, user, db)
    invalid = set(req.event_types) - VALID_EVENTS
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid event types: {invalid}. Valid: {VALID_EVENTS}")
    webhook = Webhook(
        project_id=project_id,
        url=req.url,
        event_types=req.event_types,
        secret=req.secret,
        created_by=user.id,
    )
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)
    return webhook


@router.get("/projects/{project_id}/webhooks", response_model=list[WebhookResponse])
async def list_webhooks(project_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify_project(project_id, user, db)
    result = await db.execute(select(Webhook).where(Webhook.project_id == project_id).order_by(Webhook.created_at.desc()))
    return result.scalars().all()


@router.delete("/webhooks/{webhook_id}", status_code=204)
async def delete_webhook(webhook_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await _verify_project(webhook.project_id, user, db)
    await db.delete(webhook)
    await db.commit()


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(webhook_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await _verify_project(webhook.project_id, user, db)

    payload = {"event": "ping", "timestamp": datetime.utcnow().isoformat(), "data": {"message": "Test webhook from SecureReq AI"}}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook.url, json=payload, headers={"Content-Type": "application/json", "X-SecureReq-Event": "ping"})
            return {"status": "ok", "response_code": resp.status_code}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Webhook test failed: {e}")
