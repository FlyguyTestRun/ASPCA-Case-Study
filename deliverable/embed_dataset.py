"""Build donor-data-review.html from the template plus the current dataset.

The template (donor-data-review.template.html) keeps the __DATASET_JSON__
and __CAMPAIGN_CONFIG_JSON__ placeholders and is never modified; this
script only writes the built output file. Re-run any time the fixture or
the pipeline output changes.

Run after build_dataset.py, from the repository root:
    python deliverable/build_dataset.py
    python deliverable/embed_dataset.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "deliverable" / "donor-data-review.template.html"
OUTPUT = ROOT / "deliverable" / "donor-data-review.html"
DATASET = ROOT / "deliverable" / "dataset.json"
CAMPAIGN_CONFIG = ROOT / "deliverable" / "campaign_config_embed.json"


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    html = TEMPLATE.read_text(encoding="utf-8")

    if "__DATASET_JSON__" not in html:
        raise SystemExit("dataset placeholder not found in template")
    # Dataset now embeds full generated-letter HTML (see build_dataset.py);
    # escape a literal "</script" inside that content so the browser's HTML
    # parser cannot close this script block early, regardless of what any
    # future letter template happens to contain.
    dataset_json = json.dumps(data).replace("</script", "<\\/script")
    html = html.replace("__DATASET_JSON__", dataset_json)

    if "__CAMPAIGN_CONFIG_JSON__" not in html:
        raise SystemExit("campaign config placeholder not found in template")
    config_data = json.loads(CAMPAIGN_CONFIG.read_text(encoding="utf-8"))
    config_json = json.dumps(config_data).replace("</script", "<\\/script")
    html = html.replace("__CAMPAIGN_CONFIG_JSON__", config_json)

    OUTPUT.write_text(html, encoding="utf-8")
    print(f"embedded {len(data)} donor records into {OUTPUT}")
    print(f"output size: {OUTPUT.stat().st_size / 1_000_000:.1f} MB")


if __name__ == "__main__":
    main()
