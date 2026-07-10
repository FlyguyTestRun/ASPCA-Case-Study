"""Tests for the fix-and-resubmit loop and the guarded style learner."""

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


def run_script(script: str, *args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True, text=True,
    )


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class TestCorrectionsLoop:
    def test_validator_suggests_a_fix_for_every_tier_trap(self, tmp_path):
        workdir = tmp_path / "work"
        result = run_script("validate_input.py", "--input", str(FIXTURE),
                            "--config", str(CONFIG), "--workdir", str(workdir))
        assert result.returncode == 0
        corrections = read_csv(workdir / "corrections.csv")
        by_name = {row["donor_name"]: row for row in corrections}
        assert by_name["Ruth Andersen"]["suggested_value"] == "Gold"
        assert by_name["Ada Yamamoto-Pierce"]["suggested_value"] == "Gold"
        assert by_name["Shirley Magnusdottir"]["suggested_value"] == "Gold"
        assert by_name["Arthur Mwangi"]["suggested_value"] == "Silver"
        for row in corrections:
            assert row["field"] == "tier"
            assert row["reason"]

    def test_exceptions_carry_the_suggestion_in_plain_language(self, tmp_path):
        workdir = tmp_path / "work"
        run_script("validate_input.py", "--input", str(FIXTURE),
                   "--config", str(CONFIG), "--workdir", str(workdir))
        exceptions = read_csv(workdir / "exceptions.csv")
        ruth = next(e for e in exceptions if e["donor_name"] == "Ruth Andersen")
        assert "set tier to Gold" in ruth["suggested_correction"]

    def test_apply_and_resubmit_clears_the_exceptions(self, tmp_path):
        workdir = tmp_path / "work"
        run_script("validate_input.py", "--input", str(FIXTURE),
                   "--config", str(CONFIG), "--workdir", str(workdir))

        corrected = tmp_path / "corrected.csv"
        result = run_script("apply_corrections.py", "--input", str(FIXTURE),
                            "--corrections", str(workdir / "corrections.csv"),
                            "--output", str(corrected))
        assert result.returncode == 0
        assert "corrections applied: 4" in result.stdout

        workdir2 = tmp_path / "work2"
        result = run_script("validate_input.py", "--input", str(corrected),
                            "--config", str(CONFIG), "--workdir", str(workdir2))
        assert result.returncode == 0
        assert read_csv(workdir2 / "exceptions.csv") == []
        assert len(read_csv(workdir2 / "validated.csv")) == 50

    def test_rows_flag_restricts_what_is_applied(self, tmp_path):
        workdir = tmp_path / "work"
        run_script("validate_input.py", "--input", str(FIXTURE),
                   "--config", str(CONFIG), "--workdir", str(workdir))
        corrections = read_csv(workdir / "corrections.csv")
        one_row = corrections[0]["row_number"]
        corrected = tmp_path / "corrected.csv"
        result = run_script("apply_corrections.py", "--input", str(FIXTURE),
                            "--corrections", str(workdir / "corrections.csv"),
                            "--output", str(corrected), "--rows", one_row)
        assert "corrections applied: 1" in result.stdout


class TestStyleGuardrails:
    def test_clean_values_pass(self):
        clean, ignored = rules.sanitize_style_profile(
            {"closing_phrase": "For the animals", "ps_line": "Thank you for all you do."}
        )
        assert clean == {"closing_phrase": "For the animals",
                         "ps_line": "Thank you for all you do."}

    @pytest.mark.parametrize("bad", [
        "Your gift will be matched",       # banned word
        "Send fifty dollars now $",        # money symbol
        "Act before the deadline",         # urgency device
        "With deep and everlasting gratitude from all of us",  # too long
    ])
    def test_unsafe_closings_are_rejected(self, bad):
        clean, ignored = rules.sanitize_style_profile({"closing_phrase": bad})
        assert "closing_phrase" not in clean
        assert ignored

    def test_unknown_keys_cannot_smuggle_changes(self):
        clean, ignored = rules.sanitize_style_profile(
            {"ask_amount": "999999", "closing_phrase": "Warmly"}
        )
        assert clean == {"closing_phrase": "Warmly"}
        assert any("unknown style key" in reason for reason in ignored)


