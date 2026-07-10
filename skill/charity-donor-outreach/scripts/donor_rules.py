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


# Style feedback guardrails. A style profile may only adjust approved,
# personality-level knobs, and every value must pass these checks at both
# learning time and generation time. Style can never change facts, numbers,
# claims, or urgency.
STYLE_BANNED_WORDS = {
    "match", "matched", "matching", "double", "doubled", "guarantee",
    "guaranteed", "urgent", "urgently", "deadline", "wire", "cash",
}
STYLE_CLOSING_MAX_WORDS = 6
STYLE_PS_MAX_CHARS = 160
DEFAULT_CLOSING = "With gratitude"
STYLE_MIN_EVIDENCE = 3  # identical edits required before a change is even suggested


def _style_text_ok(text: str, max_words: int | None = None,
                   max_chars: int | None = None) -> bool:
    if any(ch.isdigit() for ch in text) or "$" in text or "<" in text:
        return False
    if max_words is not None and len(text.split()) > max_words:
        return False
    if max_chars is not None and len(text) > max_chars:
        return False
    words = set(re.findall(r"[a-z']+", text.lower()))
    return not (words & STYLE_BANNED_WORDS)


def sanitize_style_profile(profile: dict) -> tuple[dict, list[str]]:
    """Return only the approved style knobs whose values pass the guardrails.

    Unknown keys are dropped, so a style profile cannot smuggle changes to
    asks, claims, or any other part of a letter.
    """
    clean: dict = {}
    ignored: list[str] = []
    closing = str(profile.get("closing_phrase") or "").strip().rstrip(",")
    if closing:
        if _style_text_ok(closing, max_words=STYLE_CLOSING_MAX_WORDS):
            clean["closing_phrase"] = closing
        else:
            ignored.append(f"closing_phrase {closing!r} rejected by style guardrails")
    ps_line = str(profile.get("ps_line") or "").strip()
    if ps_line:
        if _style_text_ok(ps_line, max_chars=STYLE_PS_MAX_CHARS):
            clean["ps_line"] = ps_line
        else:
            ignored.append("ps_line rejected by style guardrails")
    for key in profile:
        if key not in ("closing_phrase", "ps_line", "approved_by", "approved_on",
                       "evidence_edits"):
            ignored.append(f"unknown style key {key!r} ignored")
    return clean, ignored


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "donor"


def split_name(full_name: str) -> tuple[str, str]:
    """Split a full name into (first, last). The last token is the family name."""
    parts = full_name.split()
    if len(parts) == 1:
        return parts[0], parts[0]
    return " ".join(parts[:-1]), parts[-1]
