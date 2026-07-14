# Decision 0001: Applied 4 data correction(s) to sample_donors.csv

Date: 2026-07-14. Approved by: Bryan Shaw. Source: apply_corrections.py. Rules version: 1.1.0.

## Problem

Validation held these records because stated values contradicted the gift history, which is the source of truth.

## Decision

Corrections approved and applied:

- row 23 (Ada Yamamoto-Pierce): tier 'Silver' -> 'Gold' (lifetime giving of $17,000 places this donor in Gold)
- row 25 (Ruth Andersen): tier 'Silver' -> 'Gold' (lifetime giving of $25,000 places this donor in Gold)
- row 27 (Shirley Magnusdottir): tier 'Silver' -> 'Gold' (lifetime giving of $22,000 places this donor in Gold)
- row 51 (Arthur Mwangi): tier 'Bronze' -> 'Silver' (lifetime giving of $2,600 places this donor in Silver)

## Effect going forward

The corrected file supersedes the original for this run. The same corrections must be made in the source system so the discrepancy does not recur.
