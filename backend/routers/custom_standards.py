from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.project import Project
from models.custom_standard import CustomStandard
from schemas.custom_standard import CustomStandardResponse
from core.security import get_current_user
from services.custom_standard_parser import parse_file

router = APIRouter(tags=["custom_standards"])


@router.get("/projects/{project_id}/standards", response_model=list[CustomStandardResponse])
async def list_standards(project_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CustomStandard).where(CustomStandard.project_id == project_id).order_by(CustomStandard.uploaded_at.desc()))
    return result.scalars().all()


@router.post("/projects/{project_id}/standards", response_model=CustomStandardResponse, status_code=201)
async def upload_standard(
    project_id: UUID,
    name: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    proj = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not proj.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    try:
        controls = parse_file(content, file.filename or "unknown.json")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}")

    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else "unknown"

    standard = CustomStandard(
        project_id=project_id, name=name, description=description,
        file_type=ext, original_filename=file.filename,
        controls=controls, uploaded_by=user.id,
    )
    db.add(standard)
    await db.commit()
    await db.refresh(standard)
    return standard


@router.delete("/standards/{standard_id}", status_code=204)
async def delete_standard(standard_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CustomStandard).where(CustomStandard.id == standard_id))
    standard = result.scalar_one_or_none()
    if not standard:
        raise HTTPException(status_code=404, detail="Standard not found")
    await db.delete(standard)
    await db.commit()
