"""Build the combined donor dataset JSON embedded in the standalone HTML review page.

Run from the ASPCA-Case-Study repository root:
    python deliverable/build_dataset.py

Reads the fixture through the real pipeline (validate, calculate) so the
embedded dataset is never hand-maintained; it is always what the Python
system actually computed. Writes deliverable/dataset.json.
"""

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skill" / "charity-donor-outreach"
SCRIPTS = SKILL_DIR / "scripts"
FIXTURE = SKILL_DIR / "assets" / "sample_donors.csv"
CONFIG = SKILL_DIR / "assets" / "campaign_config.example.json"
WORKDIR = ROOT / "deliverable" / "_work"


def run(script, *args):
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script), "--config", str(CONFIG),
         "--workdir", str(WORKDIR), *args],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main():
    run("validate_input.py", "--input", str(FIXTURE))
    run("calculate_ask.py")

    computed = {row["donor_name"]: row for row in read_csv(WORKDIR / "computed.csv")}
    exceptions = {row["donor_name"]: row for row in read_csv(WORKDIR / "exceptions.csv")}
    raw_rows = read_csv(FIXTURE)

    donors = []
    for raw in raw_rows:
        name = raw["donor_name"]
        entry = {"donor_name": name, "region": raw["region"],
                 "volunteer": raw["volunteer"], "gifts": raw["gifts"]}
        if name in computed:
            record = computed[name]
            entry.update({
                "status": "validated",
                "stated_tier": record["stated_tier"],
                "computed_tier": record["tier"],
                "tier_mismatch": record["stated_tier"] != record["tier"],
                "donor_status": record["status"],
                "largest_gift": record["largest_gift"],
                "lifetime_total": record["lifetime_total"],
                "last_gift_year": record["last_gift_year"],
                "ask_amount": record["ask_amount"],
                "ask_trace": record["ask_trace"],
                "confidence": record["confidence"],
                "confidence_band": record["confidence_band"],
                "review_level": record["review_level"],
                "warnings": record["warnings"],
                "review_reasons": record["review_reasons"],
            })
        else:
            record = exceptions[name]
            entry.update({
                "status": "exception",
                "stated_tier": raw["tier"],
                "computed_tier": None,
                "tier_mismatch": True,
                "errors": record["errors"],
                "suggested_correction": record["suggested_correction"],
            })
        donors.append(entry)

    out_path = ROOT / "deliverable" / "dataset.json"
    out_path.write_text(json.dumps(donors, indent=2), encoding="utf-8")
    print(f"wrote {len(donors)} donor records to {out_path}")


if __name__ == "__main__":
    main()
