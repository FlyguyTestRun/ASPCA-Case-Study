# ADR 0034: Answer the brief directly in the standalone deliverable, with one worked comparison

Status: accepted. Date: 2026-07-13.

## Problem

The standalone deliverable proved the pipeline works, but did not, on its own, state what it was answering: a reviewer opening only this one file had no direct statement of the case study's two tasks (describe improvements and their impact; rewrite the skill) or a link to the artifacts that answer each. Separately, the repository's various write-ups describe the tier-mismatch defect in prose, but never showed, in one place, an actual before-and-after number: what the original instructions would have produced for a real donor, next to what this pipeline produces for the same donor. Without that, "the findings are different" is an assertion, not a demonstration.

## Decision

Two new sections in `deliverable/donor-data-review.html`, both static content (not driven by the embedded dataset, since they state a fixed claim rather than a live count):

- **"What this case study asked for"**, right after the masthead: the brief in close-to-verbatim form, and the two tasks, each linked to what answers it (the written assessment and trap registry for the first, the rewritten `SKILL.md` for the second).
- **"Same donor, two approaches"**, after the pipeline diagram: Ruth Andersen's real record, run through the original `SKILL.md`'s own literal ask-calculation steps (trusting her stated Silver tier, rounding mid-sequence, exactly as written) next to the rewrite's steps (recomputing her tier from her actual gift history to Gold, one final rounding step). $1,050 base with mid-sequence rounding cascades to $1,506; the corrected Gold-rate calculation cascades to $2,450, a $944 difference on one donor, from one label that was never checked against the money it was supposed to describe.

## What this changes going forward

`tests/test_deliverable_logic.py::TestOriginalVsRewriteComparisonStaysAccurate` independently recomputes both figures from `donor_rules.py` and the raw fixture and asserts they still match the page's static text, so this comparison cannot go stale if the fixture or the policy ever changes without the test catching it. Verified live in the browser: both new sections render correctly, all four new links (assessment, trap registry, rewritten skill, original skill) resolve, no console errors.
