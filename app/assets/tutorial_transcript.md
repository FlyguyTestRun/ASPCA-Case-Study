# Walkthrough script

Read for the guided walkthrough embedded in `deliverable/donor-data-review.html`. Six beats, under two minutes total, each matched to a spotlighted part of the page. This script is also the basis for the training point worth carrying to the team: a well-written prompt only ever improves the odds a model behaves; a well-designed harness converts parts of that into a guarantee.

Recording notes: natural pace, brief pause between beats, no need to rush. See `app/assets/README.md` for how to record and swap this in.

---

**1. The result.**
A well written prompt raises the odds a model behaves. It never guarantees it. Fifty donor records ran through this redesigned system. Here is what verified actually looks like, and why the difference matters.

**2. Checkpoint one: never trust, always verify.**
Before a model ever sees this data, every donor's tier, total, and date gets recomputed from the source numbers and checked in code. This single stage caught four donors filed under the wrong tier.

**3. Checkpoints two and three: money and language, not guesses.**
Arithmetic runs once, in code, the same way every time. Every letter is checked against a schema before it becomes a letter. A prompt asking a model to calculate or promise something is still just asking. This makes it structurally impossible to get wrong.

**4. The system admits what it does not know.**
Below ninety percent confidence, a person reviews before anything goes out. Below seventy, the system stops and asks for help instead of guessing. That is a harness admitting uncertainty instead of hiding it.

**5. One real example.**
Shirley Magnusdottir was filed as Silver. Her actual giving computes to Gold. A well written prompt might catch this on a good day. This system catches it every single time, because the check is code, not a suggestion.

**6. The whole difference, in one line.**
A well designed prompt improves probability. A well designed harness replaces probability with a guarantee, wherever a guarantee is possible, and asks a human wherever it is not. Same model. Completely different system.
