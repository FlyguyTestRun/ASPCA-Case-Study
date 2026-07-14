# Components Guide

Every moving part of this repository, explained twice: first in plain language for anyone, then an engineering note for reviewers. Paths are relative to the repository root.

To see these pieces working together against real data instead of reading about them in isolation, see [`docs/run-walkthrough.md`](run-walkthrough.md): a real run, stop by stop, with the actual command and output captured at every stage.

## The skill

### skill/charity-donor-outreach/SKILL.md

*Plain language:* the instruction sheet an AI assistant follows. It tells the assistant to run the scripts in order, stop and show a human every data problem before going further, and never guess, calculate, or send anything itself. Opens with a table naming every pipeline stage and marking which ones are deterministic code versus the one optional step that touches a model.

*Engineering note:* narrow trigger description; a pipeline overview table mapping each stage to its file and its determinism; six-step workflow (validate, stop and report, calculate, generate, bounded personalization, hand off); hard rules the assistant cannot cross. Kept small on purpose: policy detail lives in `references/`, the one model-facing prompt lives in `prompts/`, and both load only when needed (progressive disclosure); scripts are executed rather than read into context.

### references/donor.schema.json

*Plain language:* the checklist a donor row must pass before the system even starts thinking about their giving: right columns, right kinds of values.

*Engineering note:* structural JSON Schema for a raw donor row, checked by `validate_donor_row` at the top of the per-row loop in `validate_input.py`, before any business rule (tier computation, date logic) runs. Required fields, tier and volunteer enums, a gifts-field pattern. Additive to, not a replacement for, the business-rule checks that follow it.

### prompts/personalization_prompt.md

*Plain language:* the only page in this whole system that an AI model actually reads to do creative work, and the rules it has to follow while doing it.

*Engineering note:* the standalone, versioned prompt for SKILL.md step 5 (bounded personalization), extracted out of the orchestration file so the one model-facing prompt in this skill is reviewable and versionable on its own. Off by default; a letter is complete and correct with zero model calls.

### references/policy.md

*Plain language:* the rulebook. Tier definitions, how ask amounts are calculated, what each campaign is allowed to say, and who reviews what before anything is sent.

*Engineering note:* the single written source of truth for business rules. `scripts/donor_rules.py` is its only executable implementation; divergence between the two is defined as a defect. Includes the fail, report, pass confidence rubric and the escalation contract.

### references/input_schema.md

*Plain language:* what the donor file and campaign settings must contain, column by column, and what happens when something is missing (it gets flagged, never guessed).

*Engineering note:* donor CSV/XLSX column contract with validation behavior per column; campaign config JSON contract with conditional requirements (match fields when `match_confirmed`, event fields for event campaigns).

### references/letter_schema.json

*Plain language:* the checklist every letter must pass before it becomes a letter: all its parts present, exactly one ask amount, a real donation link.

*Engineering note:* letter-model schema enforced by `validate_letter_model` before rendering; unknown fields rejected; exactly one dollar amount permitted in the ask paragraph. Failing models produce a manifest entry and no letter.

## The pipeline scripts (skill/charity-donor-outreach/scripts/)

### donor_rules.py

*Plain language:* the policy rulebook translated into code, in one place, so every other tool uses identical rules.

*Engineering note:* shared module: gift parsing, tier and lapsed computation, deterministic ask calculation with audit trace, confidence scoring and bands, review levels, style-profile guardrails, CSV injection neutralization (`csv_safe`), letter-model validation, and run-metrics recording. No I/O beyond metrics; fully unit-tested.

### validate_input.py

*Plain language:* the first checkpoint. It reads the donor file, recalculates everything from the actual gift history, and sorts records into "passed" and "needs a human," each problem explained with a suggested fix.

*Engineering note:* CSV/XLSX ingestion; recomputes tier, largest gift, lifetime total, last gift year; cross-checks stated fields; date checks against config `as_of_date`; duplicate detection; graduated severity (errors exclude, warnings flag). Outputs `work/validated.csv`, `work/exceptions.csv`, `work/corrections.csv`, `work/validation_report.json`. Exit 2 on config or file errors, 0 otherwise.

### apply_corrections.py

*Plain language:* applies the fixes a person approved and writes a corrected copy of the donor file, listing every change it made so the same fix can be made in the donor database. The approval can be recorded, with a name, in the decision history.

*Engineering note:* consumes `corrections.csv`, applies approved rows (all, or `--rows` subset) to the input CSV by row number and field, prints an audit line per change; `--decision-log` plus `--approved-by` writes an ADR-style entry recording the batch. The resubmit half of the validation feedback loop.

