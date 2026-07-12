"""Apply human-approved corrections to a donor CSV and write a corrected copy.

Usage:
    python apply_corrections.py --input donors.csv --corrections work/corrections.csv \
        --output corrected_donors.csv [--rows 5,12,31]

The corrections file is produced by validate_input.py. Nothing is applied
silently: by default every suggested correction is listed and applied only
because a person ran this command; --rows restricts application to specific
row numbers. The corrected file is written alongside a printed change log so
the same fix can be made in the source system.

The intended loop: validate, review corrections, apply what you approve,
resubmit the corrected file to validate again.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import donor_rules as rules


def load_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = [(f or "").strip().lower() for f in (reader.fieldnames or [])]
        reader.fieldnames = fieldnames
        return fieldnames, list(reader)


def run(input_path: Path, corrections_path: Path, output_path: Path,
        approved_rows: set[int] | None, approved_by: str = "",
        decision_log: Path | None = None) -> int:
    fieldnames, rows = load_csv(input_path)
    _, corrections = load_csv(corrections_path)

    applied = 0
    change_lines: list[str] = []
    for fix in corrections:
        row_number = int(fix["row_number"])
        if approved_rows is not None and row_number not in approved_rows:
            continue
        row_index = row_number - 2  # data rows start at file row 2
        if not (0 <= row_index < len(rows)):
            print(f"SKIP row {row_number}: not present in the input file", file=sys.stderr)
            continue
        field = fix["field"]
        if field not in fieldnames:
            print(f"SKIP row {row_number}: no column named {field!r}", file=sys.stderr)
            continue
        before = rows[row_index].get(field, "")
        rows[row_index][field] = fix["suggested_value"]
        applied += 1
        change = (
            f"row {row_number} ({fix['donor_name']}): {field} "
            f"{before!r} -> {fix['suggested_value']!r} ({fix['reason']})"
        )
        change_lines.append(change)
        print(f"APPLIED {change}")

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    if applied and decision_log is not None:
        entry = rules.record_decision(
            decision_log,
            title=f"Applied {applied} data correction(s) to {input_path.name}",
            problem=("Validation held these records because stated values "
                     "contradicted the gift history, which is the source of truth."),
            decision="Corrections approved and applied:\n\n"
                     + "\n".join(f"- {line}" for line in change_lines),
            effect=("The corrected file supersedes the original for this run. "
                    "The same corrections must be made in the source system "
                    "so the discrepancy does not recur."),
            approved_by=approved_by or "(not recorded)",
            source="apply_corrections.py",
        )
        print(f"decision recorded:   {entry}")
    elif applied:
        print("note: no decision entry recorded; pass --decision-log (and")
        print("--approved-by) to add this change to the decision history.")

    print(f"corrections applied: {applied}")
    print(f"corrected file:      {output_path}")
    print("Reminder: make the same corrections in the source system, then")
    print("resubmit the corrected file through validate_input.py.")
    return applied


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--corrections", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--rows", default="",
                        help="comma-separated row numbers to apply; default is all")
    parser.add_argument("--approved-by", default="",
                        help="name recorded in the decision history entry")
    parser.add_argument("--decision-log", type=Path, default=None,
                        help="directory for the decision history entry, "
                             "for example docs/decision-log")
    args = parser.parse_args()
    approved = None
    if args.rows.strip():
        approved = {int(part) for part in args.rows.split(",") if part.strip()}
    run(args.input, args.corrections, args.output, approved,
        approved_by=args.approved_by, decision_log=args.decision_log)


if __name__ == "__main__":
    main()
