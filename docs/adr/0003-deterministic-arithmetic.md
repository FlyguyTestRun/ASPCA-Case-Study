# ADR 0003: All arithmetic in code, rounding exactly once

Status: accepted. Date: 2026-07-10.

## Problem

The original skill asked the language model to run a seven-step ask calculation per donor: percentage of largest gift, round to the nearest $50, then apply a loyalty uplift, a volunteer bonus, and an emergency multiplier after rounding. Language models are unreliable at arithmetic, and the formula itself was defective: rounding mid-sequence makes the result path dependent, and the loyalty condition "gave last year" was undefined. Fifty donors would get fifty subtly inconsistent calculations, unreproducible across runs.

## Decision

calculate_ask.py performs the entire calculation deterministically. The order is fixed (base, loyalty, volunteer, emergency) and rounding happens exactly once at the end, half rounding up, with a $50 floor. "Gave last year" is defined precisely as last_gift_year == as_of_year - 1. Every calculation emits a step-by-step trace stored with the record. A guardrail flags any percentage-based ask that exceeds the donor's largest single gift.

## What this changes going forward

The same file and config produce the same asks, every run, forever. Any ask amount can be audited back to the rule that produced it via the trace column. Policy changes are code changes to one module (donor_rules.py) with tests, not a prompt edit with unknowable blast radius. The model's job narrows to what it is actually good at, which is language.
