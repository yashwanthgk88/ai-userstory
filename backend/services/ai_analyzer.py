import json
import logging

import anthropic

from config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert application security analyst specializing in threat modeling, abuse case generation, and security requirements engineering. You follow STRIDE, OWASP, and NIST frameworks.

When given a user story, you produce a comprehensive security analysis in JSON format with three sections:
1. abuse_cases: Realistic threat scenarios an attacker would attempt
2. stride_threats: STRIDE-categorized threats (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)
3. security_requirements: Actionable security controls to mitigate the identified threats

Each abuse case must have: id, threat, actor, description, impact (Critical/High/Medium/Low), likelihood (High/Medium/Low), attack_vector, stride_category
Each stride threat must have: category, threat, description, risk_level (Critical/High/Medium/Low)
Each security requirement must have: id, text, priority (Critical/High/Medium), category, details"""

USER_PROMPT_TEMPLATE = """Analyze the following user story for security threats, abuse cases, and generate security requirements.

**User Story Title:** {title}
**Description:** {description}
{acceptance_criteria_section}
{custom_standards_section}

Produce a thorough security analysis. Return ONLY valid JSON with this exact structure:
{{
  "abuse_cases": [
    {{"id": "AC-001", "threat": "...", "actor": "...", "description": "...", "impact": "...", "likelihood": "...", "attack_vector": "...", "stride_category": "..."}}
  ],
  "stride_threats": [
    {{"category": "Spoofing", "threat": "...", "description": "...", "risk_level": "..."}}
  ],
  "security_requirements": [
    {{"id": "SR-001", "text": "...", "priority": "...", "category": "...", "details": "..."}}
  ],
  "risk_score": 0
}}

Generate at least 8 abuse cases, 6 STRIDE threats, and 15 security requirements. Be specific to THIS user story, not generic."""


async def analyze_with_claude(
    title: str,
    description: str,
    acceptance_criteria: str | None = None,
    custom_standards: list[dict] | None = None,
) -> dict:
    """Call Claude API to generate security analysis. Returns parsed dict or raises."""
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    ac_section = ""
    if acceptance_criteria:
        ac_section = f"**Acceptance Criteria:** {acceptance_criteria}"

    cs_section = ""
    if custom_standards:
        controls_text = "\n".join(
            f"- [{c.get('control_id', 'N/A')}] {c.get('title', '')} - {c.get('description', '')}"
            for std in custom_standards
            for c in std.get("controls", [])
        )
        cs_section = f"""
**Organization Custom Security Standards (must also map requirements to these):**
{controls_text}"""

    user_prompt = USER_PROMPT_TEMPLATE.format(
        title=title,
        description=description,
        acceptance_criteria_section=ac_section,
        custom_standards_section=cs_section,
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    response_text = message.content[0].text
    # Extract JSON from response (may be wrapped in markdown code block)
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]

    result = json.loads(response_text.strip())
    logger.info("Claude analysis completed: %d abuse cases, %d requirements",
                len(result.get("abuse_cases", [])), len(result.get("security_requirements", [])))
    return result
