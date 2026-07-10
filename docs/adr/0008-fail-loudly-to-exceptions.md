# ADR 0008: Fail loudly to an exceptions report, never assume

Status: accepted. Date: 2026-07-10.

## Problem

The original skill's final instruction was "if the donor file has missing fields, make reasonable assumptions and proceed." At scale that means invented giving histories, guessed tiers, and letters thanking donors for gifts they never made, with no record that anything was assumed. A wrong letter to one donor is an apology; a policy of assuming across a growing donor list is a systemic incident nobody can even enumerate afterward.

## Decision

Missing or contradictory required data sends the row to work/exceptions.csv with the row number, the donor, the specific error, and a disposition. Excepted rows never generate letters. The pipeline distinguishes errors (row excluded) from warnings (letter generated, flagged for review, confidence reduced), so severity is graduated rather than binary. Nothing is ever silently defaulted except documented, safe cases (blank volunteer means No).

## What this changes going forward

Data problems become a work queue instead of invisible letter defects. The exceptions report tells the operations team exactly what to fix upstream, and the run summary reports counts so a batch with 4 exceptions out of 50 is understood at a glance. "No fabrication" also becomes testable: the suite feeds broken files and asserts the rows land in exceptions with empty validated output.
