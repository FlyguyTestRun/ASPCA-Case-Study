// Builds ASSESSMENT.docx from the tightened ASSESSMENT.md content.
// Run: node assessment/build_docx.js
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  BorderStyle, ExternalHyperlink,
} = require("docx");

const US_LETTER = { width: 12240, height: 15840 };
const MARGIN = 1440; // 1 inch

const ACCENT = "0E6B5F"; // matches the standalone deliverable's petrol teal
const INK = "14211D";
const INK_SOFT = "4B5750";

function body(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 200, line: 276 },
    children: [new TextRun({ text, size: 22, color: INK, ...opts })],
  });
}

// Parses inline **bold** segments into TextRuns.
function richBody(text, opts = {}) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  const runs = parts.map((part) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return new TextRun({ text: part.slice(2, -2), bold: true, size: 22, color: INK, ...opts });
    }
    return new TextRun({ text: part, size: 22, color: INK, ...opts });
  });
  return new Paragraph({ spacing: { after: 200, line: 276 }, children: runs });
}

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 200, after: 240 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: ACCENT, space: 6 } },
    children: [new TextRun({ text, bold: true, size: 40, color: INK })],
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 360, after: 160 },
    children: [new TextRun({ text, bold: true, size: 28, color: ACCENT })],
  });
}

function byline(text) {
  return new Paragraph({
    spacing: { after: 300 },
    children: [new TextRun({ text, italics: true, size: 20, color: INK_SOFT })],
  });
}

function bullet(text, level = 0) {
  return richBody(text, {});
}

function bulletPoint(text) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  const runs = parts.map((part) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return new TextRun({ text: part.slice(2, -2), bold: true, size: 21, color: INK });
    }
    return new TextRun({ text: part, size: 21, color: INK });
  });
  return new Paragraph({
    bullet: { level: 0 },
    spacing: { after: 140, line: 264 },
    children: runs,
  });
}

function numbered(n, title, text) {
  return new Paragraph({
    spacing: { after: 140, line: 264 },
    children: [
      new TextRun({ text: `${n}. `, bold: true, size: 21, color: ACCENT }),
      new TextRun({ text: title, bold: true, size: 21, color: INK }),
      new TextRun({ text: " " + text, size: 21, color: INK }),
    ],
  });
}

