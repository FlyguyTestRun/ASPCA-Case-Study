# Charity Donor Outreach Skill: Assessment and Rewrite

Bryan Shaw, July 2026

Prepared in response to the PDS case study: assess the `charity-donor-outreach` skill, describe improvements and their impact, and rewrite the skill. The rewritten skill, its tests, run evidence, and a decision record for every change live in the accompanying repository; this document is the narrative.

## Summary

The skill looks reasonable at a glance and fails in every way that matters at scale. It embeds its data instead of reading it, trusts labels its own data contradicts, asks a language model to do arithmetic, invents facts when data is missing, and instructs the assistant to make an untrue claim to donors. None of these failures announce themselves; each one produces confident, well-formatted, wrong letters.

The rewrite is built on one principle: verify the data first, then let each tool do the job it is good at. Deterministic scripts now handle validation, tier computation, ask arithmetic, and rendering. The language model contributes only bounded personalization, grounded in verified fields. Humans review by exception through a manifest, with mandatory gates where the stakes are highest. Run against the case study's own 50 donors, the pipeline catches four mislabeled tiers (one of which my own manual review of the table had missed), flags the reference-date trap, routes two lapsed major donors away from form letters, and generates 44 letters with a full audit trail. Nothing is ever sent automatically.

## Part 1: Findings and impact

### Integrity failures (would have put the charity at risk)

**1. Instructed dishonesty about gift matching.** The Emergency Appeal instructions tell the assistant to say the donor's gift "will be matched (even if no match is confirmed, we can sort that out later)." That is a false statement made to induce a donation: fraudulent solicitation exposure, state charity-registration risk, and a permanent donor-trust loss the first time anyone asks to see the match. This was the most serious finding because it is not a bug; it is a policy, written down.

*Fix and impact:* matching language is gated behind a `match_confirmed` flag in the campaign config, which also requires the sponsor and terms. The test suite scans every generated letter and fails the build if match language appears without confirmation. A false claim went from instructed to structurally impossible.

**2. Guessing gender from first names.** The salutation rules say to guess a title if it "seems obvious" ("Elizabeth is probably Ms."). This misgenders real people, fails across cultures, and does it in the opening line of a request for money.

*Fix and impact:* titles are used only when the donor record provides one; otherwise every donor gets a neutral "Dear First Last." Tested: no generated letter may contain an honorific the file did not supply. Zero misgendered donors, mechanically guaranteed.

### Data trust failures (wrong letters at scale)

**3. Donor data embedded in the instructions.** Fifty donors' full giving histories sit inside the skill file, while step 1 of the same skill says to read an uploaded CSV. Two conflicting sources of truth; stale the day it was written; PII pushed into model context on every run; a hard ceiling on scale.

*Fix and impact:* the skill holds zero data and operates only on the provided file, validated against a published schema. Fifty donors or fifty thousand process identically.

**4. Stated fields trusted on faith.** The example data contains four donors whose stated tier contradicts their own gift history: Ruth Andersen (Silver at $25,000 lifetime), Ada Yamamoto-Pierce (Silver at $17,000), Shirley Magnusdottir (Silver at $22,000), and Arthur Mwangi (Bronze at $2,600). The original skill would have used the labels and sent each of them the wrong ask. Worth noting: when I first reviewed the table by hand I caught three of the four. The validator caught all four on its first run. That difference is the whole argument for computed verification.

*Fix and impact:* the gift history is the single source of truth. Tier, largest gift, lifetime total, and last gift year are recomputed on every run; any stated value that disagrees sends the record to an exceptions report with the exact discrepancy, and no letter is generated until a person resolves it. Bad labels became a work queue instead of wrong asks.

**5. Date logic with no reference date.** "Lapsed" and "gave last year" are date calculations, but relative to what? The data's internal clock is 2024 (one donor has a 2024 gift); run the original skill today and most of the file silently turns lapsed.

