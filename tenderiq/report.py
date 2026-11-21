import html
from datetime import datetime

from .compliance import fmt_inr

_VERDICT_COLORS = {
    "READY TO BID": "#16a34a",
    "CONDITIONAL": "#d97706",
    "NOT READY": "#dc2626",
    "NEEDS PROFILE DATA": "#2563eb",
    "INSUFFICIENT DATA": "#64748b",
}
_STATUS_COLORS = {"PASS": "#16a34a", "FAIL": "#dc2626", "INFO": "#2563eb"}


def _esc(v):
    return html.escape(str(v)) if v is not None else "—"


def _chip(status):
    color = _STATUS_COLORS.get(status.split(" ")[0], "#64748b")
    return (f'<span style="background:{color};color:#fff;padding:2px 10px;border-radius:999px;'
            f'font-size:12px;font-weight:600;white-space:nowrap">{_esc(status)}</span>')


def _verdict_color(verdict):
    for k, c in _VERDICT_COLORS.items():
        if verdict.startswith(k):
            return c
    return "#64748b"


def render_report(criteria, result, profile, warnings=None, source="upload"):
    verdict = result["verdict"]
    vcolor = _verdict_color(verdict)
    score = result["score"]

    warn_html = ""
    for w in (warnings or []):
        warn_html += (f'<div style="background:#fef3c7;border:1px solid #f59e0b;color:#92400e;'
                      f'border-radius:8px;padding:10px 12px;font-size:13px;margin:12px 0">⚠ {_esc(w)}</div>')

    sample_badge = ('<div style="display:inline-block;background:#7c3aed;color:#fff;padding:4px 12px;'
                    'border-radius:999px;font-size:12px;font-weight:700;margin-left:10px">SAMPLE DATA — DEMO</div>'
                    if source == "sample" else "")

    rows = []
    for c in result["checks"]:
        note = f'<div style="color:#64748b;font-size:12px">{_esc(c["note"])}</div>' if c["note"] else ""
        rows.append(
            f"<tr><td><b>{_esc(c['criterion'])}</b></td><td>{_esc(c['requirement'])}</td>"
            f"<td>{_esc(c['actual'])}</td><td>{_chip(c['status'])}</td><td>{note}</td></tr>")
    checks_table = (
        '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:14px;min-width:640px">'
        '<tr style="background:#f1f5f9;text-align:left"><th style="padding:8px">Criterion</th>'
        '<th style="padding:8px">Requirement</th><th style="padding:8px">Your profile</th>'
        '<th style="padding:8px">Status</th><th style="padding:8px">Action</th></tr>'
        + "".join(rows) + "</table></div>")

    sw = criteria.get("similar_works_required") or {}
    opts = sw.get("options") or []
    if opts:
        sw_txt = " OR ".join(f"{o.get('count')} works each ≥ {fmt_inr(o.get('min_value_each'))}" for o in opts) \
                 + (f", last {sw.get('window_years')} yrs" if sw.get("window_years") else "")
    else:
        sw_txt = None
    facts = [
        ("Tender ID", criteria.get("tender_id")),
        ("Work title", criteria.get("title")),
        ("Organization", criteria.get("organization")),
        ("Work location", criteria.get("work_location")),
        ("Estimated cost", fmt_inr(criteria.get("estimated_cost"))),
        ("EMD", fmt_inr(criteria.get("emd_amount"))),
        ("Tender fee", fmt_inr(criteria.get("tender_fee"))),
        ("Submission deadline", criteria.get("submission_deadline")
         or ("as per NIT/portal — see warning" if criteria.get("dates_as_per_portal") else None)),
        ("Bid opening", criteria.get("bid_opening_date")),
        ("Pre-bid meeting", criteria.get("pre_bid_meeting")),
        ("Bid validity", f"{criteria['bid_validity_days']} days" if criteria.get("bid_validity_days") else None),
        ("Min. avg annual turnover", fmt_inr(criteria.get("min_avg_annual_turnover")) +
         (f" ({criteria['turnover_window']})" if criteria.get("turnover_window") else "")),
        ("Min. experience", f"{criteria['min_experience_years']} years" if criteria.get("min_experience_years") is not None else None),
        ("Similar works", sw_txt),
        ("PAN/GST mandatory", "Yes" if criteria.get("pan_gst_required") else "Not stated"),
        ("MSE/Startup exemption", "Yes" if criteria.get("mse_exemption") else "Not stated"),
        ("Corrigenda mentioned", criteria.get("corrigenda") or 0),
    ]
    fact_cards = "".join(
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 12px;min-width:200px;flex:1 1 200px">'
        f'<div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.04em">{_esc(k)}</div>'
        f'<div style="font-size:14px;font-weight:600;margin-top:2px;word-break:break-word">{_esc(v)}</div></div>'
        for k, v in facts)

    recs = [c["note"] for c in result["checks"] if c["status"] in ("FAIL", "INFO") and c["note"]]
    rec_html = "".join(f"<li>{_esc(r)}</li>" for r in recs) or "<li>No blocking gaps found — proceed to bid preparation.</li>"

    excerpts = criteria.get("excerpts") or {}
    exc_rows = []
    label_map = {
        "tender_id": "Tender ID", "emd_amount": "EMD", "tender_fee": "Tender fee",
        "estimated_cost": "Estimated cost", "min_avg_annual_turnover": "Turnover requirement",
        "bid_validity_days": "Bid validity", "similar_works_required": "Similar works clause",
    }
    for key, label in label_map.items():
        e = excerpts.get(key)
        if e:
            exc_rows.append(f"<tr><td style='padding:6px 8px;font-weight:600;white-space:nowrap'>{_esc(label)}</td>"
                            f"<td style='padding:6px 8px'><code style='font-size:11.5px;color:#334155;background:#f1f5f9;"
                            f"padding:2px 4px;border-radius:4px'>\"{_esc(e[:220])}{'…' if len(e) > 220 else ''}\"</code></td></tr>")
    evidence_html = ""
    if exc_rows:
        evidence_html = ("<h2>4. Evidence — source excerpts behind each extraction</h2>"
                         '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:13px">'
                         + "".join(exc_rows) + "</table></div>"
                         '<div style="font-size:12px;color:#64748b;margin-top:6px">Every extracted value above is shown with the exact '
                         "document text it came from, so a human can verify it in seconds. Deterministic parser — same input, same output.</div>")

    company = profile.get("name", "Your Company")
    generated = datetime.now().strftime("%d %b %Y, %H:%M")

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>TenderIQ Report — {_esc(company)}</title>
<style>body{{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#f1f5f9;margin:0;padding:16px;color:#0f172a}}
.wrap{{max-width:1000px;margin:0 auto;background:#fff;border-radius:12px;box-shadow:0 1px 4px rgba(0,0,0,.08);padding:20px}}
h1{{margin:0 0 4px;font-size:21px}}.sub{{color:#64748b;font-size:13px;margin-bottom:16px}}
.verdict{{display:inline-block;color:#fff;background:{vcolor};padding:6px 16px;border-radius:8px;font-weight:700;font-size:15px}}
.scorebar{{background:#e2e8f0;border-radius:999px;height:14px;margin:14px 0 4px;overflow:hidden}}
.scorefill{{background:{vcolor};height:100%;width:{score}%}}
.scorepct{{font-size:13px;color:#475569;margin-bottom:8px}}
h2{{font-size:16px;margin:24px 0 10px;border-bottom:2px solid #e2e8f0;padding-bottom:6px}}
.grid{{display:flex;flex-wrap:wrap;gap:10px}}
ul{{padding-left:20px;font-size:14px;line-height:1.7}}
.footer{{margin-top:28px;font-size:12px;color:#94a3b8}}
td,th{{padding:8px;border-bottom:1px solid #e2e8f0;vertical-align:top;text-align:left}}
@media(max-width:640px){{.wrap{{padding:14px}}h1{{font-size:18px}}}}
</style></head><body><div class="wrap">
<h1>Bid-Readiness Report — {_esc(company)}{sample_badge}</h1>
<div class="sub">Generated by TenderIQ on {generated} · source: {_esc(source)}</div>
{warn_html}
<div class="verdict">{_esc(verdict)}</div>
<div class="scorebar"><div class="scorefill"></div></div>
<div class="scorepct">Readiness score: <b>{score}/100</b> &nbsp;·&nbsp; {result['fail_count']} gap(s) found</div>
<h2>1. Extracted tender requirements</h2>
<div class="grid">{fact_cards}</div>
<h2>2. Eligibility checks</h2>
{checks_table}
<h2>3. Recommended actions</h2>
<ul>{rec_html}</ul>
{evidence_html}
<div class="footer">TenderIQ Labs Pvt. Ltd. — deterministic, offline tender analysis for Indian bidders. Not legal advice; always verify against the
official tender document and corrigenda. Scanned/image-only PDFs require OCR (not included in this version).</div>
</div></body></html>"""
