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
import time
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


def build_letter_model(donor: dict, config: dict, style: dict) -> dict:
    """Assemble the structured letter model. Validated against
    references/letter_schema.json before anything is rendered."""
    letter_date = date.fromisoformat(config["as_of_date"])
    return {
        "donor_id": donor["donor_id"],
        "letter_date": f"{letter_date:%B} {letter_date.day}, {letter_date.year}",
        "salutation": build_salutation(donor),
        "opening_paragraph": build_opening(donor, config["charity_name"]),
        "campaign_paragraph": build_campaign_paragraph(donor, config),
        "ask_paragraph": build_ask_paragraph(donor, config),
        "closing_phrase": style.get("closing_phrase", rules.DEFAULT_CLOSING),
        "ps_line": style.get("ps_line", ""),
        "signer_name": config["signer_name"],
        "signer_title": config["signer_title"],
        "charity_name": config["charity_name"],
        "donation_url": config["donation_url"],
    }


def render_letter(model: dict, template: str) -> str:
    """Turn a schema-valid letter model into HTML. Rendering is the last step
    and does no thinking of its own."""
    ps_block = ""
    if model["ps_line"]:
        ps_block = f"<p>P.S. {html.escape(model['ps_line'])}</p>"
    fields = {
        "DATE": model["letter_date"],
        "SALUTATION": html.escape(model["salutation"]),
        "OPENING_PARAGRAPH": html.escape(model["opening_paragraph"]),
        "CAMPAIGN_PARAGRAPH": html.escape(model["campaign_paragraph"]),
        "ASK_PARAGRAPH": html.escape(model["ask_paragraph"]),
        "DONATION_URL": html.escape(model["donation_url"], quote=True),
        "SIGNER_NAME": html.escape(model["signer_name"]),
        "SIGNER_TITLE": html.escape(model["signer_title"]),
        "CHARITY_NAME": html.escape(model["charity_name"]),
        "CLOSING_PHRASE": html.escape(model["closing_phrase"]),
        "PS_BLOCK": ps_block,
    }
    rendered = template
    for key, value in fields.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def load_style(style_path: Path | None) -> dict:
    """Load and sanitize an approved style profile; absent means defaults."""
    if style_path is None or not style_path.exists():
        return {}
    profile = json.loads(style_path.read_text(encoding="utf-8"))
    clean, ignored = rules.sanitize_style_profile(profile)
    for reason in ignored:
        print(f"STYLE GUARDRAIL: {reason}", file=sys.stderr)
    return clean


def run(config_path: Path, workdir: Path, outdir: Path, template_path: Path,
        style_path: Path | None = None) -> list[dict]:
    started = time.perf_counter()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    template = template_path.read_text(encoding="utf-8")
    style = load_style(style_path)
    schema = json.loads(
        (Path(__file__).resolve().parent.parent / "references" / "letter_schema.json")
        .read_text(encoding="utf-8")
    )

    computed_path = workdir / "computed.csv"
    if not computed_path.exists():
        print("ERROR: work/computed.csv not found; run calculate_ask.py first", file=sys.stderr)
        raise SystemExit(2)

    with computed_path.open(newline="", encoding="utf-8") as handle:
        donors = list(csv.DictReader(handle))

    letters_dir = outdir / "letters"
    letters_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    schema_rejections = 0
    models_path = workdir / "letter_models.jsonl"
    with models_path.open("w", encoding="utf-8") as models_out:
        for donor in donors:
            entry = {
                "donor_id": donor["donor_id"],
                "donor_name": donor["donor_name"],
                "tier": donor["tier"],
                "status": donor["status"],
                "ask_amount": donor["ask_amount"],
                "confidence": donor["confidence"],
                "confidence_band": donor.get("confidence_band", ""),
                "review_level": donor["review_level"],
                "warnings": donor["warnings"],
                "review_reasons": donor["review_reasons"],
                "letter_file": "",
            }
            if donor["ask_amount"]:
                model = build_letter_model(donor, config, style)
                errors = rules.validate_letter_model(model, schema)
                if errors:
                    schema_rejections += 1
                    entry["review_level"] = "mandatory"
                    reasons = [donor["review_reasons"]] if donor["review_reasons"] else []
                    reasons.append(f"letter failed schema validation: {'; '.join(errors)}")
                    entry["review_reasons"] = " | ".join(reasons)
                else:
                    models_out.write(json.dumps(model) + "\n")
                    letter_path = letters_dir / f"{donor['donor_id']}.html"
                    letter_path.write_text(render_letter(model, template), encoding="utf-8")
                    entry["letter_file"] = f"letters/{donor['donor_id']}.html"
            manifest.append(entry)

    manifest_path = outdir / "manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest[0].keys()) if manifest else [])
        writer.writeheader()
        writer.writerows(rules.csv_safe_row(entry) for entry in manifest)

    letters = sum(1 for entry in manifest if entry["letter_file"])
    rules.record_stage_metrics(workdir, "generate", (time.perf_counter() - started) * 1000, {
        "letters_written": letters,
        "manifest_rows": len(manifest),
        "schema_rejections": schema_rejections,
    })
    print(f"letters written:    {letters}")
    print(f"schema rejections:  {schema_rejections}")
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
    parser.add_argument(
        "--style", default=Path("feedback/style_profile.json"), type=Path,
        help="approved style profile; missing file means house defaults",
    )
    args = parser.parse_args()
    run(args.config, args.workdir, args.outdir, args.template, args.style)


if __name__ == "__main__":
    main()