const doc = new Document({
  sections: [
    {
      properties: {
        page: { size: US_LETTER, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } },
      },
      children: [
        h1("Charity Donor Outreach Skill: Assessment and Rewrite"),
        byline("Bryan Shaw, July 2026"),
        body(
          "Prepared in response to the case study brief: assess the charity-donor-outreach skill, describe improvements and their impact, and rewrite the skill. This document answers both parts directly; the full repository (rewritten skill, tests, run evidence, and a decision record for every change) is the working proof behind it."
        ),

        h2("Summary"),
        body(
          "The skill reads as reasonable prose and fails at every layer that matters in production. It embeds its data instead of reading it, trusts labels its own data contradicts, asks a language model to do arithmetic, invents facts when data is missing, and instructs the assistant to make an untrue claim to donors. None of these failures announce themselves; each produces a confident, well-formatted, wrong letter."
        ),
        body(
          "The fix is one principle applied consistently: verify the data first, then let each tool do the job it is actually good at. Deterministic code owns validation, tier computation, ask arithmetic, and rendering. The model contributes only bounded, optional personalization, grounded in verified fields, off by default. Humans review by exception, with mandatory gates where the stakes are highest."
        ),
        body(
          "Run against the case study's own 50 donors: the pipeline catches four mislabeled tiers (one my own manual review of the table had missed), flags a reference-date trap, routes two lapsed major donors away from form letters, and generates 44 letters with a full audit trail. Nothing is ever sent automatically. 122 automated tests hold this behavior in place, re-run on every change by CI."
        ),

        h2("Part 1: Improvements and Their Impact"),
        body("The original's ten defects, grouped by what they would have done in production:", { bold: true }),

        richBody("**Would have defrauded donors.** The skill instructs the assistant to tell every donor their gift is matched, “even if no match is confirmed, we can sort that out later.” That is not a hallucination risk to mitigate; it is a written instruction to lie, exposing the charity to fraudulent-solicitation and state charity-registration liability. Fix: matching language is gated behind a match_confirmed config flag with a required sponsor and terms, and every generated letter is scanned by the test suite. An instructed falsehood is now a structural impossibility, not a training reminder."),

        richBody("**Would have misgendered donors.** Salutation rules guess a title from the first name “if it seems obvious.” Fix: a title is used only when the file provides one; otherwise every donor gets a neutral salutation, tested for on every letter."),

        richBody("**Would have sent the wrong ask, at scale, silently.** Two compounding defects: the donor database lives inside the instruction file instead of the CSV the skill's own step 1 says to read, and every stated field (tier, totals) is trusted without verification. The example data proves the cost: four donors' stated tiers contradict their own gift history. My own manual read of the table caught three; the validator caught all four on its first run. Fix: the skill holds zero data, operates only on a schema-validated input file, and recomputes tier, totals, and dates from the gift history on every run. A stated value that disagrees routes to an exceptions report with the exact discrepancy and a suggested correction; nothing is trusted on faith."),

        richBody("**Would have drifted with the calendar.** “Lapsed” and “gave last year” are date calculations with no defined reference point; the data's own internal clock is 2024, so running the skill on a different day silently changes who counts as lapsed. Fix: every run requires an explicit as_of_date, used everywhere a date matters. Runs are reproducible and testable regardless of when they execute."),

        richBody("**Would have produced inconsistent numbers.** A seven-step ask formula, executed by the model per donor, rounds mid-sequence and leaves “gave last year” undefined; a model is a poor calculator even when the formula is exact. Fix: one deterministic function, fixed operation order, one rounding step at the end, a full trace per calculation. Identical input now produces identical output, every time."),

        richBody("**Would have fabricated data and people.** “Make reasonable assumptions and proceed” on missing fields, and an instruction to invent a “relationship manager name” for Platinum donors. Fix: missing or contradictory data fails loudly to an exceptions report; every letter is signed by a real person named in the campaign config, never invented. A run with a missing required field stops with a named error instead of improvising."),

        richBody("**Would not have scaled past a demo.** Output is HTML pasted into chat, with no review step, and the skill's trigger fires on any mention of money, email, or events. Fix: letters are files plus a review manifest with per-donor confidence and review level; Platinum letters and anything flagged are always reviewed by a person before anything ships, and the skill never sends anything itself. The trigger now names the one job it does."),

        body(
          "Full mapping from each defect to its fix, its test, and its decision record is in docs/trap-registry.md. Full mapping from named production-readiness controls (schema validation, audit logging, versioned business rules, and more) to their implementation is in docs/requirements-checklist.md."
        ),

        h2("Part 2: The Rewrite"),
        body(
          "skill/charity-donor-outreach/ is a lean orchestrator over three deterministic stages, plus one optional, bounded, off-by-default step where a model may touch language:"
        ),
        numbered(1, "Validate (validate_input.py):", "schema-check the file, recompute everything computable, verify every stated field, and stop for a human before anything else happens."),
        numbered(2, "Calculate (calculate_ask.py):", "apply the ask policy from references/policy.md with a full audit trace and a confidence score."),
        numbered(3, "Generate (generate_letters.py):", "assemble a structured letter object from approved language, validate it against a schema, and only then render it. A model may personalize within the guardrails in prompts/personalization_prompt.md, its own versioned file, only if a user explicitly asks; a letter is complete and correct with zero model calls."),
        body(
          "SKILL.md is short because policy lives in references/, mechanics live in scripts/, and the one model-facing prompt lives in prompts/, each independently reviewable and versionable. The model's remaining job is judgment inside guardrails, which is what it is actually suited for."
        ),
        body("Beyond the brief's two questions, four things the brief's own goals (consistent, reliable, scalable) required building:", { bold: true }),

        bulletPoint("**A review interface** (app/review_app.py) so fundraising staff, not just engineers, can run and audit this system: upload or use a built-in sample, see every held record and warning in plain language, sign off individually on anything that matters, and archive a completed run before the next one overwrites it. Every stage names the exact script behind it, so the interface teaches as it operates."),
        bulletPoint("**A fix-and-resubmit loop**: the validator suggests the correct value wherever it is computable; a person approves, the file re-runs in one click."),
        bulletPoint("**A style feedback loop**: reviewer edits teach the system's voice, only after repeated evidence, only within hard guardrails, only on named adoption; it can change how a letter sounds, never what it claims or asks."),
        bulletPoint("**30 Architecture Decision Records**, one per correction, and an operational decision log the running system writes for itself (approvals, adoptions, sign-offs, archives), each with a named approver."),

        body(
          "The same rigor applied to the original skill was turned on the rewrite itself before submission, twice. A second-pass audit found and fixed two scale-triggered defects the first pass's own tests had not caught (a donor-name-derived ID could collide between two different donors; output was never cleared between runs, risking stale files). A full proofread across all four campaign types, not just the one committed run, found and fixed a letter telling a lapsed donor his support had been “steady,” a factual claim his own record contradicts. Every one of these is now a permanent regression test, not a lesson learned once. docs/trap-registry.md records all of it, findings the rewrite introduced included."
        ),

        h2("Part 3: Where Production Hardening Goes From Here"),
        body(
          "This exercise stops at the review manifest on purpose. The path forward, and the trigger condition for each step, is documented in docs/scale-architecture.md: a CRM connector replacing file upload, do-not-contact and consent checks at the validation boundary, a batch and approval workflow, evaluation over time as reviewer edits accumulate, and confidence-rubric recalibration once there is outcome data to recalibrate against. None of it is speculative scope; each is a documented extension point this architecture was built to accept without a redesign."
        ),
        body(
          "The through line: the durable asset is the donor data and the policy, not the model. This rebuild is arranged so the data gets cleaner every run, the policy is executable and versioned, and the model can be swapped or upgraded without touching either.",
          { italics: true }
        ),
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(__dirname + "/ASSESSMENT.docx", buffer);
  console.log("wrote ASSESSMENT.docx");
});
