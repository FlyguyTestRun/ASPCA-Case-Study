# ADR 0004: Every date calculation runs against an explicit as_of_date

Status: accepted. Date: 2026-07-10.

## Problem

Lapsed status ("no gift in over 3 years") and the loyalty uplift ("gave last year") are date calculations, but the original skill never said relative to what. The wall clock is the wrong answer: the example data's internal clock is clearly 2024 (one donor, Susan Nakamura, has a 2024 gift), so a run today would silently classify most of the file as lapsed. Whatever date the model assumed would change from run to run and would never be visible to anyone reviewing the output.

## Decision

The campaign config requires an explicit as_of_date, and every date rule in the pipeline uses it: lapsed status, loyalty eligibility, and future-gift detection. Gifts dated after the as_of year are errors. A gift dated within the as_of year is legal but attaches a warning, because it is exactly the situation where an ambiguous reference date changes the outcome.

## What this changes going forward

Runs are reproducible regardless of when they execute, which also makes them testable: the test suite pins as_of_date and asserts exact results. The Susan Nakamura record, a trap under the original design, now surfaces as a visible warning with a confidence deduction instead of silently flipping her loyalty uplift depending on the day the batch runs.
