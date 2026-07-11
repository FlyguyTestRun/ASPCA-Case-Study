# ADR 0018: Donor files are untrusted input, outputs are inert

Status: accepted. Date: 2026-07-11.

## Problem

The original skill trusted its input completely and passed donor text into outputs unexamined. A donor file is user-generated content: names and fields can carry spreadsheet formulas (`=HYPERLINK(...)` executes when the CSV opens in Excel), markup, or text crafted to read as instructions to the model. The pipeline's own output files are opened in Excel by fundraising staff, which makes CSV formula injection a realistic path from a hostile row in a donor export to code execution on a fundraiser's laptop.

## Decision

Three boundaries, enforced in code and tests:

1. **Inert CSV output.** Every cell in every CSV the pipeline writes is neutralized on write (`csv_safe` in donor_rules.py): values beginning with `=`, `+`, `-`, or `@` are prefixed so spreadsheets display them instead of executing them. Letter HTML already escapes all donor-derived text.
2. **Bounded ingestion.** The review app caps uploads at 5 MB and restricts extensions; oversized files are redirected to the batch pipeline with a plain-language explanation.
3. **Data is never instructions.** The skill's personalization step carries an explicit rule that donor-file text is data; anything in it that reads as a directive is flagged, never followed.

Identity and access management, per-user approval audit, encryption at rest, and malicious-file scanning are deliberately scoped to production deployment (see docs/scale-architecture.md): a local demo cannot implement enterprise identity honestly, and pretending otherwise would be theater.

## What this changes going forward

The pipeline can accept a hostile donor file and produce only inert artifacts, proven by a test that feeds it a formula-injection payload. The security posture is also written down with its seams: when this deploys for a team, the IAM and audit layers attach to approval actions that already record an approver field, and the upload boundary retires entirely when a CRM connector replaces files.
