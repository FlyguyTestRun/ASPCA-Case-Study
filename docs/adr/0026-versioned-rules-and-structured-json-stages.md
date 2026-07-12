# ADR 0026: Explicit rules versioning and structured JSON at every stage boundary

Status: accepted. Date: 2026-07-12.

## Problem

Two properties of the system were true in substance but not visible as artifacts. First, business rules were versioned only implicitly, through git: nothing in a validation report, a computed ask, or a decision-log entry stated which version of the tier thresholds, ask formula, or confidence rubric had produced it. An auditor asking "what rules were in effect when this batch ran" had to correlate a timestamp against commit history rather than read an answer off the output itself. Second, the donor record passed between pipeline stages as a CSV row. CSV is the right working format for a file fundraising staff open in Excel, but a CSV row is not a structured object in the sense a downstream system, a schema check, or an integration would expect; nothing in the repository showed a validated donor as the JSON object it conceptually is at each stage.

## Decision

`donor_rules.RULES_VERSION` is a single version string, bumped whenever a threshold, formula, or gate changes output for the same input. It is stamped into `validation_report.json`, every stage entry in `run_metrics.json`, and every decision-log entry's metadata line. Separately, `validate_input.py` and `calculate_ask.py` now write a `.jsonl` file alongside each `.csv` file they already produced (`validated.jsonl` beside `validated.csv`, `computed.jsonl` beside `computed.csv`), one JSON donor object per line, identical data, different shape. `letter_models.jsonl` already existed for the generation stage (ADR 0017) and needed no change. Nothing about the CSV working files changes; this is additive.

## What this changes going forward

Any artifact this system produces can answer "which rules made this decision" without leaving the artifact. A structured donor object exists at every stage boundary for any consumer that wants JSON rather than a spreadsheet row, without giving up the CSV format the human-facing workflow depends on. Recalibrating the confidence rubric or changing an ask formula (both anticipated in `docs/scale-architecture.md`) now has a natural place to record which version of the system a comparison is against.
