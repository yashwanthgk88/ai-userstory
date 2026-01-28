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
from models.custom_standard import CustomStandard
from models.compliance_mapping import ComplianceMapping
from schemas.analysis import AnalysisResponse, AnalysisSummary
from core.security import get_current_user
from services.ai_analyzer import analyze_with_claude
from services.template_analyzer import analyze_with_templates
from services.compliance_mapper import map_requirements_to_standards

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analysis"])


async def _analyze_single_story(story: UserStory, db: AsyncSession) -> SecurityAnalysis:
    """Core analysis logic for a single story."""
    cs_result = await db.execute(select(CustomStandard).where(CustomStandard.project_id == story.project_id))
    custom_stds = cs_result.scalars().all()
    custom_std_data = [{"name": cs.name, "controls": cs.controls} for cs in custom_stds] if custom_stds else None

    max_version = (await db.execute(
        select(func.max(SecurityAnalysis.version)).where(SecurityAnalysis.user_story_id == story.id)
    )).scalar() or 0

    ai_model = None
    try:
        analysis_data = await analyze_with_claude(
            story.title, story.description, story.acceptance_criteria, custom_std_data
        )
        ai_model = "claude-sonnet-4-20250514"
    except Exception as e:
        logger.warning("Claude API failed, falling back to templates: %s", e)
        analysis_data = analyze_with_templates(story.title, story.description, story.acceptance_criteria)
        ai_model = "template-fallback"

    analysis = SecurityAnalysis(
        user_story_id=story.id,
        version=max_version + 1,
        abuse_cases=analysis_data.get("abuse_cases", []),
        stride_threats=analysis_data.get("stride_threats", []),
        security_requirements=analysis_data.get("security_requirements", []),
        risk_score=analysis_data.get("risk_score", 0),
        ai_model_used=ai_model,
    )
    db.add(analysis)
    await db.flush()

    mappings = map_requirements_to_standards(
        analysis_data.get("security_requirements", []),
        custom_standards=custom_std_data,
    )
    for m in mappings:
        db.add(ComplianceMapping(
            analysis_id=analysis.id,
            requirement_id=m["requirement_id"],
            standard_name=m["standard_name"],
            control_id=m["control_id"],
            control_title=m.get("control_title"),
            relevance_score=m.get("relevance_score", 0.0),
        ))

    return analysis


@router.post("/stories/{story_id}/analyze", response_model=AnalysisResponse)
async def run_analysis(story_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserStory).where(UserStory.id == story_id))
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    proj = await db.execute(select(Project).where(Project.id == story.project_id, Project.owner_id == user.id))
    if not proj.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    analysis = await _analyze_single_story(story, db)
    await db.commit()
    await db.refresh(analysis)

    # Fire webhooks
    try:
        from services.webhook_service import fire_webhooks
        await fire_webhooks(story.project_id, "analysis.completed", {
            "analysis_id": str(analysis.id), "story_id": str(story.id),
            "risk_score": analysis.risk_score, "status": "success",
        }, db)
    except Exception as e:
        logger.warning("Webhook delivery error: %s", e)

    return analysis


@router.post("/projects/{project_id}/analyze")
async def bulk_analyze(project_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    proj = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not proj.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    stories_result = await db.execute(select(UserStory).where(UserStory.project_id == project_id))
    stories = stories_result.scalars().all()
    if not stories:
        raise HTTPException(status_code=400, detail="No stories in this project")

    results = []
    for story in stories:
        try:
            analysis = await _analyze_single_story(story, db)
            results.append({"story_id": str(story.id), "story_title": story.title, "status": "success", "analysis_id": str(analysis.id), "risk_score": analysis.risk_score})
        except Exception as e:
            logger.error("Bulk analyze failed for story %s: %s", story.id, e)
            results.append({"story_id": str(story.id), "story_title": story.title, "status": "error", "error": str(e)})

    await db.commit()

    # Fire bulk webhook
    try:
        from services.webhook_service import fire_webhooks
        await fire_webhooks(project_id, "bulk_analysis.completed", {
            "project_id": str(project_id), "total": len(stories), "results": results,
        }, db)
    except Exception as e:
        logger.warning("Webhook delivery error: %s", e)

    return {"total": len(stories), "results": results}


@router.get("/stories/{story_id}/analyses", response_model=list[AnalysisSummary])
async def list_analyses(story_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SecurityAnalysis).where(SecurityAnalysis.user_story_id == story_id).order_by(SecurityAnalysis.version.desc())
    )
    analyses = result.scalars().all()
    return [
        AnalysisSummary(
            id=a.id, version=a.version, risk_score=a.risk_score,
            abuse_case_count=len(a.abuse_cases) if isinstance(a.abuse_cases, list) else 0,
            requirement_count=len(a.security_requirements) if isinstance(a.security_requirements, list) else 0,
            ai_model_used=a.ai_model_used, created_at=a.created_at,
        )
        for a in analyses
    ]


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(analysis_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SecurityAnalysis).where(SecurityAnalysis.id == analysis_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis
