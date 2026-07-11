# Confidence and Escalation: Fail, Report, Pass

Covers problem 7 from the [design review index](README.md).

## Problem 7: no scoring logic, no escalation path

The original has one implicit quality state: generated, therefore fine. Nothing measures uncertainty, nothing routes attention, and nobody finds out about a problem unless they happen to read the right letter. Production AI must handle uncertainty explicitly or it will guess, and a system that guesses quietly loses the user's trust exactly once.

**Verdict: valid, and this review drove the full implementation.** The first rebuild pass had confidence scores and review levels; this pass completed the rubric and the notification path.

**The fix: a fail, report, pass rubric with escalation.** Every record's confidence starts at 1.00 and loses 0.10 per attached warning. The bands, implemented in [donor_rules.py](../../skill/charity-donor-outreach/scripts/donor_rules.py) and set out in [policy.md](../../skill/charity-donor-outreach/references/policy.md):

| Band | Threshold | What happens |
|------|-----------|--------------|
| Fail | below 0.70 | The record is blocked. No letter exists until the data is fixed and resubmitted. |
| Report | below 0.90 | The letter is generated but held for mandatory human review, and an escalation event is emitted. |
| Pass | 0.90 and above | The letter proceeds; any warning still flags it for recommended review. |

Independent of score, every Platinum letter is reviewed by a person, and any record carrying a routing reason (a lapsed major donor, a schema rejection) is mandatory.

**Escalation events** are the notification half of the rubric. Every held or blocked record produces a structured event (donor, band, confidence, warnings, reasons, timestamp) written to `work/escalations.jsonl` on every run. Setting the `ESCALATION_WEBHOOK_URL` environment variable posts each event to that endpoint as well, which is how this plugs into a real alerting channel (Teams, Slack, PagerDuty, a ticketing queue) without this repo shipping any network dependency: by default, no call leaves the machine. This mirrors the escalation design I run in production systems: admins hear about held records in their own channel, in real time, without reading logs.

Scoring is deliberately explainable: the warnings column beside every score lists exactly what was deducted and why, so a score is an argument, not a vibe. Identify, never speculate. Decision record: [ADR 0011](../adr/0011-confidence-scoring-feedback-loop.md).

## What changes at scale

The penalty weights are a starting point designed to be recalibrated against evidence: compare reviewer outcomes to scores and adjust. At volume, the escalation stream becomes a metric in its own right; a spike in report-band events is an early warning of upstream data drift long before donors notice anything. Score distributions per run belong on the same dashboard as the [run metrics](evaluation-and-observability.md).
