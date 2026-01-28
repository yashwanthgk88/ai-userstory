import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.project import Project
from models.user_story import UserStory
from models.analysis import SecurityAnalysis
from models.integration import Integration
from schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, JiraProjectImport
from core.security import get_current_user
from core.encryption import decrypt_token
from services.jira_client import JiraClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
async def list_projects(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.owner_id == user.id).order_by(Project.updated_at.desc()))
    projects = result.scalars().all()

    responses = []
    for p in projects:
        story_count = (await db.execute(select(func.count()).where(UserStory.project_id == p.id))).scalar() or 0
        analysis_count = (await db.execute(
            select(func.count()).select_from(SecurityAnalysis).join(UserStory).where(UserStory.project_id == p.id)
        )).scalar() or 0
        resp = ProjectResponse.model_validate(p)
        resp.story_count = story_count
        resp.analysis_count = analysis_count
        responses.append(resp)
    return responses


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(req: ProjectCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    project = Project(name=req.name, description=req.description, owner_id=user.id)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    resp = ProjectResponse.model_validate(project)
    resp.story_count = 0
    resp.analysis_count = 0
    return resp


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    story_count = (await db.execute(select(func.count()).where(UserStory.project_id == project.id))).scalar() or 0
    analysis_count = (await db.execute(
        select(func.count()).select_from(SecurityAnalysis).join(UserStory).where(UserStory.project_id == project.id)
    )).scalar() or 0
    resp = ProjectResponse.model_validate(project)
    resp.story_count = story_count
    resp.analysis_count = analysis_count
    return resp


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: UUID, req: ProjectUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if req.name is not None:
        project.name = req.name
    if req.description is not None:
        project.description = req.description
    await db.commit()
    await db.refresh(project)
    resp = ProjectResponse.model_validate(project)
    return resp


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()


@router.post("/from-jira", response_model=ProjectResponse, status_code=201)
async def create_project_from_jira(
    req: JiraProjectImport,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new space from a Jira project and import its issues as stories."""
    # Get the integration
    result = await db.execute(select(Integration).where(Integration.id == req.integration_id))
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    if integration.created_by != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if integration.integration_type != "jira":
        raise HTTPException(status_code=400, detail="Not a Jira integration")

    # Check if project with this jira_project_key already exists
    existing = await db.execute(
        select(Project).where(Project.owner_id == user.id, Project.jira_project_key == req.jira_project_key)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"A space for Jira project {req.jira_project_key} already exists")

    # Create the project
    project = Project(
        name=req.jira_project_name,
        description=f"Imported from Jira project {req.jira_project_key}",
        owner_id=user.id,
        jira_project_key=req.jira_project_key,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Also create a project-level integration linked to this project
    project_integration = Integration(
        project_id=project.id,
        integration_type="jira",
        name=f"Jira - {req.jira_project_key}",
        config=integration.config,
        encrypted_token=integration.encrypted_token,
        created_by=user.id,
    )
    db.add(project_integration)
    await db.commit()

    # Fetch and import issues from Jira
    token = decrypt_token(integration.encrypted_token)
    config = integration.config
    client = JiraClient(config.get("url", ""), config.get("email", ""), token)

    logger.info("Importing Jira issues - project_id=%s, project_key=%s", req.jira_project_id, req.jira_project_key)

    try:
        issues = await client.get_project_issues(req.jira_project_id)
        imported_count = 0
        for issue in issues:
            fields = issue.get("fields", {})
            description = _extract_description_from_adf(fields.get("description"))
            story = UserStory(
                project_id=project.id,
                title=fields.get("summary", "Untitled"),
                description=description,
                source="jira",
                external_id=issue.get("key"),
            )
            db.add(story)
            imported_count += 1
        await db.commit()
        logger.info("Imported %d stories from Jira project %s", imported_count, req.jira_project_key)
    except Exception as e:
        logger.exception("Failed to import Jira issues: %s", str(e))
        raise HTTPException(status_code=400, detail=f"Jira import failed: {str(e)}")

    resp = ProjectResponse.model_validate(project)
    story_count = (await db.execute(select(func.count()).where(UserStory.project_id == project.id))).scalar() or 0
    resp.story_count = story_count
    resp.analysis_count = 0
    return resp


def _extract_description_from_adf(desc) -> str:
    """Extract plain text from Atlassian Document Format."""
    if desc is None:
        return ""
    if isinstance(desc, str):
        return desc
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
