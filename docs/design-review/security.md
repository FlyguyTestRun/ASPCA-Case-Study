# Security Boundaries: Untrusted Input, Inert Output

Covers problem 11 from the [design review index](README.md).

## Problem 11: no security boundaries anywhere

The original trusts everything: the uploaded file is assumed accurate and benign, donor text flows unexamined into outputs, and there is no sanitization, no injection defense, no size limit, no identity model. The case study's planted data errors prove the accuracy assumption wrong on arrival; the rest of the trust assumptions are wrong on principle, because a donor file is user-generated content and has to be treated like it.

**Verdict: valid, and this review drove the implementation.** Three concrete defenses were buildable immediately; the identity and environment controls belong to production and are scoped honestly below.

**Built now:**

- **Spreadsheet formula injection (CSV injection).** Excel and Google Sheets execute cell values that begin with `=`, `+`, `-`, or `@`. Every CSV this pipeline writes (validated donors, exceptions, corrections, computed asks, the review manifest) is fundraising-staff-facing and will be opened in Excel, so every cell is neutralized on write: a donor named `=HYPERLINK(...)` arrives inert, proven by [test](../../tests/test_pipeline.py). Implementation: `csv_safe` in [donor_rules.py](../../skill/charity-donor-outreach/scripts/donor_rules.py).
- **Output escaping.** All donor-derived text is HTML-escaped at render time, so letter files cannot carry script or markup from the input file.
- **Upload limits.** The review app caps uploads at 5 MB with a plain-language redirect to the batch pipeline for anything larger, which keeps the browser path from becoming an unbounded ingestion route.
- **Data is never instructions.** The skill's personalization step carries an explicit rule: donor-file text is data; anything in it that reads like a directive is flagged, never followed. That is the prompt-injection boundary for the one step where a model touches donor text.
- **Fabrication defenses double as security.** Signers only from config, claims only from confirmed sources, unknown schema fields rejected: the same gates that stop errors stop several classes of abuse.
- **The same two defenses apply where the browser accepts a file.** The standalone deliverable's donor-file upload (ADR 0029) changed its threat model the same way the review app's upload always had one: CSV formula injection is neutralized on export (`csvSafe`, mirroring `csv_safe` exactly) and every donor field is HTML-escaped at render time, not only in the pipeline's own output. See [ADR 0032](../adr/0032-hostile-input-parity-for-the-browser-tool.md).

**Scoped to production (deliberately not built here):** identity and access management on the review app, per-user audit of who approved which correction, encrypted storage for donor files at rest, CRM-side access controls replacing file upload entirely, and malicious-file scanning at the ingestion boundary. These need the enterprise environment they run in; pretending to implement IAM in a local demo would be theater. The honest version is the list, the order, and the interfaces they attach to, which is written in [scale-architecture.md](../scale-architecture.md). Decision record: [ADR 0018](../adr/0018-security-boundaries.md).

## What changes at scale

The trust boundary moves from "a file someone uploads" to "a CRM the organization governs," which retires the upload path and its risks entirely. The validation and sanitization layers stay exactly where they are; they just start receiving their input from a connector instead of a browser.
