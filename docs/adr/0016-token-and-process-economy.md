# ADR 0016: Token and process economy at scale

Status: accepted. Date: 2026-07-10.

## Problem

The original design was maximally expensive by construction: the entire 50-donor table rode inside the instructions into every model call, the model performed arithmetic and rendering per donor, and output streamed through chat. Cost grew linearly with donors on every run, quality risk grew with it, and nothing was reusable between runs. At 5,000 donors that is not a big bill, it is an outage.

## Decision

Cost is treated as an architectural property, removed in layers ordered by how much each removes:

1. **No model in the hot path.** Validation, tier computation, ask arithmetic, and letter rendering are code. The batch cost of a 50,000-donor run is the same as a 50-donor run: zero tokens.
2. **Progressive disclosure in the skill.** SKILL.md stays small (well under the recommended 500-line ceiling); policy and schema live in references/ and load only when needed; scripts are executed, never read into context.
3. **Bounded, targeted generation.** When a model is used at all, it personalizes only flagged letters, one paragraph, from validated fields, with the approved library as fallback. Per-donor token cost is bounded and optional rather than mandatory and unbounded.
4. **Learned style instead of repeated generation.** The style profile (ADR 0015) captures voice once and applies it deterministically forever, replacing per-letter regeneration with a string substitution.
5. **Batch-friendly process.** Exceptions are fixed at the source and resubmitted (ADR 0014), so a batch is re-run cheaply rather than re-reviewed expensively; stable system prompts and tool definitions are cache-friendly if a hosted model is introduced; run outputs are files, reusable and diffable between runs.

## What this changes going forward

Scaling the donor list scales file sizes, not spend. The only cost knob that grows with volume (optional personalization) is explicit, per-letter, and gated, so a budget cap is trivial to enforce. And because the deterministic layers do the bulk of the work, a future model upgrade or swap changes one bounded step instead of the whole system.
