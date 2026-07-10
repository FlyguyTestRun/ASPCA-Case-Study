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


def load_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = [(f or "").strip().lower() for f in (reader.fieldnames or [])]
        reader.fieldnames = fieldnames
        return fieldnames, list(reader)


def run(input_path: Path, corrections_path: Path, output_path: Path,
        approved_rows: set[int] | None) -> int:
    fieldnames, rows = load_csv(input_path)
    _, corrections = load_csv(corrections_path)

    applied = 0
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
        print(
            f"APPLIED row {row_number} ({fix['donor_name']}): "
            f"{field} {before!r} -> {fix['suggested_value']!r} ({fix['reason']})"
        )

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

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
    args = parser.parse_args()
    approved = None
    if args.rows.strip():
        approved = {int(part) for part in args.rows.split(",") if part.strip()}
    run(args.input, args.corrections, args.output, approved)


if __name__ == "__main__":
    main()
