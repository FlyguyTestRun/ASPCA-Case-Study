# Structured Output: Schema First, Render Last

Covers problem 6 from the [design review index](README.md).

## Problem 6: free-form HTML with no schema

The original asks the model to emit finished HTML letters directly into chat. There is no schema, so there is no definition of what a valid letter even is, no way to check one before a donor sees it, and no way for production AI to know when it does not know. An uncertain system without a schema does not stop; it guesses with confidence, and free-form output is where those guesses hide.

**Verdict: valid, and this review drove the implementation.** The first rebuild pass validated inputs rigorously but still rendered letters directly from computed values. Structured output belongs on the way out, not just on the way in.

**The fix: validate first, then render.** Every letter is now assembled as a structured model (salutation, opening, campaign paragraph, ask paragraph, closing, signer fields) and validated against [letter_schema.json](../../skill/charity-donor-outreach/references/letter_schema.json) before any HTML exists:

- Required fields must be present and non-empty.
- The ask paragraph must contain exactly one dollar amount: the computed ask, no more, no fewer.
- The donation URL must be a real http(s) URL.
- Unknown fields are rejected outright, so nothing can ride along into a letter unnoticed.

A model that fails the schema produces no letter; the record lands in the manifest with the specific errors and a mandatory review flag. Valid models are written to `work/letter_models.jsonl` as the structured artifact of the run, and rendering ([generate_letters.py](../../skill/charity-donor-outreach/scripts/generate_letters.py)) becomes a dumb final step that does no thinking of its own. Decision record: [ADR 0017](../adr/0017-letter-schema-validation.md).

## What changes at scale

The letter model is the integration surface. When delivery moves to a real mail system, the mail system consumes validated JSON, not scraped HTML; when a model contributes personalization at scale, its output is validated against the same schema before it can touch a letter. Schema-constrained output is also what makes multi-channel delivery (email, print, CRM notes) a rendering concern instead of a redesign.
