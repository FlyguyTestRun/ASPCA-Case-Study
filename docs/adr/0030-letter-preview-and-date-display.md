# ADR 0030: Show the real generated letter per donor, and display gift dates honestly

Status: accepted. Date: 2026-07-12.

## Problem

Two gaps in the standalone deliverable surfaced from direct use: the "Last Gift Yr" column showed a bare year (`2020`), which reads as a legacy, half-finished data field next to columns of real dollar amounts and dates; and expanding a donor's row showed only the ask calculation trace, not the actual letter the pipeline generated for them, so a reviewer had to leave the page and open a file in `output/letters/` to see the real output.

## Decision

**Date display.** The source data has only ever recorded a gift year, never a day or month; inventing one would be exactly the kind of fabricated precision this whole project exists to eliminate (ADR 0008). `formatLastGiftDate` displays the last gift year as the last day of that year (`12/31/2020`), the most defensible single choice since it is also the most conservative point for lapsed-status math, editable the same way as before (`yearFromDateLikeText` extracts the year back out of whatever is typed). The value that actually drives tier, lapsed status, review level, and the CSV export stays a plain year underneath; nothing about the underlying data model or the pipeline's contract changed, only how the year is presented.

**Letter preview.** `deliverable/build_dataset.py` now runs `generate_letters.py` as part of its own scratch pipeline run (into `deliverable/_work/out`, never the committed `output/`), so the embedded dataset always carries the real, freshly generated letter HTML for every donor the pipeline actually produced one for, with the same 44-of-50 outcome as the committed evidence run. Each donor's row-detail expansion now shows that letter, unmodified, inside a sandboxed `<iframe srcdoc>` so its markup is isolated from the surrounding page and cannot execute anything. A donor with no letter (held pending correction, or a lapsed major donor routed to personal outreach) shows the specific reason instead, taken from the same manifest and review-reason text the Python pipeline itself produces, never invented for the occasion.

**Reference date.** Separately, `as_of_date` stays pinned at 2024-06-30, unchanged. [ADR 0004](0004-explicit-as-of-date.md) now includes an explicit section on why the committed demo does not track today's date: a fixed reference date is a reproducibility property, not staleness, and the deliverable's footer says so directly rather than leaving a reviewer to wonder.

## What this changes going forward

Rebuilding the deliverable (`python deliverable/build_dataset.py && python deliverable/embed_dataset.py`) now always regenerates letters fresh alongside the validated and computed data, so the two can never silently drift apart. `tests/test_deliverable_logic.py` continues to pin the page's tier and date logic against the fixture; the letter content itself is proven by the pipeline's own existing letter-quality tests (`test_rules.py`, `test_pipeline.py`), not re-verified a second time in JavaScript, consistent with keeping one implementation of letter content.
