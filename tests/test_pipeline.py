"""End-to-end pipeline tests against the 50-donor fixture.

The fixture is the original skill's embedded donor table, transcribed
verbatim, planted errors included. These tests prove the pipeline catches
every planted trap and that the letters obey the content policy.
"""

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import SKILL_DIR

FIXTURE = SKILL_DIR / "assets" / "sample_donors.csv"
CONFIG = SKILL_DIR / "assets" / "campaign_config.example.json"
SCRIPTS = SKILL_DIR / "scripts"

# The four donors whose stated tier contradicts their own gift history.
PLANTED_TIER_TRAPS = {
    "Ruth Andersen",
    "Ada Yamamoto-Pierce",
    "Shirley Magnusdottir",
    "Arthur Mwangi",
}


@pytest.fixture(scope="module")
def pipeline(tmp_path_factory):
    """Run validate -> calculate -> generate once, in an isolated directory."""
    root = tmp_path_factory.mktemp("pipeline")
    workdir = root / "work"
    outdir = root / "output"
    for script, extra in (
        ("validate_input.py", ["--input", str(FIXTURE)]),
        ("calculate_ask.py", []),
        ("generate_letters.py", ["--outdir", str(outdir)]),
    ):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / script), "--config", str(CONFIG),
             "--workdir", str(workdir), *extra],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"{script} failed:\n{result.stderr}"
    return {"workdir": workdir, "outdir": outdir}


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_every_planted_tier_trap_is_caught(pipeline):
    exceptions = read_csv(pipeline["workdir"] / "exceptions.csv")
    trapped = {row["donor_name"] for row in exceptions}
    assert trapped == PLANTED_TIER_TRAPS
    for row in exceptions:
        assert "tier mismatch" in row["errors"]


def test_validated_plus_exceptions_equals_input(pipeline):
    validated = read_csv(pipeline["workdir"] / "validated.csv")
    exceptions = read_csv(pipeline["workdir"] / "exceptions.csv")
    assert len(validated) + len(exceptions) == 50


def test_reference_date_trap_is_flagged_not_guessed(pipeline):
    validated = read_csv(pipeline["workdir"] / "validated.csv")
    susan = next(row for row in validated if row["donor_name"] == "Susan Nakamura")
    assert "as_of year" in susan["warnings"]


def test_lapsed_status_is_computed_from_dates(pipeline):
    validated = read_csv(pipeline["workdir"] / "validated.csv")
    by_name = {row["donor_name"]: row for row in validated}
    # Filed as Platinum, but last gifts in 2020 make them lapsed at as_of 2024.
    assert by_name["Robert Svensson"]["status"] == "lapsed"
    assert by_name["Walter Adeyemi"]["status"] == "lapsed"
    # Recent giver stays active.
    assert by_name["Brenda Kowalski"]["status"] == "active"


def test_lapsed_major_donors_get_no_letter(pipeline):
    manifest = read_csv(pipeline["outdir"] / "manifest.csv")
    by_name = {row["donor_name"]: row for row in manifest}
    for name in ("Robert Svensson", "Walter Adeyemi"):
        assert by_name[name]["letter_file"] == ""
        assert by_name[name]["review_level"] == "mandatory"


def test_all_platinum_letters_require_mandatory_review(pipeline):
    manifest = read_csv(pipeline["outdir"] / "manifest.csv")
    for row in manifest:
        if row["tier"] == "Platinum":
            assert row["review_level"] == "mandatory"


def test_no_match_language_when_match_not_confirmed(pipeline):
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["match_confirmed"] is False
    for letter in (pipeline["outdir"] / "letters").glob("*.html"):
        text = letter.read_text(encoding="utf-8").lower()
        assert "match" not in text, f"unconfirmed match language in {letter.name}"


def test_no_invented_titles_or_genders(pipeline):
    # The fixture has no titles, so no letter may contain an honorific.
    for letter in (pipeline["outdir"] / "letters").glob("*.html"):
        text = letter.read_text(encoding="utf-8")
        for honorific in ("Mr.", "Ms.", "Mrs.", "Mx."):
            assert honorific not in text, f"invented honorific in {letter.name}"


def test_no_lifetime_flattery_below_threshold(pipeline):
    manifest = read_csv(pipeline["outdir"] / "manifest.csv")
    validated = read_csv(pipeline["workdir"] / "validated.csv")
    lifetimes = {row["donor_id"]: float(row["lifetime_total"]) for row in validated}
    for row in manifest:
        if row["letter_file"] and lifetimes[row["donor_id"]] < 500:
            text = (pipeline["outdir"] / row["letter_file"]).read_text(encoding="utf-8")
            assert "over the years" not in text, (
                f"lifetime flattery for a small donor in {row['letter_file']}"
            )


def test_every_generated_ask_traces_to_policy(pipeline):
    computed = read_csv(pipeline["workdir"] / "computed.csv")
    for row in computed:
        if row["ask_amount"]:
            assert row["ask_trace"], f"no audit trace for {row['donor_name']}"
            assert int(row["ask_amount"]) >= 50
            assert int(row["ask_amount"]) % 50 == 0


def test_future_dated_gift_goes_to_exceptions(tmp_path):
    donors = tmp_path / "donors.csv"
    donors.write_text(
        "donor_name,gifts\nTime Traveler,2019:100|2031:500\n", encoding="utf-8"
    )
    workdir = tmp_path / "work"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "validate_input.py"), "--input", str(donors),
         "--config", str(CONFIG), "--workdir", str(workdir)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    exceptions = read_csv(workdir / "exceptions.csv")
    assert len(exceptions) == 1
    assert "after as_of year" in exceptions[0]["errors"]


def test_missing_required_fields_fail_loudly(tmp_path):
    donors = tmp_path / "donors.csv"
    donors.write_text(
        "donor_name,gifts\n,2020:100\nNo Gifts Given,\n", encoding="utf-8"
    )
    workdir = tmp_path / "work"
    subprocess.run(
        [sys.executable, str(SCRIPTS / "validate_input.py"), "--input", str(donors),
         "--config", str(CONFIG), "--workdir", str(workdir)],
        capture_output=True, text=True, check=True,
    )
    exceptions = read_csv(workdir / "exceptions.csv")
    assert len(exceptions) == 2
    validated = read_csv(workdir / "validated.csv")
    assert validated == []


def test_unknown_campaign_type_stops_the_run(tmp_path):
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    config["campaign_type"] = "bake_sale"
    bad_config = tmp_path / "config.json"
    bad_config.write_text(json.dumps(config), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "validate_input.py"), "--input", str(FIXTURE),
         "--config", str(bad_config), "--workdir", str(tmp_path / "work")],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "unknown campaign_type" in result.stderr


def test_match_confirmed_requires_sponsor_and_terms(tmp_path):
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    config["match_confirmed"] = True
    bad_config = tmp_path / "config.json"
    bad_config.write_text(json.dumps(config), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "validate_input.py"), "--input", str(FIXTURE),
         "--config", str(bad_config), "--workdir", str(tmp_path / "work")],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "match_sponsor" in result.stderr
