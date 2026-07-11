# ADR 0011: Confidence scoring, bands, and escalation

Status: accepted. Date: 2026-07-10. Revised 2026-07-11 to the full fail, report, pass rubric with escalation events.

## Problem

The original skill had one implicit quality state: generated, therefore fine. There was no signal distinguishing a clean record from one carrying anomalies, no way to prioritize human attention, no notification path when something needed a person, and no measurement that could improve over time. Production AI must know when it does not know, and must act on that knowledge instead of guessing.

## Decision

Every record gets a deterministic confidence score: 1.00 minus 0.10 per attached warning (date ambiguities, asks exceeding the largest gift, anomalies that did not rise to exceptions). The score is explainable by construction, because the warnings column beside it lists exactly what was deducted and why.

The score maps to a fail, report, pass rubric:

- **Below 0.70: fail.** The record is blocked; no letter is generated until the data is fixed and resubmitted.
- **Below 0.90: report.** The letter is generated but held for mandatory review.
- **0.90 and above: pass.** Any warning still flags the letter for recommended review.

Independent of score, every Platinum letter is reviewed, and any routing reason (lapsed major donor, schema failure) is mandatory.

Every held or blocked record emits a structured escalation event to `work/escalations.jsonl` on every run. If `ESCALATION_WEBHOOK_URL` is set, each event is also posted to that endpoint, which is how the rubric plugs into a real alerting channel; by default no network call is made. This mirrors the escalation design used across production agentic deployments: administrators hear about held records in their own channel, in real time, without reading logs.

## What this changes going forward

Human review effort lands where the risk is, and problems announce themselves instead of waiting to be found. The escalation stream is also a metric: a spike in report-band events is an early warning of upstream data drift. The deliberately simple penalty model is a starting point designed to be recalibrated with evidence, by comparing reviewer outcomes against scores, and it lives in one function with tests.
