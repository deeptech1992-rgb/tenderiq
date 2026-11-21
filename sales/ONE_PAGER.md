# TenderIQ — Sales One-Pager (v0.2, evidence-checked)
**Company:** TenderIQ Labs Pvt. Ltd. · **Product:** TenderIQ — offline, auditable bid-readiness checker for Indian government tenders (NIT PDF → clauses + eligibility verdict + source excerpts).

## 30-second pitch

"Your bid team reads 80–150-page NITs and still misses clauses — a missed EMD or turnover clause means disqualification and a forfeited EMD (GFR 2017 Rule 165). TenderIQ reads the tender in seconds, shows every requirement **with the exact source text it came from**, and scores your company profile against it: READY / CONDITIONAL / NOT READY. It runs fully offline — your tender documents never leave your machine."

## Target customer (specific, not "everyone")

- **Segment:** MSME/Class-II EPC contractors and PSU vendors in India bidding 5–20 tenders/month on GeM/CPPP/state portals, esp. those handling **defence/PSU tenders where uploading bid documents to a third-party cloud is a security concern** (hypothesis — validate in discovery).
- **Day-to-day user:** bid coordinator / tender executive.
- **Evaluator:** GM Projects / Head of bids.
- **Buyer/budget owner:** MD/Owner (MSMEs) — already spends ₹2.4k–₹50k/yr on tender aggregators and bid consultants.
- **Job-to-be-done:** go/no-go on each tender in minutes, with a verifiable compliance checklist, without risking document confidentiality.

## Pricing (test, don't assume)

| Plan | Price | Notes |
|---|---|---|
| Single-tender pilot | ₹25,000 one-time | 5 tenders analyzed + reports |
| Annual license | ₹1,00,000 + GST/yr | unlimited analyses, 5 seats, offline desktop build |
| White-label / API embed for aggregators | custom | our engine inside their portal |

⚠ Honesty flag: competitors advertise lower entry prices (TenderFlow Pro claims ₹2,999/mo unlimited on its own blog — vendor claim, unverified). Our ₹1L anchor must be justified by offline/privacy/enterprise needs or lowered (₹49k–₹99k entry tier is the safer test). Validate willingness-to-pay before quoting.

## Competitor landscape (researched this session; links in docs/REVIEW notes)

| Player | What they do | Pricing evidence | Our gap vs them |
|---|---|---|---|
| Tender247 + BidControl247 (bidcontrol247.com) | Discovery + AI tender analysis, Go/No-Go vs company profile, annexures | Not published; free demo registration; sales-gated | They are cloud LLM; we are offline + excerpt-auditable |
| BidCompass.in | Discovery + AI eligibility + bid doc generation | ₹10,000 wallet credit free tier (self-reported) | Same feature overlap; they add doc-gen |
| Minaions.com | 200+ portals, OCR 20+ languages, eligibility verification | Not verified | OCR we lack; offline we have |
| QuickBid.co.in, BidIndia.co.in, Arched.ai | AI tender analysis/discovery | Not verified | — |
| TenderFlow Pro (tenderflowpro.in) | "Bid Readiness Score", rejection-risk scan, ₹2,999/mo claim | Vendor blog (Aug 2026), unverified | Price anchor for the category |
| Tender Tiger / TendersOnTime / TenderDetail / BidAssist | Discovery aggregators (no deep eligibility parsing) | Tender Tiger from ~₹2,400/yr (ContraVault blog); TendersOnTime free Indian tier | They find tenders; we judge them |
| Global RFP tools (Loopio, Responsive, 1up, DeepRFP, AutogenAI) | US/EU enterprise RFP response | Loopio ~$20k/yr/10 seats; Responsive $15–25k+/yr (community reports); 1up $300/mo; DeepRFP $75/user/mo | Wrong geography; not GeM/NIT-native |
| Manual bid teams / Excel checklists | Status quo | Cost = 2–5 person-days per tender (inference) | We are faster and auditable |

## Market evidence (verified vs estimated)

- **Verified (PIB/DD News, 2025–2026):** GeM GMV >₹5 lakh crore in FY 2024-25 (₹4.09 lakh cr by 23 Jan 2025, ~50% YoY); cumulative >₹20 lakh crore; 25.45 lakh sellers, 1.37 lakh buyer orgs; MSEs = 45.6% of cumulative GMV; 42,242 startups won ₹65,633 cr of orders.
- **Estimate (industry, not official):** total Indian public procurement ₹50–70 lakh crore/yr (~20–22% of GDP) — TenderDekho blog, Oct 2025.
- **Pain mechanism verified:** EMD forfeiture on withdrawal/non-acceptance is automatic under GFR 2017 Rule 165(ix) (CWC circular, nic.in). "68% of MSME bids rejected" / "20–30% rejected pre-price" are **vendor blog claims (TenderFlow Pro), unverified** — do not quote them to customers as facts.

## Demo script (3 min)

1. `GET /demo` — one click, sample NIT, SAMPLE DATA badge visible. Show verdict + score.
2. Expand "Evidence — source excerpts": every extracted value sits next to the document text that produced it.
3. Upload a real tender PDF the prospect brings; show warnings (e.g., "dates as per NIT/portal") instead of silent gaps.
4. Close: "Send me 5 of your last tenders — I'll show you which ones you were actually eligible for. If even one was wrongly skipped, the pilot pays for itself."

## Objection handling

- "We use Tender247/BidControl247" → "Those upload your bid documents to their cloud and give you a black-box score. TenderIQ runs offline and shows the exact clause behind every number — your compliance team can verify, not trust."
- "₹1 lakh is steep vs ₹2,999/mo tools" → agree, then: those are per-seat cloud SaaS with per-doc limits; we're unlimited offline for the whole bid team, and defence/PSU bids often can't be uploaded externally at all. If price is the blocker, pilot at ₹25k.
- "Does it read scanned PDFs?" → Not yet — it says so explicitly on the report instead of guessing. OCR layer is the next build.

## Readiness verdict (see TESTING.md)

Ready to **show the prototype with limitations stated** and run **customer-discovery conversations**. Not yet ready for a commercial offer: accuracy verified on only n=3 documents, OCR missing, no auth/security hardening, willingness-to-pay unvalidated, and the category has funded cloud competitors.
