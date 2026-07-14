# ADR 0043: Hide the raw confidence score, and an editorial pass on the written materials

Status: accepted. Date: 2026-07-14.

## Problem

Three unrelated but same-day changes, grouped here rather than split into three thin records since none of them touch pipeline logic:

1. The donor table showed a raw confidence score (a column, and the number embedded in the Review pill's text, e.g. "Confidence 0.90: mandatory review"). That number is an internal weighting the confidence rubric uses to decide a review band; showing it invites a reviewer to read meaning into the specific decimal rather than the review level it produces, which is the fact that actually matters.
2. A separate wording review of the assessment and README, checked line by line rather than adopted wholesale, surfaced real improvements worth keeping and some that were not.
3. `README.md`, `assessment/ASSESSMENT.md`, and `docs/components.md` each named the current ADR count as a headline number ("41 Architecture Decision Records"). That number needs updating on every new ADR, which this repository has done faithfully all project, but it is also the least interesting fact about the ADR system: what matters to a reviewer is what the system does with it, not how many files are in the folder.

## Decision

**Confidence score.** Removed the column and header from the donor table, and rewrote the review-level text to state the qualitative outcome only ("Mandatory review," "Recommended review") without the underlying number. The pipeline still computes and exports the real score in `manifest.csv` and the cleaned CSV, matching the real pipeline's own output shape; only the on-page table and its review-pill text stop surfacing it.

**Editorial pass, adopted:** a "Review path" section in `README.md` naming the three things worth reading first, in order; an explicit `pip install` line in "Try it" (dependencies were named but never given an install command); softer, less accusatory defect headers in the assessment ("Unsupported donor claims" instead of "Would have defrauded donors," and five more in the same register) since the original headers read as an attack on the original author rather than a technical finding; and an explicit "Impact:" sentence on every defect item, answering the brief's own "describe improvements and their impact" more directly than folding impact into the fix sentence.

**Editorial pass, not adopted:** compressing the "ten defects" framing into the assessment's opening sentence without stating the trap registry's own count, and cutting the ADR count to a vague gesture rather than a specific fact. Both traded away real, checkable detail for a shorter sentence, and the resulting doc still needed the count-and-grouping reconciliation this same day's second review already flagged as ambiguous (see the entry above). Handled here instead: state both numbers and the grouping directly, and describe the ADR system by function.

**ADR references, still exact.** `README.md`, `assessment/ASSESSMENT.md`, `docs/components.md`, and `deliverable/donor-data-review.template.html` no longer state a running ADR total, replaced with a description of what the system does with the records: "one per architecture choice, the problem, the decision, and the forward impact," paired with the operational decision log the running system writes for itself, together named as the audit trail, the validation record, and the learning loop for the system. Individual ADR citations next to specific claims (linking ADR 0002, ADR 0011, and so on) are untouched; this only removes the aggregate count as a headline number.

## What this changes going forward

No pipeline behavior changed. Suite holds at 155. The doc-count-bump step that closed out every prior round in this project's history no longer applies to ADRs specifically; test counts still get corrected when the suite grows, since that number is evidence of coverage, not a count for its own sake.
