# ADR 0002: Verify every stated field against the gift history

Status: accepted. Date: 2026-07-10.

## Problem

The donor file states tier, largest gift, lifetime total, and last gift year alongside the raw gift history, and the original skill took all of them on faith. The example data contains four tier labels that contradict the donor's own gift history: Ruth Andersen (Silver, $25,000 lifetime), Ada Yamamoto-Pierce (Silver, $17,000), Shirley Magnusdottir (Silver, $22,000), and Arthur Mwangi (Bronze, $2,600). Trusting the label means asking a Gold-capacity donor for a Silver-sized gift, silently and at scale.

## Decision

The gift history column is the single source of truth. validate_input.py recomputes tier, largest gift, lifetime total, and last gift year from it, and any stated value that disagrees sends the row to work/exceptions.csv with the exact discrepancy spelled out. Mismatched rows never generate letters until a data steward resolves them at the source.

## What this changes going forward

Bad labels are caught on every run, not discovered after a donor receives the wrong ask. The exceptions report becomes the feedback loop to the CRM: each entry names the field, the stated value, and the computed value, so the upstream fix is obvious. On this fixture the validator caught all four planted mismatches, including one (Shirley Magnusdottir) that manual review of the original table had missed. That is the argument for computed checks in one sentence.
