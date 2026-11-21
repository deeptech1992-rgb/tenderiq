"""Extraction accuracy benchmark for TenderIQ.

Runs the deterministic extractor over a small labeled set (1 synthetic NIT +
2 real government PDFs with hand-verified ground truth) and prints per-field
results. Small sample by design — see TESTING.md for limitations.

Usage: python tools/benchmark.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tenderiq.extractor import extract_tender
from tenderiq.pipeline import load_text

CASES = [
    ("sample_data/sample_tender.txt", {
        "tender_id": "EE/PUNE/2024-25/142", "emd_amount": 500000, "tender_fee": 10000,
        "min_avg_annual_turnover": 5000000, "min_experience_years": 5, "bid_validity_days": 180,
        "submission_deadline_prefix": "15/01/2035", "bid_opening_date_prefix": "16/01/2035",
        "pre_bid_meeting_prefix": "05/01/2035", "pan_gst_required": True, "mse_exemption": True,
        "similar_count": 3, "similar_min_value": 2000000, "similar_window_years": 7,
        "work_location_contains": "Pune",
    }),
    ("tests/real_world/iocl_primetenders.pdf", json.loads(
        (ROOT / "tests/real_world/ground_truth.json").read_text())["iocl_primetenders.pdf"]),
    ("tests/real_world/cwc_emd_circular.pdf", json.loads(
        (ROOT / "tests/real_world/ground_truth.json").read_text())["cwc_emd_circular.pdf"]),
]


def check(field, expected, actual):
    if field.endswith("_contains"):
        return expected.lower() in (actual or "").lower(), actual
    if field.endswith("_prefix"):
        return (actual or "").startswith(expected), actual
    if field == "similar_options":
        got = sorted([o["count"], o["min_value_each"]] for o in (actual or {}).get("options") or [])
        return got == sorted(expected), got
    if field == "similar_count":
        return (actual or {}).get("count") == expected, (actual or {}).get("count")
    if field == "similar_min_value":
        return (actual or {}).get("min_value_each") == expected, (actual or {}).get("min_value_each")
    if field == "similar_window_years":
        return (actual or {}).get("window_years") == expected, (actual or {}).get("window_years")
    return actual == expected, actual


def main():
    total = passed = 0
    for rel, expected in CASES:
        text = load_text(ROOT / rel)
        got = extract_tender(text)
        print(f"\n=== {rel}  ({len(text)} chars extracted) ===")
        for field, exp in expected.items():
            if field in ("note",):
                continue
            if field == "tender_id_contains":
                ok, act = check(field, exp, got.get("tender_id"))
            elif field == "title_contains":
                ok, act = check(field, exp, got.get("title"))
            elif field == "organization_contains":
                ok, act = check(field, exp, got.get("organization"))
            elif field == "work_location_contains":
                ok, act = check(field, exp, got.get("work_location"))
            elif field == "turnover_window_contains":
                ok, act = check(field, exp, got.get("turnover_window"))
            elif field == "submission_deadline_prefix":
                ok, act = check(field, exp, got.get("submission_deadline"))
            elif field == "bid_opening_date_prefix":
                ok, act = check(field, exp, got.get("bid_opening_date"))
            elif field == "pre_bid_meeting_prefix":
                ok, act = check(field, exp, got.get("pre_bid_meeting"))
            elif field == "similar_options":
                ok, act = check(field, exp, got.get("similar_works_required"))
            elif field.startswith("similar_"):
                ok, act = check(field, exp, got.get("similar_works_required"))
            else:
                ok, act = check(field, exp, got.get(field))
            total += 1
            passed += ok
            print(f"  [{'PASS' if ok else 'FAIL'}] {field:32} expected={exp!r} actual={act!r}")
    print(f"\nTOTAL: {passed}/{total} field checks passed ({round(100*passed/total)}%) on n={len(CASES)} documents")


if __name__ == "__main__":
    main()
