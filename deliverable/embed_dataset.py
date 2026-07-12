"""Build donor-data-review.html from the template plus the current dataset.

The template (donor-data-review.template.html) keeps the __DATASET_JSON__
placeholder and is never modified; this script only writes the built output
file. Re-run any time the fixture or pipeline output changes.

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

data = json.loads(DATASET.read_text(encoding="utf-8"))
html = TEMPLATE.read_text(encoding="utf-8")
if "__DATASET_JSON__" not in html:
    raise SystemExit("placeholder not found in template")
html = html.replace("__DATASET_JSON__", json.dumps(data))
OUTPUT.write_text(html, encoding="utf-8")
print(f"embedded {len(data)} donor records into {OUTPUT}")
