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

    async def get_projects(self) -> list[dict]:
        """Get all accessible Jira projects."""
        async with httpx.AsyncClient(timeout=30) as client:
            # Use the simple /project endpoint which is more universally supported
            resp = await client.get(
                f"{self.base_url}/rest/api/3/project",
                headers=self.headers,
            )
            if resp.status_code >= 400:
                logger.error("Jira get_projects failed: %s - %s", resp.status_code, resp.text)
                # Try search endpoint as fallback (newer Jira Cloud)
                resp = await client.get(
                    f"{self.base_url}/rest/api/3/project/search",
                    headers=self.headers,
                    params={"maxResults": 100}
                )
                if resp.status_code >= 400:
                    logger.error("Jira project/search also failed: %s - %s", resp.status_code, resp.text)
                resp.raise_for_status()
                data = resp.json()
                return data.get("values", [])
            return resp.json()  # /project returns array directly

    async def get_project_issues(self, project_id: str, max_results: int = 100) -> list[dict]:
        """Get all issues (user stories) from a Jira project."""
        # Use numeric project ID in JQL to avoid all reserved word issues with project keys like "AND"
        jql = f"project = {project_id} ORDER BY created DESC"
        logger.info("Fetching issues with JQL: %s", jql)
        async with httpx.AsyncClient(timeout=60) as client:
            # Use the new /rest/api/3/search/jql endpoint (old /search was deprecated Jan 2025)
            resp = await client.get(
                f"{self.base_url}/rest/api/3/search/jql",
                headers=self.headers,
                params={
                    "jql": jql,
                    "maxResults": max_results,
                    "fields": "summary,description,issuetype,status,created,updated"
                }
            )
            if resp.status_code >= 400:
                logger.error("Jira search failed: %s - %s", resp.status_code, resp.text)
            resp.raise_for_status()
            data = resp.json()
            return data.get("issues", [])

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
        logger.info("Updating Jira issue %s with fields: %s", issue_key, list(fields.keys()))
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.put(
                f"{self.base_url}/rest/api/3/issue/{issue_key}",
                json=payload,
                headers=self.headers,
            )
            if resp.status_code >= 400:
                error_text = resp.text
                logger.error("Jira update failed for %s: %s - %s", issue_key, resp.status_code, error_text)
                # Try to parse error details and raise with meaningful message
                try:
                    error_data = resp.json()
                    errors = error_data.get("errors", {})
                    error_messages = error_data.get("errorMessages", [])
                    logger.error("Jira errors: %s, messages: %s", errors, error_messages)
                    # Build a helpful error message
                    error_details = []
                    if error_messages:
                        error_details.extend(error_messages)
                    if errors:
                        for field_id, msg in errors.items():
                            error_details.append(f"{field_id}: {msg}")
                    if error_details:
                        raise ValueError(f"Jira API error: {'; '.join(error_details)}")
                except ValueError:
                    raise
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

    def _build_abuse_cases_adf(self, abuse_cases: list[dict]) -> dict:
        """Build Atlassian Document Format content for abuse cases."""
        content = []

        for i, ac in enumerate(abuse_cases, 1):
            # Heading for each abuse case
            content.append({
                "type": "heading",
                "attrs": {"level": 3},
                "content": [{"type": "text", "text": f"Abuse Case #{i}: {ac.get('threat', 'Unknown Threat')}"}]
            })

            # Bullet list with details
            items = [
                {"type": "listItem", "content": [{"type": "paragraph", "content": [
                    {"type": "text", "text": "Threat: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": ac.get('threat', 'N/A')}
                ]}]},
                {"type": "listItem", "content": [{"type": "paragraph", "content": [
                    {"type": "text", "text": "Threat Actor: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": ac.get('actor', 'N/A')}
                ]}]},
                {"type": "listItem", "content": [{"type": "paragraph", "content": [
                    {"type": "text", "text": "Impact: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": ac.get('impact', 'N/A')}
                ]}]},
                {"type": "listItem", "content": [{"type": "paragraph", "content": [
                    {"type": "text", "text": "Likelihood: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": ac.get('likelihood', 'N/A')}
                ]}]},
                {"type": "listItem", "content": [{"type": "paragraph", "content": [
                    {"type": "text", "text": "Attack Vector: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": ac.get('attack_vector', 'N/A')}
                ]}]},
            ]

            if ac.get("description"):
                items.append({"type": "listItem", "content": [{"type": "paragraph", "content": [
                    {"type": "text", "text": "Description: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": ac.get('description', '')}
                ]}]})

            content.append({"type": "bulletList", "content": items})

            # Mitigations as sub-list
            if ac.get("mitigations"):
                content.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Recommended Mitigations:", "marks": [{"type": "strong"}]}]
                })
                mitigation_items = [
                    {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": m}]}]}
                    for m in ac.get("mitigations", [])
                ]
                content.append({"type": "bulletList", "content": mitigation_items})

            # Separator
            content.append({"type": "rule"})

        # Footer
        content.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": f"Generated by SecureReq AI | Total: {len(abuse_cases)} abuse cases", "marks": [{"type": "em"}]}]
        })

        return {"type": "doc", "version": 1, "content": content}

    def _build_security_requirements_adf(self, requirements: list[dict]) -> dict:
        """Build Atlassian Document Format content for security requirements."""
        content = []

        # Group by priority
        priority_order = ["Critical", "High", "Medium", "Low"]
        grouped = {p: [] for p in priority_order}
        for req in requirements:
            priority = req.get("priority", "Medium")
            if priority in grouped:
                grouped[priority].append(req)
            else:
                grouped["Medium"].append(req)

        for priority in priority_order:
            reqs = grouped[priority]
            if not reqs:
                continue

            # Priority heading
            content.append({
                "type": "heading",
                "attrs": {"level": 3},
                "content": [{"type": "text", "text": f"{priority} Priority ({len(reqs)})"}]
            })

            # Requirements as bullet list
            items = []
            for req in reqs:
                req_content = [
                    {"type": "text", "text": f"[{req.get('id', 'N/A')}] ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": req.get('text', '')},
                ]
                if req.get("category"):
                    req_content.append({"type": "text", "text": f" (Category: {req.get('category')})", "marks": [{"type": "em"}]})

                items.append({"type": "listItem", "content": [{"type": "paragraph", "content": req_content}]})

            content.append({"type": "bulletList", "content": items})

        # Footer
        content.append({"type": "rule"})
        content.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": f"Generated by SecureReq AI | Total: {len(requirements)} requirements", "marks": [{"type": "em"}]}]
        })

        return {"type": "doc", "version": 1, "content": content}

    def _build_abuse_cases_text(self, abuse_cases: list[dict]) -> str:
        """Build detailed plain text content for abuse cases."""
        lines = []
        for i, ac in enumerate(abuse_cases, 1):
            lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            lines.append(f"ABUSE CASE #{i}: {ac.get('threat', 'Unknown Threat')}")
            lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            lines.append("")
            lines.append(f"THREAT: {ac.get('threat', 'N/A')}")
            lines.append(f"THREAT ACTOR: {ac.get('actor', 'N/A')}")
            lines.append(f"IMPACT: {ac.get('impact', 'N/A')}")
            lines.append(f"LIKELIHOOD: {ac.get('likelihood', 'N/A')}")
            lines.append("")
            lines.append(f"ATTACK VECTOR:")
            lines.append(f"   {ac.get('attack_vector', 'N/A')}")
            lines.append("")
            if ac.get("description"):
                lines.append(f"DESCRIPTION:")
                lines.append(f"   {ac.get('description')}")
                lines.append("")
            if ac.get("mitigations"):
                lines.append(f"RECOMMENDED MITIGATIONS:")
                for mitigation in ac.get("mitigations", []):
                    lines.append(f"   - {mitigation}")
                lines.append("")
            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"Generated by SecureReq AI | Total: {len(abuse_cases)} abuse cases")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        return "\n".join(lines)

    def _build_security_requirements_text(self, requirements: list[dict]) -> str:
        """Build plain text content for security requirements."""
        lines = []

        # Group by priority
        critical = [r for r in requirements if r.get("priority") == "Critical"]
        high = [r for r in requirements if r.get("priority") == "High"]
        medium = [r for r in requirements if r.get("priority") == "Medium"]
        low = [r for r in requirements if r.get("priority") == "Low"]

        def format_reqs(reqs: list[dict], priority_label: str) -> None:
            if not reqs:
                return
            lines.append(f"━━━ {priority_label} PRIORITY ({len(reqs)}) ━━━")
            lines.append("")
            for req in reqs:
                lines.append(f"[{req.get('id', 'N/A')}] {req.get('text', '')}")
                lines.append(f"   Category: {req.get('category', 'N/A')}")
                if req.get("details"):
                    lines.append(f"   Details: {req.get('details')}")
                lines.append("")

        format_reqs(critical, "🔴 CRITICAL")
        format_reqs(high, "🟠 HIGH")
        format_reqs(medium, "🟡 MEDIUM")
        format_reqs(low, "🟢 LOW")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"Generated by SecureReq AI | Total: {len(requirements)} requirements")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        return "\n".join(lines)

    async def publish_analysis_to_issue(self, issue_key: str, analysis: dict, custom_fields: dict | None = None) -> dict:
        """
        Publish analysis results directly into the Jira issue custom fields.

        Looks for custom fields named "Abuse cases" and "Security requirements"
        and populates them with detailed analysis data.
        Does NOT modify the description field.
        """
        abuse_cases = analysis.get("abuse_cases", [])
        requirements = analysis.get("security_requirements", [])

        fields_to_update = {}
        updated_field_names = []
        missing_fields = []

        # Auto-discover custom field IDs by name
        logger.info("Looking for custom fields in Jira...")
        abuse_field_id = await self.find_custom_field_id("Abuse cases")
        req_field_id = await self.find_custom_field_id("Security requirements")

        if abuse_field_id:
            logger.info("Found 'Abuse cases' custom field: %s", abuse_field_id)
        else:
            logger.warning("Custom field 'Abuse cases' not found in Jira")
            missing_fields.append("Abuse cases")

        if req_field_id:
            logger.info("Found 'Security requirements' custom field: %s", req_field_id)
        else:
            logger.warning("Custom field 'Security requirements' not found in Jira")
            missing_fields.append("Security requirements")

        # Get editmeta to check field types and editability
        try:
            editmeta = await self.get_issue_editmeta(issue_key)
            available_fields = editmeta.get("fields", {})
            logger.info("Editable fields for %s: %s", issue_key, list(available_fields.keys()))
        except Exception as e:
            logger.warning("Could not get editmeta for %s: %s", issue_key, e)
            available_fields = {}

        # Populate "Abuse cases" custom field
        if abuse_field_id and abuse_cases:
            if abuse_field_id not in available_fields:
                logger.warning("Field %s exists but is not editable for issue %s", abuse_field_id, issue_key)

            logger.info("Building ADF content for Abuse cases field (%d cases)", len(abuse_cases))
            # Build structured ADF content for abuse cases
            adf_content = self._build_abuse_cases_adf(abuse_cases)
            fields_to_update[abuse_field_id] = adf_content
            updated_field_names.append("Abuse cases")

        # Populate "Security requirements" custom field
        if req_field_id and requirements:
            if req_field_id not in available_fields:
                logger.warning("Field %s exists but is not editable for issue %s", req_field_id, issue_key)

            logger.info("Building ADF content for Security requirements field (%d requirements)", len(requirements))
            # Build structured ADF content for security requirements
            adf_content = self._build_security_requirements_adf(requirements)
            fields_to_update[req_field_id] = adf_content
            updated_field_names.append("Security requirements")

        if not fields_to_update:
            if missing_fields:
                error_msg = f"Custom fields not found in Jira: {', '.join(missing_fields)}. Please create these custom text fields in your Jira project settings: Project Settings > Fields > Custom Fields > Create Field (Text Area)."
            else:
                error_msg = "No analysis data to publish (no abuse cases or security requirements)."
            logger.error(error_msg)
            raise ValueError(error_msg)

        result = await self.update_issue(issue_key, fields_to_update)

        logger.info("Updated Jira issue %s with fields: %s", issue_key, updated_field_names)

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
