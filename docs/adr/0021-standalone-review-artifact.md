# ADR 0021: A standalone HTML artifact for offline review of the full dataset

Status: accepted. Date: 2026-07-11.

## Problem

The Python pipeline and the Streamlit review app both require an installed environment to run. Doug, or anyone reviewing this case study on a machine without Python, needed a way to see the verified result and inspect or correct the underlying donor data with nothing more than a browser: no server, no install, no network dependency, and at fifty records, no reason not to have one.

## Decision

`deliverable/donor-data-review.html` is a single self-contained file that embeds the pipeline's own output (built by `deliverable/build_dataset.py` running the real validator and calculator, never hand-typed) and reimplements the tier and lapsed-status rules in JavaScript so a reviewer can edit any flagged field and see the check re-run instantly, entirely client-side. It states the verified result first (record counts by status), diagrams the pipeline with each stage annotated to the problem it solves, then presents the full fifty-donor table with search, filtering, per-record calculation detail, and a corrected-CSV export. Nothing in the page transmits data anywhere.

Reimplementing validation logic in a second language is a real risk, and it produced a real bug during development: the first version compared every donor's stated tier directly against the computed financial tier, which is correct for Platinum, Gold, Silver, and Bronze but wrong for the ten donors filed with the literal tier value "Lapsed", a status claim the Python validator checks against computed lapsed-by-date status, never against a financial tier. That single gap inflated flagged records from 4 to 14 and would have told a reviewer the dataset was three and a half times worse than it is. `tests/test_deliverable_logic.py` now executes the page's actual embedded JavaScript with Node against the same fixture the Python tests use and fails the build if the two implementations ever disagree again.

## What this changes going forward

Anyone can review or correct this dataset with nothing but a browser, which matches the deliverable to its audience: fundraising staff and reviewers, not only engineers. The drift risk of a second implementation is real but bounded and tested, not assumed away, and the bug that risk actually produced is now a permanent regression test rather than a lesson learned once and forgotten.
