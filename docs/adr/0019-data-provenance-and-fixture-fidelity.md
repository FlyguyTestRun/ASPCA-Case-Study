# ADR 0019: Data provenance is audited and fixture fidelity is enforced

Status: accepted. Date: 2026-07-11.

## Problem

The rebuilt system's credibility rests on one claim: the test fixture is a verbatim copy of the original skill's embedded donor table, planted errors included. Nothing enforced that claim. A well-meaning edit could "fix" Ruth Andersen's tier in the fixture and every trap-catching demonstration would quietly become a rigged one. There was also no audited answer to the provenance question: what data actually arrived with this exercise?

## Decision

Provenance first: the case-study zip contained exactly two files, the original SKILL.md and a macOS .DS_Store (Finder folder metadata containing no data). The 50-donor table inside SKILL.md is therefore the sole data source, and it is preserved unmodified in original/.

Fidelity second: a dedicated test suite (tests/test_fixture_fidelity.py) parses the donor table out of the original markdown and compares it to assets/sample_donors.csv field by field, all 50 donors, all 8 columns. It additionally asserts that the planted errors are preserved, not sanitized: the four mislabeled tiers, the 2024 reference-date gift, and the lapsed-by-date Platinum donors must stay exactly as the consultant filed them, or the build fails.

## What the audit found

The suite also audits the original table against itself, and the result sharpens the analysis: every stated largest gift, lifetime total, and last gift year in the original is arithmetically consistent with its own gift list. The planted defects are categorical (tier labels that contradict the giving) and temporal (dates with no reference point), not arithmetic. That is worth knowing because it says where validation effort pays off in real donor files: cross-field consistency and date logic catch what column-level arithmetic checks cannot, and a system that only re-adds the numbers would have passed this file while sending four donors the wrong ask.

## What this changes going forward

Transcription fidelity is a CI-enforced invariant instead of a promise, so the demonstration can never drift from the source it claims to demonstrate. The provenance record also closes the audit trail end to end: source file, verbatim preservation, transcribed fixture, enforced equivalence, and the pipeline's findings on top, every link testable.
