import re

LAKH = 100_000
CRORE = 10_000_000

_DATE_RE = re.compile(r"\b(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4})\b")
_TIME_RE = re.compile(r"\b([01]?\d[:.][0-5]\d)\s*(?:hrs?|hours?)?\s*(?:AM|PM|am|pm)?")

_WORD_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
             "seven": 7, "eight": 8, "nine": 9, "ten": 10}

_ID_STOPWORDS = {"tender", "no", "number", "id", "ref", "reference", "nit", "bid"}


def parse_money(text):
    if not text:
        return None
    s = str(text).lower()
    for token in ("₹", "rs.", "rs", "inr", "/-"):
        s = s.replace(token, " ")
    s = s.replace(",", "").strip()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(crore|crores|lakh|lakhs|lac|lacs|thousand)", s)
    if m:
        v = float(m.group(1))
        unit = m.group(2)
        if unit.startswith("crore"):
            return int(v * CRORE)
        if unit.startswith("lakh") or unit.startswith("lac"):
            return int(v * LAKH)
        return int(v * 1000)
    nums = re.findall(r"\d+(?:\.\d+)?", s)
    if nums:
        return int(float(nums[0]))
    return None


def _money_tokens(text, start, span=260, min_bare=100):
    toks = []
    seg = text[start:start + span]
    for m in re.finditer(r"\d[\d,.\-/]{0,20}\s*(?:lakh|lac|crore|thousand)?", seg, re.I):
        slice_ = m.group(0)
        has_unit = bool(re.search(r"lakh|lac|crore|thousand", slice_, re.I))
        val = parse_money(slice_)
        if val is None:
            continue
        if not has_unit and val < min_bare:
            continue
        excerpt = text[max(0, start + m.start() - 90):start + m.end() + 10].strip()
        toks.append((val, excerpt, has_unit))
    return toks


def _pick_turnover_token(toks):
    unit_toks = [t for t in toks if t[2]]
    if unit_toks:
        return unit_toks[0][0], unit_toks[0][1]
    if toks:
        smallest = min(toks, key=lambda t: t[0])
        return smallest[0], smallest[1]
    return None, None


def _first_date_in(text):
    m = _DATE_RE.search(text)
    if not m:
        return None
    parts = re.split(r"[/.\-]", m.group(1))
    if len(parts) == 3:
        dd, mm, yy = parts
        if len(yy) == 2:
            yy = "20" + yy
        try:
            return f"{int(dd):02d}/{int(mm):02d}/{int(yy)}"
        except ValueError:
            return m.group(1)
    return m.group(1)


def _date_time_near(text, keywords):
    for kw in keywords:
        for m in re.finditer(kw, text, re.I):
            for start, end in ((m.end(), min(len(text), m.end() + 160)),
                               (max(0, m.start() - 80), min(len(text), m.end() + 160))):
                win = text[start:end]
                d = _first_date_in(win)
                if d:
                    t = _TIME_RE.search(win)
                    return d + (f" {t.group(1)}" if t else "")
    return None


def _line_after(text, pattern):
    for line in text.splitlines():
        m = re.search(pattern, line, re.I)
        if m:
            tail = line[m.end():].strip(" .,:&")
            if tail:
                return tail
    return None


def _int_near(text, pattern):
    m = re.search(pattern, text, re.I)
    if not m:
        return None
    g = m.group(1).lower()
    if g in _WORD_NUM:
        return _WORD_NUM[g]
    try:
        return int(g)
    except ValueError:
        return None


def _extract_tender_id(flat):
    for pat in (r"(?<![\w-])Tender\s*No\.?\s*[:.]?\s*([A-Za-z0-9][A-Za-z0-9/.\-]*)",
                r"(?<![\w-])E-?Tender\s*Ref\.?\s*[:.]?\s*([A-Za-z0-9][A-Za-z0-9/.\-_]*)",
                r"(?<![\w-])NIT\s*(?:No\.?|Number|ID)\s*[:.]?\s*([A-Za-z0-9][A-Za-z0-9/.\-]*)",
                r"(?<![\w-])Bid\s*(?:No\.?|ID)\s*[:.]?\s*([A-Za-z0-9][A-Za-z0-9/.\-]*)",
                r"(?<![\w-])(?:NIT|Tender)\s*(?:No\.?|Number|ID|Ref(?:erence)?\.?)\s*[:.]?\s*([A-Za-z0-9][A-Za-z0-9/.\-]{3,40})"):
        m = re.search(pat, flat, re.I)
        if m:
            val = m.group(1).strip(" .,:")
            if len(val) >= 3 and val.lower() not in _ID_STOPWORDS:
                return val
    return None


def _extract_emd(flat):
    pat = re.compile(r"(?:Amount of EMD|EMD|Earnest Money(?: Deposit)?|Bid Security)\s*(?:of|is|shall be|:)?\s*(?:Rs\.?|INR|₹)?", re.I)
    for m in pat.finditer(flat):
        toks = _money_tokens(flat, m.end(), span=70, min_bare=1000)
        if toks:
            return toks[0][0], toks[0][1]
    return None, None


