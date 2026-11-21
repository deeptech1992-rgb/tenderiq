import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tenderiq.extractor import extract_tender, parse_money
from tenderiq.compliance import check_compliance
from tenderiq.pipeline import analyze_text, load_profile

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = (ROOT / "sample_data" / "sample_tender.txt").read_text(encoding="utf-8")


def test_parse_money():
    assert parse_money("Rs. 5,00,000/-") == 500000
    assert parse_money("₹50.00 lakh") == 5000000
    assert parse_money("20 lakh") == 2000000
    assert parse_money("2 crore") == 20000000
    assert parse_money("10,000") == 10000
    assert parse_money("nothing here") is None


def test_extract_sample_tender():
    c = extract_tender(SAMPLE)
    assert c["tender_id"] == "EE/PUNE/2024-25/142"
    assert c["emd_amount"] == 500000
    assert c["tender_fee"] == 10000
    assert c["min_avg_annual_turnover"] == 5000000
    assert c["turnover_window"] == "any 3 of last 5 financial years"
    assert c["min_experience_years"] == 5
    sw = c["similar_works_required"]
    assert sw["count"] == 3
    assert sw["min_value_each"] == 2000000
    assert sw["window_years"] == 7
    assert c["bid_validity_days"] == 180
    assert c["submission_deadline"].startswith("15/01/2035")
    assert c["bid_opening_date"].startswith("16/01/2035")
    assert c["pre_bid_meeting"].startswith("05/01/2035")
    assert c["pan_gst_required"] is True
    assert c["mse_exemption"] is True
    assert "Pune" in (c["work_location"] or "")


def test_compliance_pass_profile():
    c = extract_tender(SAMPLE)
    profile = load_profile(ROOT / "sample_data" / "profile_pass.json")
    r = check_compliance(c, profile, today=date(2025, 1, 1))
    assert r["verdict"] == "READY TO BID"
    assert r["score"] == 100
    assert r["days_to_deadline"] == (date(2035, 1, 15) - date(2025, 1, 1)).days


def test_compliance_fail_profile():
    c = extract_tender(SAMPLE)
    profile = load_profile(ROOT / "sample_data" / "profile_fail.json")
    r = check_compliance(c, profile, today=date(2025, 1, 1))
    assert r["verdict"].startswith("NOT READY")
    assert r["fail_count"] >= 4
    failed = {chk["criterion"] for chk in r["checks"] if chk["status"] == "FAIL"}
    assert "Minimum average annual turnover" in failed
    assert "Similar works completed" in failed
    assert "PAN / GST registration" in failed


def test_pipeline_end_to_end():
    profile = load_profile(ROOT / "sample_data" / "profile_pass.json")
    result = analyze_text(SAMPLE, profile, today=date(2025, 1, 1))
    assert result["verdict"] == "READY TO BID"
    assert "READY TO BID" in result["report_html"]
    assert "EE/PUNE/2024-25/142" in result["report_html"]


def test_deadline_passed():
    c = extract_tender(SAMPLE)
    profile = load_profile(ROOT / "sample_data" / "profile_pass.json")
    r = check_compliance(c, profile, today=date(2035, 2, 1))
    assert r["days_to_deadline"] < 0
    dl = next(chk for chk in r["checks"] if chk["criterion"] == "Submission deadline")
    assert dl["status"] == "FAIL"


def test_api_smoke():
    from fastapi.testclient import TestClient
    sys.path.insert(0, str(ROOT / "app"))
    from main import app
    client = TestClient(app)
    assert client.get("/api/health").json()["status"] == "ok"
    profile = json.dumps(load_profile(ROOT / "sample_data" / "profile_pass.json"))
    resp = client.post(
        "/api/analyze",
        files={"tender_file": ("tender.txt", SAMPLE, "text/plain")},
        data={"profile": profile},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "READY TO BID"
