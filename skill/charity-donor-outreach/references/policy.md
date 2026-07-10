# Donor Outreach Policy

This document is the single source of truth for tiers, ask amounts, messaging rules, and review gates. The scripts in `scripts/` implement these rules; if this document and the code ever disagree, that is a defect to fix, not an ambiguity to interpret.

## Giving tiers

Tier is computed from lifetime giving. It is never taken on faith from an input file. If a file states a tier that disagrees with the computed tier, the record is routed to the exceptions report for a data steward to resolve.

| Tier | Lifetime giving |
|------|-----------------|
| Platinum | $50,000 and above |
| Gold | $10,000 to $49,999 |
| Silver | $1,000 to $9,999 |
| Bronze | under $1,000 |

## Lapsed status

Lapsed is a status, not a tier. A donor is lapsed when more than 3 full years have passed since their last gift, measured against the campaign's `as_of_date` (never the current wall clock):

```
lapsed = (as_of_year - last_gift_year) > 3
```

Every donor therefore has both a financial tier and an active or lapsed status. A lapsed Bronze or Silver donor receives the re-engagement treatment. A lapsed Gold or Platinum donor is never sent an automated letter; those records are routed to review for personal outreach, because a form letter to a lapsed major donor risks more than it can raise.

## Ask amount policy

All arithmetic is performed by `scripts/calculate_ask.py`, never by a language model. The calculation order is fixed and rounding happens exactly once, at the end.

1. Base ask.
   - Platinum: 40% of largest single gift.
   - Gold: 25% of largest single gift.
   - Silver: 15% of largest single gift.
   - Bronze: flat $150.
   - Lapsed (Bronze or Silver lifetime band): flat $50 re-engagement ask.
2. Loyalty uplift: if the donor gave last year, defined precisely as `last_gift_year == as_of_year - 1`, multiply by 1.10.
3. Volunteer uplift: if the donor is a volunteer, add $100.
4. Emergency multiplier: if the campaign type is `emergency_appeal`, multiply by 1.2.
5. Round once to the nearest $50 (half rounds up). Minimum ask is $50.

Guardrails applied after calculation:

- If a percentage-based ask exceeds the donor's largest single gift, the letter is flagged for review. An ask should stretch a donor, not startle them.
- Every calculation emits a step-by-step trace that is stored with the record, so any ask amount can be audited back to the rule that produced it.

## Salutation policy

- If the file provides a title: `Dear {Title} {Last Name},`
- Otherwise: `Dear {First Name} {Last Name},`
- Titles and gender are never inferred from a first name. Guessing wrong in a donation ask is far more costly than a neutral salutation.
- Lapsed donors get the same respectful salutation as everyone else. The re-engagement message belongs in the body, not in a gimmick greeting.

## Campaign messaging

The campaign paragraph comes from the approved library below. A language model may adapt phrasing or add one personalization sentence grounded in validated fields (region, most recent gift year, volunteer status), but it may never introduce numbers, promises, program claims, or urgency devices that are not in this document or the campaign config.

**Emergency appeal.** Urgent and honest. Describe the immediate need and what a gift enables. Matching language is permitted only when `match_confirmed` is `true` in the campaign config, and must name the sponsor and terms from the config. If no match is confirmed, no match is mentioned. Approved base paragraph:

> Right now, animals rescued from cruelty and neglect need emergency shelter, veterinary care, and a safe place to recover. Your gift today goes to work immediately, funding rescue operations and urgent medical treatment for animals with nowhere else to turn.

**Annual fund.** Consistency and community. A giving streak may be mentioned only when the computed streak is 2 or more consecutive years ending at `as_of_year - 1`. Approved base paragraph:

> Year after year, steady support from donors like you is what allows us to plan rescues, staff shelters, and answer every call for help. Your continued partnership is the foundation this work is built on.

**Capital campaign.** Legacy and permanence. Approved base paragraph:

> We are building spaces that will shelter and heal animals for decades to come. A gift to this campaign is a lasting investment, one that will still be saving lives long after the construction dust has settled.

**Event fundraiser.** Community and participation. Registration counts may be cited only from the `event_registered_count` config field; if it is empty, no count is mentioned. Approved base paragraph:

> Our upcoming event brings together supporters from across the community for the animals we all care about. We would love for you to be part of it.

**Unknown campaign type.** Processing stops with an error. Defaulting silently to another campaign's messaging sends donors the wrong letter at scale.

## Tier-specific closing lines

- Platinum: invite a conversation about naming and recognition opportunities. Never invent a relationship manager; the letter is signed by the configured signer.
- Gold: mention legacy giving options.
- Silver: mention the monthly giving upgrade.
- Bronze: mention peer fundraising pages.
- Lapsed: warm welcome back, mention the re-engagement gift only if `reengagement_gift` is set in the config.

## Content rules for every letter

- Lifetime giving totals are mentioned only when lifetime giving is $500 or more. Thanking someone for their "incredible generosity of $75" reads as sarcasm.
- Every factual claim in a letter must trace to a validated input field or the campaign config.
- All donor-derived text is HTML-escaped before rendering.

## Review gates

- All Platinum letters are individually reviewed by a human before sending. No exceptions.
- Any letter carrying a warning (confidence below 1.00) is flagged for recommended review; below 0.70 review is mandatory.
- Records in the exceptions report never generate letters until a data steward resolves them.
- Nothing produced by this skill is ever sent automatically. Output is files for review, not outbound mail.
