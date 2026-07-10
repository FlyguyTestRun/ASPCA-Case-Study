# ADR 0006: Matching language only when a match is confirmed

Status: accepted. Date: 2026-07-10.

## Problem

The original emergency appeal instructions said to tell every donor their gift would be matched "even if no match is confirmed (we can sort that out later)." That is a false statement made to induce a donation: fraudulent solicitation exposure for the charity, registration risk with state regulators, and permanent trust damage if a single donor asks to see the match. This was the most serious defect in the skill, because it was not a bug, it was an instruction.

## Decision

Matching language is gated behind a match_confirmed boolean in the campaign config. When false, no letter mentions matching, and the test suite enforces it against every generated letter. When true, the config must also supply the sponsor and the exact terms, and only those flow into the letter. The same pattern gates every other unverifiable claim: event registration counts and re-engagement gifts are only mentioned when the config supplies them.

## What this changes going forward

Every factual claim in every letter traces to a confirmed source: a validated data field or an explicit config value. There is no path through the pipeline that fabricates an inducement. When a real match exists, adding two config fields turns the language on for exactly that campaign, with the terms stated correctly and identically in all letters.
