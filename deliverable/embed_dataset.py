"""Build donor-data-review.html from the template plus the current dataset
and the walkthrough narration audio.

The template (donor-data-review.template.html) keeps the __DATASET_JSON__
and src="__AUDIO_DATA_URI__" placeholders and is never modified; this script
only writes the built output file. Re-run any time the fixture, the pipeline
output, or the narration audio changes.

The audio is embedded as a base64 data URI rather than referenced by path,
so the deliverable stays a single file: open it anywhere, email it, no
sibling files required. If no audio file is found, the placeholder is
removed instead, and the walkthrough falls back to timed captions with no
narration, still fully functional.

Run after build_dataset.py, from the repository root:
    python deliverable/build_dataset.py
    python deliverable/embed_dataset.py
"""

import base64
import json
import mimetypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "deliverable" / "donor-data-review.template.html"
OUTPUT = ROOT / "deliverable" / "donor-data-review.html"
DATASET = ROOT / "deliverable" / "dataset.json"
AUDIO_CANDIDATES = [
    ROOT / "app" / "assets" / "tutorial_walkthrough.wav",
    ROOT / "app" / "assets" / "tutorial_walkthrough.mp3",
]


def find_audio() -> Path | None:
    for candidate in AUDIO_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    html = TEMPLATE.read_text(encoding="utf-8")

    if "__DATASET_JSON__" not in html:
        raise SystemExit("dataset placeholder not found in template")
    html = html.replace("__DATASET_JSON__", json.dumps(data))

    if 'src="__AUDIO_DATA_URI__"' not in html:
        raise SystemExit("audio placeholder not found in template")
    audio_path = find_audio()
    if audio_path is not None:
        mime = mimetypes.guess_type(audio_path.name)[0] or "audio/wav"
        encoded = base64.b64encode(audio_path.read_bytes()).decode("ascii")
        html = html.replace(
            'src="__AUDIO_DATA_URI__"', f'src="data:{mime};base64,{encoded}"'
        )
        audio_note = f"{audio_path.name}, {audio_path.stat().st_size / 1_000_000:.1f} MB"
    else:
        html = html.replace(' src="__AUDIO_DATA_URI__"', "")
        audio_note = "none found, walkthrough will use timed captions only"

    OUTPUT.write_text(html, encoding="utf-8")
    print(f"embedded {len(data)} donor records into {OUTPUT}")
    print(f"narration audio: {audio_note}")
    print(f"output size: {OUTPUT.stat().st_size / 1_000_000:.1f} MB")


if __name__ == "__main__":
    main()