def _extract_fee(flat):
    m = re.search(r"(?:tender fee|document fee|cost of (?:the )?tender (?:document|form))\s*[:.]?\s*(Nil|Free|zero)", flat, re.I)
    if m:
        return 0, flat[max(0, m.start() - 40):m.end() + 20].strip()
    pat = re.compile(r"(?:tender fee|document fee|cost of (?:the )?tender (?:document|form))\s*(?:of|is|:)?\s*(?:Rs\.?|INR|₹)?", re.I)
    for m in pat.finditer(flat):
        toks = _money_tokens(flat, m.end(), span=70, min_bare=100)
        if toks:
            return toks[0][0], toks[0][1]
    return None, None


def _extract_turnover(flat):
    anchors = (r"minimum\s+(?:average\s+)?annual\s+turnover",
               r"average\s+annual\s+turnover",
               r"required\s+minimum\s+annual\s+turnover",
               r"annual\s+turnover\s+(?:shall be|should be|must be)\s+(?:at least|not less than|minimum)")
    for a in anchors:
        for m in re.finditer(a, flat, re.I):
            toks = _money_tokens(flat, m.end(), span=240, min_bare=10000)
            if toks:
                return _pick_turnover_token(toks)
    return None, None


def _extract_similar(flat):
    labels = [(int(m.group(1)), m.end()) for m in re.finditer(
        r"Value of\s*(\d+)\s+similar\s+completed\s+works?\s+each\s+costing\s+not\s+less\s+than", flat, re.I)]
    if labels:
        start = max(0, labels[0][1] - 350)
        win_years = _int_near(flat[start:labels[0][1]], r"last\s+([a-z0-9]+)\s*(?:years|yrs)")
        toks = _money_tokens(flat, labels[-1][1], span=220, min_bare=100000)
        vals = [v for v, _, _ in toks]
        counts = [c for c, _ in labels]
        if counts and len(vals) >= len(counts):
            vals = vals[-len(counts):]
            options = [{"count": c, "min_value_each": v} for c, v in zip(counts, vals)]
            return options, win_years, flat[start:labels[-1][1] + 220].strip()[:300]
    win = re.search(r"similar\s+w[oa]?r?ks?", flat, re.I)
    sw_win = flat[max(0, win.start() - 200):win.end() + 260] if win else ""
    count = _int_near(sw_win, r"(?:at least\s*)?(\d+)\s*(?:\([a-z]+\)\s*)?similar")
    if count is None and sw_win:
        count = _int_near(sw_win, r"(\d+)\s*(?:\([a-z]+\)\s*)?(?:similar\s+)?works?")
    val = None
    m = re.search(r"not less than\s*(?:the amount equal to\s*)?(?:Rs\.?\s*|₹\s*)?", sw_win, re.I)
    if m:
        toks = _money_tokens(sw_win, m.end(), span=60, min_bare=1000)
        if toks:
            val = toks[0][0]
    win_years = _int_near(sw_win, r"last\s*([a-z0-9]+)\s*(?:years|yrs)")
    if count or val:
        return [{"count": count, "min_value_each": val}], win_years, sw_win.strip()[:300]
    return None, None, None


def _extract_validity(flat):
    for m in re.finditer(r"valid\w*[^\d]{0,20}?(\d+)\s*(days|months)", flat, re.I):
        n = int(m.group(1))
        days = n * 30 if m.group(2).lower().startswith("month") else n
        return days, flat[max(0, m.start() - 40):m.end() + 10].strip()
    return None, None


def _extract_estimated_cost(flat):
    for m in re.finditer(r"estimated\s+cost[^.;]{0,80}?Rs\.?\s*", flat, re.I):
        toks = _money_tokens(flat, m.end(), span=40, min_bare=1000)
        if toks:
            return toks[0][0], toks[0][1]
    return None, None


