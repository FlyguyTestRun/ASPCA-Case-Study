# Recording the walkthrough

The guided tour in `donor-data-review.html` has no embedded audio on purpose ([ADR 0044](../docs/adr/0044-the-walkthrough-becomes-a-live-demonstration.md)): a synthesized voice was never going to stop sounding robotic, and the actual fix is a real recording. The captions below are exactly what's on screen at each step, in order, so you can read them aloud while the tour performs the real, live actions in the background: filtering to the flagged rows, applying the correction, checking off review, opening the export gate.

## Setup

1. Open `donor-data-review.html` (the live link or the local file) in a normal browser window, sized comfortably (1280×800 or your usual window size is fine).
2. Start a screen recorder before you click anything:
   - **Windows, built in, no install:** `Win + Alt + R` starts and stops a recording of the focused window. Saved to `Videos\Captures`.
   - **Windows, more control (webcam corner, mic level meter, trimming):** [OBS Studio](https://obsproject.com), free. Add a "Display Capture" or "Window Capture" source, a mic source, hit Start Recording.
3. Click **Start the guided walkthrough**. Use **Pause** to stop the auto-advance timer any time you want to talk longer than a caption's default pace allows, **Next** to move on when you're ready, **Back** if you want to redo a beat. Nothing here is timed against you.
4. If you flub a section, `End` the tour, refresh the page (this resets everything to the clean starting state), and start again. Cheap to redo.

## The script

### 1 / 17 — The result
A well written prompt raises the odds a model behaves. It never guarantees it. Fifty donor records ran through this redesigned system. Here is what verified actually looks like, why the difference matters, and by the end of this walkthrough, exactly how to run your own donor file through the same checks.

### 2 / 17 — What the original prompt would have done
The original skill embedded the donor list inside its own instructions, trusted every stated field on faith, and asked a model to do arithmetic. Doug's brief asked for outreach that is consistent, reliable, and scalable. A prompt that trusts unverified data on faith is none of those three: not consistent, because the same donor can get a different answer depending on how the model reads the file that day; not reliable, because a wrong tier means a wrong ask, sent with total confidence; not scalable, because every one of those risks multiplies with every donor added to the list.

### 3 / 17 — The gap, in dollars
Ruth Andersen's file says Silver. Her actual giving computes to Gold. Followed literally, the original skill's own steps ask her for fifteen hundred and six dollars. This system recomputes her tier from her real gift history, catches the mismatch, and asks for twenty-four fifty. Nine hundred and forty-four dollars, from one label nobody checked against the money it was supposed to describe.

### 4 / 17 — SKILL.md: the file that runs this, not explains it
SKILL.md is what an AI assistant actually reads to trigger this system. It holds the required inputs, the exact command for every stage, and five hard rules, nothing else. The reasoning behind each of those lives in decision records, one link away, not inline, because every line in this file costs context at the exact moment an agent is deciding what to do next.

### 5 / 17 — Validate: never trust, always verify
validate_input.py is the first thing that touches a donor file, before a model ever sees it. It recomputes every tier, total, and date from the source numbers and checks the stated value against what it actually computes, writing anything that disagrees to an exceptions report instead of guessing. This single stage is what caught the four mislabeled tiers in this file, including one my own manual read of the table had missed on the first pass.

### 6 / 17 — Calculate: the money, once, in code
calculate_ask.py runs the ask formula once, in a fixed order, the same way every time, with a full trace attached to every donor. A prompt asking a model to do arithmetic is still just asking; there is no version of a language model that guarantees the same input produces the same output twice. Running the math in code instead makes a wrong calculation structurally impossible, not just unlikely.

### 7 / 17 — Generate: a letter is checked before it exists
generate_letters.py assembles the letter as structured data first, a donor name, a tier, an ask amount, a closing, and checks that structure against a schema before any HTML is ever written. An unconfirmed matching claim or an invented fact cannot reach a donor here, not because the model was told not to write one, but because there is no field in the checked structure for it to go in.

### 8 / 17 — The system admits what it does not know
Below ninety percent confidence, a person reviews before anything goes out. Below seventy, the system stops and asks for help instead of guessing. Every Platinum donor is reviewed regardless of score. That is a harness admitting uncertainty instead of hiding it, at exactly the scale where a hidden mistake would otherwise reach a real donor.

### 9 / 17 — The actual scripts, not a description of them
Every stage above is a real, short Python file on GitHub, not a summary of one. validate_input.py, calculate_ask.py, generate_letters.py, and the shared policy module donor_rules.py that all three of them import from, one implementation of tier, date, and ask logic, used everywhere it matters.

### 10 / 17 — Five layers, one job each
Schema validation twice, once on the raw row and once on the assembled letter. Deterministic arithmetic. A confidence rubric that escalates instead of hiding. Mandatory human gates on the highest-stakes records. One bounded exception where a model may touch phrasing, never a fact or a number. That is the whole harness: bounded probability where a guarantee is not possible, a guarantee everywhere it is.

### 11 / 17 — What this system chose not to build
No orchestration framework, no vector database, no machine learning, because a three-stage pipeline for fifty donors does not need any of them yet. Each one has a written trigger, the specific condition that would justify adding it. Restraint is a decision here, documented, not an oversight.

### 12 / 17 — What a caught error actually looks like *(live: filters to the 4 flagged rows)*
This is the table, filtered to exactly what needs correction right now: four donors, including Shirley Magnusdottir, filed Silver, computing to Gold from her own gift history. This is not a mockup. This is the real embedded dataset, filtered live, the same way you would filter it on your own file.

### 13 / 17 — One click, watch it happen *(live: applies the correction — Shirley's row visibly flips to Gold)*
This is the same button you would click on a real file. Watch Shirley Magnusdottir's stated tier flip from Silver to Gold, live, right now, not narrated after the fact. The suggested value comes from the same recomputed gift history the validator already checked; a person is still the one clicking approve.

### 14 / 17 — A person still has to look *(live: all 5 mandatory reviews checked off)*
Correcting the data does not skip review. Every Platinum donor, and anyone a warning still flags, needs a person to check them off before this batch can be considered handled. On a real file you would do this one row at a time as you actually review each one; this button exists for exactly the moment you have already decided they are all clear.

### 15 / 17 — Everything Doug needs, in one file *(live: export gate unlocks — button stays clickable if you want to show the actual download)*
The gate is open now. This button packages the cleaned data, every generated letter, a manifest, and a snapshot of this exact reviewed state into one dated ZIP. The tour will not click it for you, a file downloading itself without being asked is a bad habit for any tool to have, but it is live and ready right now if you want to see it yourself.

### 16 / 17 — How to run a different file through this *(live: the upload panel opens)*
Everything above ran on the case study's own fifty donors. Upload a different file in the same shape here, and the exact same checks run against it: tiers and lapsed status recomputed, mismatches held for correction, nothing trusted on faith. Growing an existing list works the same way, merge a second file in without losing review state on any donor whose data did not actually change.

### 17 / 17 — The whole difference, in one line
A well designed prompt improves probability. A well designed harness replaces probability with a guarantee, wherever a guarantee is possible, and asks a human wherever it is not. Same model. Completely different system, at any scale you actually need to run it at.

## After recording

This file, the recording itself, and `donor-data-review.html` are not wired together, on purpose: the page never depends on a video existing, so nothing breaks if you skip this or redo it later. If you want to send the recording to Doug, it's a separate attachment or link alongside the existing package, not something to embed back into the HTML.
