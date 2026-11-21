import json
import re
from datetime import date
from pathlib import Path

from .extractor import extract_tender
from .compliance import check_compliance
from .report import render_report


def load_text(path):
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(p))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    return p.read_text(encoding="utf-8", errors="replace")


def analyze_text(text, profile, today=None, source="upload"):
    today = today or date.today()
    text = text or ""
    warnings = []
    if len(text.strip()) < 50:
        warnings.append(
            f"Only {len(text.strip())} characters of text could be extracted from this file. "
            "If it is a scanned/image-only PDF, OCR is required — OCR is NOT supported in this version. "
            "Results below are unreliable.")
    criteria = extract_tender(text)
    if criteria.get("dates_as_per_portal") and not criteria.get("submission_deadline"):
        warnings.append(
            "This document references key dates 'as per NIT / e-tender portal' — the actual dates are not in the "
            "file. Check the procurement portal before relying on the deadline check.")
    result = check_compliance(criteria, profile, today=today)
    report_html = render_report(criteria, result, profile, warnings=warnings, source=source)
    return {
        "criteria": {k: v for k, v in criteria.items() if k != "excerpts"},
        "excerpts": criteria.get("excerpts", {}),
        "checks": result["checks"],
        "score": result["score"],
        "verdict": result["verdict"],
        "days_to_deadline": result["days_to_deadline"],
        "warnings": warnings,
        "source": source,
        "text_chars": len(text.strip()),
        "report_html": report_html,
    }


def analyze_file(path, profile, today=None, source="upload"):
    return analyze_text(load_text(path), profile, today=today, source=source)


def load_profile(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
