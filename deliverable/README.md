# Standalone Deliverable

`donor-data-review.html` is a single self-contained file: open it in any
browser, no server, no install, no internet connection required. It is what
goes to Doug alongside the repository link and the assessment.

## What it does

- Opens with a "Start the two-minute walkthrough" control: a guided,
  spotlighted tour of six real, live parts of the page, narrated and
  captioned, answering one question: why a well written prompt only ever
  improves the odds a model behaves, and what a well designed harness adds
  on top of that. Built to double as a training artifact, not just a demo.
- States the verified result up front: 50 records, how many are clean, held
  for review, or need correction.
- Shows the pipeline as a diagram, each stage annotated with the specific
  problem it exists to catch.
- Lists every donor in a searchable, filterable, sortable table. Any
  highlighted cell (stated tier, largest gift, last gift year) is editable
  in place, and the tier and status logic re-runs live in the browser,
  mirroring the Python validator exactly.
- Exports a corrected CSV a data steward can hand back to the source system.

Nothing in the page sends data anywhere. It reads the embedded dataset,
computes in the browser, and writes a download to the local machine.

## The guided walkthrough

Six beats, spotlighting the verified result, each pipeline stage, the
confidence gate, one of the four real caught errors (Shirley Magnusdottir's
tier), and the closing thesis. Controls: Prev, Next, Play/Pause, End, arrow
keys, Escape. Works two ways at once:

- **With narration.** The audio is embedded as a base64 data URI in the same
  file, no second file to keep track of. Step timing is not hand-authored:
  each step gets a share of the total audio duration proportional to its
  caption's word count, so the tour re-times itself automatically for any
  narration, placeholder or real, without editing a timestamp table.
- **Without sound.** The same caption text is always on screen, so a team
  member reading over someone's shoulder, or presenting on mute, gets the
  same content a listener would hear.

The script is under two minutes at a natural reading pace, and that budget
is enforced: `tests/test_deliverable_logic.py` reads the real per-step word
counts and the real pacing constant out of the built file and fails if the
walkthrough drifts past two minutes or a step's spotlight target breaks.
See `app/assets/tutorial_transcript.md` for the script and how to record
over the placeholder narration.

## How the data gets in

The dataset is not hand-written. `build_dataset.py` runs the real pipeline
(`validate_input.py`, `calculate_ask.py`) against the fixture and writes
`dataset.json`; `embed_dataset.py` inlines that JSON into
`donor-data-review.template.html` (which keeps the `__DATASET_JSON__`
placeholder and is never modified) to produce the final
`donor-data-review.html`. Rebuild after any change to the fixture, the
policy, or the pipeline:

```bash
python deliverable/build_dataset.py
python deliverable/embed_dataset.py
```

## Why a second implementation of the tier and date logic

The page reimplements `compute_tier` and `is_lapsed` in JavaScript so edits
can be checked instantly without a server round trip. That is a real
maintenance cost: two implementations of the same two small functions,
Python in `donor_rules.py` and JavaScript here, and they must agree. `tests/
test_deliverable_logic.py` pins the JavaScript against the same fixture the
Python tests use and fails the build if they diverge. This is also exactly
how a real bug was caught while building this page: the first version of the
JavaScript compared every stated tier straight to the computed financial
tier, which is correct for Platinum, Gold, Silver, and Bronze but wrong for
the ten donors filed with the literal value "Lapsed", a status claim the
Python validator checks against computed lapsed-by-date status, never
against a financial tier. The bug inflated "needs correction" from 4 records
to 14. The same lesson applied a second time while building the walkthrough:
the test harness's own DOM stub had only ever passed by accident (a stubbed
dropdown's default value happened to make the table skip every row before
`document.createElement` was ever called), and adding the walkthrough's
`window`/`document.body` usage exposed it immediately. The stub is now a
complete, reusable headless element factory rather than a thin one that
happened to work. Decision record: [ADR 0021](../docs/adr/0021-standalone-review-artifact.md).
