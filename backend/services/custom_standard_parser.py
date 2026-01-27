"""Parse uploaded custom security standards (JSON, CSV, PDF) into structured controls."""

import csv
import io
import json
import logging

logger = logging.getLogger(__name__)


def parse_json(content: bytes) -> list[dict]:
    data = json.loads(content)
    if isinstance(data, list):
        return [_normalize_control(c) for c in data]
    if isinstance(data, dict) and "controls" in data:
        return [_normalize_control(c) for c in data["controls"]]
    raise ValueError("JSON must be an array of controls or an object with a 'controls' key")


def parse_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    controls = []
    for row in reader:
        controls.append(_normalize_control(row))
    return controls


def parse_pdf(content: bytes) -> list[dict]:
    """Extract text from PDF and attempt structured parsing. Falls back to raw text blocks."""
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber not installed, returning raw text control")
        return [{"control_id": "PDF-001", "title": "Imported PDF Standard", "description": "PDF parsing requires pdfplumber", "category": "General"}]

    controls = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += (page.extract_text() or "") + "\n"

    # Simple heuristic: split by numbered patterns like "1." or "1.1"
    import re
    sections = re.split(r"\n(?=\d+\.)", full_text)
    for i, section in enumerate(sections):
        section = section.strip()
        if len(section) > 20:
            lines = section.split("\n", 1)
            title = lines[0].strip()[:200]
            desc = lines[1].strip()[:500] if len(lines) > 1 else ""
            controls.append({
                "control_id": f"PDF-{i+1:03d}",
                "title": title,
                "description": desc,
                "category": "General",
            })

    return controls if controls else [{"control_id": "PDF-001", "title": "Imported PDF Standard", "description": full_text[:1000], "category": "General"}]


def _normalize_control(raw: dict) -> dict:
    return {
        "control_id": raw.get("control_id") or raw.get("id") or raw.get("Control ID") or "N/A",
        "title": raw.get("title") or raw.get("Title") or raw.get("name") or "",
        "description": raw.get("description") or raw.get("Description") or "",
        "category": raw.get("category") or raw.get("Category") or "General",
    }


def parse_file(content: bytes, filename: str) -> list[dict]:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "json":
        return parse_json(content)
    elif ext == "csv":
        return parse_csv(content)
    elif ext == "pdf":
        return parse_pdf(content)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Use JSON, CSV, or PDF.")
