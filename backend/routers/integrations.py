import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.project import Project
from models.integration import Integration
from schemas.integration import IntegrationCreate, IntegrationResponse, IntegrationUpdate, GlobalIntegrationCreate
from core.security import get_current_user
from core.encryption import encrypt_token, decrypt_token
from services.jira_client import JiraClient

logger = logging.getLogger(__name__)
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
    # Only verify project ownership if it's a project-level integration
    if integration.project_id:
        await _verify_project(integration.project_id, user, db)
    elif integration.created_by != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

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


# ============================================
# Global Integrations (user-level, no project)
# ============================================

@router.get("/integrations/global", response_model=list[IntegrationResponse])
async def list_global_integrations(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List all global integrations for the current user."""
    result = await db.execute(
        select(Integration).where(
            Integration.created_by == user.id,
            Integration.project_id.is_(None)
        ).order_by(Integration.created_at.desc())
    )
    return result.scalars().all()


@router.post("/integrations/global", response_model=IntegrationResponse, status_code=201)
async def create_global_integration(req: GlobalIntegrationCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Create a global integration not tied to any project."""
    if req.integration_type not in ("jira", "ado", "servicenow"):
        raise HTTPException(status_code=400, detail="Invalid integration type")
    integration = Integration(
        project_id=None,  # Global integration
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


@router.get("/integrations/{integration_id}/jira/projects")
async def get_jira_projects(integration_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get all Jira projects accessible via this integration."""
    result = await db.execute(select(Integration).where(Integration.id == integration_id))
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Verify ownership
    if integration.project_id:
        await _verify_project(integration.project_id, user, db)
    elif integration.created_by != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if integration.integration_type != "jira":
        raise HTTPException(status_code=400, detail="Not a Jira integration")

    token = decrypt_token(integration.encrypted_token)
    config = integration.config

    client = JiraClient(config.get("url", ""), config.get("email", ""), token)

    try:
        projects = await client.get_projects()
        return [
            {
                "id": p.get("id"),
                "key": p.get("key"),
                "name": p.get("name"),
                "avatar_url": p.get("avatarUrls", {}).get("48x48"),
            }
            for p in projects
        ]
    except Exception as e:
        logger.exception("Failed to fetch Jira projects")
        raise HTTPException(status_code=502, detail=f"Failed to fetch Jira projects: {e}")


@router.get("/integrations/{integration_id}/jira/projects/{project_key}/issues")
async def get_jira_project_issues(
    integration_id: UUID,
    project_key: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all issues from a specific Jira project."""
    result = await db.execute(select(Integration).where(Integration.id == integration_id))
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Verify ownership
    if integration.project_id:
        await _verify_project(integration.project_id, user, db)
    elif integration.created_by != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if integration.integration_type != "jira":
        raise HTTPException(status_code=400, detail="Not a Jira integration")

    token = decrypt_token(integration.encrypted_token)
    config = integration.config

    client = JiraClient(config.get("url", ""), config.get("email", ""), token)

    try:
        issues = await client.get_project_issues(project_key)
        return [
            {
                "id": issue.get("id"),
                "key": issue.get("key"),
                "summary": issue.get("fields", {}).get("summary"),
                "description": _extract_description(issue.get("fields", {}).get("description")),
                "issue_type": issue.get("fields", {}).get("issuetype", {}).get("name"),
                "status": issue.get("fields", {}).get("status", {}).get("name"),
            }
            for issue in issues
        ]
    except Exception as e:
        logger.exception("Failed to fetch Jira issues")
        raise HTTPException(status_code=502, detail=f"Failed to fetch Jira issues: {e}")


def _extract_description(desc) -> str:
    """Extract plain text from ADF description or return as-is if string."""
    if desc is None:
        return ""
    if isinstance(desc, str):
        return desc
    # ADF format - extract text nodes
    if isinstance(desc, dict) and desc.get("type") == "doc":
        texts = []
        def extract_text(node):
            if isinstance(node, dict):
                if node.get("type") == "text":
                    texts.append(node.get("text", ""))
                for child in node.get("content", []):
                    extract_text(child)
        extract_text(desc)
        return " ".join(texts)
    return str(desc)
