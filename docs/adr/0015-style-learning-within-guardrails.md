# ADR 0015: Learning reviewer style, inside hard guardrails

Status: accepted. Date: 2026-07-10.

## Problem

Reviewers edit generated letters to match their voice, and the system learned nothing from it: the same edits had to be made on every batch, forever. But naively learning from edits is dangerous in this domain, because an edit could reintroduce exactly what the pipeline exists to prevent (urgency devices, match language, changed amounts).

## Decision

A deliberately narrow preference-learning loop (scripts/learn_style.py, and the Letter style tab in the review app):

- **What can be learned:** personality-level knobs only, currently the closing phrase and an optional P.S. line. Body language stays policy-controlled; edits to it are reported for a human to consider as a policy change, never learned.
- **Evidence threshold:** a change is suggested only after it appears identically in 3 or more edited letters. One-off edits are noise, not preference.
- **Guardrails at two points:** a suggested value must contain no digits, no dollar signs, no HTML, and none of the banned words (match, double, guarantee, urgent, deadline, and so on), checked when learning and re-checked on every generation run, so a hand-edited profile file cannot bypass them. Unknown profile keys are dropped, so the profile cannot smuggle changes to asks or claims.
- **Human adoption:** suggestions become active only when a named person adopts them; the profile records who and when.

## What this changes going forward

The system converges on the team's voice instead of fighting it, and each adoption is one decision made once instead of fifty edits made per batch. The same pattern (observe, threshold, guardrail, named approval) is the template for any future preference the team wants the system to learn, and the tests pin the security property that matters: a style profile can change how a letter sounds, never what it claims or asks.
