"""Azure DevOps REST API client for pushing security requirements as work items."""

import logging
from base64 import b64encode

import httpx

logger = logging.getLogger(__name__)


class ADOClient:
    def __init__(self, org_url: str, project: str, pat: str):
        self.org_url = org_url.rstrip("/")
        self.project = project
        auth = b64encode(f":{pat}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json-patch+json",
        }

    async def create_work_item(self, work_item_type: str, title: str, description: str, tags: str = "") -> dict:
        url = f"{self.org_url}/{self.project}/_apis/wit/workitems/${work_item_type}?api-version=7.1"
        payload = [
            {"op": "add", "path": "/fields/System.Title", "value": title},
            {"op": "add", "path": "/fields/System.Description", "value": description},
        ]
        if tags:
            payload.append({"op": "add", "path": "/fields/System.Tags", "value": tags})

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            logger.info("Created ADO work item: %s", data.get("id"))
            return data

    async def push_analysis(self, work_item_type: str, abuse_cases: list[dict], requirements: list[dict]) -> list[dict]:
        created = []
        for ac in abuse_cases:
            desc = f"<b>Threat Actor:</b> {ac.get('actor', '')}<br><b>Attack Vector:</b> {ac.get('attack_vector', '')}<br><b>Impact:</b> {ac.get('impact', '')}<br><b>Likelihood:</b> {ac.get('likelihood', '')}<br><b>STRIDE:</b> {ac.get('stride_category', '')}<br><br>{ac.get('description', '')}"
            result = await self.create_work_item(work_item_type, f"[Abuse Case] {ac.get('threat', '')}", desc, "security;abuse-case")
            created.append(result)

        for req in requirements:
            desc = f"<b>Priority:</b> {req.get('priority', '')}<br><b>Category:</b> {req.get('category', '')}<br><br>{req.get('text', '')}<br><br><b>Details:</b> {req.get('details', '')}"
            result = await self.create_work_item(work_item_type, f"[Security Req] {req.get('id', '')} - {req.get('text', '')[:80]}", desc, "security;requirement")
            created.append(result)

        return created
