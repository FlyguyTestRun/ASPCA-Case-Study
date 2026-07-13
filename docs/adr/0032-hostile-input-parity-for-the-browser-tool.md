# ADR 0032: The browser tool makes the same hostile-input guarantees the Python pipeline does

Status: accepted. Date: 2026-07-12.

## Problem

ADR 0029 added the ability to upload an arbitrary CSV into the standalone deliverable, which changes its threat model: every donor field the page renders or exports can now come from a file nobody has reviewed, not only the trusted, pipeline-built embedded dataset. A pass looking specifically for that gap found three real ones, none exercised by any existing test because none had ever been possible before uploads existed:

1. **Formula injection on export.** The Python pipeline's `csv_safe` neutralizes a cell beginning with `= + - @` before writing any CSV (ADR 0018), because every CSV it writes is opened directly in Excel by fundraising staff. The browser's "Download cleaned CSV" export had no equivalent: a donor named `=HYPERLINK(...)`, typed in an edit or arriving via an uploaded file, would export as a live formula.
2. **Unescaped HTML rendering.** `donor_name`, `region`, and `stated_tier` were written into the table via `innerHTML` string concatenation with no escaping, and the tier-mismatch/flag text built from `stated_tier` flowed through the same path unescaped. This was safe only because every prior value came from the pipeline's own controlled output; an uploaded donor named `<img src=x onerror=...>` would execute.
3. **A silent crash on blocked storage.** Every `window.localStorage` call ran unguarded. Safari private browsing and browsers with storage fully blocked throw just from touching `localStorage`, not only on write, and `updateCleanControlsVisibility()` runs unconditionally on page load, so a browser with blocked storage would fail to render the page at all rather than degrade gracefully.

## Decision

- `csvSafe(value)` mirrors `donor_rules.csv_safe` exactly and is applied to every exported cell before CSV-quoting.
- `escapeHtml(text)` (already used for the ask trace and no-letter reason) is now applied to `donor_name`, `region`, and `stated_tier` at their point of insertion, and `pill(level, text)` escapes its own `text` argument internally, since flag and review text can embed a raw field value.
- Every `window.localStorage` call (`getItem`, `setItem`, `removeItem`) is wrapped so a thrown exception degrades to "storage unavailable," never a page crash; `loadSavedPayload`, and by extension `updateCleanControlsVisibility` at bootstrap, return null/no-op instead of propagating.

## What this changes going forward

Verified directly in the browser: uploading a file containing `<img src=x onerror=alert(1)>` as a donor name and `West & <b>Coast</b>` as a region renders both as inert literal text, with no alert and no console error; a real apostrophe in "Jane O'Brien" still displays correctly. `tests/test_deliverable_logic.py::TestExportAndRenderingAreSafeAgainstHostileInput` pins `csvSafe` against the same four adversarial prefixes `test_pipeline.py::test_formula_injection_arrives_inert` uses on the Python side, and pins `escapeHtml`/`pill` against a script-tag injection attempt, so this class of defect is now guarded the same way on both sides of the tool, not just the one that existed first.
