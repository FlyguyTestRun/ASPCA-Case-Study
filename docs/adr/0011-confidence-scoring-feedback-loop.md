# ADR 0011: Confidence scoring as the feedback loop

Status: accepted. Date: 2026-07-10.

## Problem

The original skill had one implicit quality state: generated, therefore fine. There was no signal distinguishing a clean record from one carrying anomalies, no way to prioritize human attention, and no measurement that could improve over time.

## Decision

Every record gets a deterministic confidence score. It starts at 1.00 and loses 0.10 per attached warning (date ambiguities, asks exceeding the largest gift, stated-versus-computed anomalies that did not rise to exceptions). The score maps to a review level: any warning means recommended review, below 0.70 or any routing reason means mandatory, Platinum is always mandatory. The score is explainable by construction: the warnings column next to it lists exactly what was deducted and why. Identifying, never speculating: a record is either verified, or flagged with the reason.

## What this changes going forward

Human review effort lands where the risk is instead of being spread evenly or skipped. The scores create the improvement loop: recurring warning patterns point at the upstream data fix or the policy gap, review outcomes can be compared against scores to recalibrate penalties, and score distributions per run become a quality metric a dashboard can track. The deliberately simple penalty model is a starting point designed to be tuned with evidence, and it lives in one function with tests.