def extract_tender(text):
    flat = re.sub(r"\s+", " ", text or "")
    out = {}
    exc = {}

    out["tender_id"] = _extract_tender_id(flat)
    exc["tender_id"] = flat[:200].strip() if out["tender_id"] else None

    out["title"] = _line_after(text, r"(?:NAME OF WORK|Name of work|Description of work|Title of work|Name of the work|Item of work)\s*[:.]?")
    if not out["title"]:
        m = re.search(r"(?:NAME OF WORK|Name of work|Description of work|Title of work)\s*[:.]?\s*([A-Za-z0-9 ,.\-()/'&]{5,200})", flat, re.I)
        out["title"] = m.group(1).strip(" .,:") if m else None
    exc["title"] = out["title"]

    m = re.search(r"((?:[A-Z][a-z][A-Za-z0-9&'-]*\s+){0,5}[A-Z][a-z][A-Za-z0-9&'-]*)\s+invites\s+(?:electronic\s+)?(?:e-?tenders?|bids|quotations)", flat)
    out["organization"] = m.group(1).strip(" .,:") if m else None
    if not out["organization"]:
        out["organization"] = _line_after(text, r"(?:Office of the|Department of|Issued by|Organisation|Organization)\s*[:.]?")
    if not out["organization"]:
        m = re.search(r"([A-Z][A-Za-z0-9 ,.&'()\-]*(?:Corporation|Limited|Ltd|Department|Board|Authority|Nigam|Division|PWD))", flat)
        out["organization"] = m.group(1).strip(" .,:") if m else None
    exc["organization"] = out["organization"]

    emd, e = _extract_emd(flat)
    out["emd_amount"] = emd
    exc["emd_amount"] = e
    fee, e = _extract_fee(flat)
    out["tender_fee"] = fee
    exc["tender_fee"] = e
    cost, e = _extract_estimated_cost(flat)
    out["estimated_cost"] = cost
    exc["estimated_cost"] = e

    out["submission_deadline"] = _date_time_near(flat, [
        r"last date (?:&|and)?\s*(?:time)?\s*(?:for|of)?\s*(?:submission|receipt|bid)?",
        r"bid (?:submission|closing)\s*(?:date|end date|deadline|ends on)",
        r"submission (?:end|closing) date",
        r"ends on",
        r"due date",
        r"bids? (?:must|should|shall) be (?:submitted|received) (?:online )?(?:by|before)",
        r"before",
    ])
    out["bid_opening_date"] = _date_time_near(flat, [
        r"due date for opening", r"opening of (?:the )?tender", r"bid opening",
        r"opening of (?:technical )?bids", r"date of opening",
    ])
    out["pre_bid_meeting"] = _date_time_near(flat, [r"pre[- ]bid"])
    out["dates_as_per_portal"] = bool(re.search(
        r"(?:submission|opening|pre-?bid)[^.;]{0,80}as per (?:the )?(?:NIT|e-?tender portal|portal)", flat, re.I))

    validity, e = _extract_validity(flat)
    out["bid_validity_days"] = validity
    exc["bid_validity_days"] = e

    to, e = _extract_turnover(flat)
    out["min_avg_annual_turnover"] = to
    exc["min_avg_annual_turnover"] = e
    out["turnover_window"] = None
    m = re.search(r"(?:any|in)\s*(?:of the preceding|of the last|of last)?\s*(\d+)\s*(?:of the last|of last)?\s*(\d+)\s*financial years", flat, re.I)
    if m:
        out["turnover_window"] = f"any {m.group(1)} of last {m.group(2)} financial years"
    else:
        m = re.search(r"(?:preceding|last)\s*(\d+)\s*financial years", flat, re.I)
        if m:
            out["turnover_window"] = f"any of preceding {m.group(1)} financial years"

    out["min_experience_years"] = _int_near(flat, r"(?:minimum\s+)?experience\s+of\s+(?:at least\s+)?([a-z0-9]+)\s*(?:years|yrs)")
    if out["min_experience_years"] is None:
        out["min_experience_years"] = _int_near(flat, r"([a-z0-9]+)\s*(?:years|yrs)\s+of\s+(?:relevant\s+)?experience")

    options, win_years, sw_exc = _extract_similar(flat)
    sw = {"options": options, "count": options[0]["count"] if options else None,
          "min_value_each": options[0]["min_value_each"] if options else None,
          "window_years": win_years}
    out["similar_works_required"] = sw
    exc["similar_works_required"] = sw_exc

    loc = _line_after(text, r"(?:place of (?:work|execution)|work location|site location|location of work)\s*[:.]?")
    if not loc:
        m = re.search(r"at\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)\s+(Terminal|Depot|Refinery|Plant|Airport|Port)\b", flat)
        if m:
            loc = f"{m.group(1)} {m.group(2)}"
    if not loc:
        m = re.search(r"District\s+([A-Za-z ]{2,40})", flat)
        if m:
            loc = "District " + m.group(1).strip()
    out["work_location"] = loc
    exc["work_location"] = loc

    out["pan_gst_required"] = bool(
        re.search(r"(?:PAN|GST(?:IN)?|GST registration)[^.;]{0,100}(?:mandatory|required|must|shall)", flat, re.I)
        or re.search(r"(?:mandatory|required)[^.;]{0,80}(?:PAN|GST(?:IN)?)", flat, re.I))
    out["mse_exemption"] = bool(re.search(
        r"(?:MSE|Micro and Small|Startup India|Udyam|DPIIT)[^.;]{0,140}(?:exempt|relaxation|applicable|preference)", flat, re.I))
    out["corrigenda"] = len(re.findall(r"corrigendum", flat, re.I))

    out["excerpts"] = exc
    return out
