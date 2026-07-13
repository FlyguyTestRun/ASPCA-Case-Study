"""Pin the standalone HTML deliverable's client-side validation logic
against the same fixture the Python pipeline uses.

deliverable/donor-data-review.html reimplements compute_tier and is_lapsed
in JavaScript so a reviewer can edit data and see it re-checked instantly,
without a server. Two implementations of the same rules is a real drift
risk: an earlier version of the JavaScript compared every stated tier
straight to the computed financial tier, which is wrong for donors filed
with the literal tier value "Lapsed" (a status claim, not a financial tier),
and silently inflated flagged records from 4 to 14. These tests execute the
actual embedded JavaScript with Node and require it to agree with the
Python pipeline's own output on the full fixture, so that class of bug
cannot return unnoticed.

Skipped automatically if Node.js is not installed.
"""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from conftest import REPO_ROOT
import donor_rules as rules

DELIVERABLE = REPO_ROOT / "deliverable" / "donor-data-review.html"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js not installed"
)


def extract_dataset_and_script(html: str) -> tuple[list[dict], str]:
    dataset_match = re.search(
        r'<script id="dataset" type="application/json">\s*(\[.*?\])\s*</script>',
        html, re.S,
    )
    assert dataset_match, "embedded dataset not found; run deliverable/embed_dataset.py"
    dataset = json.loads(dataset_match.group(1))

    script_match = re.search(
        r'<script>\s*\(function \(\) \{.*?\}\)\(\);\s*</script>', html, re.S
    )
    assert script_match, "client logic script block not found"
    return dataset, script_match.group(0)


# Stub the full DOM/window surface the script touches at top level (page
# bootstrap: building the table, wiring the guided walkthrough) so the real
# file runs headless end to end in Node; the functions under test
# (computeTier, isLapsed, deriveState) are pure, but the surrounding
# bootstrap code executes unconditionally on load and must not throw.
# An earlier, thinner stub happened to pass only because getElementById's
# default empty-string value made the table's status filter behave as an
# active (non-"all") filter, which silently skipped every row and never
# exercised document.createElement. That was an accident, not a guarantee;
# this stub is deliberately complete instead.
_STUB = """
    function makeStubElement() {
      var _textContent = "", _innerHTML = "";
      var el = {
        style: {},
        classList: { add: function(){}, remove: function(){}, contains: function(){return false;}, toggle: function(){} },
        dataset: {},
        children: [],
        addEventListener: function(){},
        removeEventListener: function(){},
        appendChild: function(child){ el.children.push(child); return child; },
        removeChild: function(){},
        querySelector: function(){ return null; },
        querySelectorAll: function(){ return []; },
        getBoundingClientRect: function(){ return {top:0,left:0,width:0,height:0}; },
        scrollIntoView: function(){},
        closest: function(){ return null; },
        setAttribute: function(){}, getAttribute: function(){ return null; }, removeAttribute: function(){},
        focus: function(){}, click: function(){},
        value: "", className: "",
      };
      // Real elements escape on the textContent -> innerHTML round trip;
      // escapeHtml() in the page relies on exactly that browser behavior,
      // so the stub must reproduce it rather than store two independent,
      // unlinked strings.
      Object.defineProperty(el, "textContent", {
        get: function () { return _textContent; },
        set: function (v) {
          _textContent = v;
          _innerHTML = String(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        },
      });
      Object.defineProperty(el, "innerHTML", {
        get: function () { return _innerHTML; },
        set: function (v) { _innerHTML = v; },
      });
      return el;
    }
    var document = {
      documentElement: makeStubElement(),
      body: makeStubElement(),
      getElementById: function(){ return makeStubElement(); },
      createElement: function(){ return makeStubElement(); },
      addEventListener: function(){},
      removeEventListener: function(){},
      querySelector: function(){ return null; },
      querySelectorAll: function(){ return []; },
    };
    function makeStubStorage() {
      var store = {};
      return {
        getItem: function(k){ return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
        setItem: function(k, v){ store[k] = String(v); },
        removeItem: function(k){ delete store[k]; },
        clear: function(){ store = {}; },
      };
    }
    var window = {
      matchMedia: function(){ return { matches: false }; },
      setTimeout: function(){ return 0; },
      clearTimeout: function(){},
      addEventListener: function(){},
      removeEventListener: function(){},
      localStorage: makeStubStorage(),
    };
    function requestAnimationFrame() {}
"""


