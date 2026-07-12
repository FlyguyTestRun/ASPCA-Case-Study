# ADR 0022: Donor ID collisions are caught, and generated output cannot go stale

Status: accepted. Date: 2026-07-12.

## Problem

A second-pass audit of the rewritten pipeline, after it was already passing its own test suite, found two silent-failure paths that the design otherwise goes out of its way to eliminate everywhere else.

First, `donor_id` is derived from `donor_name` by `slugify()`, which strips punctuation and collapses whitespace to hyphens. Two different donors can produce the same slug: "Jean-Paul Ostrowski" and "Jean Paul Ostrowski" both slugify to `jean-paul-ostrowski`. The existing duplicate check in `validate_input.py` only catches identical names; it never looks at the derived id. Because `donor_id` is also the letter filename (`output/letters/<donor_id>.html`) and the manifest join key, a collision meant one donor's letter could silently overwrite another's, with no exception, no warning, and no test. It does not happen on the 50-row fixture, which is exactly why it had gone unnoticed: this is a scale-triggered defect, the same category every other fix in this repository targets.

Second, `generate_letters.py` created `output/letters/` if missing but never cleared it. A donor who received a letter in one run and was excluded from the next (a new exception, a newly lapsed major donor) left a stale HTML file behind with no corresponding manifest row. A reviewer who opened the letters folder directly, rather than working strictly from `manifest.csv`, could act on out-of-date content that the current run no longer stands behind.

## Decision

1. **Donor ID collisions are detected and held, not silently resolved.** After the per-row validation pass in `validate_input.py`, every validated row's `donor_id` is checked against every other validated row's. Any `donor_id` produced by more than one row sends every row in that group to `exceptions.csv`, naming the colliding row numbers, with a suggested fix pointing at the source system. No row in a colliding group is ever written to `validated.csv`, so neither the earlier nor the later row wins by accident.
2. **Every `generate_letters.py` run clears `output/letters/*.html` before writing.** The manifest and the folder can never disagree about which letters belong to the current run.

Full run-versioning (`output/runs/<run_id>/...`, preserving every past run as its own audit trail rather than overwriting in place) was considered and deliberately deferred; it touches the review app, the deliverable builder, and CI, and the manifest and `work/run_metrics.json` already carry enough information to justify building it later. It is recorded as a scale trigger in `docs/scale-architecture.md` rather than implemented now, alongside the other components this system defers on purpose.

## What this changes going forward

`donor_name` remains a fixture-scale join key with a documented limitation (see `references/input_schema.md`), but the failure mode of that limitation changes from silent data loss to a held record with a specific, actionable reason. Regenerating letters after any data change, correction, or campaign rerun can never leave orphaned files behind for a reviewer to mistake for current output. Both properties are pinned by tests in `tests/test_pipeline.py`: `test_donor_id_collision_is_caught_not_overwritten` and `test_generate_letters_clears_stale_output`.
