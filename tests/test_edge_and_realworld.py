import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tenderiq.extractor import extract_tender
from tenderiq.pipeline import analyze_text, load_text, load_profile

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = (ROOT / "sample_data" / "sample_tender.txt").read_text(encoding="utf-8")
IOCL = ROOT / "tests/real_world/iocl_primetenders.pdf"
CWC = ROOT / "tests/real_world/cwc_emd_circular.pdf"


def test_real_world_iocl_fields():
    c = extract_tender(load_text(IOCL))
    assert "PT-019" in c["tender_id"]
    assert c["emd_amount"] == 77427
    assert c["tender_fee"] == 0
    assert c["estimated_cost"] == 30970530
    assert c["bid_validity_days"] == 180
    assert c["min_avg_annual_turnover"] == 18583000
    opts = sorted([o["count"], o["min_value_each"]] for o in c["similar_works_required"]["options"])
    assert opts == [[1, 15486000], [2, 12389000], [3, 9292000]]
    assert c["similar_works_required"]["window_years"] == 7
    assert c["submission_deadline"] is None
    assert c["dates_as_per_portal"] is True
    assert "Jaipur" in c["work_location"]
    assert "Indian Oil" in c["organization"]


def test_real_world_circular_negative():
    c = extract_tender(load_text(CWC))
    assert c["emd_amount"] is None
    assert c["min_avg_annual_turnover"] is None
    assert c["tender_id"] is None


def test_empty_input_warns_and_does_not_crash():
    r = analyze_text("", {}, today=date(2025, 1, 1))
    assert r["verdict"] == "INSUFFICIENT DATA"
    assert any("OCR" in w for w in r["warnings"])
    assert "⚠" in r["report_html"]


def test_garbage_input_no_crash():
    r = analyze_text("lorem ipsum dolor sit amet 12345", {"name": "X"}, today=date(2025, 1, 1))
    assert r["verdict"] in ("INSUFFICIENT DATA", "READY TO BID", "NOT READY", "CONDITIONAL — 1 GAP")
    assert isinstance(r["report_html"], str) and len(r["report_html"]) > 500


def test_string_typed_profile_coerced():
    profile = {"name": "Str Co", "avg_annual_turnover": "80,00,000", "years_in_business": "8",
               "similar_works_completed": "4", "avg_similar_work_value": "30,00,000",
               "emd_budget": "10,00,000", "has_pan_gst": "yes"}
    r = analyze_text(SAMPLE, profile, today=date(2025, 1, 1))
    assert r["verdict"] == "READY TO BID"


def test_missing_profile_keys_needs_data_not_false_fail():
    r = analyze_text(SAMPLE, {"name": "Empty Co"}, today=date(2025, 1, 1))
    assert r["verdict"] == "NEEDS PROFILE DATA"
    statuses = {c["criterion"]: c["status"] for c in r["checks"]}
    assert statuses["Minimum average annual turnover"] == "INFO"
    assert statuses["PAN / GST registration"] == "INFO"


def test_sample_source_labelled():
    profile = load_profile(ROOT / "sample_data" / "profile_pass.json")
    r = analyze_text(SAMPLE, profile, today=date(2025, 1, 1), source="sample")
    assert "SAMPLE DATA" in r["report_html"]
    assert r["source"] == "sample"


def test_api_journeys():
    from fastapi.testclient import TestClient
    sys.path.insert(0, str(ROOT / "app"))
    from main import app
    client = TestClient(app)

    assert client.get("/api/health").json()["status"] == "ok"
    idx = client.get("/")
    assert idx.status_code == 200 and 'name="viewport"' in idx.text

    demo = client.get("/demo")
    assert demo.status_code == 200 and "SAMPLE DATA" in demo.text and "READY TO BID" in demo.text

    profile = json.dumps(load_profile(ROOT / "sample_data" / "profile_pass.json"))
    ok = client.post("/api/analyze", data={"use_sample": "1", "profile": profile})
    assert ok.status_code == 200 and ok.json()["verdict"] == "READY TO BID"

    bad_ext = client.post("/api/analyze", files={"tender_file": ("evil.exe", b"MZ", "application/octet-stream")},
                          data={"profile": profile})
    assert bad_ext.status_code == 400 and "error" in bad_ext.json()

    empty = client.post("/api/analyze", files={"tender_file": ("empty.txt", b"", "text/plain")},
                        data={"profile": profile})
    assert empty.status_code == 400 and "empty" in empty.json()["error"]

    whitespace = client.post("/api/analyze", files={"tender_file": ("scan.txt", b"   ", "text/plain")},
                             data={"profile": profile})
    assert whitespace.status_code == 200 and any("OCR" in w for w in whitespace.json()["warnings"])

    bad_json = client.post("/api/analyze", data={"use_sample": "1", "profile": "{not json"})
    assert bad_json.status_code == 400

    real_pdf = client.post("/api/analyze",
                           files={"tender_file": ("iocl.pdf", IOCL.read_bytes(), "application/pdf")},
                           data={"profile": profile})
    assert real_pdf.status_code == 200
    body = real_pdf.json()
    assert body["criteria"]["emd_amount"] == 77427
    assert body["criteria"]["estimated_cost"] == 30970530
    assert any("as per NIT" in w for w in body["warnings"])
    assert "Evidence" in body["report_html"] if "report_html" in body else True

    form = client.post("/analyze", data={"use_sample": "1", "name": "Demo Co"})
    assert form.status_code == 200 and "Bid-Readiness Report" in form.text

    fake_pdf = client.post("/analyze", files={"tender_file": ("bad.pdf", b"not a pdf", "application/pdf")})
    assert fake_pdf.status_code == 400 and "not a valid PDF" in fake_pdf.text

    big = client.post("/api/analyze", files={"tender_file": ("big.txt", b"x" * (11 * 1024 * 1024), "text/plain")},
                      data={"profile": profile})
    assert big.status_code == 400 and "too large" in big.json()["error"]
