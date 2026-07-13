# Production-Readiness Requirements Checklist

The original skill was missing every control an enterprise AI system needs before it can be trusted with donor data and donor money. This page states each one, in the exact terms a reviewer would look for, with a direct pointer to where it lives and the test that proves it. Nothing here is aspirational; every link is to working code, a passing test, or a decision record in this repository.

## Schema validation

Two schemas, checked at two different boundaries. [`references/donor.schema.json`](../skill/charity-donor-outreach/references/donor.schema.json) is the structural contract a raw donor row must satisfy before any business rule runs, enforced by [`validate_donor_row`](../skill/charity-donor-outreach/scripts/donor_rules.py) and called first in [`validate_input.py`](../skill/charity-donor-outreach/scripts/validate_input.py). [`references/letter_schema.json`](../skill/charity-donor-outreach/references/letter_schema.json) is the contract a generated letter must satisfy before it is rendered to HTML, enforced by `validate_letter_model` and called in [`generate_letters.py`](../skill/charity-donor-outreach/scripts/generate_letters.py). Design records: [ADR 0024](adr/0024-donor-schema-validation-layer.md), [ADR 0017](adr/0017-letter-schema-validation.md). Proof: `tests/test_pipeline.py::test_malformed_tier_label_caught_by_schema_before_business_rules`, `test_gifts_field_not_matching_expected_shape_caught_by_schema`, `tests/test_rules.py::TestLetterSchema`.

## Required field validation

`references/donor.schema.json` and `references/input_schema.md` both name required fields (`donor_name`, `gifts` for a donor row; `campaign_type`, `as_of_date`, `charity_name`, `donation_url`, `signer_name`, `signer_title`, `match_confirmed` for campaign config). A missing required field stops the run (config) or holds the row (donor data), always with the specific field named. Proof: `tests/test_pipeline.py::test_missing_required_fields_fail_loudly`, `test_missing_config_field_stops_the_run` (parametrized across all five required config fields).

## Input sanitization

Every CSV this pipeline writes neutralizes spreadsheet formula injection (`csv_safe` in [`donor_rules.py`](../skill/charity-donor-outreach/scripts/donor_rules.py)): a donor named `=HYPERLINK(...)` arrives inert in Excel. Every letter HTML-escapes all donor-derived text at render time. Uploads in the review interfaces are capped at 5 MB. Design record: [ADR 0018](adr/0018-security-boundaries.md). Proof: `tests/test_pipeline.py::test_formula_injection_arrives_inert`.

## Failure handling

Nothing is ever assumed or fabricated. Missing or contradictory data fails loudly to `work/exceptions.csv` with a specific, actionable reason and a suggested correction a human can approve; a bad campaign config stops the run entirely with named errors. Graduated severity distinguishes a hard failure (row excluded) from a warning (letter generated, flagged, confidence reduced). Design record: [ADR 0008](adr/0008-fail-loudly-to-exceptions.md). Proof: `tests/test_pipeline.py::test_missing_required_fields_fail_loudly`, `test_unknown_campaign_type_stops_the_run`, `test_match_confirmed_requires_sponsor_and_terms`.

## Audit logging

Every run writes `work/validation_report.json` (named exceptions and warnings), `work/run_metrics.json` (per-stage timing and counts), and `work/escalations.jsonl` (one structured event per record held or blocked, webhook-ready). Every persistent operational decision, an applied correction, an adopted style preference, a review sign-off, writes a numbered, human-readable entry to [`docs/decision-log/`](decision-log/), the running system's own audit history, with a named approver. Design records: [ADR 0011](adr/0011-confidence-scoring-feedback-loop.md), [ADR 0020](adr/0020-operational-decision-log.md). Proof: `tests/test_pipeline.py::test_escalation_events_cover_every_held_record`, `test_run_metrics_record_all_three_stages`, `tests/test_corrections_and_style.py::TestDecisionLog`.

## Structured JSON between processing stages

A donor exists as a structured JSON object, not only a CSV row, at every stage boundary: `validated.jsonl` after validation, `computed.jsonl` after ask calculation, `letter_models.jsonl` after letter assembly, one line, one JSON object, per donor. CSV remains alongside every one of these as the working format fundraising staff open directly in Excel; this is additive, not a replacement. Design record: [ADR 0026](adr/0026-versioned-rules-and-structured-json-stages.md). Proof: `tests/test_pipeline.py::test_structured_json_mirrors_the_csv_at_every_stage`.

## Separation of prompt, data, and business logic

