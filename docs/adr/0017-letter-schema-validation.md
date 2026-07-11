# ADR 0017: Letters are validated as structured data before rendering

Status: accepted. Date: 2026-07-11.

## Problem

The original skill emitted free-form HTML straight from the model, so there was no definition of a valid letter and no checkpoint between assembly and delivery. The first rebuild pass fixed the inputs but still rendered letters directly from computed values: correct today, but with no structural guarantee that a future change (a new campaign paragraph, a style profile, a model-written personalization) could not slip a second dollar amount, an empty salutation, or an unexpected field into a donor's letter.

## Decision

Every letter is assembled as a structured model and validated against `references/letter_schema.json` before any HTML is rendered. The schema requires every named part of a letter to be present and non-empty, permits exactly one dollar amount in the ask paragraph, requires an http(s) donation URL, and rejects unknown fields outright. A model that fails produces no letter; the manifest records the specific errors with a mandatory review flag. Valid models are written to `work/letter_models.jsonl` as the run's structured output artifact, and rendering becomes a final step with no judgment of its own.

## What this changes going forward

"Valid letter" is now a testable contract instead of a reviewer's impression, and every future contributor to letter content (config, style profile, model personalization, new campaign types) is checked against the same contract at the same gate. The JSONL artifact is also the future integration surface: a mail system, a CRM, or a print vendor consumes validated data, not scraped HTML.
