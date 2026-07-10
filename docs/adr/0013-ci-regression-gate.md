# ADR 0013: CI runs the traps on every change

Status: accepted. Date: 2026-07-10.

## Problem

A validation pipeline that silently stops catching errors is worse than no pipeline, because it launders bad data with a green checkmark. Every future edit to the policy, the scripts, or the schema risks quietly breaking a guardrail, and nothing in a local-only workflow would notice.

## Decision

A GitHub Actions workflow runs on every push and pull request: the full pytest suite, then the pipeline end to end against the planted-trap fixture, asserting that all four tier mismatches land in exceptions, the reference-date warning fires, lapsed major donors get no letter, and no unconfirmed match language appears in any letter. The run artifacts (manifest, exceptions, validation report) are uploaded with each CI run.

## What this changes going forward

The planted traps in the original case-study data become a permanent regression suite: the mistakes this exercise was seeded with can never quietly come back. Guardrails are enforced by the repository, not by whoever remembers them. Any policy change that would weaken a protection has to delete a failing test in public to do it, which is exactly the kind of visibility a governance change deserves.
