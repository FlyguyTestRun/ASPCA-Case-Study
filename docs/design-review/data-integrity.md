# Data Integrity: Source of Truth, Data Placement, Validation

Covers problems 2, 5, and 10 from the [design review index](README.md).

## Problem 2: the model as the source of truth

The original skill makes the model the owner of business logic: it holds the tier rules, the ask formula, the messaging policy, and the donor data, all in one instruction file, all interpreted probabilistically at run time. Enterprise systems put those in layers: data (the CSV), parser, validator, schema, business logic, model, renderer. The LLM should never own business logic.

**Verdict: valid.** This is the same data-first conviction that enterprise platforms are built on: the durable asset is the data and the policy, not the model.

**The fix.** [policy.md](../../skill/charity-donor-outreach/references/policy.md) is the single written source of the rules; [donor_rules.py](../../skill/charity-donor-outreach/scripts/donor_rules.py) is its single executable implementation; the gift history column is the single source of truth for every derived number. If the document and the code ever disagree, that is a defect, not an interpretation question. Decision record: [ADR 0002](../adr/0002-verify-inputs-never-trust-them.md).

## Problem 5: the donor database inside the instructions

Fifty donors' complete giving histories sit inside the original SKILL.md, while the skill's own step 1 says to read an uploaded CSV. Data belongs in data files (CSV, XLSX, a database), never in a prompt. Embedding it bloats the context window on every call, sends donor PII to the model whether needed or not, goes stale immediately, contradicts the skill's own instructions, and caps the system at whatever fits in a file. It does not matter much at 50 rows. It is fatal at 5,000, and it is avoidable at every size.

**Verdict: valid.** One sub-point from my first pass deserves a correction: I initially flagged the absence of a semantic cache. A cache is the right tool for repeated interactive queries; this batch workload is fixed more fundamentally by removing the model from the hot path. The stronger claim stands: data in the prompt is the wrong placement at any scale.

**The fix.** The skill holds zero data. The 50 donors were transcribed verbatim, planted errors included, into [a test fixture](../../skill/charity-donor-outreach/assets/sample_donors.csv) that doubles as the permanent regression suite. Decision records: [ADR 0001](../adr/0001-separate-data-from-instructions.md), [ADR 0016](../adr/0016-token-and-process-economy.md).

## Problem 10: no input validation

The original validates nothing: not the tiers against the giving, not the totals against the gift list, not the dates against a reference point. The planted data proves why that matters. Four donors carry tiers their own gift history contradicts, and the math ties out wrong for each of them. Mislabeled data creates exactly the wrong-ask, wrong-tone letters this skill exists to prevent.

**Verdict: valid, with one correction from the audit.** My first-pass note said the math does not tie out. The fidelity audit ([ADR 0019](../adr/0019-data-provenance-and-fixture-fidelity.md)) showed the opposite, and the correction makes the finding stronger: every arithmetic column in the original (largest gift, lifetime total, last gift year) is consistent with its own gift list. The planted defects are categorical (tier labels contradicting the giving) and temporal (dates with no reference point). A validator that only re-added the numbers would have passed this file while sending four donors the wrong ask, which is exactly why validation has to check cross-field consistency and date logic, not just sums. And worth stating plainly: when I reviewed the table by hand I caught three of the four mislabeled tiers. The validator caught all four on its first run. Computed verification beats careful reading, every time.

**The fix.** [validate_input.py](../../skill/charity-donor-outreach/scripts/validate_input.py) recomputes everything computable from the gift history, checks every stated field against it, ties out the totals, checks dates against an explicit as-of date, and routes every failure to an exceptions report with a suggested correction a human can approve and resubmit. Decision records: [ADR 0002](../adr/0002-verify-inputs-never-trust-them.md), [ADR 0008](../adr/0008-fail-loudly-to-exceptions.md), [ADR 0014](../adr/0014-suggested-corrections-resubmit-loop.md).

## What changes at scale

The validation stage is where a CRM connector eventually replaces file upload, with the same checks applied at the boundary and donor IDs replacing names as the join key. See [scale-architecture.md](../scale-architecture.md).
