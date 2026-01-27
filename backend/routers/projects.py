from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.project import Project
from models.user_story import UserStory
from models.analysis import SecurityAnalysis
from schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from core.security import get_current_user

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