*Fix and impact:* every run requires an explicit `as_of_date` in the campaign config, and all date rules use it. Future-dated gifts are errors; a gift inside the as-of year attaches a warning. Runs are now reproducible on any day, which is also what makes them testable.

### Consistency failures (same input, different answers)

**6. Arithmetic performed by the language model.** A seven-step formula (percentage, round to the nearest $50, then a loyalty uplift, a volunteer bonus, an emergency multiplier) executed in-model, per donor. Models are unreliable calculators, and the formula itself rounds mid-sequence, so even a perfect calculator produces path-dependent amounts. Undefined terms ("gave last year") add a second layer of drift.

*Fix and impact:* all arithmetic moved to a deterministic script with a fixed order and exactly one rounding step at the end, half rounding up, with a $50 floor. Every ask carries a step-by-step trace, so any amount can be audited back to policy. Identical input produces identical asks, every run.

### Reliability failures (silent, cumulative damage)

**7. "Make reasonable assumptions and proceed."** The original's instruction for missing fields. At scale this is invented giving histories and letters thanking donors for gifts they never made, with no record anything was assumed.

*Fix and impact:* missing or contradictory data fails loudly to `exceptions.csv` with the row, the field, and the reason. Errors exclude the row; warnings generate the letter but flag it for review and reduce its confidence score. Nothing is fabricated anywhere in the pipeline.

**8. Invented people and unsourced placeholders.** Platinum letters were signed by a "relationship manager name" the model was told to assign, meaning a made-up employee in letters to the charity's largest donors. The template also shipped placeholders (charity name, donation URL) with no defined source.

*Fix and impact:* a required campaign config supplies every run parameter, including the real human who signs the letters. Missing config stops the run with named errors instead of improvisation.

### Scale and operability failures

**9. Output pasted into chat, no review step.** Unusable at 50 donors, and structurally it means nobody reviews anything.

*Fix and impact:* letters are files, one per donor, plus a review manifest listing every donor's tier, ask, confidence score, warnings, and review level. Review is policy: all Platinum letters are individually reviewed; any warning means review; lapsed Gold and Platinum donors get no automated letter at all and are routed to personal outreach. The skill sends nothing, ever.

**10. A trigger that fires on everything.** The skill activates on any mention of money, emails, letters, events, reports, or grants, which guarantees collisions in any real skill library.

*Fix and impact:* the description now states the one job, the required inputs, and the explicit non-triggers.

## Part 2: The rewrite

The rewritten skill is a folder with a lean instruction file and three deterministic stages, and it is in the repository at `skill/charity-donor-outreach/`:

1. **Validate** (`validate_input.py`): parse the donor file (CSV or Excel), recompute everything computable, verify every stated field, split the file into validated rows and an exceptions report, and stop for a human look before anything else happens.
2. **Calculate** (`calculate_ask.py`): apply the ask policy from `references/policy.md` with a per-donor audit trace and a confidence score that maps to a review level.
3. **Generate** (`generate_letters.py`): render letters from an approved message library into files, plus the review manifest. Language beyond the library is bounded: the model may personalize using verified fields only, may not introduce numbers or claims, and may not touch the ask.

The instruction file (`SKILL.md`) is now short because the policy lives in `references/` and the mechanics live in `scripts/`. The model's remaining job is judgment inside guardrails, which is the job it is actually suited for.

Proof it works, using the case study's own data as the fixture: 50 rows in, 46 validated, 4 held in exceptions (the four mislabeled tiers, each with the exact discrepancy stated), 1 reference-date warning (Susan Nakamura's 2024 gift), 2 lapsed Platinum donors routed to personal outreach instead of form letters, 44 letters generated with zero unconfirmed claims and zero guessed titles. 107 automated tests pin all of this behavior, and a CI workflow re-runs the planted traps on every change so the guardrails cannot silently regress. A completed run is committed in `output/` as evidence.

