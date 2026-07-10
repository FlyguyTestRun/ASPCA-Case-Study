"""Shared policy implementation for the charity-donor-outreach skill.

Every threshold in this module mirrors references/policy.md. The pipeline
scripts import from here so the policy has exactly one implementation. If
policy.md and this file ever disagree, that is a defect.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

TIER_MINIMUMS = [
    ("Platinum", 50_000),
    ("Gold", 10_000),
    ("Silver", 1_000),
    ("Bronze", 0),
]
FINANCIAL_TIERS = tuple(name for name, _ in TIER_MINIMUMS)

PERCENT_ASK = {"Platinum": 0.40, "Gold": 0.25, "Silver": 0.15}
FLAT_ASK_BRONZE = 150
FLAT_ASK_LAPSED = 50
LAPSED_AFTER_YEARS = 3
LOYALTY_UPLIFT = 0.10
VOLUNTEER_UPLIFT = 100
EMERGENCY_MULTIPLIER = 1.2
ROUND_TO = 50
MIN_ASK = 50

LIFETIME_MENTION_MINIMUM = 500

CAMPAIGN_TYPES = (
    "emergency_appeal",
    "annual_fund",
    "capital_campaign",
    "event_fundraiser",
)

REVIEW_MANDATORY_BELOW = 0.70
WARNING_CONFIDENCE_PENALTY = 0.10

_GIFT_TOKEN = re.compile(r"^\s*(\d{4})\s*:\s*\$?\s*([\d,]+(?:\.\d+)?)\s*$")
_MONEY = re.compile(r"^\s*\$?\s*([\d,]+(?:\.\d+)?)\s*$")


def parse_gifts(raw: str | None) -> list[tuple[int, float]]:
    """Parse a pipe-separated ``year:amount`` string into (year, amount) pairs.

    Raises ValueError with a specific message on any malformed entry. The
    pipeline never guesses at what a broken gift record was supposed to say.
    """
    if raw is None or not str(raw).strip():
        raise ValueError("gifts field is empty")
    gifts: list[tuple[int, float]] = []
    for token in str(raw).split("|"):
        match = _GIFT_TOKEN.match(token)
        if not match:
            raise ValueError(f"unparseable gift entry: {token.strip()!r}")
        year = int(match.group(1))
        amount = float(match.group(2).replace(",", ""))
        if amount <= 0:
            raise ValueError(f"non-positive gift amount: {token.strip()!r}")
        gifts.append((year, amount))
    return sorted(gifts)


def parse_money(raw: str | None) -> float | None:
    """Parse a stated money value. Returns None for blank, raises on garbage."""
    if raw is None or not str(raw).strip():
        return None
    match = _MONEY.match(str(raw))
    if not match:
        raise ValueError(f"unparseable amount: {raw!r}")
    return float(match.group(1).replace(",", ""))


def compute_tier(lifetime_total: float) -> str:
    for tier, minimum in TIER_MINIMUMS:
        if lifetime_total >= minimum:
            return tier
    return "Bronze"


def is_lapsed(last_gift_year: int, as_of_year: int) -> bool:
    return (as_of_year - last_gift_year) > LAPSED_AFTER_YEARS


def giving_streak(gift_years, as_of_year: int) -> int:
    """Consecutive giving years ending at ``as_of_year - 1``."""
    years = set(int(y) for y in gift_years)
    streak = 0
    year = as_of_year - 1
    while year in years:
        streak += 1
        year -= 1
    return streak


def round_half_up(amount: float, step: int = ROUND_TO) -> int:
    """Round to the nearest ``step`` with halves rounding up.

    Python's built-in round() rounds halves to the nearest even number,
    which would make ask amounts depend on parity. Donors deserve better.
    """
    return int((amount + step / 2) // step) * step


@dataclass
class AskResult:
    amount: int | None
    trace: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    review_reasons: list[str] = field(default_factory=list)


def compute_ask(
    tier: str,
    lapsed: bool,
    largest_gift: float,
    last_gift_year: int,
    volunteer: bool,
    campaign_type: str,
    as_of_year: int,
) -> AskResult:
    """Deterministic ask calculation per references/policy.md.

    Order is fixed: base, loyalty, volunteer, emergency, then one rounding.
    """
    result = AskResult(amount=None)

    if lapsed and tier in ("Gold", "Platinum"):
        result.review_reasons.append(
            f"lapsed {tier} donor: no automated letter, route to personal outreach"
        )
        result.trace.append("lapsed major donor, ask calculation skipped by policy")
        return result

    if lapsed:
        amount = float(FLAT_ASK_LAPSED)
        result.trace.append(f"base: lapsed re-engagement flat ${FLAT_ASK_LAPSED}")
    elif tier in PERCENT_ASK:
        pct = PERCENT_ASK[tier]
        amount = largest_gift * pct
        result.trace.append(
            f"base: {tier} {pct:.0%} of largest gift ${largest_gift:,.0f} = ${amount:,.2f}"
        )
    else:
        amount = float(FLAT_ASK_BRONZE)
        result.trace.append(f"base: Bronze flat ${FLAT_ASK_BRONZE}")

    if last_gift_year == as_of_year - 1:
        amount *= 1 + LOYALTY_UPLIFT
        result.trace.append(
            f"loyalty uplift: gave in {as_of_year - 1}, x{1 + LOYALTY_UPLIFT:.2f} = ${amount:,.2f}"
        )
    if volunteer:
        amount += VOLUNTEER_UPLIFT
        result.trace.append(f"volunteer uplift: +${VOLUNTEER_UPLIFT} = ${amount:,.2f}")
    if campaign_type == "emergency_appeal":
        amount *= EMERGENCY_MULTIPLIER
        result.trace.append(
            f"emergency multiplier: x{EMERGENCY_MULTIPLIER} = ${amount:,.2f}"
        )

    rounded = max(round_half_up(amount), MIN_ASK)
    result.trace.append(f"rounded once to nearest ${ROUND_TO}: ${rounded:,}")
    result.amount = rounded

    if not lapsed and tier in PERCENT_ASK and rounded > largest_gift:
        result.warnings.append(
            f"computed ask ${rounded:,} exceeds largest single gift ${largest_gift:,.0f}"
        )

    return result


def confidence_score(warning_count: int) -> float:
    score = 1.0 - WARNING_CONFIDENCE_PENALTY * warning_count
    return round(max(score, 0.0), 2)


def review_level(tier: str, confidence: float, review_reasons) -> str:
    if tier == "Platinum" or review_reasons or confidence < REVIEW_MANDATORY_BELOW:
        return "mandatory"
    if confidence < 1.0:
        return "recommended"
    return "none"


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "donor"


def split_name(full_name: str) -> tuple[str, str]:
    """Split a full name into (first, last). The last token is the family name."""
    parts = full_name.split()
    if len(parts) == 1:
        return parts[0], parts[0]
    return " ".join(parts[:-1]), parts[-1]
