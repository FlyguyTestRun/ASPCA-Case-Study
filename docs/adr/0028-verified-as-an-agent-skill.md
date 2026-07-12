# ADR 0028: Verified as an agent skill, not only as a human-operated pipeline

Status: accepted. Date: 2026-07-12.

## Problem

Every prior verification of this system ran through either the CLI directly (as the person who wrote the scripts, who already knows what to expect) or the Streamlit review app (a human-operated interface). Neither proves the actual thing the case study asked for: a *skill*, triggered and followed by an AI assistant the way the original `charity-donor-outreach` skill describes itself, "use this skill when someone uploads a CSV or donor list and wants to generate personalized outreach letters." An interface can be polished and the underlying skill can still be wrong for an agent to follow, if its documented commands have drifted from what the scripts actually accept, if a promised output file no longer gets written, or if the workflow assumes context an agent encountering the skill fresh would not have.

## Decision

A clean-room dry run: acting only on what `SKILL.md` says, with no access to prior knowledge of the deeper build, from a scratch directory outside the repository, with the donor file and campaign config placed where an uploaded file actually would be (not pre-staged inside the skill's own folder). Every command was copied verbatim from `SKILL.md` and run in order:

1. `validate_input.py` against the fixture and the example config: 50 rows in, 46 validated, 4 held with named reasons, exactly as documented.
2. `apply_corrections.py` with `--decision-log` and `--approved-by`, exactly as documented: all four corrections applied, a decision-log entry written.
3. `validate_input.py` re-run on the corrected file, per the documented restart instruction: 50 of 50 validated.
4. `calculate_ask.py`: 50 asks computed, 5 mandatory reviews, 2 records correctly routed with no ask.
5. `generate_letters.py`: 48 letters, 0 schema rejections, manifest and every promised file present.

Every file `SKILL.md` promises at each step existed, with the promised shape, after running only the documented command. Step 5 (bounded personalization) was correctly never invoked, because the simulated request never asked for it: the run produced 48 policy-correct, schema-validated letters with zero model calls. A spot-checked letter (one of the four corrected donors, now Gold tier) carried the right tier-specific closing line, the right ask, no unconfirmed match language, and no drift from policy.

## What this changes going forward

The case study's actual ask, a working, triggerable skill, is proven independently of any interface built on top of it. The Streamlit review app remains in the repository as a genuine, tested addition for non-technical staff and training use, but it is not load-bearing for the core claim: an agent that discovers this skill by its description and follows `SKILL.md` literally will produce correct output, because that is exactly what was tested.
