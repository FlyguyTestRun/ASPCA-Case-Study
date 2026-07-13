# Standalone Deliverable

`donor-data-review.html` is a single self-contained file: open it in any
browser, no server, no install, no internet connection required. It is meant
to travel alongside the repository link and the written assessment, viewable
by anyone regardless of their technical setup.

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
  mirroring the Python validator exactly. A Review column shows the same
  letter-eligibility conditions the pipeline enforces downstream: blocked
  pending correction, routed to personal outreach, mandatory or recommended
  review, or clear for an automated letter. The last gift year displays as
  an end-of-year date (`12/31/2020`), the source data's own year with no
  invented day, edited and exported the same way as before.
- Expanding a donor's row shows the ask calculation trace and, when the
  pipeline actually produced one, the real generated letter, rendered
  exactly as written in a sandboxed frame. A donor with no letter shows the
  specific reason (held pending correction, or routed to personal outreach)
  instead of a blank space.
- Accepts an upload of the case study's own unedited donor file, or any file
  in the same shape, and runs it through the same checks: "Apply suggested
  corrections" approves every held mismatch at once, the way
  `apply_corrections.py` does on the command line. "Save cleaned dataset"
  keeps the corrected result in the browser (`localStorage`) so it survives
  a reload; "Restore saved dataset" brings it back on a later visit.
- Exports a cleaned CSV in the exact shape `validate_input.py` reads, so it
  can be handed straight back to the real pipeline, with no remapping,
  before `calculate_ask.py` and `generate_letters.py` run. Ask amounts and
  letter text are still computed nowhere but Python; see "Why a second
  implementation" below for why the browser stops at tier and date logic.
- Every mandatory-review donor gets a "Reviewed" checkbox, and a "Required
  reviews: X of Y complete" indicator tracks progress across the whole
  file, not just what is currently visible under a search or filter.
- "Download dated archive" stays locked until every mandatory-review donor
  is checked off, then packages the cleaned CSV, every generated letter,
  and a manifest (tier, ask, confidence, review level, reviewed status, and
  letter file or reason for none, per donor) into one
  `donor-archive-<timestamp>.zip`, built by a small dependency-free ZIP
  writer (CRC32 plus a minimal STORED-method archive) since the file has to
  stay self-contained, no library, no build step.
- The pipeline diagram names the real script at each stage and, for the
  generate stage, its output path, and a "Scripts on GitHub" panel links
  directly to `validate_input.py`, `calculate_ask.py`, `generate_letters.py`,
  and the shared `donor_rules.py`, not a description of them.
- A "What this case study asked for" section states the brief's two tasks
  plainly, and a "Same donor, two approaches" section computes one donor's
  ask both ways from the same raw record: the original skill's own literal
  steps against the rewrite's, a real dollar-figure difference, not an
  assertion.
- An architecture section explains what changed in `SKILL.md` (181 to 141
  lines, every command byte-identical) and why a harness of deterministic
  checks surrounds the model at all: a prompt only ever raises the odds a
  model behaves correctly, and the checks convert bounded parts of that
  probability into a guarantee, each one linked to its decision record. A
  read-only panel below it displays the actual campaign configuration that
  produced every number on the page, embedded at build time; it is read-only
  because the browser never recomputes an ask, so an editable copy would
  misrepresent what changing a value does.
- A style-learning tool, ported from the review app: upload a set of edited
  letters and it suggests a closing phrase or P.S. line once the same edit
  appears identically across at least three of them, checked against the
  same guardrails the Python side enforces (no banned words, no links, a
  length cap), and downloadable as a `style_profile.json` for the real
  pipeline to pick up.
- A second donor file can be uploaded to merge into the currently loaded
  list, matched by donor name (normalized for case and whitespace). A donor
  present in both files with different data is held for review, exactly the
  way a tier mismatch already is, with a side-by-side comparison and a
  one-click resolution either way, never silently overwritten; a
  punctuation-stripped secondary key flags likely near-duplicate spellings
  of the same name for a person to look at. A session-local archive log
  (browser storage only, never the file contents) records what was
  downloaded earlier in the same browser.

Nothing in the page sends data anywhere. It reads the embedded dataset (or
an uploaded file), computes and stores in the browser, and writes a
download to the local machine. Design records: [ADR 0029](../docs/adr/0029-browser-side-upload-clean-and-persist.md), [ADR 0030](../docs/adr/0030-letter-preview-and-date-display.md), [ADR 0035](../docs/adr/0035-html-review-gate-and-dated-archive.md), [ADR 0037](../docs/adr/0037-streamlit-capabilities-merged-into-the-deliverable.md).

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
(`validate_input.py`, `calculate_ask.py`, `generate_letters.py`) against the
fixture, into a scratch directory never the committed `output/`, and writes
`dataset.json`, letter HTML included for every donor the run actually
produced one for; `embed_dataset.py` inlines that JSON into
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
