# ADR 0021: A standalone HTML artifact for offline review of the full dataset

Status: accepted. Date: 2026-07-11. Revised same day to add a guided, spotlighted walkthrough.

## Problem

The Python pipeline and the Streamlit review app both require an installed environment to run. Anyone reviewing this case study on a machine without Python needed a way to see the verified result and inspect or correct the underlying donor data with nothing more than a browser: no server, no install, no network dependency, and at fifty records, no reason not to have one.

## Decision

`deliverable/donor-data-review.html` is a single self-contained file that embeds the pipeline's own output (built by `deliverable/build_dataset.py` running the real validator and calculator, never hand-typed) and reimplements the tier and lapsed-status rules in JavaScript so a reviewer can edit any flagged field and see the check re-run instantly, entirely client-side. It states the verified result first (record counts by status), diagrams the pipeline with each stage annotated to the problem it solves, then presents the full fifty-donor table with search, filtering, per-record calculation detail, and a corrected-CSV export. Nothing in the page transmits data anywhere.

Reimplementing validation logic in a second language is a real risk, and it produced a real bug during development: the first version compared every donor's stated tier directly against the computed financial tier, which is correct for Platinum, Gold, Silver, and Bronze but wrong for the ten donors filed with the literal tier value "Lapsed", a status claim the Python validator checks against computed lapsed-by-date status, never against a financial tier. That single gap inflated flagged records from 4 to 14 and would have told a reviewer the dataset was three and a half times worse than it is. `tests/test_deliverable_logic.py` now executes the page's actual embedded JavaScript with Node against the same fixture the Python tests use and fails the build if the two implementations ever disagree again.

## What this changes going forward

Anyone can review or correct this dataset with nothing but a browser, which matches the deliverable to its audience: fundraising staff and reviewers, not only engineers. The drift risk of a second implementation is real but bounded and tested, not assumed away, and the bug that risk actually produced is now a permanent regression test rather than a lesson learned once and forgotten.

## Revision: a guided walkthrough, not just a static page

A page that states its findings is not the same as a page that teaches them. The deliverable needed to answer one question in under two minutes, in a way a reviewer with no context could follow unassisted and a team could reuse as training: why does a well written prompt only ever improve the odds a model behaves, and what does a well designed harness add on top of that.

The page now opens with a "Start the two-minute walkthrough" control. Six beats, each spotlighting a real, live part of the page (the verified result, each pipeline stage, the confidence gate, one of the four actual caught errors, the closing thesis) with a floating caption card, keyboard navigation, and Prev/Next/Play/Pause/End controls. The narration audio is embedded as a base64 data URI in the same single file, so the walkthrough plays with sound with no second file to keep track of; if audio cannot play, or is silenced, the captions alone carry the same content, since a team member sharing a screen without sound needs to read the same words a listener would hear. Step timing is not hand-authored: each step's on-screen duration is the audio's total duration allocated proportionally to that step's caption word count, so the tour re-times itself automatically whether it is running the placeholder narration or Bryan's own recording, without anyone updating a timestamp table by hand.

Building this against a real Node-executed test surfaced a second real bug, the same way the earlier tier-mismatch bug did: the walkthrough's setup code touches `window.matchMedia` and `document.body` unconditionally at page load, and the test harness's original DOM stub was thin enough that it had only ever passed by accident, because a stubbed dropdown's default empty value happened to make the donor table's render loop skip every row and never reach `document.createElement`. The stub is now a complete, reusable headless element factory, and the tests execute the real `TOUR_STEPS` array and the real pacing constant out of the built file, so "under two minutes" is a property Node checks on every build, not a claim in a comment.

## What the revision changes going forward

The under-two-minutes budget and the six-beat structure are now enforced, not promised: a future edit that lengthens the script past the budget, drops a step, or breaks a spotlight target fails the test suite before it fails a live demo. The proportional-timing design also means the file never needs re-timing work again when the real recording replaces the placeholder.
