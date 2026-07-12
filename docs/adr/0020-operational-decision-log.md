# ADR 0020: The running system keeps its own decision history

Status: accepted. Date: 2026-07-11.

## Problem

The authored ADRs in docs/adr/ record how this system was designed, but nothing recorded how it evolves in operation. Corrections get applied, style preferences get adopted, batches get signed off, and each of those changes what the system does next, yet the only trace was scattered artifacts (a corrected CSV here, a style profile there). Six months in, "why does the system behave this way, who approved it, and based on what" needs a better answer than archaeology.

## Decision

Every persisted operational change writes a numbered, ADR-style entry to `docs/decision-log/`: the problem, the decision (with the specific changes listed), the effect going forward, who approved it, when, and through which surface. Three event types write entries today: applied correction batches (apply_corrections.py and the review app's findings step), adopted style preferences (learn_style.py and the review app), and batch review sign-offs (the review app's finalize step). Entries are written by the same code paths that persist the change, so the log cannot drift from reality; the review app requires an operator name before any of those actions is enabled. Authored architecture ADRs and the operational log stay in separate folders on purpose: one records how the system was designed, the other how it has been governed since.

## What this changes going forward

The system carries its own audit history, in the same decision-record form its designers used, readable by anyone. "Who approved raising Ruth Andersen to Gold, and why" has a file as its answer. The log also becomes the seed of the improvement loop: recurring correction entries point at upstream data problems, and the sequence of style adoptions documents how the house voice converged. When the deployment gains real identity management, the approver field graduates from a typed name to an authenticated one without changing the design.
