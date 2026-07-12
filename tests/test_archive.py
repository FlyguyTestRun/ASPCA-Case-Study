"""Tests for the on-demand run archive feature (ADR 0027).

generate_letters.py clears output/letters/ at the start of every run so the
manifest and the folder can never disagree (ADR 0022). archive_run is the
lightweight, on-demand way to keep a labeled snapshot of a run before the
next one overwrites it, without the full run-versioning system ADR 0022
deferred.
"""

import json
import subprocess
import sys

import pytest

import donor_rules as rules
from conftest import SKILL_DIR

FIXTURE = SKILL_DIR / "assets" / "sample_donors.csv"
CONFIG = SKILL_DIR / "assets" / "campaign_config.example.json"
SCRIPTS = SKILL_DIR / "scripts"


def run_pipeline(tmp_path, workdir_name="work", outdir_name="output"):
    workdir = tmp_path / workdir_name
    outdir = tmp_path / outdir_name
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
    return outdir


def test_archive_run_copies_manifest_and_letters(tmp_path):
    outdir = run_pipeline(tmp_path)
    archive_root = tmp_path / "archive"

    archived = rules.archive_run(outdir, archive_root, label="Pre-launch snapshot")

    assert (archived / "manifest.csv").exists()
    assert (archived / "letters").is_dir()
    original_letters = sorted((outdir / "letters").glob("*.html"))
    archived_letters = sorted((archived / "letters").glob("*.html"))
    assert len(archived_letters) == len(original_letters) == 44


def test_archive_run_writes_metadata(tmp_path):
    outdir = run_pipeline(tmp_path)
    archived = rules.archive_run(outdir, tmp_path / "archive", "Test run", "a note")

    info = json.loads((archived / "archive_info.json").read_text(encoding="utf-8"))
    assert info["label"] == "Test run"
    assert info["note"] == "a note"
    assert info["rules_version"] == rules.RULES_VERSION
    assert info["letter_count"] == 44
    assert info["donor_count"] == 46


def test_archive_survives_the_next_run_clearing_output(tmp_path):
    outdir = run_pipeline(tmp_path)
    archived = rules.archive_run(outdir, tmp_path / "archive", "Before rerun")

    # Simulate a later run that excludes a donor previously included: the
    # live output changes, the archive must not.
    run_pipeline(tmp_path)  # generate_letters.py clears and rewrites outdir/letters

    assert len(list((archived / "letters").glob("*.html"))) == 44


def test_list_archived_runs_returns_newest_first(tmp_path):
    outdir = run_pipeline(tmp_path)
    archive_root = tmp_path / "archive"
    rules.archive_run(outdir, archive_root, "First")
    rules.archive_run(outdir, archive_root, "Second")

    runs = rules.list_archived_runs(archive_root)
    assert len(runs) == 2
    assert {run["label"] for run in runs} == {"First", "Second"}


def test_list_archived_runs_empty_when_no_archive_yet(tmp_path):
    assert rules.list_archived_runs(tmp_path / "does_not_exist") == []


def test_archive_run_requires_a_completed_run(tmp_path):
    with pytest.raises(FileNotFoundError):
        rules.archive_run(tmp_path / "no_output_here", tmp_path / "archive", "Nothing")
