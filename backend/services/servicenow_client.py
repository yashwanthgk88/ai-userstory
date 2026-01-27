"""ServiceNow REST API client for pushing security requirements."""

import logging

import httpx

logger = logging.getLogger(__name__)


class ServiceNowClient:
    def __init__(self, instance_url: str, username: str, password: str):
        self.instance_url = instance_url.rstrip("/")
        self.auth = (username, password)
        self.headers = {"Content-Type": "application/json", "Accept": "application/json"}

    async def create_record(self, table: str, fields: dict) -> dict:
        url = f"{self.instance_url}/api/now/table/{table}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=fields, auth=self.auth, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            logger.info("Created ServiceNow record in %s: %s", table, data.get("result", {}).get("sys_id"))
            return data.get("result", {})

    async def push_analysis(self, table: str, abuse_cases: list[dict], requirements: list[dict]) -> list[dict]:
        created = []
        for ac in abuse_cases:
            fields = {
                "short_description": f"[Abuse Case] {ac.get('threat', '')}",
                "description": f"Threat Actor: {ac.get('actor', '')}\nAttack Vector: {ac.get('attack_vector', '')}\nImpact: {ac.get('impact', '')}\nLikelihood: {ac.get('likelihood', '')}\nSTRIDE: {ac.get('stride_category', '')}\n\n{ac.get('description', '')}",
                "category": "Security",
                "priority": "1" if ac.get("impact") == "Critical" else "2" if ac.get("impact") == "High" else "3",
            }
            result = await self.create_record(table, fields)
            created.append(result)

        for req in requirements:
            fields = {
                "short_description": f"[Security Req] {req.get('id', '')} - {req.get('text', '')[:80]}",
                "description": f"Priority: {req.get('priority', '')}\nCategory: {req.get('category', '')}\n\n{req.get('text', '')}\n\nDetails: {req.get('details', '')}",
                "category": "Security",
                "priority": "1" if req.get("priority") == "Critical" else "2" if req.get("priority") == "High" else "3",
            }
            result = await self.create_record(table, fields)
            created.append(result)

        return created