### calculate_ask.py

*Plain language:* works out each donor's suggested gift amount using the rulebook, shows its arithmetic step by step, scores its own confidence, and raises a hand (an escalation) for anything a person should look at.

*Engineering note:* deterministic ask policy with per-record trace; confidence score and fail/report/pass band; fail band blocks the record; emits `work/computed.csv`, `work/escalations.jsonl`, and stage metrics. `ESCALATION_WEBHOOK_URL` optionally posts each event; default is log-only, no network.

### generate_letters.py

*Plain language:* builds each letter as structured data, checks it against the letter checklist, and only then turns it into an HTML draft, together with a review list showing who needs to look at what.

*Engineering note:* letter model per donor, schema validation before render, approved campaign language plus config-gated additions, sanitized style profile applied (closing, P.S. only), HTML-escaped rendering, `output/letters/*.html`, `output/manifest.csv`, `work/letter_models.jsonl`, stage metrics. Lapsed major donors and schema failures produce manifest rows with no letter.

### learn_style.py

*Plain language:* learns how your team likes letters to sound by comparing your edited copies against the drafts, and suggests a change only after seeing it several times. A named person has to approve before anything changes.

*Engineering note:* diffs original/edited letter pairs; extracts closing-phrase and P.S. changes only; 3-identical-edits evidence threshold; guardrails ban digits, currency, HTML, urgency and matching vocabulary; two-step CLI (learn, then `--adopt` with `--approved-by`); body-text edits reported, never learned. Generation re-sanitizes the profile on every run.

## The interfaces

### app/review_app.py

*Plain language:* the website version of all of the above for fundraising staff, as a guided four-step path: upload the file, work through every finding in plain words (approving fixes as you go), review letters one donor at a time with search and a full table, then sign off. Export unlocks only after every required review is checked, and the sign-off is recorded with your name. It never sends email and never changes your original file.

*Engineering note:* Streamlit; zero business logic; shells out to the same scripts in a temp dir per run. Staged flow (upload, findings, review, finalize) with a review gate: mandatory-review records must be individually signed off before export. Persistent actions (correction batches, style adoptions, sign-offs) write entries to docs/decision-log/ and require an operator name. Per-donor detail shows the letter preview and the full ask-calculation trace. Tutorial mode and narrated audio walkthrough as toggles; 5 MB upload cap; run log and metrics in a footer expander.

### app/assets/

*Plain language:* the audio tour and its written transcript.

*Engineering note:* `tutorial_walkthrough.wav` is generated offline from `tutorial_transcript.md` via Windows speech synthesis; the regeneration recipe is in `app/assets/README.md`. The transcript is the source of truth.

## The evidence

### assets/sample_donors.csv and assets/campaign_config.example.json

*Plain language:* the practice donor file (with the original exercise's planted mistakes kept on purpose) and a filled-in example of the campaign settings.

*Engineering note:* the fixture is the permanent regression dataset; the config demonstrates the honest defaults (`match_confirmed: false`, explicit `as_of_date` matching the data's internal 2024 clock).

### tests/ and .github/workflows/ci.yml

*Plain language:* 154 automatic checks that re-run on every change, including proof that every planted mistake is still caught and that no letter can make an unconfirmed claim.

*Engineering note:* unit tests over the rules module (hand-calculated expectations), end-to-end pipeline tests over the fixture, corrections round-trip, style guardrails, schema rejection, formula-injection, escalation coverage. CI runs the suite plus the pipeline and asserts the trap catches, then uploads run evidence as artifacts.

### output/

*Plain language:* the results of a real run, kept in the repository as proof: the review list and all 44 drafted letters.

*Engineering note:* committed run artifacts from the fixture at `as_of_date` 2024-06-30. Working files (`work/`) are gitignored; run them yourself with the three commands in the [README](../README.md).

### docs/

*Plain language:* the paper trail: the design review of the original skill, one decision record per correction, the trap catalog, this guide, the plan for growing the system, and the running system's own decision history.

*Engineering note:* [design-review/](design-review/README.md) (validity-checked problem analysis), [adr/](adr/) (the decision-record audit trail: one per architecture choice, the problem, the decision, the forward impact), [decision-log/](decision-log/) (the same kind of record, written by the running system for itself: corrections, style adoptions, sign-offs), [trap-registry.md](trap-registry.md), [scale-architecture.md](scale-architecture.md), and [HOURS.md](../HOURS.md) at the root for the engagement time log.
