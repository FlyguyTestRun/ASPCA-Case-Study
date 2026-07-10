"""Compute ask amounts, confidence scores, and review levels for validated donors.

Usage:
    python calculate_ask.py --config <campaign.json> [--workdir work]

Reads work/validated.csv (produced by validate_input.py) and writes
work/computed.csv with the ask amount, a step-by-step calculation trace,
a confidence score, and the review level for every donor.

All arithmetic happens here, deterministically. A language model never
calculates an ask amount.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import donor_rules as rules


def run(config_path: Path, workdir: Path) -> list[dict]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    as_of_year = date.fromisoformat(config["as_of_date"]).year
    campaign_type = config["campaign_type"]

    validated_path = workdir / "validated.csv"
    if not validated_path.exists():
        print("ERROR: work/validated.csv not found; run validate_input.py first", file=sys.stderr)
        raise SystemExit(2)

    with validated_path.open(newline="", encoding="utf-8") as handle:
        donors = list(csv.DictReader(handle))

    computed: list[dict] = []
    for donor in donors:
        ask = rules.compute_ask(
            tier=donor["tier"],
            lapsed=donor["status"] == "lapsed",
            largest_gift=float(donor["largest_gift"]),
            last_gift_year=int(donor["last_gift_year"]),
            volunteer=donor["volunteer"] == "Yes",
            campaign_type=campaign_type,
            as_of_year=as_of_year,
        )

        validation_warnings = [w for w in donor["warnings"].split(" | ") if w]
        all_warnings = validation_warnings + ask.warnings
        confidence = rules.confidence_score(len(all_warnings))
        level = rules.review_level(donor["tier"], confidence, ask.review_reasons)

        record = dict(donor)
        record.update({
            "ask_amount": "" if ask.amount is None else str(ask.amount),
            "ask_trace": " -> ".join(ask.trace),
            "warnings": " | ".join(all_warnings),
            "review_reasons": " | ".join(ask.review_reasons),
            "confidence": f"{confidence:.2f}",
            "review_level": level,
            "streak": str(rules.giving_streak(donor["gift_years"].split("|"), as_of_year)),
        })
        computed.append(record)

    out_path = workdir / "computed.csv"
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(computed[0].keys()) if computed else [])
        writer.writeheader()
        writer.writerows(computed)

    mandatory = sum(1 for r in computed if r["review_level"] == "mandatory")
    recommended = sum(1 for r in computed if r["review_level"] == "recommended")
    no_letter = sum(1 for r in computed if not r["ask_amount"])
    print(f"asks computed:      {len(computed)}")
    print(f"review mandatory:   {mandatory}")
    print(f"review recommended: {recommended}")
    print(f"routed to personal outreach (no letter): {no_letter}")
    return computed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--workdir", default=Path("work"), type=Path)
    args = parser.parse_args()
    run(args.config, args.workdir)


if __name__ == "__main__":
    main()
