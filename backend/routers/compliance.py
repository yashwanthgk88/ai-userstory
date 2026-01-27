from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.analysis import SecurityAnalysis
from models.compliance_mapping import ComplianceMapping
from schemas.compliance import ComplianceMappingResponse, ComplianceSummary
from core.security import get_current_user

router = APIRouter(tags=["compliance"])


@router.get("/analyses/{analysis_id}/compliance", response_model=list[ComplianceMappingResponse])
async def get_compliance_mappings(analysis_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ComplianceMapping).where(ComplianceMapping.analysis_id == analysis_id))
    return result.scalars().all()


@router.get("/analyses/{analysis_id}/compliance/summary", response_model=list[ComplianceSummary])
async def get_compliance_summary(analysis_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ComplianceMapping).where(ComplianceMapping.analysis_id == analysis_id))
    mappings = result.scalars().all()

    by_standard: dict[str, set[str]] = {}
    for m in mappings:
        by_standard.setdefault(m.standard_name, set()).add(m.control_id)

    return [
        ComplianceSummary(
            standard_name=name,
            total_controls=len(controls),
            mapped_controls=len(controls),
            coverage_percent=min(100.0, len(controls) * 10.0),
        )
        for name, controls in by_standard.items()
    ]
