# Charity Donor Outreach Skill: Assessment and Rewrite

Bryan Shaw, July 2026

Prepared in response to the case study brief: assess the `charity-donor-outreach` skill, describe improvements and their impact, and rewrite the skill. This document answers both parts directly; the full repository (rewritten skill, tests, run evidence, and a decision record for every change) is the working proof behind it.

## Summary

The original skill reads as reasonable prose, but it has the failure modes that matter in production: embedded data, trusted-but-contradictory labels, model-run arithmetic, invented facts when data is missing, and an instruction to make an unsupported claim to donors. None of these failures announces itself; each can produce a confident, well-formatted, wrong letter.

The fix is one principle applied consistently: verify the data first, then let each tool do the job it is actually good at. Deterministic code owns validation, tier computation, ask arithmetic, and rendering. The model contributes only bounded, optional personalization, grounded in verified fields and off by default. Humans review by exception, with mandatory gates where the stakes are highest.

Run against the case study's own 50 donors: the pipeline catches four mislabeled tiers (one my own manual review of the table had missed), flags a reference-date trap, routes two lapsed major donors away from form letters, and generates 44 letters with a full audit trail. Nothing is ever sent automatically. 140 automated tests hold this behavior in place, re-run on every change by CI.

## Part 1: Improvements and their impact

The brief asks for consistent, reliable, and scalable donor outreach. The original prompt puts all three at risk; the rewrite addresses each risk with a control that can be tested.

**Unsupported donor claims.** The skill instructs the assistant to tell every donor their gift is matched, "even if no match is confirmed, we can sort that out later." That is not a hallucination risk to mitigate; it is an unsupported fundraising claim written into the instructions. *Fix:* matching language is gated behind a `match_confirmed` config flag with a required sponsor and terms, and every generated letter is scanned by the test suite. The impact is compliance-ready reliability: a claim appears only when the campaign configuration proves it.

**Gender and title inference.** Salutation rules guess a title from the first name "if it seems obvious." *Fix:* a title is used only when the file provides one; otherwise every donor gets a neutral salutation, tested for on every letter. The impact is more respectful personalization and less reputational risk.

**Silent ask errors at scale.** Two compounding defects: the donor database lives inside the instruction file instead of the CSV the skill's own step 1 says to read, and every stated field (tier, totals) is trusted without verification. The example data proves the cost: four donors' stated tiers contradict their own gift history. My own manual read of the table caught three; the validator caught all four on its first run. *Fix:* the skill holds zero data, operates only on a schema-validated input file, and recomputes tier, totals, and dates from the gift history on every run. A stated value that disagrees routes to an exceptions report with the exact discrepancy and a suggested correction. The impact is consistent, auditable asks instead of confident mistakes.

**Calendar drift.** "Lapsed" and "gave last year" are date calculations with no defined reference point; the data's own internal clock is 2024, so running the skill on a different day silently changes who counts as lapsed. *Fix:* every run requires an explicit `as_of_date`, used everywhere a date matters. The impact is reproducibility: the same input and policy produce the same result whenever the batch runs.

**Inconsistent numbers.** A multi-step ask formula, executed by the model per donor, leaves too much room for rounding and ordering drift. *Fix:* one deterministic function, fixed operation order, one rounding step at the end, and a full trace per calculation. The impact is reliability: identical input produces identical output every time.

**Fabricated data and people.** "Make reasonable assumptions and proceed" on missing fields, and an instruction to invent a "relationship manager name" for Platinum donors. *Fix:* missing or contradictory data fails loudly to an exceptions report; every letter is signed by a real person named in the campaign config, never invented. The impact is operational trust: a run with missing required data stops with a named error instead of improvising.

**No scalable review path.** Output is HTML pasted into chat, with no review step, and the skill's trigger fires on any mention of money, email, or events. *Fix:* letters are files plus a review manifest with per-donor confidence and review level; Platinum letters and anything flagged are always reviewed by a person before anything ships, and the skill never sends anything itself. The impact is scale with control: larger batches become review queues, not longer chat transcripts.

Full mapping from each defect to its fix, its test, and its decision record: [`docs/trap-registry.md`](../docs/trap-registry.md). Full mapping from named production-readiness controls (schema validation, audit logging, versioned business rules, and more) to their implementation: [`docs/requirements-checklist.md`](../docs/requirements-checklist.md).

## Part 2: The rewrite

`skill/charity-donor-outreach/` is a lean orchestrator over three deterministic stages, plus one optional, bounded, off-by-default step where a model may touch language:

1. **Validate** (`validate_input.py`): schema-check the file, recompute everything computable, verify every stated field, and stop for a human before anything else happens.
2. **Calculate** (`calculate_ask.py`): apply the ask policy from `references/policy.md` with a full audit trace and a confidence score.
3. **Generate** (`generate_letters.py`): assemble a structured letter object from approved language, validate it against a schema, and only then render it. A model may personalize within the guardrails in `prompts/personalization_prompt.md`, its own versioned file, only if a user explicitly asks; a letter is complete and correct with zero model calls.

`SKILL.md` is short because policy lives in `references/`, mechanics live in `scripts/`, and the one model-facing prompt lives in `prompts/`, each independently reviewable and versionable. The model's remaining job is judgment inside guardrails, which is what it is actually suited for.

Beyond the brief's two questions, the repo includes four pieces of implementation evidence. These are not required infrastructure for every deployment; they prove the architecture can support the consistent, reliable, scalable workflow the brief asks for:

- **A review interface** (`app/review_app.py`) and standalone HTML deliverable so fundraising staff, not just engineers, can review the supplied data, upload a replacement file in the same shape, apply approved corrections, inspect generated letters, and export a cleaned batch for the next pipeline run or source-system merge.
- **A fix-and-resubmit loop**: the validator suggests the correct value wherever it is computable; a person approves, the file re-runs in one click.
- **A style feedback loop**: reviewer edits can tune the system's voice only after repeated evidence and named approval; it can change how a letter sounds, never what it claims or asks.
- **Architecture Decision Records and an operational decision log**: the design choices and persistent approvals are traceable without turning the case study into a heavier production platform than it needs to be today.

The same rigor applied to the original skill was turned on the rewrite itself before submission, twice. A second-pass audit found and fixed two scale-triggered defects the first pass's own tests had not caught (a donor-name-derived ID could collide between two different donors; output was never cleared between runs, risking stale files). A full proofread across all four campaign types, not just the one committed run, found and fixed a letter telling a lapsed donor his support had been "steady," a factual claim his own record contradicts. Every one of these is now a permanent regression test, not a lesson learned once. [`docs/trap-registry.md`](../docs/trap-registry.md) records all of it, findings the rewrite introduced included.

## Part 3: Where production hardening goes from here

This exercise stops at the review manifest on purpose. The path forward, and the trigger condition for each step, is documented in [`docs/scale-architecture.md`](../docs/scale-architecture.md): a CRM connector replacing file upload, do-not-contact and consent checks at the validation boundary, a batch and approval workflow, evaluation over time as reviewer edits accumulate, and confidence-rubric recalibration once there is outcome data to recalibrate against. Those are documented extension points, not scope I would build before the operating need exists.

The through line: the durable asset is the donor data and the policy, not the model. This rebuild is arranged so the data gets cleaner every run, the policy is executable and versioned, and the model can be swapped or upgraded without touching either.
