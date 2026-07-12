# ADR 0023: Lapsed donor letters cannot claim ongoing giving

Status: accepted. Date: 2026-07-12.

## Problem

A letter-quality proofread pass across all four campaign types (only `emergency_appeal` had been read end to end before) found that the annual fund campaign paragraph, rendered for a lapsed donor, reads: "Year after year, steady support from donors like you is what allows us to plan rescues, staff shelters, and answer every call for help." Michael Torres last gave in 2019 and is lapsed by five years at `as_of_date` 2024-06-30. Telling him his support has been steady is a factual claim his own gift history contradicts, in the identical spirit of trap 6 in the trap registry (donors filed as active when their dates say lapsed), except this defect was introduced by the rewrite rather than inherited from the original skill.

A second, related issue in the same letters: the opening paragraph names the donor's specific last-gift year ("including your most recent gift in 2019") in the same sentence that thanks them for present-tense generosity, immediately before the ask paragraph pivots to "it has been a while since we last heard from you." The two paragraphs are not factually inconsistent, but back to back they read as a jarring, slightly tone-deaf transition, undercutting the "warm welcome back" tone `references/policy.md` already calls for.

## Decision

1. `references/policy.md` now defines a lapsed variant of the annual fund paragraph that describes the mission, not the donor's own giving pattern, and states the general rule: no campaign paragraph may describe a lapsed donor's giving as current or ongoing.
2. `generate_letters.py`'s `build_campaign_paragraph` selects the lapsed variant whenever `campaign_type == "annual_fund"` and `donor["status"] == "lapsed"`. The other three campaign paragraphs are mission-focused rather than donor-behavior claims and needed no lapsed variant.
3. `build_opening` no longer names the specific last-gift year for a lapsed donor; it still thanks them by name for their lifetime giving total. The year, and the fact that time has passed, is left to the ask paragraph, which already carries that message warmly and is the one place `references/policy.md` designates for it.

## What this changes going forward

Every campaign type was rendered end to end against the fixture as part of this fix, not just the committed `emergency_appeal` run, closing a real gap in what had actually been eyeballed before submission. `tests/test_lapsed_letters_never_claim_current_giving` runs the pipeline under `annual_fund` specifically and asserts no lapsed donor's letter contains "steady support" or names their specific last-gift year, so this defect class cannot silently return. The general rule in `references/policy.md`'s content section, not just the specific fix, is what a reviewer or a future campaign paragraph should be checked against.
