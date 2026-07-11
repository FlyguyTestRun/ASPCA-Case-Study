"""The fixture must match the original skill's embedded table, verbatim.

Data provenance for this exercise: the zip from the case study contained
exactly two files, SKILL.md and a macOS .DS_Store artifact (Finder folder
metadata, no data). The 50-donor table inside SKILL.md is therefore the only
data source that exists, and assets/sample_donors.csv claims to be a verbatim
transcription of it, planted errors included.

These tests prove that claim field by field, donor by donor, so transcription
fidelity is a CI-enforced invariant instead of a promise. If anyone ever
"fixes" the fixture's planted errors, or a row drifts during an edit, the
build fails.
"""

import csv
import re

from conftest import REPO_ROOT, SKILL_DIR

import donor_rules as rules

ORIGINAL = REPO_ROOT / "original" / "charity-donor-outreach" / "SKILL.md"
FIXTURE = SKILL_DIR / "assets" / "sample_donors.csv"

GIFT_ENTRY = re.compile(r"(\d{4}):\s*\$([\d,]+)")


def money(text: str) -> float:
    return float(text.replace("$", "").replace(",", "").strip())


def parse_original_table() -> dict[str, dict]:
    """Parse the markdown donor table out of the original SKILL.md."""
    donors: dict[str, dict] = {}
    for line in ORIGINAL.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 8:
            continue
        if cells[0] == "Donor Name" or set(cells[0]) <= {"-", " "}:
            continue
        gifts = [(int(year), float(amount.replace(",", "")))
                 for year, amount in GIFT_ENTRY.findall(cells[3])]
        donors[cells[0]] = {
            "tier": cells[1],
            "region": cells[2],
            "gifts": sorted(gifts),
            "largest_gift": money(cells[4]),
            "lifetime_total": money(cells[5]),
            "last_gift_year": int(cells[6]),
            "volunteer": cells[7],
        }
    return donors


def parse_fixture() -> dict[str, dict]:
    with FIXTURE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {
        row["donor_name"]: {
            "tier": row["tier"],
            "region": row["region"],
            "gifts": sorted(rules.parse_gifts(row["gifts"])),
            "largest_gift": float(row["largest_gift"]),
            "lifetime_total": float(row["lifetime_total"]),
            "last_gift_year": int(row["last_gift_year"]),
            "volunteer": row["volunteer"],
        }
        for row in rows
    }


def test_original_table_parses_to_exactly_50_donors():
    assert len(parse_original_table()) == 50


def test_fixture_contains_exactly_the_original_donors():
    original = parse_original_table()
    fixture = parse_fixture()
    assert set(fixture) == set(original)


def test_every_field_of_every_donor_matches_the_original():
    original = parse_original_table()
    fixture = parse_fixture()
    mismatches = []
    for name, source_row in original.items():
        for field, source_value in source_row.items():
            fixture_value = fixture[name][field]
            if fixture_value != source_value:
                mismatches.append(
                    f"{name}.{field}: original {source_value!r}, "
                    f"fixture {fixture_value!r}"
                )
    assert mismatches == []


def test_planted_errors_are_preserved_not_sanitized():
    """The fixture must keep the original's defects: they are the test data."""
    fixture = parse_fixture()
    # The four mislabeled tiers, exactly as the consultant filed them.
    assert fixture["Ruth Andersen"]["tier"] == "Silver"          # 25,000 lifetime
    assert fixture["Ada Yamamoto-Pierce"]["tier"] == "Silver"    # 17,000 lifetime
    assert fixture["Shirley Magnusdottir"]["tier"] == "Silver"   # 22,000 lifetime
    assert fixture["Arthur Mwangi"]["tier"] == "Bronze"          # 2,600 lifetime
    # The reference-date trap: Susan's 2024 gift stays.
    assert (2024, 1500.0) in fixture["Susan Nakamura"]["gifts"]
    # The lapsed-by-date Platinums keep their stated active tiers.
    assert fixture["Robert Svensson"]["last_gift_year"] == 2020
    assert fixture["Walter Adeyemi"]["last_gift_year"] == 2020


def test_original_totals_actually_tie_out_except_where_planted():
    """Independent audit of the source data itself: every stated largest gift,
    lifetime total, and last gift year in the original table is consistent
    with its own gift list. The consultant's planted defects are the tier
    labels and the date handling, not the arithmetic columns."""
    original = parse_original_table()
    for name, row in original.items():
        amounts = [amount for _, amount in row["gifts"]]
        years = [year for year, _ in row["gifts"]]
        assert max(amounts) == row["largest_gift"], name
        assert sum(amounts) == row["lifetime_total"], name
        assert max(years) == row["last_gift_year"], name
