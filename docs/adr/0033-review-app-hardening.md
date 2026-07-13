# ADR 0033: Harden the review app's own hostile-input gaps

Status: accepted. Date: 2026-07-13.

## Problem

Auditing `app/review_app.py` with the same lens as the standalone deliverable (ADR 0032) found two real gaps, both pre-existing, neither previously tested:

1. **`apply_corrections_to_bytes`** rewrites only the field being corrected (usually `tier`); every other column, including `donor_name`, is carried through from the uploaded file untouched, then written out with plain `frame.to_csv()` for the "Download corrected file for your source system" button. Every other CSV this system writes neutralizes a leading `= + - @` before saving (`csv_safe`, ADR 0018); this one did not, so a donor named `=HYPERLINK(...)` in an uploaded file would export as a live formula.
2. Several `st.markdown` calls interpolate `donor_name` directly, most visibly the donor detail panel in the Review step and the "required reviews outstanding" list in Finalize. Unlike `tier`, `status`, or `review_level`, which are schema-constrained enums validated before a row ever reaches this app, `donor_name` is arbitrary text from an uploaded file. Streamlit's default `unsafe_allow_html=False` (used throughout, confirmed by grep, no exceptions) already blocks raw HTML, but markdown link syntax is still parsed, so an unescaped name could still render as a link or otherwise distort the layout.

## Decision

`apply_corrections_to_bytes` now applies `rules.csv_safe` to every cell (`frame.map(rules.csv_safe)`) before writing the corrected CSV, matching the guarantee every other pipeline-written CSV already makes. A new `md_escape` helper escapes markdown-significant characters and is applied at both `donor_name` interpolation points; tier, status, confidence, and review_level are left alone since they are enum-constrained upstream, not free text.

## What this changes going forward

`tests/test_review_app.py` is new: `app/review_app.py` runs Streamlit UI code at module scope, so a plain import executes past `st.stop()` outside a real script run and crashes; the test file parses the source with `ast` and executes only the imports and the two functions under test, exercising the real code without a Streamlit runtime. It pins `apply_corrections_to_bytes` against the same adversarial formula prefixes used elsewhere and confirms the approved correction still applies; it pins `md_escape` against a markdown-link injection attempt and confirms an ordinary name passes through unchanged. Verified live as well: ran the app with `streamlit run`, completed a full sample run through Findings, and confirmed the Review step's donor panel still renders "Robert Svensson" correctly, no console errors.
