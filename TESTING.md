# TenderIQ — Testing & Verification Log

**Date of run:** this session · **Environment:** Python 3.12, Linux sandbox, loopback-only HTTP tests (127.0.0.1). No mobile device or real browser was available; mobile layout was verified only via viewport meta tag + responsive CSS, not visually.

## 1. Unit / integration tests

`python -m pytest tests/ -q` → **15 passed, 0 failed** (last run this session).

Coverage: money parsing (lakh/crore/comma formats), extraction on synthetic NIT, pass/fail profiles,
deadline-passed case, real-world IOCL PDF fields, CWC circular negative case, empty/garbage input,
string-typed profile coercion, missing profile → INFO not false-FAIL, sample labeling, API health,
`/demo`, sample analyze, `.exe` → 400, empty file → 400, whitespace file → 200 + OCR warning,
bad JSON profile → 400, fake PDF → 400, >10 MB → 400, HTML form flow.

## 2. Extraction accuracy benchmark (labeled set, hand-verified ground truth)

`python tools/benchmark.py` → **32/32 field checks passed (100%) on n=3 documents**.

| Document | Type | Source | Fields checked | Result |
|---|---|---|---|---|
| `sample_data/sample_tender.txt` | synthetic NIT (PWD-style) | written for tests | 15 | 15/15 |
| `tests/real_world/iocl_primetenders.pdf` | **real** IOCL e-tender notice, 21 pages, 63,687 chars | docs.primetenders.com (May 2025) | 14 | 14/14 |
| `tests/real_world/cwc_emd_circular.pdf` | **real** CWC circular (negative case — not a tender), 18,393 chars | cewacor.nic.in (28.12.2023) | 3 | 3/3 |

Ground-truth method: a human (me) read the extracted text of each PDF and recorded the correct values
in `tests/real_world/ground_truth.json` — e.g., IOCL: EMD ₹77,427/-, estimated cost ₹3,09,70,530.02,
min annual turnover ₹1,85,83,000, 3/2/1 similar-works rule (≥₹92,92,000 / ₹1,23,89,000 / ₹1,54,86,000),
validity 180 days, tender no. MnC/NR/RSO/ENG/PT-019/25-26, location Jaipur Terminal. The extractor's
output was compared against these, not against itself.

Known real-world behavior worth stating plainly: the IOCL summary document says submission/opening
dates are "As per NIT" (they live on the portal, not in the file). The product now detects this and
shows a warning instead of silently showing no deadline.

## 3. Live end-to-end smoke tests (uvicorn on 127.0.0.1, via httpx)

- `GET /api/health` → 200 ok (v0.2.0)
- `GET /` → 200, viewport meta present, sample-demo button present
- `GET /demo` → 200, report with SAMPLE DATA badge, verdict READY TO BID, evidence-excerpt section
- `POST /api/analyze` (sample) → 200, READY TO BID, score 100, excerpts included
- `POST /api/analyze` (real IOCL PDF upload) → 200, emd 77427, est 30970530, turnover 18583000, id correct, 1 warning (dates as per portal), verdict NOT READY — 2 GAPS (correct: demo profile fails the 3/2/1 rule and turnover)
- `POST /api/analyze` `.exe` → 400 friendly error; empty file → 400; whitespace → 200 + OCR warning; bad JSON → 400; fake PDF → 400; >10 MB → 400
- `POST /analyze` form (sample) → 200 full HTML report

One bug found and fixed during smoke testing: error page used `str.format` on a template containing
CSS braces → 500 on invalid upload. Now uses `str.replace`; regression test added.

## 4. Limitations (honest list — do not demo past these)

1. **Sample size is tiny: n=3 documents.** 100% on 3 docs is not a statistical accuracy claim. Need 50–200 real NITs across portals (CPPP, GeM, state eProcurement, PSUs) before quoting accuracy.
2. **Text-layer PDFs only.** Scanned/image PDFs extract ~0 chars → the app now warns explicitly (OCR not built). Many PSU/state NITs are scanned.
3. **Table heuristics.** The 3/2/1 similar-works rule and "minimum turnover = smallest bare number in the table row" work on IOCL-style tables but can fail on unusual layouts.
4. **English only.** No Hindi/regional-language documents tested.
5. **Dates referenced "as per NIT/portal"** are not in many summary docs — handled with a warning, not extraction.
6. **PAN/GST and MSE flags are keyword booleans** — can false-positive/negative on odd phrasing.
7. **No corrigendum merging, no BOQ parsing, no clause-level risk scoring** — those are competitors' features.
8. **Not legal advice**; the compliance verdict is a screening aid, not a guarantee of qualification.
9. Security: no auth, no rate limiting, loopback demo only; uploads are read in-memory, never stored. Not production-hardened.
