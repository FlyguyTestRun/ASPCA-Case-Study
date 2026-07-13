"""Tests for the review app's pure helper functions.

app/review_app.py runs Streamlit UI code at module scope (st.set_page_config,
sidebar widgets, the four-stage flow), so a plain import executes past
st.stop() outside a real Streamlit script run and crashes on missing
session state. load_pure_functions() below parses the file with ast and
executes only the import statements and the two functions under test,
never any Streamlit call, so this exercises the app's actual source, not a
reimplementation of it, without needing a Streamlit runtime.

These fill a real gap: app/review_app.py had no tests at all before this
file, so the CSV formula-injection guard added to apply_corrections_to_bytes
and the markdown-escaping added to md_escape (ADR 0032) were unverified.
"""

import ast
import io

import pandas as pd
import pytest

from conftest import REPO_ROOT

REVIEW_APP = REPO_ROOT / "app" / "review_app.py"

pytestmark = pytest.mark.skipif(not REVIEW_APP.exists(), reason="app/review_app.py not found")


def load_pure_functions() -> dict:
    source = REVIEW_APP.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(REVIEW_APP))
    wanted = {"apply_corrections_to_bytes", "md_escape", "_MD_SPECIAL"}
    kept = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            kept.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted:
            kept.append(node)
        elif isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in wanted
            for target in node.targets
        ):
            kept.append(node)
    module = ast.Module(body=kept, type_ignores=[])
    ast.fix_missing_locations(module)
    code = compile(module, filename=str(REVIEW_APP), mode="exec")
    namespace: dict = {}
    exec(code, namespace)  # noqa: S102 - executing our own reviewed source, not user input
    return namespace


@pytest.fixture(scope="module")
def helpers():
    return load_pure_functions()


class TestApplyCorrectionsToBytesNeutralizesFormulaInjection:
    """apply_corrections_to_bytes only rewrites the field being corrected
    (usually tier); every other column, including donor_name, is carried
    through verbatim from whatever the uploaded file said. This file is
    also handed straight back to Excel via a download button."""

    def _run(self, helpers, donor_name: str) -> str:
        csv_bytes = (
            f"donor_name,tier,region,gifts,largest_gift,lifetime_total,last_gift_year,volunteer\n"
            f'"{donor_name}",Silver,West,2020:5000|2021:6000,6000,11000,2021,No\n'
        ).encode("utf-8")
        approved = pd.DataFrame([
            {"row_number": "2", "donor_name": donor_name, "field": "tier",
             "current_value": "Silver", "suggested_value": "Gold",
             "reason": "lifetime giving of $11,000 places this donor in Gold"},
        ])
        result = helpers["apply_corrections_to_bytes"](csv_bytes, ".csv", approved)
        return result.decode("utf-8")

    def test_formula_injection_arrives_inert(self, helpers):
        out = self._run(helpers, '=HYPERLINK("http://evil")')
        frame = pd.read_csv(io.StringIO(out), dtype=str)
        assert frame.loc[0, "donor_name"].startswith("'=")

    def test_ordinary_name_is_untouched(self, helpers):
        out = self._run(helpers, "Robert Svensson")
        frame = pd.read_csv(io.StringIO(out), dtype=str)
        assert frame.loc[0, "donor_name"] == "Robert Svensson"

    def test_the_approved_correction_still_applies(self, helpers):
        out = self._run(helpers, "Robert Svensson")
        frame = pd.read_csv(io.StringIO(out), dtype=str)
        assert frame.loc[0, "tier"] == "Gold"


class TestMdEscape:
    """donor_name is arbitrary text from an uploaded file, unlike tier or
    review_level, which are schema-constrained enums; md_escape keeps it
    from being interpreted as markdown when shown in the review UI."""

    def test_escapes_markdown_link_syntax(self, helpers):
        escaped = helpers["md_escape"]("[click me](javascript:alert(1))")
        assert "[click me]" not in escaped
        assert "\\[click me\\]" in escaped

    def test_escapes_bold_and_underscore_markers(self, helpers):
        escaped = helpers["md_escape"]("**bold** _em_")
        assert "**bold**" not in escaped

    def test_ordinary_name_is_unchanged_in_meaning(self, helpers):
        # Escaping prefixes a backslash; the visible characters are the same.
        escaped = helpers["md_escape"]("Robert Svensson")
        assert escaped.replace("\\", "") == "Robert Svensson"