Four additions go beyond the brief because the brief's goals (consistent, reliable, scalable) require them:

- **A review interface** (`app/review_app.py`): fundraising staff upload a donor file, set the campaign, and see every held-back record, warning, confidence score, and calculation trace in plain language, with letter previews and downloads. A tutorial mode and a narrated audio walkthrough are built in and toggleable, because the skill's end users are non-technical and tooling should teach, not gatekeep. The interface is a thin shell over the same scripts, so it can never disagree with the automation.
- **A fix-and-resubmit loop**: wherever the correct value is computable from the donor's own gift history, the validator emits a suggested correction. A person approves each fix individually, the corrected file re-runs in one click, and a copy is downloadable so the same fix lands in the source system. On the sample data, approving the four suggestions takes the run from 4 exceptions to a clean 50 of 50.
- **A style feedback loop**: reviewers' edited letters teach the system their voice, within hard limits. A change is suggested only after it appears identically in 3 or more edits, only for personality-level items (closing phrase, P.S. line), only if it passes guardrails that ban numbers, amounts, urgency, and matching language, and it activates only when a named person adopts it. Style can change how a letter sounds, never what it claims or asks, and the tests pin that property.
- **Architecture Decision Records** (`docs/adr/`): one per correction, each stating the problem, the decision, and what it changes going forward, plus a trap registry (`docs/trap-registry.md`) mapping every planted defect to the mechanism that catches it and the test that proves it. Every choice here can be audited, challenged, or reversed deliberately.

The same discipline applied to the original skill was turned on the rewrite itself before submission. A second-pass audit found two latent defects that the first pass's own tests had not caught: `donor_id`, derived from the donor's name, could collide between two different donors and let one letter silently overwrite another's, and the letters folder was never cleared between runs, so a donor dropped from a later run could leave a stale file behind with no manifest row pointing to it. Both are the same class of silent, scale-triggered failure this whole rewrite exists to eliminate, just one layer further down. Both are fixed, with regression tests, in [ADR 0022](../docs/adr/0022-donor-id-collisions-and-stale-output.md). A letter-quality proofread pass across all four campaign types, not just the committed `emergency_appeal` run, then found that the annual fund paragraph told a donor lapsed five years his support had been "steady," a factual claim his own record contradicts, in the same spirit as the tier and date traps this document catches in the original data. Fixed in [ADR 0023](../docs/adr/0023-lapsed-donor-messaging-cannot-claim-current-giving.md), with the general rule now stated in `references/policy.md`: no campaign paragraph may describe a lapsed donor's giving as current.

## Part 3: What production hardening looks like from here

This exercise stops at the review manifest on purpose, but the path to production is visible from the architecture:

- **CRM as the source of truth.** Replace file upload with a connector to the donor CRM, keyed on donor IDs rather than names, with the same validation applied at the boundary. The exceptions report becomes a feedback loop that improves the CRM rather than a standalone artifact.
- **Suppression and consent.** A production system needs do-not-contact, deceased-donor, and solicitation-consent checks as a validation stage. The current design contains none of this data but its exception mechanism is exactly where those checks plug in.
- **Batch and approval workflow.** Queue runs, route the manifest to reviewers with sign-off tracking, and release approved letters to the mail system only after the gates clear.
- **Evaluation over time.** The confidence scores and review outcomes are the seed of an evaluation set: compare reviewer edits against generated drafts to measure letter quality, recalibrate the scoring penalties with evidence, and add a regression suite for tone the same way this repo already regression-tests the data guardrails.
- **Observability and cost.** Per-run structured logs already exist (`validation_report.json`); production adds run dashboards, alerting on exception-rate spikes (an early-warning signal of upstream data drift), and per-campaign cost attribution.

The through line: the durable asset is the donor data and the policy, not the model. Everything in this rebuild is arranged so the data gets cleaner every run, the policy is executable and versioned, and the model can be swapped or upgraded without touching either.
