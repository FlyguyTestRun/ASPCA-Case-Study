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
import os
import sys
import time
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import donor_rules as rules


def emit_escalations(computed: list[dict], workdir: Path) -> int:
    """Write escalation events for every record needing human attention.

    Events always land in work/escalations.jsonl. If ESCALATION_WEBHOOK_URL
    is set they are also posted there so admins are notified in real time;
    by default no network call is made.
    """
    events = []
    for record in computed:
        if record["review_level"] == "none":
            continue
        events.append({
            "donor_id": record["donor_id"],
            "donor_name": record["donor_name"],
            "tier": record["tier"],
            "confidence": float(record["confidence"]),
            "confidence_band": record["confidence_band"],
            "review_level": record["review_level"],
            "warnings": record["warnings"],
            "review_reasons": record["review_reasons"],
            "emitted_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
    path = workdir / "escalations.jsonl"
    path.write_text(
        "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
    )

    webhook = os.environ.get("ESCALATION_WEBHOOK_URL", "").strip()
    if webhook:
        for event in events:
            try:
                request = urllib.request.Request(
                    webhook, data=json.dumps(event).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                urllib.request.urlopen(request, timeout=3)
            except OSError as exc:
                print(f"WEBHOOK WARNING: {exc} (event kept in {path})", file=sys.stderr)
    return len(events)


def run(config_path: Path, workdir: Path) -> list[dict]:
    started = time.perf_counter()
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
        band = rules.confidence_band(confidence)
        if band == "fail" and ask.amount is not None:
            ask.amount = None
            ask.review_reasons.append(
                f"confidence {confidence:.2f} is below the fail threshold "
                f"{rules.CONFIDENCE_FAIL_BELOW:.2f}: blocked pending data fixes"
            )
        level = rules.review_level(donor["tier"], confidence, ask.review_reasons)

        record = dict(donor)
        record.update({
            "ask_amount": "" if ask.amount is None else str(ask.amount),
            "ask_trace": " -> ".join(ask.trace),
            "warnings": " | ".join(all_warnings),
            "review_reasons": " | ".join(ask.review_reasons),
            "confidence": f"{confidence:.2f}",
            "confidence_band": band,
            "review_level": level,
            "streak": str(rules.giving_streak(donor["gift_years"].split("|"), as_of_year)),
        })
        computed.append(record)

    out_path = workdir / "computed.csv"
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(computed[0].keys()) if computed else [])
        writer.writeheader()
        writer.writerows(rules.csv_safe_row(record) for record in computed)
    # Structured JSON alongside the CSV, same records, one donor object per
    # line; see the matching note in validate_input.py.
    (workdir / "computed.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in computed), encoding="utf-8"
    )

    escalated = emit_escalations(computed, workdir)

    mandatory = sum(1 for r in computed if r["review_level"] == "mandatory")
    recommended = sum(1 for r in computed if r["review_level"] == "recommended")
    blocked = sum(1 for r in computed if r["confidence_band"] == "fail")
    no_letter = sum(1 for r in computed if not r["ask_amount"])
    rules.record_stage_metrics(workdir, "calculate", (time.perf_counter() - started) * 1000, {
        "asks_computed": len(computed),
        "review_mandatory": mandatory,
        "review_recommended": recommended,
        "blocked_below_fail_threshold": blocked,
        "escalation_events": escalated,
    })
    print(f"asks computed:      {len(computed)}")
    print(f"review mandatory:   {mandatory}")
    print(f"review recommended: {recommended}")
    print(f"blocked (confidence fail band): {blocked}")
    print(f"escalation events:  {escalated} (work/escalations.jsonl)")
    print(f"no letter (routed to a person): {no_letter}")
    return computed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--workdir", default=Path("work"), type=Path)
    args = parser.parse_args()
    run(args.config, args.workdir)


if __name__ == "__main__":
    main()
