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

    async def get_issue(self, issue_key: str, expand: str = "") -> dict:
        """Get issue details."""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        if expand:
            url += f"?expand={expand}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def get_fields(self) -> list[dict]:
        """Get all fields including custom fields."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{self.base_url}/rest/api/3/field", headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def find_custom_field_id(self, field_name: str) -> str | None:
        """Find a custom field ID by its name (case-insensitive)."""
        fields = await self.get_fields()
        field_name_lower = field_name.lower()
        for field in fields:
            if field.get("name", "").lower() == field_name_lower:
                return field.get("id")
        return None

    async def get_issue_editmeta(self, issue_key: str) -> dict:
        """Get edit metadata for an issue to see available fields."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/editmeta",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def update_issue(self, issue_key: str, fields: dict) -> dict:
        """Update issue fields."""
        payload = {"fields": fields}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.put(
                f"{self.base_url}/rest/api/3/issue/{issue_key}",
                json=payload,
                headers=self.headers,
            )
            if resp.status_code >= 400:
                error_text = resp.text
                logger.error("Jira update failed for %s: %s - %s", issue_key, resp.status_code, error_text)
                # Try to parse error details
                try:
                    error_data = resp.json()
                    errors = error_data.get("errors", {})
                    error_messages = error_data.get("errorMessages", [])
                    logger.error("Jira errors: %s, messages: %s", errors, error_messages)
                except Exception:
                    pass
                resp.raise_for_status()
            logger.info("Updated Jira issue: %s", issue_key)
            return {"key": issue_key, "updated": True}

    def _build_adf_content(self, sections: list[dict]) -> dict:
        """Build Atlassian Document Format content from sections."""
        content = []
        for section in sections:
            if section["type"] == "heading":
                content.append({
                    "type": "heading",
                    "attrs": {"level": section.get("level", 2)},
                    "content": [{"type": "text", "text": section["text"]}]
                })
            elif section["type"] == "paragraph":
                content.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": section["text"]}]
                })
            elif section["type"] == "rule":
                content.append({"type": "rule"})
            elif section["type"] == "bullet_list":
                items = []
                for item in section["items"]:
                    if isinstance(item, dict):
                        # Item with bold label and text
                        items.append({
                            "type": "listItem",
                            "content": [{
                                "type": "paragraph",
                                "content": [
                                    {"type": "text", "text": item.get("label", ""), "marks": [{"type": "strong"}]},
                                    {"type": "text", "text": f" {item.get('text', '')}"}
                                ]
                            }]
                        })
                    else:
                        items.append({
                            "type": "listItem",
                            "content": [{"type": "paragraph", "content": [{"type": "text", "text": str(item)}]}]
                        })
                content.append({"type": "bulletList", "content": items})
            elif section["type"] == "table":
                rows = []
                # Header row
                header_cells = [
                    {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": h, "marks": [{"type": "strong"}]}]}]}
                    for h in section["headers"]
                ]
                rows.append({"type": "tableRow", "content": header_cells})
                # Data rows
                for row in section["rows"]:
                    cells = [
                        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": str(cell)}]}]}
                        for cell in row
                    ]
                    rows.append({"type": "tableRow", "content": cells})
                content.append({"type": "table", "content": rows})

        return {"type": "doc", "version": 1, "content": content}

    async def publish_analysis_to_issue(self, issue_key: str, analysis: dict, custom_fields: dict | None = None) -> dict:
        """
        Publish analysis results directly into the Jira issue.

        Looks for custom fields named "Abuse cases" and "Security requirements".
        Always updates the description with the full analysis.
        """
        risk_score = analysis.get("risk_score", 0)
        abuse_cases = analysis.get("abuse_cases", [])
        requirements = analysis.get("security_requirements", [])
        stride_threats = analysis.get("stride_threats", [])

        # Get current issue to preserve description
        issue = await self.get_issue(issue_key)
        current_desc = issue.get("fields", {}).get("description")

        # Build the full analysis for description
        analysis_sections = [
            {"type": "rule"},
            {"type": "heading", "level": 2, "text": "🛡️ SecureReq AI - Security Analysis"},
            {"type": "paragraph", "text": f"Risk Score: {risk_score}/100"},
        ]

        # Add abuse cases
        if abuse_cases:
            analysis_sections.append({"type": "heading", "level": 3, "text": f"⚠️ Abuse Cases ({len(abuse_cases)})"})
            analysis_sections.append({
                "type": "table",
                "headers": ["#", "Threat", "Actor", "Impact", "Likelihood", "STRIDE"],
                "rows": [[i+1, ac.get("threat", ""), ac.get("actor", ""), ac.get("impact", ""), ac.get("likelihood", ""), ac.get("stride_category", "")] for i, ac in enumerate(abuse_cases)]
            })

        # Add security requirements
        if requirements:
            analysis_sections.append({"type": "heading", "level": 3, "text": f"🛡️ Security Requirements ({len(requirements)})"})
            analysis_sections.append({
                "type": "table",
                "headers": ["ID", "Priority", "Category", "Requirement"],
                "rows": [[req.get("id", ""), req.get("priority", ""), req.get("category", ""), req.get("text", "")] for req in requirements]
            })

        # Add STRIDE threats
        if stride_threats:
            analysis_sections.append({"type": "heading", "level": 3, "text": f"📊 STRIDE Threats ({len(stride_threats)})"})
            analysis_sections.append({
                "type": "table",
                "headers": ["Category", "Threat", "Risk Level"],
                "rows": [[st.get("category", ""), st.get("threat", ""), st.get("risk_level", "")] for st in stride_threats]
            })

        analysis_sections.append({"type": "rule"})
        analysis_sections.append({"type": "paragraph", "text": "Generated by SecureReq AI"})

        analysis_adf = self._build_adf_content(analysis_sections)

        # Build fields to update
        fields_to_update = {}

        # Merge with existing description (remove old analysis if present)
        if current_desc and isinstance(current_desc, dict) and current_desc.get("content"):
            new_content = []
            skip_section = False
            for block in current_desc.get("content", []):
                if block.get("type") == "heading" and any(
                    "SecureReq AI" in (c.get("text", "") or "")
                    for c in block.get("content", [])
                ):
                    skip_section = True
                    continue
                if skip_section:
                    if block.get("type") == "paragraph" and any(
                        "Generated by SecureReq AI" in (c.get("text", "") or "")
                        for c in block.get("content", [])
                    ):
                        skip_section = False
                        continue
                    continue
                new_content.append(block)

            new_content.extend(analysis_adf["content"])
            fields_to_update["description"] = {"type": "doc", "version": 1, "content": new_content}
        else:
            fields_to_update["description"] = analysis_adf

        result = await self.update_issue(issue_key, fields_to_update)

        # Log what was updated
        updated_fields = list(fields_to_update.keys())
        logger.info("Updated Jira issue %s with fields: %s", issue_key, updated_fields)

        return result

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
