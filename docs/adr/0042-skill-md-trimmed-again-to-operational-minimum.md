# ADR 0042: SKILL.md trimmed a second time, to the operational minimum

Status: accepted. Date: 2026-07-14.

## Problem

[ADR 0036](0036-skill-md-trimmed-to-operational-content.md) cut `SKILL.md` from 181 lines to 141 by moving rationale out to one-line ADR pointers while keeping every structural section intact: the pipeline overview table, a paragraph on why personalization is optional, the workflow steps, and a closing list of reference documents. That pass answered "does this line explain a decision, or does it change what the agent does next," and moved the former out. It stopped short of asking the same question of entire sections that are still present for a human reader's benefit rather than the agent's: an overview table restating what the six workflow steps below it already say with real commands, a short essay on why stage 6 is optional when the workflow steps already convey that by their own structure, and a bibliography of reference documents whose paths already appear inline wherever they are actually used.

## Decision

A second pass, same rule, applied more strictly: if a line does not change what the agent does next, it does not belong in this file, including whole sections, not just individual sentences. Removed:

- **The pipeline overview table.** Redundant with the Workflow section immediately below it, which has the same six stages with real, runnable commands instead of a summary. A human wanting the overview gets it from this deliverable's own pipeline diagram, or from `docs/components.md`.
- **The stage-6-is-optional rationale paragraph.** The fact itself (personalization is optional, off by default) is already structural: step 5 of the workflow is titled "Optional bounded personalization" and is the only step conditioned on the user asking for it. The paragraph only restated that in prose and pointed to an ADR for why, which belongs in the ADR, not repeated here.
- **The decision-history section.** The one operationally relevant fact, that `apply_corrections.py` should be run with `--decision-log` and `--approved-by`, is already in the literal command shown in step 2. The surrounding sentence explaining why only mattered to a human, not to an agent executing the command as written.
- **The reference documents list.** Every path in it (`donor.schema.json`, `policy.md`, `input_schema.md`, `letter_schema.json`, `personalization_prompt.md`) already appears inline in Required Inputs or the relevant Workflow step, the place an agent would actually need it. The two documentation pointers at the end (`docs/requirements-checklist.md`, `docs/run-walkthrough.md`) are for a human auditing the system, not for the agent running it.

## What this changes going forward

141 lines became 100. Every command line is unchanged, byte for byte, confirmed by diff a second time: `git diff` on this file shows zero differing lines matching `python `. Re-verified with the same clean-room dry run [ADR 0028](0028-verified-as-an-agent-skill.md) and the ADR 0036 trim both used, from a fresh scratch directory outside the repository: the exact same result, 50/46/4, corrections applied, 50/50, 5 mandatory and 2 no-letter, 48 letters, 0 rejections. Nothing about what the skill does changed; only how much a trigger-time read costs to find out.