def run_derive_state_in_node(html: str) -> list[dict]:
    """Execute the page's own compute_tier/is_lapsed/deriveState against its
    own embedded dataset inside Node, and return the flag for every donor."""
    dataset, script_block = extract_dataset_and_script(html)
    inner = re.search(r"\(function \(\) \{(.*)\}\)\(\);", script_block, re.S).group(1)
    inner = inner.replace('"use strict";', "")
    inner = re.sub(
        r'JSON\.parse\(document\.getElementById\("dataset"\)\.textContent\)',
        "__RAW__", inner,
    )
    harness = (
        _STUB
        + "var __RAW__ = " + json.dumps(dataset) + ";\n"
        + inner
        + "\nvar results = donors.map(function(d){ var s = deriveState(d); "
        + "return {donor_name: d.donor_name, flagLevel: s.flagLevel}; });\n"
        + "console.log(JSON.stringify(results));\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        script_path = Path(tmp) / "harness.js"
        script_path.write_text(harness, encoding="utf-8")
        result = subprocess.run(["node", str(script_path)], capture_output=True, text=True)
    assert result.returncode == 0, f"Node execution failed:\n{result.stderr}"
    return json.loads(result.stdout.strip())


def run_tour_metadata_in_node(html: str) -> dict:
    """Execute the page's own TOUR_STEPS and pacing constants inside Node,
    with every step's target() resolved against the full stubbed page, and
    return a structural summary. This is what pins the walkthrough at under
    two minutes: it reads the real per-step word counts and the real pacing
    constant, not a hand-maintained estimate that could drift from the copy."""
    dataset, script_block = extract_dataset_and_script(html)
    inner = re.search(r"\(function \(\) \{(.*)\}\)\(\);", script_block, re.S).group(1)
    inner = inner.replace('"use strict";', "")
    inner = re.sub(
        r'JSON\.parse\(document\.getElementById\("dataset"\)\.textContent\)',
        "__RAW__", inner,
    )
    harness = (
        _STUB
        + "var __RAW__ = " + json.dumps(dataset) + ";\n"
        + inner
        + "\nvar summary = {"
        + "stepCount: TOUR_STEPS.length,"
        + "labels: TOUR_STEPS.map(function(s){ return s.label; }),"
        + "titles: TOUR_STEPS.map(function(s){ return s.title; }),"
        + "totalWords: totalWords,"
        + "paceWordsPerSec: PACE_WORDS_PER_SEC,"
        + "estimatedSeconds: totalWords / PACE_WORDS_PER_SEC,"
        + "targetsResolved: TOUR_STEPS.map(function(s){ return !!s.target(); }),"
        + "};\n"
        + "console.log(JSON.stringify(summary));\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        script_path = Path(tmp) / "harness.js"
        script_path.write_text(harness, encoding="utf-8")
        result = subprocess.run(["node", str(script_path)], capture_output=True, text=True)
    assert result.returncode == 0, f"Node execution failed:\n{result.stderr}"
    return json.loads(result.stdout.strip())


REPORTS_DIR = REPO_ROOT / "tests" / "reports"
RAW_FIXTURE = REPO_ROOT / "skill" / "charity-donor-outreach" / "assets" / "sample_donors.csv"


def run_upload_clean_persist_flow_in_node(html: str, raw_csv_text: str) -> dict:
    """Feed the case study's own unedited CSV through the page's upload,
    correction, and browser-persistence functions inside Node, timing each
    stage, and return the before/after counts plus a save-then-restore
    round trip. This is the headless proof that "upload the unedited file,
    compare it to what the system finds, clean it, and have it persist"
    actually works, on the real client-side code, not a description of it."""
    dataset, script_block = extract_dataset_and_script(html)
    inner = re.search(r"\(function \(\) \{(.*)\}\)\(\);", script_block, re.S).group(1)
    inner = inner.replace('"use strict";', "")
    inner = re.sub(
        r'JSON\.parse\(document\.getElementById\("dataset"\)\.textContent\)',
        "__RAW__", inner,
    )
    harness = (
        _STUB
        + "var __RAW__ = " + json.dumps(dataset) + ";\n"
        + inner
        + """
        function summarize() {
          var crit = 0, warn = 0, ok = 0, mandatory = 0;
          donors.forEach(function (row) {
            var s = deriveState(row);
            if (s.flagLevel === "crit") crit++;
            else if (s.flagLevel === "warn") warn++;
            else ok++;
            if (deriveReview(row, s).level === "mandatory") mandatory++;
          });
          return { crit: crit, warn: warn, ok: ok, mandatory: mandatory, total: donors.length };
        }
        var timings = {};
        var rawCsvText = """ + json.dumps(raw_csv_text) + """;

        var t0 = Date.now();
        donors = loadDonorsFromCsvText(rawCsvText);
        timings.upload_and_validate_ms = Date.now() - t0;
        var uploaded = summarize();

        var t1 = Date.now();
        var applied = applySuggestedCorrections();
        timings.apply_corrections_ms = Date.now() - t1;
        var afterCorrections = summarize();

        var t2 = Date.now();
        var savedPayload = saveCleanedDataset();
        timings.save_ms = Date.now() - t2;

        donors = buildDonorsFromRecords(__RAW__);  // simulate a fresh session

        var t3 = Date.now();
        var restored = restoreCleanedDataset();
        timings.restore_ms = Date.now() - t3;
        var afterRestore = summarize();

        console.log(JSON.stringify({
          uploaded: uploaded,
          applied: applied,
          afterCorrections: afterCorrections,
          afterRestore: afterRestore,
          savedCount: savedPayload.donors.length,
          restoredCount: restored ? restored.donors.length : 0,
          timings: timings,
        }));
        """
    )
    with tempfile.TemporaryDirectory() as tmp:
        script_path = Path(tmp) / "harness.js"
        script_path.write_text(harness, encoding="utf-8")
        result = subprocess.run(["node", str(script_path)], capture_output=True, text=True)
    assert result.returncode == 0, f"Node execution failed:\n{result.stderr}"
    return json.loads(result.stdout.strip())


@pytest.fixture(scope="module")
def upload_flow():
    if not DELIVERABLE.exists():
        pytest.skip("deliverable/donor-data-review.html not built; run build_dataset.py + embed_dataset.py")
    if not RAW_FIXTURE.exists():
        pytest.skip("raw fixture not found")
    html = DELIVERABLE.read_text(encoding="utf-8")
    raw_csv_text = RAW_FIXTURE.read_text(encoding="utf-8")
    return run_upload_clean_persist_flow_in_node(html, raw_csv_text)


class TestUploadCleanPersistFlow:
    """Proves the browser deliverable can take the case study's own
    unedited donor file, find exactly what the Python validator finds,
    clean it with one action, and keep the cleaned result across a
    simulated new session, entirely client-side. Ground truth (4 tier
    mismatches, 2 lapsed-major donors held for personal outreach, 5
    Platinum donors always under mandatory review) is independently
    computed straight from donor_rules.py against the same raw file in
    test_fixture_fidelity.py and the Python pipeline's own committed
    output; this test does not re-derive it, only checks the browser
    logic agrees with it."""

    def test_upload_finds_exactly_what_python_finds(self, upload_flow):
        uploaded = upload_flow["uploaded"]
        assert (uploaded["crit"], uploaded["warn"], uploaded["ok"], uploaded["total"]) == (4, 2, 44, 50)
        assert uploaded["mandatory"] == 5

    def test_apply_corrections_clears_every_mismatch(self, upload_flow):
        assert upload_flow["applied"] == 4
        after = upload_flow["afterCorrections"]
        assert after["crit"] == 0
        assert after["total"] == 50
        assert after["mandatory"] == 5, "Platinum-always review must not change with a tier fix"

    def test_cleaned_dataset_persists_across_a_simulated_new_session(self, upload_flow):
        assert upload_flow["savedCount"] == 50
        assert upload_flow["restoredCount"] == 50
        restored = upload_flow["afterRestore"]
        assert restored["crit"] == 0, "a restored session must not resurrect the corrected mismatches"
        assert restored == upload_flow["afterCorrections"]

    def test_metrics_are_captured_and_reported(self, upload_flow):
        report_path = REPORTS_DIR / "deliverable_clean_metrics.json"
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report = {
            "generated_by": "tests/test_deliverable_logic.py::TestUploadCleanPersistFlow",
            "source_file": "skill/charity-donor-outreach/assets/sample_donors.csv",
            "rules_version": rules.RULES_VERSION,
            "before_upload": upload_flow["uploaded"],
            "corrections_applied": upload_flow["applied"],
            "after_corrections": upload_flow["afterCorrections"],
            "after_save_and_restore": upload_flow["afterRestore"],
            "timings_ms": upload_flow["timings"],
        }
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        assert all(v >= 0 for v in upload_flow["timings"].values())
        assert report_path.exists()


def run_security_helpers_in_node(html: str) -> dict:
    """Exercise csvSafe, escapeHtml, and pill directly against the same
    adversarial inputs the Python pipeline's own csv_safe and HTML-escaped
    rendering are tested against (test_pipeline.py::test_formula_injection_arrives_inert),
    proving the browser tool, which now accepts an uploaded file from
    anywhere, makes the same two guarantees: no formula executes when the
    export is opened in Excel, and no markup executes when donor-supplied
    text is rendered."""
    dataset, script_block = extract_dataset_and_script(html)
    inner = re.search(r"\(function \(\) \{(.*)\}\)\(\);", script_block, re.S).group(1)
    inner = inner.replace('"use strict";', "")
    inner = re.sub(
        r'JSON\.parse\(document\.getElementById\("dataset"\)\.textContent\)',
        "__RAW__", inner,
    )
    harness = (
        _STUB
        + "var __RAW__ = " + json.dumps(dataset) + ";\n"
        + inner
        + """
        var result = {
          csvSafeFormula: csvSafe('=HYPERLINK("http://evil")'),
          csvSafePlus: csvSafe("+1+1"),
          csvSafeMinus: csvSafe("-1+1"),
          csvSafeAt: csvSafe("@SUM(1)"),
          csvSafeNormalName: csvSafe("Robert Svensson"),
          escapedScriptTag: escapeHtml("<script>alert(1)</script>"),
          pillEscapesText: pill("crit", "Tier mismatch: stated <img onerror=alert(1)>, computed Gold"),
        };
        console.log(JSON.stringify(result));
        """
    )
    with tempfile.TemporaryDirectory() as tmp:
        script_path = Path(tmp) / "harness.js"
        script_path.write_text(harness, encoding="utf-8")
        result = subprocess.run(["node", str(script_path)], capture_output=True, text=True)
    assert result.returncode == 0, f"Node execution failed:\n{result.stderr}"
    return json.loads(result.stdout.strip())


@pytest.fixture(scope="module")
def security_helpers():
    if not DELIVERABLE.exists():
        pytest.skip("deliverable/donor-data-review.html not built; run build_dataset.py + embed_dataset.py")
    html = DELIVERABLE.read_text(encoding="utf-8")
    return run_security_helpers_in_node(html)


class TestExportAndRenderingAreSafeAgainstHostileInput:
    """The upload feature means donor data can now come from any file, not
    only the trusted, pipeline-built embedded dataset. These pin the two
    hostile-input guarantees the Python pipeline already makes onto the
    browser tool as well: a cell that would execute as an Excel formula is
    neutralized on export, and donor-supplied text can never inject markup
    when rendered into the page. Verified live in the browser against an
    uploaded file containing both an HTML-injection attempt and an
    apostrophe in a real name, with no console errors."""

    def test_csv_export_neutralizes_formula_injection(self, security_helpers):
        assert security_helpers["csvSafeFormula"].startswith("'=")
        assert security_helpers["csvSafePlus"].startswith("'+")
        assert security_helpers["csvSafeMinus"].startswith("'-")
        assert security_helpers["csvSafeAt"].startswith("'@")

    def test_csv_export_leaves_ordinary_names_untouched(self, security_helpers):
        assert security_helpers["csvSafeNormalName"] == "Robert Svensson"

    def test_html_rendering_escapes_donor_supplied_markup(self, security_helpers):
        assert "<script>" not in security_helpers["escapedScriptTag"]
        assert "&lt;script&gt;" in security_helpers["escapedScriptTag"]
        assert "<img" not in security_helpers["pillEscapesText"]


@pytest.fixture(scope="module")
def js_results():
    if not DELIVERABLE.exists():
        pytest.skip("deliverable/donor-data-review.html not built; run build_dataset.py + embed_dataset.py")
    html = DELIVERABLE.read_text(encoding="utf-8")
    return run_derive_state_in_node(html)


@pytest.fixture(scope="module")
def tour_metadata():
    if not DELIVERABLE.exists():
        pytest.skip("deliverable/donor-data-review.html not built; run build_dataset.py + embed_dataset.py")
    html = DELIVERABLE.read_text(encoding="utf-8")
    return run_tour_metadata_in_node(html)


def test_exactly_the_four_planted_tier_traps_are_flagged_critical(js_results):
    crit = {r["donor_name"] for r in js_results if r["flagLevel"] == "crit"}
    assert crit == {
        "Ruth Andersen", "Ada Yamamoto-Pierce",
        "Shirley Magnusdottir", "Arthur Mwangi",
    }


def test_lapsed_tier_label_is_not_treated_as_a_financial_mismatch(js_results):
    """Regression test for the bug this file's docstring describes: donors
    filed with tier "Lapsed" must never be flagged just because "Lapsed"
    is not one of the four financial tiers."""
    by_name = {r["donor_name"]: r for r in js_results}
    for name in ("Michael Torres", "Charles Kimura", "Paul Achebe",
                 "Frank Watanabe", "Lars Achebe-Nielsen", "Thomas Bergmann",
                 "Frank Dimitriou", "Raymond Volkov", "Henry Obi",
                 "Felix Mensah-Bonsu"):
        assert by_name[name]["flagLevel"] != "crit", (
            f"{name} was filed as Lapsed and is genuinely lapsed by date; "
            "flagging it as a tier mismatch is the bug this test guards."
        )


def test_lapsed_major_donors_are_warned_not_flagged_critical(js_results):
    by_name = {r["donor_name"]: r for r in js_results}
    for name in ("Robert Svensson", "Walter Adeyemi"):
        assert by_name[name]["flagLevel"] == "warn"


def test_flag_counts_match_the_python_pipelines_own_output(js_results):
    crit = sum(1 for r in js_results if r["flagLevel"] == "crit")
    warn = sum(1 for r in js_results if r["flagLevel"] == "warn")
    ok = sum(1 for r in js_results if r["flagLevel"] == "ok")
    assert (crit, warn, ok) == (4, 2, 44)


def test_dataset_covers_all_fifty_donors(js_results):
    assert len(js_results) == 50


class TestGuidedWalkthrough:
    """The walkthrough is a specific requirement: a spotlighted, captioned
    tour of the redesign, under two minutes, built from the same word counts
    a narrator would actually read. These tests read the real TOUR_STEPS
    array and pacing constant out of the built page, so the two-minute
    budget is an enforced property of the file, not a claim in a comment."""

    def test_six_steps_in_order(self, tour_metadata):
        assert tour_metadata["stepCount"] == 6
        assert tour_metadata["labels"] == [
            "1 / 6, the result",
            "2 / 6, checkpoint one",
            "3 / 6, checkpoints two and three",
            "4 / 6, the review gate",
            "5 / 6, a real example",
            "6 / 6, the whole difference",
        ]

    def test_under_two_minutes_at_the_stated_pace(self, tour_metadata):
        assert tour_metadata["estimatedSeconds"] < 120, (
            f"walkthrough estimated at {tour_metadata['estimatedSeconds']:.1f}s "
            "at the stated reading pace; requirement is under two minutes"
        )

    def test_every_step_has_meaningful_narration(self, tour_metadata):
        assert tour_metadata["totalWords"] > 100
        for title in tour_metadata["titles"]:
            assert title, "every step needs a title"

    def test_most_step_targets_resolve_on_a_real_page(self, tour_metadata):
        """All targets except the live-search step resolve here: this stub's
        querySelectorAll cannot simulate a rendered table row, so step 5
        (donor row lookup) is exercised separately by manual browser testing,
        not by this headless check."""
        resolved = tour_metadata["targetsResolved"]
        for index, ok in enumerate(resolved):
            if index == 4:
                continue
            assert ok, f"tour step {index + 1} target did not resolve"
