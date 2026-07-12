# ADR 0031: The date printed on a letter is not the campaign's as_of_date

Status: accepted. Date: 2026-07-12.

## Problem

`generate_letters.py` built every letter's printed date line from `config["as_of_date"]`, the same fixed reference point [ADR 0004](0004-explicit-as-of-date.md) requires for tier and lapsed-status math. That conflated two unrelated facts: as_of_date is a business-logic anchor that must stay fixed for a run to be reproducible, while the date on a real letter a donor receives should read the way any real mail-merge does, as of the day the letter was actually written. Every letter in the committed evidence carried "June 30, 2024" regardless of when the pipeline was actually run, which reads as neglect (an old, unmaintained artifact) rather than what it actually was: a byproduct of reusing one date value for two different jobs.

## Decision

`generate_letters.py` now takes an independent `letter_date`, defaulting to `date.today()`, with an optional `--letter-date YYYY-MM-DD` override for a reproducible test run or a deliberately backdated batch. `as_of_date` is untouched and still drives every business-rule date calculation exactly as ADR 0004 requires. `build_letter_model` takes `letter_date` as an explicit argument rather than deriving it from the config, so the two concepts cannot be silently reconnected by a future edit.

## What this changes going forward

Every letter now prints the actual day it was generated. The committed `output/letters/` evidence and the standalone deliverable's embedded letters were regenerated and now read "July 12, 2026," the day this correction was made, not a frozen 2024 date; only the date line changed, confirmed against `output/manifest.csv` and a diff of every letter. Two new tests guard this: `test_letter_date_is_not_the_as_of_date` asserts no letter contains the as_of_date's date string and every letter contains today's, and `test_letter_date_override_is_respected` proves `--letter-date` still allows a fixed, reproducible date when one is needed.
