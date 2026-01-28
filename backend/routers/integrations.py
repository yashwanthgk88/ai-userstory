from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.project import Project
from models.integration import Integration
from schemas.integration import IntegrationCreate, IntegrationResponse, IntegrationUpdate
from core.security import get_current_user
from core.encryption import encrypt_token, decrypt_token

router = APIRouter(tags=["integrations"])


async def _verify_project(project_id: UUID, user: User, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects/{project_id}/integrations", response_model=list[IntegrationResponse])
async def list_integrations(project_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify_project(project_id, user, db)
    result = await db.execute(select(Integration).where(Integration.project_id == project_id).order_by(Integration.created_at.desc()))
    return result.scalars().all()


@router.post("/projects/{project_id}/integrations", response_model=IntegrationResponse, status_code=201)
async def create_integration(project_id: UUID, req: IntegrationCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify_project(project_id, user, db)
    if req.integration_type not in ("jira", "ado", "servicenow"):
        raise HTTPException(status_code=400, detail="Invalid integration type")
    integration = Integration(
        project_id=project_id,
        integration_type=req.integration_type,
        name=req.name,
        config=req.config,
        encrypted_token=encrypt_token(req.token),
        created_by=user.id,
    )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    return integration


@router.delete("/integrations/{integration_id}", status_code=204)
async def delete_integration(integration_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Integration).where(Integration.id == integration_id))
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    await _verify_project(integration.project_id, user, db)
    await db.delete(integration)
    await db.commit()


@router.post("/integrations/{integration_id}/test")
async def test_integration(integration_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Integration).where(Integration.id == integration_id))
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    await _verify_project(integration.project_id, user, db)

    token = decrypt_token(integration.encrypted_token)
    config = integration.config

    import httpx
    from base64 import b64encode

    try:
        if integration.integration_type == "jira":
            auth = b64encode(f"{config['email']}:{token}".encode()).decode()
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{config['url'].rstrip('/')}/rest/api/3/myself", headers={"Authorization": f"Basic {auth}", "Accept": "application/json"})
                resp.raise_for_status()
                return {"status": "ok", "message": f"Connected as {resp.json().get('displayName', 'unknown')}"}
        elif integration.integration_type == "ado":
            auth = b64encode(f":{token}".encode()).decode()
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{config['url'].rstrip('/')}/_apis/projects?api-version=7.1", headers={"Authorization": f"Basic {auth}"})
                resp.raise_for_status()
                return {"status": "ok", "message": f"Connected. {resp.json().get('count', 0)} projects found."}
        elif integration.integration_type == "servicenow":
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{config['url'].rstrip('/')}/api/now/table/sys_user?sysparm_limit=1", auth=(config.get("username", ""), token))
                resp.raise_for_status()
                return {"status": "ok", "message": "Connected to ServiceNow"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Connection test failed: {e}")
