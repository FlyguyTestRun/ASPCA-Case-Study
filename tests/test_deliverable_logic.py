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
        value: "", textContent: "", innerHTML: "", className: "",
      };
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
    var window = {
      matchMedia: function(){ return { matches: false }; },
      setTimeout: function(){ return 0; },
      clearTimeout: function(){},
      addEventListener: function(){},
      removeEventListener: function(){},
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
