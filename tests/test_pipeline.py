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

import donor_rules as rules
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


def test_lapsed_letters_never_claim_current_giving(tmp_path):
    # A lapsed donor's letter must never describe their support as ongoing
    # or steady (the annual fund paragraph's default claim), and must not
    # name the specific last-gift year in the same breath as thanking them
    # for present-tense generosity.
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    config["campaign_type"] = "annual_fund"
    annual_config = tmp_path / "config.json"
    annual_config.write_text(json.dumps(config), encoding="utf-8")

    workdir = tmp_path / "work"
    outdir = tmp_path / "output"
    for script, extra in (
        ("validate_input.py", ["--input", str(FIXTURE)]),
        ("calculate_ask.py", []),
        ("generate_letters.py", ["--outdir", str(outdir)]),
    ):
        subprocess.run(
            [sys.executable, str(SCRIPTS / script), "--config", str(annual_config),
             "--workdir", str(workdir), *extra],
            capture_output=True, text=True, check=True,
        )

    manifest = read_csv(outdir / "manifest.csv")
    validated = read_csv(workdir / "validated.csv")
    status_by_id = {row["donor_id"]: row["status"] for row in validated}
    last_gift_year_by_id = {row["donor_id"]: row["last_gift_year"] for row in validated}
    lapsed_letters = [
        row for row in manifest
        if row["letter_file"] and status_by_id.get(row["donor_id"]) == "lapsed"
    ]
    assert lapsed_letters, "fixture should contain at least one lapsed donor with a letter"
    for row in lapsed_letters:
        text = (outdir / row["letter_file"]).read_text(encoding="utf-8")
        assert "steady support" not in text
        year = last_gift_year_by_id[row["donor_id"]]
        assert f"most recent gift in {year}" not in text


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


def test_escalation_events_cover_every_held_record(pipeline):
    lines = (pipeline["workdir"] / "escalations.jsonl").read_text(encoding="utf-8")
    events = [json.loads(line) for line in lines.splitlines() if line]
    manifest = read_csv(pipeline["outdir"] / "manifest.csv")
    held = [row for row in manifest if row["review_level"] != "none"]
    assert len(events) == len(held)
    by_id = {event["donor_id"]: event for event in events}
    # Susan carries the reference-date warning and must be escalated.
    assert by_id["susan-nakamura"]["review_level"] == "recommended"
    # Every Platinum letter escalates as mandatory.
    for event in events:
        if event["tier"] == "Platinum":
            assert event["review_level"] == "mandatory"


def test_run_metrics_record_all_three_stages(pipeline):
    metrics = json.loads(
        (pipeline["workdir"] / "run_metrics.json").read_text(encoding="utf-8")
    )
    for stage in ("validate", "calculate", "generate"):
        assert stage in metrics
        assert metrics[stage]["duration_ms"] >= 0
        assert metrics[stage]["rules_version"] == rules.RULES_VERSION
    assert metrics["validate"]["rows_in"] == 50
    assert metrics["generate"]["letters_written"] == 44
    assert metrics["generate"]["schema_rejections"] == 0
    assert "zero" in metrics["token_cost"]


def test_every_letter_has_a_schema_valid_model(pipeline):
    lines = (pipeline["workdir"] / "letter_models.jsonl").read_text(encoding="utf-8")
    models = [json.loads(line) for line in lines.splitlines() if line]
    letters = list((pipeline["outdir"] / "letters").glob("*.html"))
    assert len(models) == len(letters) == 44


def test_formula_injection_arrives_inert(tmp_path):
    donors = tmp_path / "donors.csv"
    donors.write_text(
        'donor_name,gifts\n"=HYPERLINK(""http://evil.example"",""x"")",2023:100\n',
        encoding="utf-8",
    )
    workdir = tmp_path / "work"
    subprocess.run(
        [sys.executable, str(SCRIPTS / "validate_input.py"), "--input", str(donors),
         "--config", str(CONFIG), "--workdir", str(workdir)],
        capture_output=True, text=True, check=True,
    )
    validated_raw = (workdir / "validated.csv").read_text(encoding="utf-8")
    assert "'=HYPERLINK" in validated_raw  # neutralized with a leading apostrophe
    rows = read_csv(workdir / "validated.csv")
    assert len(rows) == 1  # still processed, just made inert for spreadsheets


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


@pytest.mark.parametrize(
    "missing_key",
    ["signer_name", "signer_title", "charity_name", "donation_url", "as_of_date"],
)
def test_missing_config_field_stops_the_run(tmp_path, missing_key):
    # The original skill shipped placeholders (relationship manager, charity
    # name, donation URL) with no defined source. A required field being
    # absent must stop the run with a named error, never fall back to an
    # invented or blank value.
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    del config[missing_key]
    bad_config = tmp_path / "config.json"
    bad_config.write_text(json.dumps(config), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "validate_input.py"), "--input", str(FIXTURE),
         "--config", str(bad_config), "--workdir", str(tmp_path / "work")],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert f"config missing required key: {missing_key}" in result.stderr


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


