# TenderIQ — auditable, offline bid-readiness checker for Indian government tenders

**Company:** TenderIQ Labs Pvt. Ltd.
**Product:** upload any NIT/tender PDF (or TXT) → get every key clause extracted **with the source excerpt behind each value** (EMD, tender fee, estimated cost, turnover requirement, experience, 3/2/1 similar-works rule, all dates, bid validity, PAN/GST, MSE exemption) → scored against your company profile → READY / CONDITIONAL / NOT READY + action list, as a shareable HTML report.

**Core design choice:** deterministic parser, runs fully offline, no LLM/API keys, same input → same output. Every extracted value is shown next to the exact document text it came from, so a bid manager can verify in seconds. This is the differentiation vs black-box LLM SaaS: auditable + private (no tender PDF leaves your machine) + zero per-document cost.

## Run it

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
# open http://127.0.0.1:8000  → click "Try it instantly with the sample tender"
# or one-click report: http://127.0.0.1:8000/demo

# CLI
python -m tenderiq.cli sample_data/sample_tender.txt --profile sample_data/profile_pass.json --out report.html

# Tests + accuracy benchmark (see TESTING.md)
python -m pytest tests/ -q        # 15 tests
python tools/benchmark.py         # 32/32 field checks on n=3 labeled docs
```

## API

- `GET /` upload UI · `GET /demo` one-click sample report (labeled SAMPLE DATA)
- `POST /analyze` form → HTML report · `POST /api/analyze` file+JSON profile → JSON (400s with friendly messages for bad/empty/oversized/wrong-type uploads)
- `GET /api/health`

## Verified status (see TESTING.md for detail)

- 15/15 automated tests pass; live HTTP smoke tests of every journey pass (this session).
- Extraction accuracy: **32/32 fields on n=3 documents** (1 synthetic + 2 real government PDFs, hand-verified ground truth) — small sample, not a statistical claim.
- Known gaps: scanned PDFs need OCR (not built; app warns instead of failing silently), English only, table heuristics can fail on unusual layouts, dates "as per NIT" are flagged not extracted, no corrigenda/BOQ parsing.

## Market context (sources in sales/ONE_PAGER.md)

GeM alone transacted >₹5 lakh crore in FY 2024-25 with 25.45 lakh registered sellers (PIB); total Indian
public procurement is estimated at ₹50–70 lakh crore/yr (industry estimate). Crowded field: Tender247/BidControl247,
BidCompass, Minaions, QuickBid, TenderFlow Pro already sell AI tender analysis/eligibility checks as cloud SaaS.
TenderIQ's defensible niche is **offline, auditable, no-upload** analysis for privacy-sensitive bids (defence/PSU)
and as an embeddable/white-label engine for aggregators — to be validated with customers, not assumed.
