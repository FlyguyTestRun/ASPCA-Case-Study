# Design Review: the Original Skill, Problem by Problem

This is the full architectural review of the original `charity-donor-outreach` skill. Each problem states what is wrong, why it matters, whether the concern survives scrutiny (a few of my first-pass instincts needed sharpening, and those verdicts are recorded honestly), what the rebuild does about it, and what changes at scale.

One framing point before the list. The original is a prompt wearing a skill's file format. It has no tools, no gates, no verifiable state, and no separation between data, logic, and language. A skill earns a place in an agentic system when it gives the agent those things: deterministic tools to call, policies it cannot cross, and outputs that can be checked. That is the difference between instructing a model and engineering a system, and it is the whole thesis of this rebuild. Knowing when not to use an LLM is almost as important as anything the model was trained on.

## The problems

| # | Problem | Verdict | Where it is fixed | Detail |
|---|---------|---------|-------------------|--------|
| 1 | Deterministic computation performed inside the LLM | Valid | [ADR 0003](../adr/0003-deterministic-arithmetic.md) | [prompt-design.md](prompt-design.md) |
| 2 | The model treated as the source of truth for business logic | Valid | [ADR 0002](../adr/0002-verify-inputs-never-trust-them.md) | [data-integrity.md](data-integrity.md) |
| 3 | False claims to donors instructed by design (the gift match) | Valid, sharpened: this is instructed falsehood, worse than hallucination | [ADR 0006](../adr/0006-no-unconfirmed-match-claims.md) | [integrity-and-claims.md](integrity-and-claims.md) |
| 4 | Gender guessed from first names | Valid | [ADR 0005](../adr/0005-never-infer-gender-or-title.md) | [integrity-and-claims.md](integrity-and-claims.md) |
| 5 | The donor database embedded inside the instructions | Valid; the caching sub-point is reframed | [ADR 0001](../adr/0001-separate-data-from-instructions.md), [ADR 0016](../adr/0016-token-and-process-economy.md) | [data-integrity.md](data-integrity.md) |
| 6 | No output schema; free-form HTML straight from the model | Valid, and it drove a new build: schema-then-render | [ADR 0017](../adr/0017-letter-schema-validation.md) | [structured-output.md](structured-output.md) |
| 7 | No confidence scoring or escalation path | Valid, and it drove a new build: the fail, report, pass rubric with webhook escalation | [ADR 0011](../adr/0011-confidence-scoring-feedback-loop.md) | [confidence-and-escalation.md](confidence-and-escalation.md) |
| 8 | No evaluation harness, no regression testing, no versioning | Valid | [ADR 0013](../adr/0013-ci-regression-gate.md) | [evaluation-and-observability.md](evaluation-and-observability.md) |
| 9 | LLM-first pipeline: every input becomes a model call | Valid | [ADR 0016](../adr/0016-token-and-process-economy.md) | [prompt-design.md](prompt-design.md) |
| 10 | No input validation of any kind | Valid | [ADR 0002](../adr/0002-verify-inputs-never-trust-them.md), [ADR 0008](../adr/0008-fail-loudly-to-exceptions.md) | [data-integrity.md](data-integrity.md) |
| 11 | No security boundaries: trusted uploads, no sanitization, no injection defenses | Valid, and it drove a new build: CSV injection guards, upload caps, data-not-instructions rule | [ADR 0018](../adr/0018-security-boundaries.md) | [security.md](security.md) |
| 12 | No observability: nothing logged, measured, or comparable between runs | Valid, and it drove a new build: per-stage run metrics | [ADR 0016](../adr/0016-token-and-process-economy.md), [ADR 0018](../adr/0018-security-boundaries.md) | [evaluation-and-observability.md](evaluation-and-observability.md) |

Problems 6, 7, 11, and 12 were not fully addressed by the first rebuild pass; this review drove their implementation. That is the review process working as intended.

## Where the verdicts pushed back

Three of my first-pass reactions deserved their own scrutiny, and a review that never overrules itself is not a review:

- **"Hallucination is encouraged."** The match-claim instruction is worse than hallucination. A hallucination is a model failure; this was a person instructing the system to lie. The fix is the same (claims only from confirmed sources) but the accountability is different, and precision matters when the finding is this serious.
- **"There is no semantic cache."** True, but a cache is the right fix for repeated interactive queries, which this workload does not have. A batch letter pipeline is fixed more fundamentally by removing the model from the hot path entirely, which is what the rebuild does. Reaching for a cache here would be treating the symptom. The cache has its place; see [scale-architecture.md](../scale-architecture.md) for when.
- **"Where are the containers, the MCP servers, the orchestration?"** Missing architecture was the right instinct; prescribing heavy architecture is not. At 50 donors, an MCP server in front of a CSV file is bloat wearing a best-practice costume. The discipline of knowing when not to use an LLM extends to knowing when not to use infrastructure. Each of those components has a trigger condition that justifies it, documented in [scale-architecture.md](../scale-architecture.md).

## The root cause, and what would improve the system most

Strip the twelve problems back and they share one root: this was treated as a prompt engineering problem, and prompt engineering alone cannot fix it. A sharper prompt would still be doing arithmetic in a probability engine, still trusting labels the data contradicts, and still holding a database inside an instruction file. The durable improvement is structural: put deterministic logic around the data first, and let the model do only the work that is genuinely linguistic. That is my standing default whenever the work involves data, and doubly so for spreadsheets: spreadsheets are ledgers, and ledgers get logic, not pattern recognition.

The audit that closed this review made the point concretely ([ADR 0019](../adr/0019-data-provenance-and-fixture-fidelity.md)): the original table's arithmetic was internally consistent all along. Its defects were categorical and temporal, the kinds of errors no amount of prompt wording reliably catches and thirty lines of validation code catches every time.

## Related documents

- [Requirements checklist](../requirements-checklist.md): every production-readiness control named directly, hyperlinked to its implementation and its test.
- [Trap registry](../trap-registry.md): every planted defect in the case data, the mechanism that catches it, and the test that proves it, plus the defects a second-pass audit of the rewrite itself found and fixed.
- [Components guide](../components.md): every script and tool explained for both non-technical readers and engineers.
- [Scale architecture](../scale-architecture.md): what gets built when volume, integration, or interactivity demand it, and what triggers each addition.
- [ADR index](../adr/): the full decision record, one per correction.