def test_malformed_tier_label_caught_by_schema_before_business_rules(tmp_path):
    # "Platnium" is not a valid tier label at all (a typo, not a mismatch);
    # the structural schema layer catches this before tier-mismatch business
    # logic ever runs, with a "schema:" prefixed reason.
    donors = tmp_path / "donors.csv"
    donors.write_text(
        "donor_name,tier,gifts\nTest Donor,Platnium,2023:100\n", encoding="utf-8",
    )
    workdir = tmp_path / "work"
    subprocess.run(
        [sys.executable, str(SCRIPTS / "validate_input.py"), "--input", str(donors),
         "--config", str(CONFIG), "--workdir", str(workdir)],
        capture_output=True, text=True, check=True,
    )
    exceptions = read_csv(workdir / "exceptions.csv")
    assert len(exceptions) == 1
    assert "schema:" in exceptions[0]["errors"]
    assert "tier" in exceptions[0]["errors"]


def test_gifts_field_not_matching_expected_shape_caught_by_schema(tmp_path):
    donors = tmp_path / "donors.csv"
    donors.write_text(
        "donor_name,gifts\nTest Donor,not even close to year:amount\n",
        encoding="utf-8",
    )
    workdir = tmp_path / "work"
    subprocess.run(
        [sys.executable, str(SCRIPTS / "validate_input.py"), "--input", str(donors),
         "--config", str(CONFIG), "--workdir", str(workdir)],
        capture_output=True, text=True, check=True,
    )
    exceptions = read_csv(workdir / "exceptions.csv")
    assert len(exceptions) == 1
    assert "schema:" in exceptions[0]["errors"]
    assert "gifts" in exceptions[0]["errors"]


def test_structured_json_mirrors_the_csv_at_every_stage(pipeline):
    # A donor object exists as JSON, not just a CSV row, at every stage
    # boundary: validated.jsonl after validation, computed.jsonl after ask
    # calculation, letter_models.jsonl after letter assembly.
    workdir = pipeline["workdir"]
    validated_csv = read_csv(workdir / "validated.csv")
    with open(workdir / "validated.jsonl", encoding="utf-8") as handle:
        validated_json = [json.loads(line) for line in handle if line.strip()]
    assert len(validated_json) == len(validated_csv)
    assert validated_json[0]["donor_id"] == validated_csv[0]["donor_id"]

    computed_csv = read_csv(workdir / "computed.csv")
    with open(workdir / "computed.jsonl", encoding="utf-8") as handle:
        computed_json = [json.loads(line) for line in handle if line.strip()]
    assert len(computed_json) == len(computed_csv)
    assert computed_json[0]["ask_amount"] == computed_csv[0]["ask_amount"]


def test_rules_version_stamped_into_the_validation_report(pipeline):
    report = json.loads(
        (pipeline["workdir"] / "validation_report.json").read_text(encoding="utf-8")
    )
    assert report["rules_version"] == rules.RULES_VERSION


def test_donor_id_collision_is_caught_not_overwritten(tmp_path):
    # Different names, same slug: both must be held, neither may silently
    # overwrite the other's letter file downstream.
    donors = tmp_path / "donors.csv"
    donors.write_text(
        "donor_name,gifts\n"
        "Jean-Paul Ostrowski,2023:100\n"
        "Jean Paul Ostrowski,2023:200\n",
        encoding="utf-8",
    )
    workdir = tmp_path / "work"
    subprocess.run(
        [sys.executable, str(SCRIPTS / "validate_input.py"), "--input", str(donors),
         "--config", str(CONFIG), "--workdir", str(workdir)],
        capture_output=True, text=True, check=True,
    )
    validated = read_csv(workdir / "validated.csv")
    exceptions = read_csv(workdir / "exceptions.csv")
    assert validated == []
    assert len(exceptions) == 2
    for row in exceptions:
        assert "donor_id" in row["errors"]
        assert "also produced by row" in row["errors"]


def test_generate_letters_clears_stale_output(tmp_path):
    # A donor written to output/letters/ in one run must not survive into a
    # later run's output once the manifest no longer lists them.
    workdir = tmp_path / "work"
    outdir = tmp_path / "output"
    for script, extra in (
        ("validate_input.py", ["--input", str(FIXTURE)]),
        ("calculate_ask.py", []),
        ("generate_letters.py", ["--outdir", str(outdir)]),
    ):
        subprocess.run(
            [sys.executable, str(SCRIPTS / script), "--config", str(CONFIG),
             "--workdir", str(workdir), *extra],
            capture_output=True, text=True, check=True,
        )

    stray = outdir / "letters" / "not-a-real-donor-from-a-previous-run.html"
    stray.write_text("<html>stale</html>", encoding="utf-8")
    assert stray.exists()

    subprocess.run(
        [sys.executable, str(SCRIPTS / "generate_letters.py"), "--config", str(CONFIG),
         "--workdir", str(workdir), "--outdir", str(outdir)],
        capture_output=True, text=True, check=True,
    )
    assert not stray.exists()
    # The real run's letters are still there; this isn't just an empty wipe.
    assert len(list((outdir / "letters").glob("*.html"))) == 44


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
