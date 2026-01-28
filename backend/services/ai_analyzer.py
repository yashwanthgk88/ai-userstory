import json
import logging

from config import settings
from services.llm_provider import get_default_provider, get_provider, PROVIDER_DEFAULTS

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """You are an expert application security analyst specializing in threat modeling, abuse case generation, and security requirements engineering. You follow STRIDE, OWASP, and NIST frameworks.

When given a user story, you produce a comprehensive security analysis in JSON format with three sections:
1. abuse_cases: Realistic threat scenarios an attacker would attempt
2. stride_threats: STRIDE-categorized threats (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)
3. security_requirements: Actionable security controls to mitigate the identified threats

Each abuse case must have: id, threat, actor, description, impact (Critical/High/Medium/Low), likelihood (High/Medium/Low), attack_vector, stride_category
Each stride threat must have: category, threat, description, risk_level (Critical/High/Medium/Low)
Each security requirement must have: id, text, priority (Critical/High/Medium), category, details"""

DEFAULT_USER_PROMPT_TEMPLATE = """Analyze the following user story for security threats, abuse cases, and generate security requirements.

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

# Keep old names for backward compat
SYSTEM_PROMPT = DEFAULT_SYSTEM_PROMPT
USER_PROMPT_TEMPLATE = DEFAULT_USER_PROMPT_TEMPLATE

DEFAULT_MODEL = settings.default_model or PROVIDER_DEFAULTS.get(settings.llm_provider, "claude-sonnet-4-20250514")
DEFAULT_MAX_TOKENS = 4096


async def analyze_with_llm(
    title: str,
    description: str,
    acceptance_criteria: str | None = None,
    custom_standards: list[dict] | None = None,
    system_prompt: str | None = None,
    user_prompt_template: str | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
    provider_name: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> dict:
    """Call configured LLM provider to generate security analysis. Returns parsed dict or raises."""
    sys_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
    usr_template = user_prompt_template or DEFAULT_USER_PROMPT_TEMPLATE
    tokens = max_tokens or DEFAULT_MAX_TOKENS

    # Determine provider
    if provider_name and api_key:
        provider = get_provider(provider_name, api_key=api_key, base_url=base_url or "")
    else:
        provider = get_default_provider()

    # Determine model
    effective_provider = provider_name or settings.llm_provider
    ai_model = model or settings.default_model or PROVIDER_DEFAULTS.get(effective_provider, "")
    if not ai_model:
        raise ValueError(f"No model configured for provider {effective_provider}")

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

    user_prompt = usr_template.format(
        title=title,
        description=description,
        acceptance_criteria_section=ac_section,
        custom_standards_section=cs_section,
    )

    llm_response = await provider.chat(sys_prompt, user_prompt, ai_model, tokens)

    response_text = llm_response.text
    raw_response = response_text

    # Extract JSON from response (may be wrapped in markdown code block)
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]

    result = json.loads(response_text.strip())
    result["_raw_response"] = raw_response
    result["_model"] = llm_response.model
    result["_input_tokens"] = llm_response.input_tokens
    result["_output_tokens"] = llm_response.output_tokens
    logger.info("LLM analysis completed (%s/%s): %d abuse cases, %d requirements",
                effective_provider, ai_model,
                len(result.get("abuse_cases", [])), len(result.get("security_requirements", [])))
    return result


# Backward compatibility alias
analyze_with_claude = analyze_with_llm
