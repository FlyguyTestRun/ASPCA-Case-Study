# ADR 0035: The standalone deliverable becomes a review gate, with a dated archive and pipeline transparency

Status: accepted. Date: 2026-07-13.

## Problem

The deliverable could show a reviewer the pipeline's findings, but had no way to make review itself a real, trackable step: nothing distinguished "I looked at this Platinum donor's letter" from "I have not gotten to it yet," and there was no single artifact tying the reviewed data, the letters, and a record of what was checked into one dated package. Separately, the page asserted it ran the real pipeline scripts, but never showed which ones, or where their outputs land, and the "original data versus your own file" choice was not clearly two distinct actions.

## Decision

- **Per-donor review sign-off and a gate.** Every donor gets a "Reviewed" checkbox; `deriveReview`'s existing `mandatory` level (Platinum, a lapsed-major routing, or confidence below 0.90) now also drives a "Required reviews: X of Y complete" indicator. The new "Download dated archive" button stays disabled until every mandatory record is checked off, mirroring the Streamlit review app's sign-off gate. Nothing is sent either way; the gate controls the record-keeping export, not delivery.
- **A dated archive, built client-side.** A dependency-free ZIP writer (CRC32 plus a minimal STORED-method PKZIP implementation, no external library, since this file must open standalone) packages the cleaned CSV, a manifest (tier, computed tier, ask, confidence, review level, reviewed status, letter file or no-letter reason per donor), and every real generated letter into `donor-archive-<timestamp>.zip`.
- **Script and output transparency.** A new "Scripts on GitHub" list links directly to `validate_input.py`, `calculate_ask.py`, `generate_letters.py`, and `donor_rules.py`, and each pipeline-diagram node in the walkthrough now shows its own script filename and, for the generate stage, its output path (`output/letters/`), directly on the diagram rather than in the narrated (and time-budget-constrained) caption text.
- **Corrected-row messaging fixed.** Applying a correction in the browser only ever updates review/flag state; it never re-runs the ask formula or regenerates a letter. The detail panel previously kept showing the original held-reason and no-letter text after a correction, which read as contradicting the row's new, corrected state. It now says plainly that this page never regenerates a letter, and points to re-running the real pipeline on the exported CSV.
- **Clearer original-data vs. upload framing.** "Reset edits" is renamed "Load original 50 donors," and the section copy states directly that the default view is the case study's own file, with uploading a separate, clearly labeled path.

## What this changes going forward

`tests/test_deliverable_logic.py` gained two new test classes: `TestZipWriterProducesARealArchive` builds a zip through Node exactly as the button would and validates it with Python's independent `zipfile` module (a real cross-implementation check, not a self-consistency check), and `TestReviewGateAndArchiveExports` pins the mandatory-review count against the same ground truth established elsewhere (5 Platinum donors), confirms the gate is closed until every one is checked and open once they are, and checks the manifest and cleaned-CSV shapes. Verified live in the browser: checked all 50 review boxes, confirmed the gate opened, downloaded a real archive, and confirmed the corrected-row message now describes the actual state honestly.
