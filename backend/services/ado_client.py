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

    async def get_work_item(self, work_item_id: int) -> dict:
        """Get work item details."""
        url = f"{self.org_url}/{self.project}/_apis/wit/workitems/{work_item_id}?api-version=7.1"
        headers = {**self.headers, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def update_work_item(self, work_item_id: int, operations: list[dict]) -> dict:
        """Update work item fields using JSON Patch operations."""
        url = f"{self.org_url}/{self.project}/_apis/wit/workitems/{work_item_id}?api-version=7.1"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.patch(url, json=operations, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            logger.info("Updated ADO work item: %s", work_item_id)
            return data

    async def publish_analysis_to_work_item(self, work_item_id: int, analysis: dict, custom_fields: dict | None = None) -> dict:
        """
        Publish analysis results directly into the ADO work item description.

        If custom_fields are provided (e.g., {"abuse_cases": "Custom.AbuseCases", "security_requirements": "Custom.SecurityRequirements"}),
        the analysis will be written to those fields. Otherwise, it appends to the description.
        """
        risk_score = analysis.get("risk_score", 0)
        abuse_cases = analysis.get("abuse_cases", [])
        requirements = analysis.get("security_requirements", [])
        stride_threats = analysis.get("stride_threats", [])

        operations = []

        # Build security analysis HTML
        analysis_html = [
            '<div style="border: 2px solid #6366f1; border-radius: 8px; padding: 16px; margin-top: 20px; background: #f8fafc;">',
            '<h2 style="color: #6366f1; margin-top: 0;">🛡️ SecureReq AI - Security Analysis</h2>',
            f'<p><strong>Risk Score:</strong> <span style="font-size: 1.2em; color: {"#ef4444" if risk_score >= 70 else "#f59e0b" if risk_score >= 40 else "#22c55e"};">{risk_score}/100</span></p>',
            '<hr style="border-color: #e2e8f0;"/>',
        ]

        if abuse_cases:
            analysis_html.append(f'<h3 style="color: #f59e0b;">⚠️ Abuse Cases Identified ({len(abuse_cases)})</h3>')
            analysis_html.append('<table style="width: 100%; border-collapse: collapse; font-size: 0.9em;">')
            analysis_html.append('<tr style="background: #fef3c7;"><th style="border: 1px solid #d1d5db; padding: 8px; text-align: left;">Threat</th><th style="border: 1px solid #d1d5db; padding: 8px;">Actor</th><th style="border: 1px solid #d1d5db; padding: 8px;">Impact</th><th style="border: 1px solid #d1d5db; padding: 8px;">Likelihood</th><th style="border: 1px solid #d1d5db; padding: 8px;">STRIDE</th></tr>')
            for ac in abuse_cases:
                impact_color = "#ef4444" if ac.get("impact") == "Critical" else "#f59e0b" if ac.get("impact") == "High" else "#eab308"
                analysis_html.append(f'<tr><td style="border: 1px solid #d1d5db; padding: 8px;">{ac.get("threat", "")}</td><td style="border: 1px solid #d1d5db; padding: 8px; text-align: center;">{ac.get("actor", "")}</td><td style="border: 1px solid #d1d5db; padding: 8px; text-align: center; color: {impact_color}; font-weight: bold;">{ac.get("impact", "")}</td><td style="border: 1px solid #d1d5db; padding: 8px; text-align: center;">{ac.get("likelihood", "")}</td><td style="border: 1px solid #d1d5db; padding: 8px; text-align: center;">{ac.get("stride_category", "")}</td></tr>')
            analysis_html.append('</table>')

        if requirements:
            analysis_html.append(f'<h3 style="color: #6366f1; margin-top: 16px;">🛡️ Security Requirements ({len(requirements)})</h3>')
            analysis_html.append('<table style="width: 100%; border-collapse: collapse; font-size: 0.9em;">')
            analysis_html.append('<tr style="background: #e0e7ff;"><th style="border: 1px solid #d1d5db; padding: 8px;">ID</th><th style="border: 1px solid #d1d5db; padding: 8px;">Priority</th><th style="border: 1px solid #d1d5db; padding: 8px;">Category</th><th style="border: 1px solid #d1d5db; padding: 8px; text-align: left;">Requirement</th></tr>')
            for req in requirements:
                priority_color = "#ef4444" if req.get("priority") == "Critical" else "#f59e0b" if req.get("priority") == "High" else "#3b82f6"
                analysis_html.append(f'<tr><td style="border: 1px solid #d1d5db; padding: 8px; font-family: monospace;">{req.get("id", "")}</td><td style="border: 1px solid #d1d5db; padding: 8px; text-align: center; color: {priority_color}; font-weight: bold;">{req.get("priority", "")}</td><td style="border: 1px solid #d1d5db; padding: 8px; text-align: center;">{req.get("category", "")}</td><td style="border: 1px solid #d1d5db; padding: 8px;">{req.get("text", "")}</td></tr>')
            analysis_html.append('</table>')

        if stride_threats:
            analysis_html.append(f'<h3 style="color: #8b5cf6; margin-top: 16px;">📊 STRIDE Threats ({len(stride_threats)})</h3>')
            analysis_html.append('<table style="width: 100%; border-collapse: collapse; font-size: 0.9em;">')
            analysis_html.append('<tr style="background: #ede9fe;"><th style="border: 1px solid #d1d5db; padding: 8px;">Category</th><th style="border: 1px solid #d1d5db; padding: 8px; text-align: left;">Threat</th><th style="border: 1px solid #d1d5db; padding: 8px;">Risk Level</th></tr>')
            for st in stride_threats:
                analysis_html.append(f'<tr><td style="border: 1px solid #d1d5db; padding: 8px; font-weight: bold;">{st.get("category", "")}</td><td style="border: 1px solid #d1d5db; padding: 8px;">{st.get("threat", "")}</td><td style="border: 1px solid #d1d5db; padding: 8px; text-align: center;">{st.get("risk_level", "")}</td></tr>')
            analysis_html.append('</table>')

        analysis_html.append('<hr style="border-color: #e2e8f0; margin-top: 16px;"/>')
        analysis_html.append('<p style="color: #64748b; font-size: 0.85em; margin-bottom: 0;"><em>Generated by SecureReq AI</em></p>')
        analysis_html.append('</div>')

        analysis_html_str = "".join(analysis_html)

        # If custom fields are configured, use them
        if custom_fields:
            if custom_fields.get("abuse_cases") and abuse_cases:
                abuse_html = self._build_table_html("Abuse Cases", ["Threat", "Actor", "Impact", "Likelihood", "STRIDE", "Attack Vector"],
                    [[ac.get("threat", ""), ac.get("actor", ""), ac.get("impact", ""), ac.get("likelihood", ""), ac.get("stride_category", ""), ac.get("attack_vector", "")] for ac in abuse_cases])
                operations.append({"op": "add", "path": f"/fields/{custom_fields['abuse_cases']}", "value": abuse_html})

            if custom_fields.get("security_requirements") and requirements:
                req_html = self._build_table_html("Security Requirements", ["ID", "Priority", "Category", "Requirement", "Details"],
                    [[req.get("id", ""), req.get("priority", ""), req.get("category", ""), req.get("text", ""), req.get("details", "")] for req in requirements])
                operations.append({"op": "add", "path": f"/fields/{custom_fields['security_requirements']}", "value": req_html})

            if custom_fields.get("risk_score"):
                operations.append({"op": "add", "path": f"/fields/{custom_fields['risk_score']}", "value": risk_score})

        # Get current description and append analysis
        work_item = await self.get_work_item(work_item_id)
        current_desc = work_item.get("fields", {}).get("System.Description", "")

        # Remove existing security analysis section if present
        import re
        pattern = r'<div style="border: 2px solid #6366f1;.*?Generated by SecureReq AI</em></p>\s*</div>'
        current_desc = re.sub(pattern, '', current_desc, flags=re.DOTALL)

        # Append new analysis
        new_desc = current_desc.strip() + "\n\n" + analysis_html_str

        operations.append({"op": "replace", "path": "/fields/System.Description", "value": new_desc})

        return await self.update_work_item(work_item_id, operations)

    def _build_table_html(self, title: str, headers: list[str], rows: list[list]) -> str:
        """Build an HTML table."""
        html = [f'<h3>{title}</h3>', '<table style="width: 100%; border-collapse: collapse;">']
        html.append('<tr>' + ''.join(f'<th style="border: 1px solid #ccc; padding: 8px; background: #f0f0f0;">{h}</th>' for h in headers) + '</tr>')
        for row in rows:
            html.append('<tr>' + ''.join(f'<td style="border: 1px solid #ccc; padding: 8px;">{cell}</td>' for cell in row) + '</tr>')
        html.append('</table>')
        return ''.join(html)

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