Four kinds of content, four separate places. Business logic: [`references/policy.md`](../skill/charity-donor-outreach/references/policy.md) (the specification) and [`donor_rules.py`](../skill/charity-donor-outreach/scripts/donor_rules.py) (its one implementation). Data: [`assets/`](../skill/charity-donor-outreach/assets/), never embedded in an instruction file ([ADR 0001](adr/0001-separate-data-from-instructions.md)). Orchestration: [`SKILL.md`](../skill/charity-donor-outreach/SKILL.md), sequencing only. Prompt: [`prompts/personalization_prompt.md`](../skill/charity-donor-outreach/prompts/personalization_prompt.md), the one piece of content a model actually reads, versioned independently. Design record: [ADR 0025](adr/0025-prompt-extracted-into-its-own-versioned-asset.md).

## Elimination of hallucination-prone calculations

No arithmetic runs inside a model, anywhere. Tier assignment, ask calculation (fixed order, one rounding step at the end), lapsed-status dates, and confidence scoring are deterministic code with a full audit trace per calculation. Design record: [ADR 0003](adr/0003-deterministic-arithmetic.md). Proof: `tests/test_rules.py::TestComputeAsk` (every expected value hand-calculated from policy before the code was written) and `TestConfidenceBands`.

## Removal of unethical instructions

The original skill instructed the assistant to tell every donor their gift would be matched, "even if no match is confirmed, we can sort that out later," an instructed falsehood, not a hallucination. Matching language is now gated behind `match_confirmed` in the campaign config, requires a sponsor and terms, and is scanned for in every generated letter by the test suite. The same pattern (title guessing, invented staff names) is removed the same way, gated by verified source data instead of model discretion. Design records: [ADR 0006](adr/0006-no-unconfirmed-match-claims.md), [ADR 0005](adr/0005-never-infer-gender-or-title.md), [ADR 0007](adr/0007-campaign-config-single-source.md). Proof: `tests/test_pipeline.py::test_no_match_language_when_match_not_confirmed`, `test_no_invented_titles_or_genders`.

## Regression testing

154 automated tests, every expected value hand-calculated from policy before the code was written. The original skill's own donor table, transcribed verbatim into a permanent fixture with its planted errors preserved, is re-run by [CI](../.github/workflows/ci.yml) on every push, so the specific mistakes this exercise was seeded with can never quietly return. [`docs/trap-registry.md`](trap-registry.md) maps every planted defect to the test that guards it. Design record: [ADR 0013](adr/0013-ci-regression-gate.md).

## Versioned business rules

`donor_rules.RULES_VERSION` is a single version string, bumped whenever a threshold or formula changes output for the same input, stamped into every validation report, every stage of `run_metrics.json`, and every decision-log entry. Any output can be traced to the exact rule version that produced it without correlating a timestamp against git history. Design record: [ADR 0026](adr/0026-versioned-rules-and-structured-json-stages.md). Proof: `tests/test_pipeline.py::test_rules_version_stamped_into_the_validation_report`.

## Beyond the list

A few controls this system has that go past what is usually asked for in a first pass, worth knowing about:

- **Confidence-banded escalation** (fail below 0.70, held below 0.90, webhook-ready events): [ADR 0011](adr/0011-confidence-scoring-feedback-loop.md).
- **Donor ID collision detection**, since two different names can slug to the same letter filename at scale: [ADR 0022](adr/0022-donor-id-collisions-and-stale-output.md).
- **Stale-output prevention**, so a donor excluded from a later run can never leave an orphaned file with no manifest row: [ADR 0022](adr/0022-donor-id-collisions-and-stale-output.md).
- **A standalone, offline HTML deliverable** with a guided two-minute walkthrough, for review by anyone without Python installed: [ADR 0021](adr/0021-standalone-review-artifact.md).
- **A data provenance audit**, verifying the fixture is a verbatim transcription of the original skill's own table: [ADR 0019](adr/0019-data-provenance-and-fixture-fidelity.md).
- **A clean-room agent dry run**: every command in `SKILL.md` executed verbatim, from a scratch directory, with no prior knowledge of the deeper build, proving the skill works the way an AI assistant discovering and following it actually would, independent of any interface built on top: [ADR 0028](adr/0028-verified-as-an-agent-skill.md).

## What this document is not

It is not a claim that the system is finished. [`docs/scale-architecture.md`](scale-architecture.md) states exactly what is deliberately deferred (a CRM connector, containers, IAM, machine learning) and the trigger condition for building each one. The discipline here is knowing what a fifty-donor batch job needs and building exactly that, not everything a textbook diagram could include.
