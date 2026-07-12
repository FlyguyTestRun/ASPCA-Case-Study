# ADR 0027: On-demand run archiving, built into the review app

Status: accepted. Date: 2026-07-12.

## Problem

`generate_letters.py` clears `output/letters/` at the start of every run so the manifest and the folder can never disagree (ADR 0022), which is correct, but it means a completed run's output is otherwise gone the moment the next one starts. ADR 0022 identified the gap and deliberately deferred a full solution (`output/runs/<run_id>/...`, preserving every run automatically) as touching more of the system than was justified before the deadline. Reviewers still need a way to keep a labeled copy of a batch they signed off on, on purpose, without that larger build.

## Decision

`donor_rules.archive_run` copies a completed run's `manifest.csv` and `output/letters/*.html` into a timestamped, labeled folder under `output/archive/`, with a small `archive_info.json` (label, note, timestamp, rules version, donor and letter counts). `donor_rules.list_archived_runs` reads them back, newest first. The review app's Finalize step, after sign-off, offers "Archive this run" with a label and an optional note; archiving itself writes a decision-log entry, so the record of what was archived and by whom lives in the same audit trail as every other persistent action in this system. Because the app runs the pipeline in a temporary directory that no longer exists by the time a user reaches Finalize, the app-side implementation (`archive_current_run` in `review_app.py`) writes directly from the already-loaded manifest and letters in memory rather than copying a live directory; it produces the same file layout so archives look identical regardless of which path created them.

This is deliberately the smaller thing ADR 0022 deferred: on demand, from the interface, no change to the pipeline scripts' default behavior, no run-ID plumbing through every stage, no CI changes. Full automatic run-versioning remains a documented scale trigger in `docs/scale-architecture.md` for when it is actually needed.

## What this changes going forward

A reviewer can preserve a batch they are proud of, or one they need to reference later, in one click, and every archive is self-describing without needing to correlate it against anything else. This is also the natural next step if automatic run-versioning is ever built: the file layout and metadata shape are already settled and tested.
