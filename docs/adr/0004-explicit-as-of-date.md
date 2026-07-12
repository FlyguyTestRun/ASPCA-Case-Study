# ADR 0004: Every date calculation runs against an explicit as_of_date

Status: accepted. Date: 2026-07-10.

## Problem

Lapsed status ("no gift in over 3 years") and the loyalty uplift ("gave last year") are date calculations, but the original skill never said relative to what. The wall clock is the wrong answer: the example data's internal clock is clearly 2024 (one donor, Susan Nakamura, has a 2024 gift), so a run today would silently classify most of the file as lapsed. Whatever date the model assumed would change from run to run and would never be visible to anyone reviewing the output.

## Decision

The campaign config requires an explicit as_of_date, and every date rule in the pipeline uses it: lapsed status, loyalty eligibility, and future-gift detection. Gifts dated after the as_of year are errors. A gift dated within the as_of year is legal but attaches a warning, because it is exactly the situation where an ambiguous reference date changes the outcome.

## What this changes going forward

Runs are reproducible regardless of when they execute, which also makes them testable: the test suite pins as_of_date and asserts exact results. The Susan Nakamura record, a trap under the original design, now surfaces as a visible warning with a confidence deduction instead of silently flipping her loyalty uplift depending on the day the batch runs.

## Why the committed demo still says 2024-06-30, not today

The fixture, the trap registry, every test's expected numbers, the committed `output/` letters, and the standalone deliverable are all calibrated against `as_of_date: 2024-06-30`, the example data's own internal clock. That date staying fixed as the calendar moves forward is this ADR working as designed, not evidence of neglect: the whole point of an explicit as_of_date is that the system's output does not quietly change depending on when someone happens to open the repository or run the pipeline. A reviewer opening this in 2026, or 2030, sees the exact same four caught tier mismatches and the exact same reference-date warning that were true the day this was built, because the system was told to be as-of 2024-06-30 and it will keep answering as of 2024-06-30 until someone deliberately runs it with a different config. Nothing about the architecture prevents running against today's date: `python validate_input.py --input <file> --config <config with as_of_date: today>` recomputes everything, lapsed status included, against whatever date is passed in. The committed demo simply was not re-run that way, because doing so would shift which donors count as lapsed and require recalibrating the fixture's own trap set against a new reference point, not a config change worth making just to look current.
