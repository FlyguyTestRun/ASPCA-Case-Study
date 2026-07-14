# ADR 0039: A guided process nav, a visible action banner, and a final snapshot in the archive

Status: accepted. Date: 2026-07-14.

## Problem

Walking through the deliverable cold, with no prior knowledge of the file, surfaced a real usability gap the automated tests never would have caught, since they exercise logic, not first impressions. The page opened with the verified-result stats, then moved straight into five long sections (the brief, the architecture explanation, the pipeline diagram, the restraint list, the comparison) before ever reaching the actual actionable table. The table itself, once reached, offered nine undifferentiated buttons in a row (load, export, upload, apply corrections, save, restore, clear, merge, archive) with "Apply suggested corrections" styled identically to seven other, lower-priority actions. A first-time reviewer had no way to tell, at a glance, that four records needed attention or which control fixed them. Separately, the dated archive ZIP contained the cleaned CSV, the manifest, and every letter, but no version of the finished review itself, so the one artifact meant to be a durable, standalone record of what was reviewed did not actually exist inside the record it produced.

## Decision

Three changes, all additive, none changing the underlying validation, correction, or gating logic:

- **A sticky five-step process nav** (Data loaded, Errors found, Review & correct, Sign off, Export final package), each step a real jump to the relevant part of the page, with live badges (the error count, the reviewed-of-mandatory count) so the state of the batch is visible without reading anything. Step 2 also sets the status filter to "Needs correction," so clicking it is the fastest way on the page to see exactly the four flagged rows, not just a scroll target.
- **An action banner** in the header, shown only when records need correction, stating the count and linking straight to the same jump-and-filter behavior as step 2.
- **"Apply suggested corrections" restyled as the primary action** in its own toolbar, separated from the search/filter controls above it and the upload/merge/save-state controls below it, which now live inside a collapsed "Advanced" disclosure so the default view is: search, the one correction action that matters, then the export gate.

Separately, and prompted by the same request: the archive ZIP now includes `review-page-final.html`, a static, non-interactive summary built from the same `donors` array the CSV and manifest already use (never a copy of the live page's own HTML, which would silently discard every correction the moment it was reopened, since this page rebuilds its table from the embedded dataset on load). It lists all fifty donors with their final tier, status, ask, review level, reviewed checkbox state, and a link to their letter file, so the archive is a complete, self-contained record without needing the interactive page at all.

## What this changes going forward

Verified live end to end: the banner and step 2's badge both read "4" against the unedited fixture and disappear once corrections are applied; clicking each of the five steps resolves to a real, distinct element with zero console errors; checking off all five mandatory donors flips the sign-off badge to 5/5 and unlocks the archive button; the produced ZIP was captured directly (via an `URL.createObjectURL` intercept) and confirmed to contain `review-page-final.html` with the expected title, fifty-one table rows (header plus one per donor), and a "Yes" count in the Reviewed column matching the mandatory count exactly. A new permanent test, `test_final_snapshot_html_reflects_reviewed_state`, pins this against the same fixture the rest of the archive tests use. Suite grows from 154 to 155.
