# Charity Donor Outreach Skill: Assessment and Rewrite

Bryan Shaw, July 2026

Prepared in response to the case study brief: assess the `charity-donor-outreach` skill, describe improvements and their impact, and rewrite the skill. This document answers both parts directly; the full repository (rewritten skill, tests, run evidence, and a decision record for every change) is the working proof behind it.

## Summary

The skill reads as reasonable prose and fails at every layer that matters in production. It embeds its data instead of reading it, trusts labels its own data contradicts, asks a language model to do arithmetic, invents facts when data is missing, and instructs the assistant to make an untrue claim to donors. None of these failures announce themselves; each produces a confident, well-formatted, wrong letter.

The fix is one principle applied consistently: verify the data first, then let each tool do the job it is actually good at. Deterministic code owns validation, tier computation, ask arithmetic, and rendering. The model contributes only bounded, optional personalization, grounded in verified fields, off by default. Humans review by exception, with mandatory gates where the stakes are highest.

Run against the case study's own 50 donors: the pipeline catches four mislabeled tiers (one my own manual review of the table had missed), flags a reference-date trap, routes two lapsed major donors away from form letters, and generates 44 letters with a full audit trail. Nothing is ever sent automatically. 160 automated tests hold this behavior in place, re-run on every change by CI.

## Part 1: Improvements and their impact

**The original's defects, grouped by what they would have done in production.** Ten distinct defects, grouped below into seven themes where more than one shares a root cause; the [trap registry](../docs/trap-registry.md) itemizes them individually instead (thirteen rows tied to the original skill and data, since it also splits the four tier mismatches out by donor).

**Unsupported donor claims.** The skill instructs the assistant to tell every donor their gift is matched, "even if no match is confirmed, we can sort that out later." That is not a hallucination risk to mitigate; it is an unsupported fundraising claim written into the instructions, the kind that creates fraudulent-solicitation and state charity-registration exposure. *Fix:* matching language is gated behind a `match_confirmed` config flag with a required sponsor and terms, and every generated letter is scanned by the test suite. *Impact:* the claim only ever appears when the campaign configuration proves it; an unsupported claim is now a structural impossibility, not a training reminder.

**Gender and title inference.** Salutation rules guess a title from the first name "if it seems obvious." *Fix:* a title is used only when the file provides one; otherwise every donor gets a neutral salutation, tested for on every letter. *Impact:* no invented honorific ever reaches a donor.

**Silent ask errors at scale.** Two compounding defects: the donor database lives inside the instruction file instead of the CSV the skill's own step 1 says to read, and every stated field (tier, totals) is trusted without verification. The example data proves the cost: four donors' stated tiers contradict their own gift history. My own manual read of the table caught three; the validator caught all four on its first run. *Fix:* the skill holds zero data, operates only on a schema-validated input file, and recomputes tier, totals, and dates from the gift history on every run. A stated value that disagrees routes to an exceptions report with the exact discrepancy and a suggested correction. *Impact:* consistent, auditable asks instead of confident mistakes; nothing is trusted on faith.

**Calendar drift.** "Lapsed" and "gave last year" are date calculations with no defined reference point; the data's own internal clock is 2024, so running the skill on a different day silently changes who counts as lapsed. *Fix:* every run requires an explicit `as_of_date`, used everywhere a date matters. *Impact:* the same input and policy produce the same result no matter when the batch runs, and that result is testable.

**Inconsistent numbers.** A seven-step ask formula, executed by the model per donor, rounds mid-sequence and leaves "gave last year" undefined; a model is a poor calculator even when the formula is exact. *Fix:* one deterministic function, fixed operation order, one rounding step at the end, a full trace per calculation. *Impact:* identical input produces identical output, every time, with a trace a person can check.

**Fabricated data and people.** "Make reasonable assumptions and proceed" on missing fields, and an instruction to invent a "relationship manager name" for Platinum donors. *Fix:* missing or contradictory data fails loudly to an exceptions report; every letter is signed by a real person named in the campaign config, never invented. *Impact:* a run with a missing required field stops with a named error instead of improvising one.

**No scalable review path.** Output is HTML pasted into chat, with no review step, and the skill's trigger fires on any mention of money, email, or events. *Fix:* letters are files plus a review manifest with per-donor confidence and review level; Platinum letters and anything flagged are always reviewed by a person before anything ships, and the skill never sends anything itself. *Impact:* a larger batch becomes a longer review queue, not a longer chat transcript; the trigger now names the one job it does.

Full mapping from each defect to its fix, its test, and its decision record: [`docs/trap-registry.md`](../docs/trap-registry.md). Full mapping from named production-readiness controls (schema validation, audit logging, versioned business rules, and more) to their implementation: [`docs/requirements-checklist.md`](../docs/requirements-checklist.md).

## Part 2: The rewrite

