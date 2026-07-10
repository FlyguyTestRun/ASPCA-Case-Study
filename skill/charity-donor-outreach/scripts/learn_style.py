"""Learn letter style from reviewer edits, within hard guardrails.

Usage (two separate steps, by design):

    # 1. Compare edited letters against the originals and write suggestions
    python learn_style.py --originals output/letters --edited feedback/edited_letters

    # 2. A named person adopts a suggestion into the active style profile
    python learn_style.py --adopt closing_phrase --approved-by "Jordan Ellis"

How it works: reviewers save their edited copies of generated letters into a
folder, keeping the same file names. This script diffs each pair and looks
for style-level changes only: a different closing phrase, or a P.S. line
added after the signature. A change becomes a suggestion only after it
appears identically in at least 3 edited letters, and only if it passes the
style guardrails (no numbers, no dollar amounts, no urgency or matching
language). Everything else it finds is reported as "manual edits detected"
for a human to look at; it is never learned automatically.

Adopting a suggestion is a second, explicit, named step. The profile it
writes affects the personality of future letters (closing, P.S.) and can
never touch asks, claims, salutations, or campaign facts: generation
re-sanitizes the profile through the same guardrails on every run.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import donor_rules as rules

CLOSING_RE = re.compile(r"<p>([^<]{1,80}),<br>\s*<strong>")
PS_RE = re.compile(r"<p>P\.S\.\s*(.{1,300}?)</p>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


def extract_closing(html_text: str) -> str | None:
    match = CLOSING_RE.search(html_text)
    return match.group(1).strip() if match else None


def extract_ps(html_text: str) -> str | None:
    match = PS_RE.search(html_text)
    return match.group(1).strip() if match else None


def visible_text(html_text: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", html_text)).strip()


def learn(originals_dir: Path, edited_dir: Path, workdir: Path) -> dict:
    closings: Counter[str] = Counter()
    ps_lines: Counter[str] = Counter()
    other_edits: list[str] = []
    pairs = 0

    for edited_path in sorted(edited_dir.glob("*.html")):
        original_path = originals_dir / edited_path.name
        if not original_path.exists():
            other_edits.append(f"{edited_path.name}: no matching original, skipped")
            continue
        pairs += 1
        original = original_path.read_text(encoding="utf-8")
        edited = edited_path.read_text(encoding="utf-8")

        orig_closing = extract_closing(original)
        new_closing = extract_closing(edited)
        if new_closing and new_closing != orig_closing:
            closings[new_closing] += 1

        orig_ps = extract_ps(original)
        new_ps = extract_ps(edited)
        if new_ps and new_ps != orig_ps:
            ps_lines[new_ps] += 1

        # Anything beyond closing and P.S. is reported, never learned.
        stripped_orig = visible_text(CLOSING_RE.sub("", PS_RE.sub("", original)))
        stripped_edit = visible_text(CLOSING_RE.sub("", PS_RE.sub("", edited)))
        if stripped_orig != stripped_edit:
            other_edits.append(
                f"{edited_path.name}: body text was edited; body language is "
                "policy-controlled, propose the change in references/policy.md"
            )

    def build(counter: Counter, field: str, **checks) -> list[dict]:
        suggestions = []
        for value, count in counter.most_common():
            entry = {"field": field, "value": value, "evidence_edits": count}
            if count < rules.STYLE_MIN_EVIDENCE:
                entry["status"] = (
                    f"insufficient evidence ({count} of {rules.STYLE_MIN_EVIDENCE} "
                    "identical edits required)"
                )
            else:
                clean, ignored = rules.sanitize_style_profile({field: value})
                entry["status"] = "eligible for adoption" if clean else ignored[0]
            suggestions.append(entry)
        return suggestions

    report = {
        "generated_on": str(date.today()),
        "letter_pairs_compared": pairs,
        "suggestions": build(closings, "closing_phrase") + build(ps_lines, "ps_line"),
        "manual_edits_detected": other_edits,
    }
    workdir.mkdir(parents=True, exist_ok=True)
    out = workdir / "style_suggestions.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"letter pairs compared: {pairs}")
    for suggestion in report["suggestions"]:
        print(f"  {suggestion['field']} = {suggestion['value']!r} "
              f"(seen {suggestion['evidence_edits']}x): {suggestion['status']}")
    for note in other_edits:
        print(f"  NOTE {note}")
    print(f"suggestions written to {out}")
    print("Nothing was adopted. Run with --adopt and --approved-by to apply one.")
    return report


def adopt(field: str, approved_by: str, workdir: Path, profile_path: Path) -> None:
    suggestions_path = workdir / "style_suggestions.json"
    if not suggestions_path.exists():
        print("ERROR: no style_suggestions.json; run the learning step first", file=sys.stderr)
        raise SystemExit(2)
    report = json.loads(suggestions_path.read_text(encoding="utf-8"))
    eligible = [
        s for s in report["suggestions"]
        if s["field"] == field and s["status"] == "eligible for adoption"
    ]
    if not eligible:
        print(f"ERROR: no eligible {field} suggestion to adopt", file=sys.stderr)
        raise SystemExit(2)
    best = eligible[0]

    profile = {}
    if profile_path.exists():
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile[field] = best["value"]
    profile["approved_by"] = approved_by
    profile["approved_on"] = str(date.today())
    profile["evidence_edits"] = best["evidence_edits"]

    clean, ignored = rules.sanitize_style_profile(profile)
    if field not in clean:
        print(f"ERROR: adoption blocked by style guardrails: {ignored}", file=sys.stderr)
        raise SystemExit(2)

    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    print(f"adopted {field} = {best['value']!r} "
          f"(approved by {approved_by}, evidence {best['evidence_edits']} edits)")
    print(f"profile: {profile_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--originals", type=Path, default=Path("output/letters"))
    parser.add_argument("--edited", type=Path, default=Path("feedback/edited_letters"))
    parser.add_argument("--workdir", type=Path, default=Path("work"))
    parser.add_argument("--profile", type=Path, default=Path("feedback/style_profile.json"))
    parser.add_argument("--adopt", choices=["closing_phrase", "ps_line"])
    parser.add_argument("--approved-by", default="")
    args = parser.parse_args()

    if args.adopt:
        if not args.approved_by.strip():
            print("ERROR: --adopt requires --approved-by with a person's name", file=sys.stderr)
            raise SystemExit(2)
        adopt(args.adopt, args.approved_by.strip(), args.workdir, args.profile)
    else:
        if not args.edited.exists():
            print(f"ERROR: edited-letters folder not found: {args.edited}", file=sys.stderr)
            raise SystemExit(2)
        learn(args.originals, args.edited, args.workdir)


if __name__ == "__main__":
    main()
