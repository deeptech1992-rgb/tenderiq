import io
import json
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from tenderiq.pipeline import analyze_text, load_profile

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_TEXT = (ROOT / "sample_data" / "sample_tender.txt").read_text(encoding="utf-8")
SAMPLE_PROFILE = load_profile(ROOT / "sample_data" / "profile_pass.json")

MAX_BYTES = 10 * 1024 * 1024
ALLOWED_EXT = {".pdf", ".txt"}

app = FastAPI(title="TenderIQ", version="0.2.0")

INDEX_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>TenderIQ — Bid Readiness Checker for Indian Government Tenders</title>
<style>
body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:16px}
.wrap{max-width:760px;margin:0 auto;background:#1e293b;border-radius:14px;padding:24px}
h1{margin:0 0 4px;font-size:23px}.sub{color:#94a3b8;font-size:13px;margin-bottom:8px;line-height:1.5}
.tag{display:inline-block;background:#14532d;color:#86efac;font-size:11px;font-weight:700;padding:3px 10px;border-radius:999px;margin-bottom:12px}
label{display:block;font-size:12px;color:#94a3b8;margin:12px 0 4px;text-transform:uppercase;letter-spacing:.04em}
input[type=text],input[type=number]{width:100%;box-sizing:border-box;padding:9px 10px;border-radius:8px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;font-size:14px}
.row{display:flex;gap:12px;flex-wrap:wrap}.row>div{flex:1;min-width:140px}
button{margin-top:18px;width:100%;padding:12px;border:0;border-radius:8px;background:#16a34a;color:#fff;font-size:15px;font-weight:700;cursor:pointer}
button:hover{background:#15803d}
button.ghost{background:#334155}.ghost:hover{background:#475569}
.hint{font-size:12px;color:#64748b;margin-top:14px;line-height:1.6}
@media(max-width:640px){.wrap{padding:16px}h1{font-size:19px}}
</style></head><body><div class="wrap">
<span class="tag">OFFLINE · DETERMINISTIC · NO DATA LEAVES YOUR MACHINE</span>
<h1>TenderIQ</h1>
<div class="sub">Upload an Indian government tender (NIT) PDF and get an instant, auditable bid-readiness report:
every eligibility clause extracted with its source excerpt, scored against your company profile.
Built for MSME contractors bidding on GeM / CPPP / state e-procurement portals.</div>
<form method="post" action="/analyze" enctype="multipart/form-data">
<label>Tender document (PDF or TXT, max 10 MB)</label><input type="file" name="tender_file" accept=".pdf,.txt">
<button type="submit" name="use_sample" value="1" class="ghost">▶ Try it instantly with the sample tender</button>
<label>Company name</label><input type="text" name="name" value="Demo Constructions Pvt Ltd" required>
<div class="row">
<div><label>Avg annual turnover (₹)</label><input type="number" name="avg_annual_turnover" value="8000000"></div>
<div><label>Years in business</label><input type="number" name="years_in_business" value="8"></div>
</div>
<div class="row">
<div><label>Similar works completed</label><input type="number" name="similar_works_completed" value="4"></div>
<div><label>Avg value per similar work (₹)</label><input type="number" name="avg_similar_work_value" value="3000000"></div>
</div>
<div class="row">
<div><label>EMD budget available (₹)</label><input type="number" name="emd_budget" value="1000000"></div>
<div><label>PAN/GST registered?</label><input type="text" name="has_pan_gst" value="yes"></div>
</div>
<button type="submit">Analyze my bid readiness</button>
<div class="hint">v0.2 · Deterministic parser tuned for Indian eProcurement/GeM/NIT language. Shows the source text behind every extracted
value so you can verify it. Scanned/image-only PDFs need OCR — not included yet. Not legal advice; verify against the official document.
<a href="/demo" style="color:#86efac">Open the one-click demo report</a></div>
</form></div></body></html>"""

ERROR_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>TenderIQ — error</title>
<style>body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#0f172a;color:#e2e8f0;display:flex;
justify-content:center;padding:40px 16px}.box{max-width:520px;background:#1e293b;border-radius:12px;padding:24px}
h1{font-size:19px;margin-top:0}a{color:#86efac}</style></head><body><div class="box">
<h1>⚠ {title}</h1><p style="color:#94a3b8;font-size:14px;line-height:1.6">{msg}</p>
<p><a href="/">← Back to TenderIQ</a></p></div></body></html>"""


def _error(title, msg, status=400):
    page = ERROR_HTML.replace("{title}", str(title)).replace("{msg}", str(msg))
    return HTMLResponse(page, status_code=status)


def _profile_from_form(form):
    return {
        "name": form.get("name") or "Your Company",
        "avg_annual_turnover": form.get("avg_annual_turnover"),
        "years_in_business": form.get("years_in_business"),
        "similar_works_completed": form.get("similar_works_completed"),
        "avg_similar_work_value": form.get("avg_similar_work_value"),
        "emd_budget": form.get("emd_budget"),
        "has_pan_gst": form.get("has_pan_gst"),
    }


async def _read_upload(tender_file, use_sample):
    if use_sample == "1" or tender_file is None or not tender_file.filename:
        return SAMPLE_TEXT, "sample"
    ext = Path(tender_file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return None, f"Unsupported file type '{ext or '(none)'}'. Please upload a .pdf or .txt tender document."
    raw = await tender_file.read()
    if len(raw) == 0:
        return None, "The uploaded file is empty."
    if len(raw) > MAX_BYTES:
        return None, f"File too large ({len(raw) / 1048576:.1f} MB). Maximum allowed is 10 MB."
    if ext == ".pdf":
        if raw[:4] != b"%PDF":
            return None, "This file has a .pdf extension but is not a valid PDF."
        from pypdf import PdfReader
        try:
            reader = PdfReader(io.BytesIO(raw))
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception:
            return None, "Could not read this PDF (it may be corrupted or encrypted)."
        return text, "upload"
    return raw.decode("utf-8", errors="replace"), "upload"


@app.get("/", response_class=HTMLResponse)
def index():
    return INDEX_HTML


@app.get("/demo", response_class=HTMLResponse)
def demo():
    result = analyze_text(SAMPLE_TEXT, SAMPLE_PROFILE, source="sample")
    return HTMLResponse(result["report_html"])


@app.get("/api/health")
def health():
    return {"status": "ok", "product": "TenderIQ", "version": "0.2.0"}


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(tender_file: UploadFile = File(None), use_sample: str = Form("0"),
                  name: str = Form("Your Company"), avg_annual_turnover: str = Form(""),
                  years_in_business: str = Form(""), similar_works_completed: str = Form(""),
                  avg_similar_work_value: str = Form(""), emd_budget: str = Form(""),
                  has_pan_gst: str = Form("yes")):
    text, source = await _read_upload(tender_file, use_sample)
    if text is None:
        return _error("Upload problem", source)
    form = {"name": name, "avg_annual_turnover": avg_annual_turnover, "years_in_business": years_in_business,
            "similar_works_completed": similar_works_completed, "avg_similar_work_value": avg_similar_work_value,
            "emd_budget": emd_budget, "has_pan_gst": has_pan_gst}
    result = analyze_text(text, _profile_from_form(form), source=source)
    return HTMLResponse(result["report_html"])


@app.post("/api/analyze")
async def api_analyze(tender_file: UploadFile = File(None), profile: str = Form("{}"),
                      use_sample: str = Form("0")):
    text, source = await _read_upload(tender_file, use_sample)
    if text is None:
        return JSONResponse({"error": source}, status_code=400)
    try:
        profile_data = json.loads(profile) if profile else {}
    except json.JSONDecodeError:
        return JSONResponse({"error": "profile field is not valid JSON"}, status_code=400)
    result = analyze_text(text, profile_data, source=source)
    return JSONResponse({k: v for k, v in result.items() if k != "report_html"})
