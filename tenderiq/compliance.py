import re
from datetime import date, datetime

_NUMERIC_KEYS = ("avg_annual_turnover", "years_in_business", "similar_works_completed",
                 "avg_similar_work_value", "emd_budget")


def _num(v):
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(v)
    try:
        return int(float(str(v).replace(",", "").replace("₹", "").strip()))
    except (ValueError, TypeError):
        return None


def normalize_profile(profile):
    p = dict(profile or {})
    for k in _NUMERIC_KEYS:
        p[k] = _num(p.get(k))
    hp = p.get("has_pan_gst")
    if hp is None:
        p["has_pan_gst"] = None
    elif isinstance(hp, bool):
        p["has_pan_gst"] = hp
    else:
        p["has_pan_gst"] = str(hp).strip().lower() in ("yes", "true", "1")
    return p


def fmt_inr(n):
    if n is None:
        return "not provided"
    return "₹" + f"{int(n):,}"


def _parse_deadline(deadline_str):
    m = re.search(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})", deadline_str or "")
    if not m:
        return None
    dd, mm, yy = m.groups()
    if len(yy) == 2:
        yy = "20" + yy
    try:
        return datetime.strptime(f"{dd}/{mm}/{yy}", "%d/%m/%Y").date()
    except ValueError:
        return None


def check_compliance(criteria, profile, today=None):
    today = today or date.today()
    profile = normalize_profile(profile)
    checks = []

    def add(name, requirement, actual, status, note=""):
        checks.append({
            "criterion": name,
            "requirement": requirement,
            "actual": actual,
            "status": status,
            "note": note,
        })

    req = criteria.get("min_avg_annual_turnover")
    if req:
        actual = profile.get("avg_annual_turnover")
        window = criteria.get("turnover_window")
        req_txt = f"≥ {fmt_inr(req)}" + (f" ({window})" if window else "")
        if actual is None:
            add("Minimum average annual turnover", req_txt, "not provided", "INFO", "Enter your avg annual turnover in the profile")
        else:
            ok = actual >= req
            note = "" if ok else f"Shortfall of {fmt_inr(req - actual)} — consider JV/consortium or skip this bid"
            add("Minimum average annual turnover", req_txt, fmt_inr(actual), "PASS" if ok else "FAIL", note)

    req = criteria.get("min_experience_years")
    if req is not None:
        actual = profile.get("years_in_business")
        if actual is None:
            add("Minimum experience", f"≥ {req} years", "not provided", "INFO", "Enter years in business in the profile")
        else:
            ok = actual >= req
            note = "" if ok else f"Need {req} yrs, you have {actual} — highlight group-company experience or skip"
            add("Minimum experience", f"≥ {req} years", f"{actual} years", "PASS" if ok else "FAIL", note)

    sw = criteria.get("similar_works_required") or {}
    options = sw.get("options") or ([{"count": sw.get("count"), "min_value_each": sw.get("min_value_each")}]
                                    if sw.get("count") or sw.get("min_value_each") else [])
    if options:
        actual_count = profile.get("similar_works_completed")
        actual_value = profile.get("avg_similar_work_value")
        win = sw.get("window_years")
        win_txt = f" in last {win} years" if win else ""
        evaluated = []
        for opt in options:
            c_ok = opt.get("count") is None or (actual_count is not None and actual_count >= opt["count"])
            v_ok = opt.get("min_value_each") is None or (actual_value is not None and actual_value >= opt["min_value_each"])
            evaluated.append((opt, c_ok and v_ok))
        any_pass = any(ok for _, ok in evaluated)
        if actual_count is None and actual_value is None:
            status, note = "INFO", "Provide similar-works data in your profile to get a verdict"
        elif actual_count is None or actual_value is None:
            status, note = "INFO", "Partial similar-works data — fill both count and value for a verdict"
        else:
            status = "PASS" if any_pass else "FAIL"
            req_parts = [f"{o['count']} works each ≥ {fmt_inr(o['min_value_each'])}" for o in options if o.get("count")]
            req_txt = " OR ".join(req_parts) + win_txt if req_parts else win_txt
            note = "" if any_pass else (
                f"You have {actual_count} works @ avg {fmt_inr(actual_value)}; need any of: " + req_txt +
                " — attach all completion certificates or consider JV")
        req_txt = (" OR ".join(f"{o['count']} works each ≥ {fmt_inr(o['min_value_each'])}"
                               for o in options if o.get("count")) or "similar works") + win_txt
        add("Similar works completed", req_txt,
            f"{actual_count} works @ avg {fmt_inr(actual_value)}", status, note)

    emd = criteria.get("emd_amount")
    if emd:
        budget = profile.get("emd_budget")
        if budget is None:
            add("Earnest Money Deposit (EMD)", fmt_inr(emd), "not provided", "INFO",
                f"Arrange EMD of {fmt_inr(emd)} via Bank Guarantee / FDR before submission")
        else:
            ok = budget >= emd
            add("Earnest Money Deposit (EMD)", fmt_inr(emd), fmt_inr(budget), "PASS" if ok else "FAIL",
                "" if ok else f"EMD shortfall of {fmt_inr(emd - budget)}")

    if criteria.get("pan_gst_required"):
        hp = profile.get("has_pan_gst")
        if hp is None:
            add("PAN / GST registration", "Mandatory", "not provided", "INFO", "Confirm PAN/GST registration in the profile")
        elif not hp:
            add("PAN / GST registration", "Mandatory", "Missing", "FAIL",
                "Complete PAN/GST registration before bid submission")

    deadline = criteria.get("submission_deadline")
    days = None
    if deadline:
        d = _parse_deadline(deadline)
        if d:
            days = (d - today).days
            if days >= 0:
                add("Submission deadline", deadline, f"{days} day(s) remaining", "PASS",
                    "" if days > 3 else "Tight timeline — start document prep immediately")
            else:
                add("Submission deadline", deadline, "deadline passed", "FAIL", "Do not bid on this tender")

    scored = [c for c in checks if c["status"] in ("PASS", "FAIL")]
    score = round(100 * sum(1 for c in scored if c["status"] == "PASS") / len(scored)) if scored else 0
    fails = [c for c in checks if c["status"] == "FAIL"]
    infos = [c for c in checks if c["status"] == "INFO"]
    if not checks:
        verdict = "INSUFFICIENT DATA"
    elif fails:
        verdict = "CONDITIONAL — 1 GAP" if len(fails) == 1 else f"NOT READY — {len(fails)} GAPS"
    elif infos:
        verdict = "NEEDS PROFILE DATA"
    else:
        verdict = "READY TO BID"

    return {
        "checks": checks,
        "score": score,
        "verdict": verdict,
        "fail_count": len(fails),
        "days_to_deadline": days,
    }
