from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from base64 import b64encode

from database import get_db
from models.user import User
from models.project import Project
from models.user_story import UserStory
from models.analysis import SecurityAnalysis
from schemas.user_story import StoryCreate, StoryResponse, JiraImportRequest, ADOImportRequest
from core.security import get_current_user

router = APIRouter(tags=["user_stories"])


async def _verify_project(project_id: UUID, user: User, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects/{project_id}/stories", response_model=list[StoryResponse])
async def list_stories(project_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify_project(project_id, user, db)
    result = await db.execute(select(UserStory).where(UserStory.project_id == project_id).order_by(UserStory.created_at.desc()))
    stories = result.scalars().all()
    responses = []
    for s in stories:
        count = (await db.execute(select(func.count()).where(SecurityAnalysis.user_story_id == s.id))).scalar() or 0
        resp = StoryResponse.model_validate(s)
        resp.analysis_count = count
        responses.append(resp)
    return responses


@router.post("/projects/{project_id}/stories", response_model=StoryResponse, status_code=201)
async def create_story(project_id: UUID, req: StoryCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify_project(project_id, user, db)
    story = UserStory(
        project_id=project_id, title=req.title, description=req.description,
        acceptance_criteria=req.acceptance_criteria, source="manual", created_by=user.id,
    )
    db.add(story)
    await db.commit()
    await db.refresh(story)
    resp = StoryResponse.model_validate(story)
    resp.analysis_count = 0
    return resp


@router.get("/stories/{story_id}", response_model=StoryResponse)
async def get_story(story_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserStory).where(UserStory.id == story_id))
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    await _verify_project(story.project_id, user, db)
    count = (await db.execute(select(func.count()).where(SecurityAnalysis.user_story_id == story.id))).scalar() or 0
    resp = StoryResponse.model_validate(story)
    resp.analysis_count = count
    return resp


@router.post("/projects/{project_id}/stories/import/jira", response_model=list[StoryResponse])
async def import_from_jira(project_id: UUID, req: JiraImportRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify_project(project_id, user, db)
    auth = b64encode(f"{req.email}:{req.api_token}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Accept": "application/json"}
    jql = req.jql or f"project = {req.project_key} AND type = Story ORDER BY created DESC"
    from urllib.parse import urlparse
    parsed = urlparse(req.jira_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        # Use new /search/jql POST endpoint (Jira Cloud 2024+), fall back to legacy GET
        data = None
        headers_json = {**headers, "Content-Type": "application/json"}

        # Try new POST /rest/api/3/search/jql first
        url = f"{base_url}/rest/api/3/search/jql"
        resp = await client.post(url, json={"jql": jql, "maxResults": 50}, headers=headers_json)
        if resp.status_code == 200:
            try:
                data = resp.json()
            except Exception:
                pass

        # Fall back to legacy GET /rest/api/3/search and /rest/api/2/search
        if data is None and resp.status_code in (404, 410):
            from urllib.parse import quote
            encoded_jql = quote(jql)
            for api_ver in ["3", "2"]:
                url = f"{base_url}/rest/api/{api_ver}/search?jql={encoded_jql}&maxResults=50"
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        break
                    except Exception:
                        continue

        if resp.status_code == 401:
            raise HTTPException(status_code=401, detail="Jira authentication failed. Check your email and API token.")
        if resp.status_code == 403:
            raise HTTPException(status_code=403, detail="Jira access denied. Check your permissions for this project.")

        if data is None:
            detail = f"Jira returned error {resp.status_code}"
            try:
                err_data = resp.json()
                if "errorMessages" in err_data:
                    detail = "; ".join(err_data["errorMessages"])
            except Exception:
                detail += f": {resp.text[:200]}"
            raise HTTPException(status_code=502, detail=f"Jira import failed: {detail}")

    stories = []
    for issue in data.get("issues", []):
        fields = issue.get("fields", {})
        desc_content = fields.get("description", {})
        desc_text = ""
        if isinstance(desc_content, dict):
            for block in desc_content.get("content", []):
                for item in block.get("content", []):
                    desc_text += item.get("text", "") + " "
        elif isinstance(desc_content, str):
            desc_text = desc_content

        story = UserStory(
            project_id=project_id, title=fields.get("summary", "Untitled"),
            description=desc_text.strip() or "Imported from Jira",
            source="jira", external_id=issue.get("key"),
            external_url=f"{req.jira_url.rstrip('/')}/browse/{issue.get('key')}",
            created_by=user.id,
        )
        db.add(story)
        stories.append(story)

    await db.commit()
    for s in stories:
        await db.refresh(s)
    return [StoryResponse.model_validate(s) for s in stories]


@router.post("/projects/{project_id}/stories/import/ado", response_model=list[StoryResponse])
async def import_from_ado(project_id: UUID, req: ADOImportRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _verify_project(project_id, user, db)
    auth = b64encode(f":{req.pat}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

    wiql = req.query or f"SELECT [System.Id], [System.Title], [System.Description] FROM WorkItems WHERE [System.TeamProject] = '{req.project}' AND [System.WorkItemType] = 'User Story' ORDER BY [System.CreatedDate] DESC"
    wiql_url = f"{req.org_url.rstrip('/')}/{req.project}/_apis/wit/wiql?api-version=7.1"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(wiql_url, json={"query": wiql}, headers=headers)
        resp.raise_for_status()
        work_item_refs = resp.json().get("workItems", [])[:50]

        stories = []
        for ref in work_item_refs:
            wi_url = f"{req.org_url.rstrip('/')}/_apis/wit/workitems/{ref['id']}?api-version=7.1"
            wi_resp = await client.get(wi_url, headers=headers)
            wi_resp.raise_for_status()
            fields = wi_resp.json().get("fields", {})

            story = UserStory(
                project_id=project_id,
                title=fields.get("System.Title", "Untitled"),
                description=fields.get("System.Description", "Imported from ADO"),
                source="ado", external_id=str(ref["id"]),
                external_url=f"{req.org_url.rstrip('/')}/{req.project}/_workitems/edit/{ref['id']}",
                created_by=user.id,
            )
            db.add(story)
            stories.append(story)

    await db.commit()
    for s in stories:
        await db.refresh(s)
    return [StoryResponse.model_validate(s) for s in stories]
