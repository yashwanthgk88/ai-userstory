"""Jira REST API v3 client for pushing security requirements as issues."""

import logging
from base64 import b64encode

import httpx

logger = logging.getLogger(__name__)


class JiraClient:
    def __init__(self, base_url: str, email: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        auth = b64encode(f"{email}:{api_token}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def create_issue(self, project_key: str, summary: str, description: str, issue_type: str = "Task", priority: str = "Medium", labels: list[str] | None = None) -> dict:
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}],
                },
                "issuetype": {"name": issue_type},
            }
        }
        if labels:
            payload["fields"]["labels"] = labels

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{self.base_url}/rest/api/3/issue", json=payload, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            logger.info("Created Jira issue: %s", data.get("key"))
            return data

    async def push_analysis(self, project_key: str, issue_type: str, abuse_cases: list[dict], requirements: list[dict]) -> list[dict]:
        created = []
        for ac in abuse_cases:
            desc = f"Threat Actor: {ac.get('actor', 'N/A')}\nAttack Vector: {ac.get('attack_vector', 'N/A')}\nImpact: {ac.get('impact', 'N/A')}\nLikelihood: {ac.get('likelihood', 'N/A')}\nSTRIDE: {ac.get('stride_category', 'N/A')}\n\n{ac.get('description', '')}"
            result = await self.create_issue(project_key, f"[Abuse Case] {ac.get('threat', '')}", desc, issue_type, labels=["security", "abuse-case"])
            created.append(result)

        for req in requirements:
            desc = f"Priority: {req.get('priority', 'N/A')}\nCategory: {req.get('category', 'N/A')}\n\n{req.get('text', '')}\n\nDetails: {req.get('details', '')}"
            result = await self.create_issue(project_key, f"[Security Req] {req.get('id', '')} - {req.get('text', '')[:80]}", desc, issue_type, labels=["security", "requirement"])
            created.append(result)

        return created
