# Evaluation and Observability: Prove It, Then Watch It

Covers problems 8 and 12 from the [design review index](README.md).

## Problem 8: no evaluation harness, no regression testing, no versioning

The original has no tests, no expected outputs, and no way to build either, because it has no clean dataset to test against and no deterministic behavior to pin. Every edit to the instructions is a blind change: nothing tells you whether the skill got better or quietly worse. There is no versioning of the instructions, so there is no answer to "what did the system say in March, and why."

**Verdict: valid.** The harness is what grounds the system: it turns "the letters look right" into a property that fails a build when it stops being true.

**The fix.** The rebuild has 86 automated tests, every expected value hand-calculated from policy before the code was written, and the planted traps from the original data serve as the permanent regression suite: [CI](../../.github/workflows/ci.yml) re-runs them on every push, so the mistakes this exercise was seeded with can never quietly return. Versioning is git itself: the policy document, the rules module, the schema, and the prompt-facing instruction file are all in one repository, so any run can be reproduced against the exact rules that produced it, and any rule change is a diff with an author and a decision record. Orchestration and eval frameworks earn their place at a different scale; the trigger conditions are in [scale-architecture.md](../scale-architecture.md). Decision record: [ADR 0013](../adr/0013-ci-regression-gate.md).

## Problem 12: no observability

Nothing in the original logs, measures, or compares. No latency numbers, no token counts, no cost attribution, no exception rates, which means no feedback loop, no early warning, and nothing for a data science pass to improve later. A system nobody can measure is a system nobody can defend in review.

**Verdict: valid, and this review drove the implementation.**

**The fix.** Every run now writes structured observability artifacts alongside its outputs, all in `work/`:

- `run_metrics.json`: per-stage duration and counts (rows in, validated, excepted, letters written, schema rejections, escalations), plus the standing note that the batch path costs zero tokens at any donor count.
- `validation_report.json`: the full validation outcome with named exceptions and warnings.
- `escalations.jsonl`: one structured event per held or blocked record, the input to any alerting channel.
- `letter_models.jsonl`: the validated structured output of the run.

The review app surfaces the metrics table on its Run log tab so the numbers are visible to the people running the system, not just to engineers reading files. Decision records: [ADR 0016](../adr/0016-token-and-process-economy.md), [ADR 0011](../adr/0011-confidence-scoring-feedback-loop.md).

## What changes at scale

These files are the local form of a telemetry pipeline. At volume they stream to a dashboard instead of a folder: exception rate and escalation rate become alertable series (a spike means upstream data drift), stage durations become capacity planning, and reviewer-outcome data joins the confidence scores to recalibrate the rubric with evidence. The artifacts were designed as structured JSON precisely so that migration is a transport change, not a redesign.