def make_letter(closing: str, ps: str = "") -> str:
    ps_block = f"<p>P.S. {ps}</p>" if ps else ""
    return (
        "<html><body><p>Dear Test Donor,</p><p>Body text.</p>"
        f"<p>{closing},<br><strong>Jordan Ellis</strong><br>"
        f"Director, ASPCA</p>{ps_block}</body></html>"
    )


class TestStyleLearning:
    def _learn(self, tmp_path, edited_closings):
        originals = tmp_path / "originals"
        edited = tmp_path / "edited"
        workdir = tmp_path / "work"
        originals.mkdir()
        edited.mkdir()
        for i, closing in enumerate(edited_closings):
            name = f"donor-{i}.html"
            (originals / name).write_text(make_letter("With gratitude"), encoding="utf-8")
            (edited / name).write_text(make_letter(closing), encoding="utf-8")
        result = run_script("learn_style.py", "--originals", str(originals),
                            "--edited", str(edited), "--workdir", str(workdir))
        assert result.returncode == 0, result.stderr
        return json.loads((workdir / "style_suggestions.json").read_text(encoding="utf-8")), workdir

    def test_three_identical_edits_become_an_eligible_suggestion(self, tmp_path):
        report, _ = self._learn(tmp_path, ["For the animals"] * 3)
        suggestion = report["suggestions"][0]
        assert suggestion["value"] == "For the animals"
        assert suggestion["evidence_edits"] == 3
        assert suggestion["status"] == "eligible for adoption"

    def test_two_edits_are_not_enough(self, tmp_path):
        report, _ = self._learn(tmp_path, ["For the animals"] * 2)
        assert "insufficient evidence" in report["suggestions"][0]["status"]

    def test_banned_language_is_never_eligible(self, tmp_path):
        report, _ = self._learn(tmp_path, ["Your gift will be matched"] * 5)
        assert report["suggestions"][0]["status"] != "eligible for adoption"

    def test_adoption_requires_a_named_person(self, tmp_path):
        _, workdir = self._learn(tmp_path, ["For the animals"] * 3)
        result = run_script("learn_style.py", "--adopt", "closing_phrase",
                            "--workdir", str(workdir),
                            "--profile", str(tmp_path / "profile.json"))
        assert result.returncode == 2
        assert "approved-by" in result.stderr

    def test_adopted_style_changes_letters_but_not_asks(self, tmp_path):
        _, workdir = self._learn(tmp_path, ["For the animals"] * 3)
        profile_path = tmp_path / "profile.json"
        result = run_script("learn_style.py", "--adopt", "closing_phrase",
                            "--approved-by", "Test Reviewer",
                            "--workdir", str(workdir), "--profile", str(profile_path))
        assert result.returncode == 0

        # Full pipeline with and without the style profile.
        def full_run(style_args):
            wd = tmp_path / f"wd{len(style_args)}"
            od = tmp_path / f"od{len(style_args)}"
            run_script("validate_input.py", "--input", str(FIXTURE),
                       "--config", str(CONFIG), "--workdir", str(wd))
            run_script("calculate_ask.py", "--config", str(CONFIG), "--workdir", str(wd))
            run_script("generate_letters.py", "--config", str(CONFIG),
                       "--workdir", str(wd), "--outdir", str(od), *style_args)
            return od

        styled = full_run(["--style", str(profile_path)])
        plain = full_run([])

        styled_letter = (styled / "letters" / "earl-fontaine.html").read_text(encoding="utf-8")
        plain_letter = (plain / "letters" / "earl-fontaine.html").read_text(encoding="utf-8")
        assert "For the animals," in styled_letter
        assert "With gratitude," in plain_letter
        # The ask is identical: style can change personality, never money.
        assert "$43,300" in styled_letter and "$43,300" in plain_letter
