# Prompt Design: Computation in the Model, Model in the Hot Path

Covers problems 1 and 9 from the [design review index](README.md).

## Problem 1: deterministic computation inside the LLM

The original skill hands the model a seven-step arithmetic procedure per donor: take a percentage of the largest gift, round to the nearest $50, then stack a loyalty uplift, a volunteer bonus, and an emergency multiplier on top of the rounded number. Math is deterministic; a language model is pattern recognition running on probability. Asking it to calculate is asking for fifty subtly different answers across fifty donors, unreproducible between runs, and the formula itself is defective: rounding mid-sequence makes the result depend on the path taken, and "gave last year" is never defined.

**Verdict: valid.** This is the clearest single engineering failure in the original, and the cheapest to fix.

**The fix.** Never "LLM, please calculate." All arithmetic lives in [calculate_ask.py](../../skill/charity-donor-outreach/scripts/calculate_ask.py) with a fixed operation order, one rounding step at the end, defined terms, and a per-donor trace so any amount can be audited back to the rule that produced it. The expected values in [the test suite](../../tests/test_rules.py) were hand-calculated from policy before the code was written. Decision record: [ADR 0003](../adr/0003-deterministic-arithmetic.md).

## Problem 9: every input becomes a model call

The original design routes every donor, every run, through the model, with the entire donor table riding along in the instructions. That is tokenization and processing spent on work a pipeline does for free, and it grows linearly with the donor list on every single run. Beyond cost, it puts the least reliable component in the most critical path: ambiguous prompts produce inconsistent agents, and the original prompt is ambiguous everywhere it matters (undefined dates, undefined tiers for missing data, "make reasonable assumptions").

**Verdict: valid.** The classic pipeline design (data, parser, validator, schema, business logic, then and only then a model, then a renderer) removes the model from the batch path entirely.

**The fix.** The rebuilt pipeline runs validate, calculate, and generate as deterministic stages; the batch cost of a 50,000-donor run is the same as a 50-donor run: zero tokens. Where a model is used at all (the optional bounded personalization step in [SKILL.md](../../skill/charity-donor-outreach/SKILL.md)), it is per-flagged-letter, grounded in validated fields, and cannot touch numbers or claims. When the system cannot determine something (a donor tier that contradicts the gift history, a date that makes no sense), the answer is a flagged record for human review, never a guess with confidence. Decision records: [ADR 0016](../adr/0016-token-and-process-economy.md), [ADR 0008](../adr/0008-fail-loudly-to-exceptions.md).

## What changes at scale

Nothing in this file changes at scale, which is the point: the deterministic spine is the part of the system that scales for free. The components that do change (caching, orchestration, model tiering) have trigger conditions in [scale-architecture.md](../scale-architecture.md).
