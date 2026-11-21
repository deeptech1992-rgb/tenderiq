import argparse
import json
from pathlib import Path

from .pipeline import analyze_file, load_profile


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="tenderiq",
        description="Analyze an Indian government tender document and score your bid readiness.")
    ap.add_argument("tender", help="Path to tender PDF/TXT file")
    ap.add_argument("--profile", required=True, help="Path to bidder profile JSON")
    ap.add_argument("--out", default="report.html", help="Output HTML report path")
    ap.add_argument("--json", action="store_true", help="Also print JSON result to stdout")
    args = ap.parse_args(argv)

    profile = load_profile(args.profile)
    result = analyze_file(args.tender, profile)

    out = Path(args.out)
    out.write_text(result["report_html"], encoding="utf-8")

    summary = {
        "verdict": result["verdict"],
        "score": result["score"],
        "criteria": result["criteria"],
        "checks": result["checks"],
    }
    if args.json:
        print(json.dumps(summary, indent=2, default=str))
    else:
        print(f"Verdict: {result['verdict']}  (score {result['score']}/100)")
        for c in result["checks"]:
            print(f"  [{c['status']:4}] {c['criterion']}: required={c['requirement']} actual={c['actual']}")
    print(f"Report written to {out.resolve()}")


if __name__ == "__main__":
    main()
