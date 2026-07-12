# ADR 0025: The one prompt that touches a model lives in its own versioned file

Status: accepted. Date: 2026-07-12.

## Problem

The bounded personalization step (SKILL.md step 5) is the only place in this skill where a model is asked to produce language beyond an already-approved template. Its guardrails lived as prose inside `SKILL.md`, mixed in with orchestration instructions (which script to run, in what order, what to show the user). That is a smaller version of the original skill's defect: prompt content and orchestration logic sharing one file makes it harder to review, version, or reuse the prompt independently, and harder to see at a glance that exactly one step in an otherwise fully deterministic pipeline touches a model at all.

## Decision

`prompts/personalization_prompt.md` is now the single, standalone, versioned source of that prompt: the constraints a model must follow, written as a real system prompt a model would actually receive, not as instructions to a human reading SKILL.md. It carries its own version number and a version history section. `SKILL.md` step 5 points to it rather than repeating its content, and the pipeline overview table in `SKILL.md` names it directly as the one bounded, non-deterministic stage.

## What this changes going forward

Prompt, data, and business logic are now separated at the file level as well as conceptually: `references/policy.md` is the business-rule specification, `donor_rules.py` is its implementation, `assets/` is data, and `prompts/personalization_prompt.md` is the one piece of content a model actually reads to do its one job. Changing the personalization guardrails is a diff to one small, purpose-built file with a version bump, not an edit buried in a longer orchestration document. Anyone auditing what a model is and is not allowed to say can read one page and be done.
