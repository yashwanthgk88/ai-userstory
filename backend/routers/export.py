import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.analysis import SecurityAnalysis
from models.user_story import UserStory
from schemas.export import JiraExportRequest, ADOExportRequest, ServiceNowExportRequest, ExportResult
from core.security import get_current_user
from services.export_service import export_to_excel, export_to_csv, export_to_pdf
from services.jira_client import JiraClient
from services.ado_client import ADOClient
from services.servicenow_client import ServiceNowClient

logger = logging.getLogger(__name__)
router = APIRouter(tags=["export"])


async def _get_analysis_with_story(analysis_id: UUID, db: AsyncSession) -> tuple[SecurityAnalysis, UserStory]:
    result = await db.execute(select(SecurityAnalysis).where(SecurityAnalysis.id == analysis_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    story_result = await db.execute(select(UserStory).where(UserStory.id == analysis.user_story_id))
    story = story_result.scalar_one_or_none()
    return analysis, story


@router.post("/analyses/{analysis_id}/export/excel")
async def export_excel(analysis_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    analysis, story = await _get_analysis_with_story(analysis_id, db)
    data = {
        "abuse_cases": analysis.abuse_cases,
        "security_requirements": analysis.security_requirements,
        "stride_threats": analysis.stride_threats,
        "risk_score": analysis.risk_score,
    }
    content = export_to_excel(story.title if story else "Analysis", data)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=security_analysis_{analysis_id}.xlsx"},
    )


@router.post("/analyses/{analysis_id}/export/csv")
async def export_csv_route(analysis_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    analysis, _ = await _get_analysis_with_story(analysis_id, db)
    data = {
        "abuse_cases": analysis.abuse_cases,
        "security_requirements": analysis.security_requirements,
        "stride_threats": analysis.stride_threats,
    }
    content = export_to_csv(data)
    return Response(
        content=content, media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=security_analysis_{analysis_id}.csv"},
    )


@router.post("/analyses/{analysis_id}/export/pdf")
async def export_pdf_route(analysis_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    analysis, story = await _get_analysis_with_story(analysis_id, db)
    data = {
        "abuse_cases": analysis.abuse_cases,
        "security_requirements": analysis.security_requirements,
        "stride_threats": analysis.stride_threats,
        "risk_score": analysis.risk_score,
    }
    content = export_to_pdf(story.title if story else "Analysis", data)
    return Response(
        content=content, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=security_analysis_{analysis_id}.pdf"},
    )


@router.post("/analyses/{analysis_id}/export/jira", response_model=ExportResult)
async def export_to_jira(analysis_id: UUID, req: JiraExportRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    analysis, _ = await _get_analysis_with_story(analysis_id, db)
    client = JiraClient(req.jira_url, req.email, req.api_token)
    try:
        created = await client.push_analysis(req.project_key, req.issue_type, analysis.abuse_cases, analysis.security_requirements)
        return ExportResult(format="jira", items_exported=len(created), message=f"Created {len(created)} Jira issues")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Jira API error: {e}")


@router.post("/analyses/{analysis_id}/export/ado", response_model=ExportResult)
async def export_to_ado(analysis_id: UUID, req: ADOExportRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    analysis, _ = await _get_analysis_with_story(analysis_id, db)
    client = ADOClient(req.org_url, req.project, req.pat)
    try:
        created = await client.push_analysis(req.work_item_type, analysis.abuse_cases, analysis.security_requirements)
        return ExportResult(format="ado", items_exported=len(created), message=f"Created {len(created)} ADO work items")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ADO API error: {e}")


@router.post("/analyses/{analysis_id}/export/servicenow", response_model=ExportResult)
async def export_to_servicenow(analysis_id: UUID, req: ServiceNowExportRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    analysis, _ = await _get_analysis_with_story(analysis_id, db)
    client = ServiceNowClient(req.instance_url, req.username, req.password)
    try:
        created = await client.push_analysis(req.table, analysis.abuse_cases, analysis.security_requirements)
        return ExportResult(format="servicenow", items_exported=len(created), message=f"Created {len(created)} ServiceNow records")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ServiceNow API error: {e}")
