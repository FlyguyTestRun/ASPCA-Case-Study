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
    letters_outdir = WORKDIR / "out"
    run("validate_input.py", "--input", str(FIXTURE))
    run("calculate_ask.py")
    # letter_date defaults to the day the script runs (ADR 0031), correct
    # for a real campaign but wrong for this fixed demo: every rebuild would
    # otherwise print a later real-world date next to giving data and an
    # "emergency appeal" frozen at as_of_date, and that gap only grows with
    # time. Pinning --letter-date to the same as_of_date makes this batch
    # read as what it actually is: one internally consistent snapshot, not
    # a moving generation date layered on frozen data. See ADR 0031.
    as_of_date = json.loads(CONFIG.read_text(encoding="utf-8"))["as_of_date"]
    # Regenerated fresh from this same run, into a scratch outdir, never the
    # committed output/: the embedded letters must always match exactly what
    # this script just computed, not a possibly older separate evidence run.
    run("generate_letters.py", "--outdir", str(letters_outdir), "--letter-date", as_of_date)

    computed = {row["donor_name"]: row for row in read_csv(WORKDIR / "computed.csv")}
    exceptions = {row["donor_name"]: row for row in read_csv(WORKDIR / "exceptions.csv")}
    manifest = {row["donor_name"]: row for row in read_csv(letters_outdir / "manifest.csv")}
    raw_rows = read_csv(FIXTURE)

    def read_letter(letter_file):
        if not letter_file:
            return ""
        path = letters_outdir / letter_file
        return path.read_text(encoding="utf-8") if path.exists() else ""

    donors = []
    for raw in raw_rows:
        name = raw["donor_name"]
        entry = {"donor_name": name, "region": raw["region"],
                 "volunteer": raw["volunteer"], "gifts": raw["gifts"],
                 "letter_html": "", "no_letter_reason": ""}
        if name in computed:
            record = computed[name]
            manifest_row = manifest.get(name, {})
            entry.update({
                "status": "validated",
                "donor_id": record["donor_id"],
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
            entry["letter_html"] = read_letter(manifest_row.get("letter_file"))
            if not entry["letter_html"]:
                entry["no_letter_reason"] = (
                    record["review_reasons"] or "held for review before a letter is generated"
                )
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
            entry["no_letter_reason"] = "excluded from letter generation until a person approves a fix"
        donors.append(entry)

    letters_written = sum(1 for d in donors if d["letter_html"])
    out_path = ROOT / "deliverable" / "dataset.json"
    out_path.write_text(json.dumps(donors, indent=2), encoding="utf-8")
    print(f"wrote {len(donors)} donor records ({letters_written} with a generated letter) to {out_path}")

    # The actual config that produced every number on the page, embedded
    # read-only: the browser never recomputes an ask, so showing this
    # config editable would imply a recalculation that does not happen.
    config_path = ROOT / "deliverable" / "campaign_config_embed.json"
    config_path.write_text(CONFIG.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"wrote the campaign config used for this run to {config_path}")


if __name__ == "__main__":
    main()
