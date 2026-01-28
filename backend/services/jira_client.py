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

    async def get_issue(self, issue_key: str) -> dict:
        """Get issue details."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/rest/api/3/issue/{issue_key}",
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

        If custom_fields are provided (e.g., {"abuse_cases": "customfield_10100", "security_requirements": "customfield_10101"}),
        the analysis will be written to those fields. Otherwise, it appends to the description.
        """
        risk_score = analysis.get("risk_score", 0)
        abuse_cases = analysis.get("abuse_cases", [])
        requirements = analysis.get("security_requirements", [])
        stride_threats = analysis.get("stride_threats", [])

        fields_to_update = {}

        # If custom fields are configured, use them
        if custom_fields:
            # Build abuse cases content for custom field
            if custom_fields.get("abuse_cases") and abuse_cases:
                abuse_sections = [
                    {"type": "heading", "level": 3, "text": f"⚠️ Abuse Cases ({len(abuse_cases)})"},
                    {"type": "table", "headers": ["Threat", "Actor", "Impact", "Likelihood", "STRIDE", "Attack Vector"], "rows": [
                        [ac.get("threat", ""), ac.get("actor", ""), ac.get("impact", ""), ac.get("likelihood", ""), ac.get("stride_category", ""), ac.get("attack_vector", "")]
                        for ac in abuse_cases
                    ]}
                ]
                fields_to_update[custom_fields["abuse_cases"]] = self._build_adf_content(abuse_sections)

            # Build security requirements content for custom field
            if custom_fields.get("security_requirements") and requirements:
                req_sections = [
                    {"type": "heading", "level": 3, "text": f"🛡️ Security Requirements ({len(requirements)})"},
                    {"type": "table", "headers": ["ID", "Priority", "Category", "Requirement", "Details"], "rows": [
                        [req.get("id", ""), req.get("priority", ""), req.get("category", ""), req.get("text", ""), req.get("details", "")]
                        for req in requirements
                    ]}
                ]
                fields_to_update[custom_fields["security_requirements"]] = self._build_adf_content(req_sections)

            # Risk score field
            if custom_fields.get("risk_score"):
                fields_to_update[custom_fields["risk_score"]] = risk_score

        # Always update description with full analysis
        # First get current description
        issue = await self.get_issue(issue_key)
        current_desc = issue.get("fields", {}).get("description")

        # Build security analysis section
        analysis_sections = [
            {"type": "rule"},
            {"type": "heading", "level": 2, "text": "🛡️ SECUREREQ AI - SECURITY ANALYSIS"},
            {"type": "paragraph", "text": f"Risk Score: {risk_score}/100"},
            {"type": "rule"},
        ]

        if abuse_cases:
            analysis_sections.append({"type": "heading", "level": 3, "text": f"⚠️ Abuse Cases Identified ({len(abuse_cases)})"})
            analysis_sections.append({
                "type": "table",
                "headers": ["#", "Threat", "Actor", "Impact", "Likelihood", "STRIDE"],
                "rows": [[i+1, ac.get("threat", ""), ac.get("actor", ""), ac.get("impact", ""), ac.get("likelihood", ""), ac.get("stride_category", "")] for i, ac in enumerate(abuse_cases)]
            })

        if requirements:
            analysis_sections.append({"type": "heading", "level": 3, "text": f"🛡️ Security Requirements ({len(requirements)})"})
            analysis_sections.append({
                "type": "table",
                "headers": ["ID", "Priority", "Category", "Requirement"],
                "rows": [[req.get("id", ""), req.get("priority", ""), req.get("category", ""), req.get("text", "")] for req in requirements]
            })

        if stride_threats:
            analysis_sections.append({"type": "heading", "level": 3, "text": f"📊 STRIDE Threats ({len(stride_threats)})"})
            analysis_sections.append({
                "type": "table",
                "headers": ["Category", "Threat", "Risk Level"],
                "rows": [[st.get("category", ""), st.get("threat", ""), st.get("risk_level", "")] for st in stride_threats]
            })

        analysis_sections.append({"type": "rule"})
        analysis_sections.append({"type": "paragraph", "text": "Generated by SecureReq AI"})

        # Merge with existing description
        analysis_adf = self._build_adf_content(analysis_sections)

        if current_desc and isinstance(current_desc, dict) and current_desc.get("content"):
            # Check if security analysis already exists (look for our heading)
            new_content = []
            skip_until_rule = False
            for block in current_desc.get("content", []):
                # Skip existing security analysis section
                if block.get("type") == "heading" and any(
                    "SECUREREQ AI" in (c.get("text", "") or "")
                    for c in block.get("content", [])
                ):
                    skip_until_rule = True
                    continue
                if skip_until_rule:
                    if block.get("type") == "rule":
                        # Check if this is the end marker (after "Generated by")
                        continue
                    if block.get("type") == "paragraph" and any(
                        "Generated by SecureReq AI" in (c.get("text", "") or "")
                        for c in block.get("content", [])
                    ):
                        skip_until_rule = False
                        continue
                    continue
                new_content.append(block)

            # Append new analysis
            new_content.extend(analysis_adf["content"])
            fields_to_update["description"] = {"type": "doc", "version": 1, "content": new_content}
        else:
            fields_to_update["description"] = analysis_adf

        return await self.update_issue(issue_key, fields_to_update)

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
