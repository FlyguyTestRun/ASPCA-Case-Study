"""Render donor letters and the review manifest from computed ask data.

Usage:
    python generate_letters.py --config <campaign.json> [--workdir work] [--outdir output]

Reads work/computed.csv and writes:
    output/letters/<donor_id>.html   one letter per eligible donor
    output/manifest.csv              one row per donor for human review

Nothing is sent anywhere. The output is files for a human to review; the
manifest is the review checklist.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import donor_rules as rules

# Approved campaign paragraphs. These mirror references/policy.md; any edit
# there must be mirrored here.
CAMPAIGN_PARAGRAPHS = {
    "emergency_appeal": (
        "Right now, animals rescued from cruelty and neglect need emergency "
        "shelter, veterinary care, and a safe place to recover. Your gift today "
        "goes to work immediately, funding rescue operations and urgent medical "
        "treatment for animals with nowhere else to turn."
    ),
    "annual_fund": (
        "Year after year, steady support from donors like you is what allows us "
        "to plan rescues, staff shelters, and answer every call for help. Your "
        "continued partnership is the foundation this work is built on."
    ),
    "capital_campaign": (
        "We are building spaces that will shelter and heal animals for decades "
        "to come. A gift to this campaign is a lasting investment, one that will "
        "still be saving lives long after the construction dust has settled."
    ),
    "event_fundraiser": (
        "Our upcoming event brings together supporters from across the community "
        "for the animals we all care about. We would love for you to be part of it."
    ),
}

TIER_CLOSING_LINES = {
    "Platinum": (
        "We would also welcome a conversation about naming and recognition "
        "opportunities that celebrate your leadership in this work."
    ),
    "Gold": (
        "If you have ever considered the longer arc of your generosity, our "
        "legacy giving program is a meaningful place to explore it."
    ),
    "Silver": (
        "Many supporters at your level find monthly giving an easier and even "
        "more impactful way to help; we would be glad to set that up."
    ),
    "Bronze": (
        "If you would like to multiply your impact, starting a peer fundraising "
        "page takes just a few minutes and rallies your friends to the cause."
    ),
}


def build_salutation(donor: dict) -> str:
    if donor["title"]:
        return f"Dear {donor['title']} {donor['last_name']},"
    return f"Dear {donor['first_name']} {donor['last_name']},"


def build_opening(donor: dict, charity_name: str) -> str:
    lifetime = float(donor["lifetime_total"])
    if lifetime >= rules.LIFETIME_MENTION_MINIMUM:
        return (
            f"On behalf of everyone at {charity_name}, thank you for your "
            f"generous support. Your giving of ${lifetime:,.0f} over the years, "
            f"including your most recent gift in {donor['last_gift_year']}, has "
            "made a real difference for animals in need."
        )
    return (
        f"On behalf of everyone at {charity_name}, thank you for your support. "
        "Gifts like yours are what make this work possible."
    )


def build_campaign_paragraph(donor: dict, config: dict) -> str:
    campaign = config["campaign_type"]
    paragraph = CAMPAIGN_PARAGRAPHS[campaign]

    if campaign == "emergency_appeal" and config.get("match_confirmed"):
        sponsor = config.get("match_sponsor", "")
        terms = config.get("match_terms", "")
        paragraph += f" Thanks to {sponsor}, your gift will be {terms}."

    if campaign == "annual_fund" and int(donor["streak"]) >= 2:
        paragraph += (
            f" You have now given for {donor['streak']} consecutive years, and "
            "that kind of consistency means more than you know."
        )

    if campaign == "event_fundraiser":
        count = config.get("event_registered_count")
        if count:
            paragraph += f" {count} supporters are already registered."

    return paragraph


def build_ask_paragraph(donor: dict, config: dict) -> str:
    ask = int(donor["ask_amount"])
    if donor["status"] == "lapsed":
        text = (
            "It has been a while since we last heard from you, and we would "
            f"love to welcome you back. A gift of ${ask:,} would restart your "
            "support right where it can help the most."
        )
        gift = config.get("reengagement_gift", "")
        if gift:
            text += f" As a small thank you, we would like to send you {gift}."
        return text
    text = f"Today, I would like to invite you to consider a gift of ${ask:,}."
    closing = TIER_CLOSING_LINES.get(donor["tier"], "")
    if closing:
        text += f" {closing}"
    return text


def render_letter(donor: dict, config: dict, template: str) -> str:
    letter_date = date.fromisoformat(config["as_of_date"])
    fields = {
        "DATE": f"{letter_date:%B} {letter_date.day}, {letter_date.year}",
        "SALUTATION": html.escape(build_salutation(donor)),
        "OPENING_PARAGRAPH": html.escape(build_opening(donor, config["charity_name"])),
        "CAMPAIGN_PARAGRAPH": html.escape(build_campaign_paragraph(donor, config)),
        "ASK_PARAGRAPH": html.escape(build_ask_paragraph(donor, config)),
        "DONATION_URL": html.escape(config["donation_url"], quote=True),
        "SIGNER_NAME": html.escape(config["signer_name"]),
        "SIGNER_TITLE": html.escape(config["signer_title"]),
        "CHARITY_NAME": html.escape(config["charity_name"]),
    }
    rendered = template
    for key, value in fields.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def run(config_path: Path, workdir: Path, outdir: Path, template_path: Path) -> list[dict]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    template = template_path.read_text(encoding="utf-8")

    computed_path = workdir / "computed.csv"
    if not computed_path.exists():
        print("ERROR: work/computed.csv not found; run calculate_ask.py first", file=sys.stderr)
        raise SystemExit(2)

    with computed_path.open(newline="", encoding="utf-8") as handle:
        donors = list(csv.DictReader(handle))

    letters_dir = outdir / "letters"
    letters_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    for donor in donors:
        entry = {
            "donor_id": donor["donor_id"],
            "donor_name": donor["donor_name"],
            "tier": donor["tier"],
            "status": donor["status"],
            "ask_amount": donor["ask_amount"],
            "confidence": donor["confidence"],
            "review_level": donor["review_level"],
            "warnings": donor["warnings"],
            "review_reasons": donor["review_reasons"],
            "letter_file": "",
        }
        if donor["ask_amount"]:
            letter_path = letters_dir / f"{donor['donor_id']}.html"
            letter_path.write_text(render_letter(donor, config, template), encoding="utf-8")
            entry["letter_file"] = f"letters/{donor['donor_id']}.html"
        manifest.append(entry)

    manifest_path = outdir / "manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest[0].keys()) if manifest else [])
        writer.writeheader()
        writer.writerows(manifest)

    letters = sum(1 for entry in manifest if entry["letter_file"])
    print(f"letters written:    {letters}")
    print(f"manifest rows:      {len(manifest)}")
    print(f"manifest:           {manifest_path}")
    print("Reminder: nothing is sent automatically. Review the manifest, then")
    print("individually review every letter marked mandatory before any send.")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--workdir", default=Path("work"), type=Path)
    parser.add_argument("--outdir", default=Path("output"), type=Path)
    parser.add_argument(
        "--template",
        default=Path(__file__).resolve().parent.parent / "assets" / "template.html",
        type=Path,
    )
    args = parser.parse_args()
    run(args.config, args.workdir, args.outdir, args.template)


if __name__ == "__main__":
    main()
