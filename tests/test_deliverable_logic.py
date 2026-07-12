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
    # Stub the DOM surface the script touches during setup so it runs headless;
    # the functions under test (computeTier, isLapsed, deriveState) are pure.
    stub = """
    var document = {
      documentElement: { getAttribute: function(){return null;}, setAttribute: function(){}, removeAttribute: function(){} },
      getElementById: function(){ return { addEventListener: function(){}, value: "", textContent: "" }; },
      addEventListener: function(){},
      querySelector: function(){ return null; },
    };
    """
    harness = (
        stub
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


@pytest.fixture(scope="module")
def js_results():
    if not DELIVERABLE.exists():
        pytest.skip("deliverable/donor-data-review.html not built; run build_dataset.py + embed_dataset.py")
    html = DELIVERABLE.read_text(encoding="utf-8")
    return run_derive_state_in_node(html)


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
