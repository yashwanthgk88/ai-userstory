"""Maps security requirements to compliance framework controls."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"

# Category keywords for each standard's controls
STANDARD_CATEGORY_MAP = {
    "OWASP_ASVS": {
        "Authentication & Access Control": ["V2", "V3", "V4"],
        "Data Protection": ["V6", "V8"],
        "Input Validation": ["V5"],
        "Audit Logging": ["V7"],
        "Financial & Transaction Security": ["V6", "V11"],
        "Regulatory Compliance": ["V10"],
        "Secure Architecture": ["V1", "V10", "V14"],
    },
    "NIST_800_53": {
        "Authentication & Access Control": ["AC", "IA"],
        "Data Protection": ["SC", "MP"],
        "Input Validation": ["SI"],
        "Audit Logging": ["AU"],
        "Financial & Transaction Security": ["SC", "AC"],
        "Regulatory Compliance": ["CA", "PL"],
        "Secure Architecture": ["SA", "SC"],
    },
    "ISO_27001": {
        "Authentication & Access Control": ["A.9"],
        "Data Protection": ["A.10", "A.18"],
        "Input Validation": ["A.14"],
        "Audit Logging": ["A.12"],
        "Financial & Transaction Security": ["A.10", "A.14"],
        "Regulatory Compliance": ["A.18"],
        "Secure Architecture": ["A.13", "A.14"],
    },
    "PCI_DSS": {
        "Authentication & Access Control": ["Req 7", "Req 8"],
        "Data Protection": ["Req 3", "Req 4"],
        "Input Validation": ["Req 6"],
        "Audit Logging": ["Req 10"],
        "Financial & Transaction Security": ["Req 3", "Req 4"],
        "Regulatory Compliance": ["Req 12"],
        "Secure Architecture": ["Req 1", "Req 2"],
    },
    "HIPAA": {
        "Authentication & Access Control": ["164.312(d)", "164.312(a)"],
        "Data Protection": ["164.312(a)(2)(iv)", "164.312(e)"],
        "Input Validation": ["164.312(c)"],
        "Audit Logging": ["164.312(b)"],
        "Regulatory Compliance": ["164.308", "164.316"],
        "Secure Architecture": ["164.312(e)"],
    },
    "SOX": {
        "Authentication & Access Control": ["ITGC-AC"],
        "Data Protection": ["ITGC-DP"],
        "Audit Logging": ["ITGC-AL"],
        "Financial & Transaction Security": ["ITGC-FC"],
        "Regulatory Compliance": ["ITGC-CM"],
        "Secure Architecture": ["ITGC-SA"],
    },
    "GDPR": {
        "Authentication & Access Control": ["Art 25", "Art 32"],
        "Data Protection": ["Art 5", "Art 32"],
        "Audit Logging": ["Art 30"],
        "Regulatory Compliance": ["Art 35", "Art 37"],
    },
}


def _load_standard(name: str) -> list[dict]:
    path = DATA_DIR / f"{name.lower()}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def map_requirements_to_standards(
    security_requirements: list[dict],
    standards: list[str] | None = None,
    custom_standards: list[dict] | None = None,
) -> list[dict]:
    """
    For each security requirement, find matching controls from each compliance standard.
    Returns list of {requirement_id, standard_name, control_id, control_title, relevance_score}.
    """
    if standards is None:
        standards = list(STANDARD_CATEGORY_MAP.keys())

    mappings = []

    for req in security_requirements:
        req_id = req.get("id", "")
        req_category = req.get("category", "")

        for std_name in standards:
            category_map = STANDARD_CATEGORY_MAP.get(std_name, {})
            matched_controls = category_map.get(req_category, [])

            # Load detailed controls from data files
            controls_data = _load_standard(std_name)

            for control_prefix in matched_controls:
                # Find matching controls in the data file
                matched = [c for c in controls_data if c.get("id", "").startswith(control_prefix)]
                if matched:
                    for c in matched[:2]:  # Limit to top 2 per prefix
                        mappings.append({
                            "requirement_id": req_id,
                            "standard_name": std_name,
                            "control_id": c["id"],
                            "control_title": c.get("title", ""),
                            "relevance_score": 0.8,
                        })
                else:
                    # Use the prefix itself as a generic mapping
                    mappings.append({
                        "requirement_id": req_id,
                        "standard_name": std_name,
                        "control_id": control_prefix,
                        "control_title": f"{std_name} control {control_prefix}",
                        "relevance_score": 0.6,
                    })

        # Map to custom standards
        if custom_standards:
            for cs in custom_standards:
                for control in cs.get("controls", []):
                    ctrl_cat = control.get("category", "").lower()
                    req_cat_lower = req_category.lower()
                    if ctrl_cat and (ctrl_cat in req_cat_lower or req_cat_lower in ctrl_cat):
                        mappings.append({
                            "requirement_id": req_id,
                            "standard_name": cs.get("name", "Custom"),
                            "control_id": control.get("control_id", ""),
                            "control_title": control.get("title", ""),
                            "relevance_score": 0.7,
                        })

    return mappings
