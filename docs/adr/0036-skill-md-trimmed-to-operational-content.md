# ADR 0036: SKILL.md trimmed to operational content only

Status: accepted. Date: 2026-07-13.

## Problem

`SKILL.md` is the file that triggers this skill and is read into an agent's context at trigger time, not a design document. At 181 lines it carried real operational content (the pipeline table, exact commands, hard rules) mixed with rationale and philosophy (why stage 6 is optional, the reasoning behind decision-log discipline, pointers to other docs with a sentence of context each). None of that rationale changes what an agent needs to do to run the skill correctly; it belongs in the ADRs and design docs that already exist for it.

## Decision

Cut every paragraph whose job was explaining *why*, keeping everything whose job is telling an agent *what to do*: the pipeline table, the required-inputs list, all six workflow steps with their exact commands, the personalization guardrails, and the five hard rules are all unchanged in substance. Rationale collapsed to a single line with a link to the ADR that explains it in full (stage 6's optionality now points to ADR 0016 instead of a four-sentence justification; the decision-history section is two lines instead of a paragraph). The reference-documents list absorbed the separate "full requirements checklist" and "see it run" sections as two more bullets, removing two headers that existed only to point somewhere else.

Every command line is unchanged (confirmed by diff: zero lines matching `python ` differ between the old and new file). 181 lines became 141: real reduction, short of the original ~100-110 estimate, because the six workflow steps each still need their own command block and a one-line description of what it writes and checks; compressing those further would start cutting operationally useful information (the workflow section is the one part of SKILL.md an agent actually executes step by step) rather than rationale.

## What this changes going forward

Nothing about the skill's behavior changed, only its explanation of itself. Re-ran the exact clean-room dry run ADR 0028 performed, from a fresh scratch directory, using this trimmed file's own commands verbatim: 50 rows in, 46 validated, 4 held; corrections applied; 50 of 50 on re-validation; 50 asks computed, 5 mandatory, 2 routed with no ask; 48 letters, 0 schema rejections. Every number matches ADR 0028's original result exactly, confirming the trim changed nothing about what the skill does.
