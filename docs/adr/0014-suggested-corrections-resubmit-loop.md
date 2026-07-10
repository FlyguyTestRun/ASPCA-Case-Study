# ADR 0014: Suggested corrections with human-approved resubmission

Status: accepted. Date: 2026-07-10.

## Problem

Finding errors is half a feedback loop. The validator (ADR 0002) holds bad records back with reasons, but the operator's next step was manual: figure out the fix, edit the file somewhere else, run again. Friction there means exceptions pile up, and a pile of unresolved exceptions quietly becomes the same outcome as no validation at all.

## Decision

Wherever the correct value is computable from the donor's own gift history, the validator now emits a machine-readable suggestion (work/corrections.csv: row, field, current value, suggested value, reason). Each exception also carries its suggestion in plain language. Applying suggestions is a separate, human step: apply_corrections.py on the command line, or the Fix and resubmit tab in the review app, where each fix is individually approvable, the corrected file re-runs immediately, and a copy is downloadable for updating the source system. Nothing is ever applied silently; the four planted tier traps produce four suggestions, and approving them takes the fixture from 4 exceptions to a clean 50-of-50 run, which the test suite proves.

## What this changes going forward

The gap between "error found" and "error fixed" drops from a support ticket to a click, while keeping a person in the gate for every change. The corrections file is also the audit record of what changed and why, and the download-for-source-system step pushes fixes upstream so the same error stops recurring, which is the point of a feedback loop.