`skill/charity-donor-outreach/` is a lean orchestrator over three deterministic stages, plus one optional, bounded, off-by-default step where a model may touch language:

1. **Validate** (`validate_input.py`): schema-check the file, recompute everything computable, verify every stated field, and stop for a human before anything else happens.
2. **Calculate** (`calculate_ask.py`): apply the ask policy from `references/policy.md` with a full audit trace and a confidence score.
3. **Generate** (`generate_letters.py`): assemble a structured letter object from approved language, validate it against a schema, and only then render it. A model may personalize within the guardrails in `prompts/personalization_prompt.md`, its own versioned file, only if a user explicitly asks; a letter is complete and correct with zero model calls.

**Why validate and calculate stay as two scripts, not one.** I considered merging them into a single check-and-compute step. I kept them separate because the correction loop depends on the split: when a person fixes a flagged tier, the fastest way to confirm the fix actually worked is to re-run validation alone, not the whole pipeline. Folding the two together would mean every correction check also recomputes every dollar amount, harmless computationally, but it muddies what was actually being checked. It also keeps the audit trail honest: a bad-data problem and a bad-math problem are different kinds of failure, and I wanted the two output files, `validated.csv` versus `computed.csv`, to say which one happened, not just that something happened. Three scripts for three genuinely different jobs, not three files doing one job.

**Why `SKILL.md` is this short.** `SKILL.md` is the file an agent actually reads at the moment it decides whether and how to act, and every line in it is competing for the same attention a well-written prompt is also trying to hold. I have seen skills written like documentation, explaining the reasoning behind every rule inline, and an agent pays the context cost of all of that on every single trigger, whether or not it needed the explanation that time. My rule for this file: if a line does not change what the agent does next, it does not belong here. The reasoning lives in the decision records, one link away, for a person who wants it. The agent gets the required inputs, the exact commands, the guardrails, and the five hard rules, nothing else. That is a prompt-engineering position as much as an architecture one: a good prompt earns its length, it does not default to it.

**Why the demo still runs as of June 30, 2024, not today.** The donor file's own internal clock is 2024 (one gift is dated within that year), so that is the reference point the data itself supports. If I advanced the campaign's `as_of_date` to today without also advancing two years of donor activity that was never collected, 28% of this list would flip to lapsed overnight, not because those donors actually stopped giving, but because a frozen fixture stopped updating while the calendar kept moving. That is not a finding worth showing anyone; it would be one I manufactured. Pointing `as_of_date` at today on a live donor file is exactly what a real run should do, it is a single config value; I only declined to dress up a fixed demo dataset to look more current than it honestly is.

Beyond the brief's two questions, four things the brief's own goals (consistent, reliable, scalable) required building:

- **A review interface** (`app/review_app.py`) so fundraising staff, not just engineers, can run and audit this system: upload or use a built-in sample, see every held record and warning in plain language, sign off individually on anything that matters, and archive a completed run before the next one overwrites it. Every stage names the exact script behind it, so the interface teaches as it operates.
- **A fix-and-resubmit loop**: the validator suggests the correct value wherever it is computable; a person approves, the file re-runs in one click.
- **A style feedback loop**: reviewer edits teach the system's voice, only after repeated evidence, only within hard guardrails, only on named adoption; it can change how a letter sounds, never what it claims or asks.
- **A decision-record system**: every architecture choice in this repository has a written record of the problem, the decision, and the forward impact, and the running system writes the same kind of record for itself as it operates (a correction approved, a style adopted, a batch signed off, each with a named approver). Together they are the audit trail, the validation record, and the learning loop for the system: not just what it did, but why, and evidence it is still doing it correctly as it changes.

The same rigor applied to the original skill was turned on the rewrite itself before submission, twice. A second-pass audit found and fixed two scale-triggered defects the first pass's own tests had not caught (a donor-name-derived ID could collide between two different donors; output was never cleared between runs, risking stale files). A full proofread across all four campaign types, not just the one committed run, found and fixed a letter telling a lapsed donor his support had been "steady," a factual claim his own record contradicts. Every one of these is now a permanent regression test, not a lesson learned once. [`docs/trap-registry.md`](../docs/trap-registry.md) records all of it, findings the rewrite introduced included.

## Part 3: Where production hardening goes from here

This exercise stops at the review manifest on purpose. The path forward, and the trigger condition for each step, is documented in [`docs/scale-architecture.md`](../docs/scale-architecture.md): a CRM connector replacing file upload, do-not-contact and consent checks at the validation boundary, a batch and approval workflow, evaluation over time as reviewer edits accumulate, and confidence-rubric recalibration once there is outcome data to recalibrate against. None of it is speculative scope; each is a documented extension point this architecture was built to accept without a redesign.

The through line: the durable asset is the donor data and the policy, not the model. This rebuild is arranged so the data gets cleaner every run, the policy is executable and versioned, and the model can be swapped or upgraded without touching either.
