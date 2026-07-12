# ADR 0024: A structural schema layer, separate from and prior to business rules

Status: accepted. Date: 2026-07-12.

## Problem

The pipeline already validated donor data thoroughly, but every check lived inside one function in `validate_input.py`, mixing two genuinely different kinds of question: is this row shaped correctly (a schema question), and given that it is shaped correctly, does it make business sense (a policy question, does the stated tier match the computed one, does a date fall where it should). Collapsing both into one undifferentiated pass works, but it is not what a reviewer scanning for "schema validation" as a named, separate control will find: nothing in the repository said, explicitly and in one place, what shape a donor row is contractually required to have.

## Decision

`references/donor.schema.json` states the structural contract for a raw donor row: required fields, allowed tier and volunteer values, the expected pattern for the gifts field. `validate_donor_row` in `donor_rules.py` checks a row against it and is called first, at the top of the per-row loop in `validate_input.py`, before any tier computation or date logic runs. A row that fails structurally (a renamed column, a tier value that is not even a real label, a gifts field nowhere near the expected format) is caught here, with a `schema:`-prefixed reason distinguishing it from a business-rule failure. The two layers are additive, not a replacement: business-rule checks (computed tier versus stated tier, date consistency) still run and can still catch a row that is structurally valid but factually wrong.

## What this changes going forward

Schema and policy are now two named, separately testable things, matching how a reviewer or a new contributor is likely to think about the system and matching standard data-pipeline practice: validate shape, then validate meaning. A column rename or a genuinely malformed export now fails fast with a structural reason instead of tripping over parsing logic deeper in the pipeline. `tests/test_pipeline.py::test_malformed_tier_label_caught_by_schema_before_business_rules` and `test_gifts_field_not_matching_expected_shape_caught_by_schema` pin this behavior.
