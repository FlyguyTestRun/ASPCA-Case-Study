# Hours Log: ASPCA Case Study

Time is logged per work block. All times US Central.

| Date | Start | End | Hours | Work performed |
|------|-------|-----|-------|----------------|
| 2026-07-09 | evening | | 1.5 | Received case study from Doug Maschoff. First read of the charity-donor-outreach skill, initial flaw inventory, assessment approach drafted. |
| 2026-07-10 | 13:00 | 15:30 | 2.5 | Repo scaffold. Donor fixture transcription (50 rows, planted errors preserved). Policy and schema reference docs. Validation, ask calculation, and letter generation scripts with audit traces. 46-test suite, all passing; pipeline verified end to end (4 tier traps caught, including one manual review missed). 13 ADRs. Review app built and verified in browser. CI workflow. README with pipeline DAG. Assessment document drafted. |

| 2026-07-10 | 15:45 | 17:00 | 1.25 | Feedback-loop expansion: suggested corrections with human-approved resubmit (CLI and UI), style learning from reviewer edits with guardrails and named adoption, tutorial mode and narrated audio walkthrough in the review app, token and process economy writeup, trap registry. Test suite grown to 61, all passing. Full fix-and-resubmit loop verified in the browser: 4 exceptions to a clean 50 of 50. |

| 2026-07-11 | 10:30 | 12:15 | 1.75 | Design review of the original skill validity-checked, professionalized, and moved into docs/design-review (7 themed files plus index). Four gaps from the review implemented: letter schema validation before render, full fail/report/pass confidence rubric with webhook-ready escalation events, CSV formula-injection defenses with upload caps, per-stage run metrics. New docs: components guide, scale-architecture trigger table. ADRs 0017 and 0018 added, 0011 revised. README rewritten concise with TOC. Test suite grown to 81; pipeline, app, and resubmit loop re-verified in browser; run log clean. |

| 2026-07-11 | 12:30 | 13:00 | 0.5 | Data provenance audit. Confirmed the original zip contained only SKILL.md plus a macOS .DS_Store artifact (no data), so the embedded 50-donor table is the sole data source. Added a fixture-fidelity test suite (5 tests): parses the original markdown table and proves the fixture matches it field by field, planted errors preserved, and independently audits that the original's arithmetic columns tie out. Suite at 86. Machine learning scoped honestly into the scale-architecture trigger table (confidence recalibration, donor analytics). |

| 2026-07-11 | 13:15 | 15:30 | 2.25 | Discoveries formalized: ADR 0019 (data provenance and fixture fidelity) and the design review updated with the corrected finding (original arithmetic ties out; traps are categorical and temporal). Operational decision log built (ADR 0020): applied corrections, style adoptions, and review sign-offs now write ADR-style entries automatically, wired into apply_corrections.py, learn_style.py, and the app. Review app rebuilt as a guided 4-step flow (Upload, Findings, Review, Finalize) with a named-approver requirement and an export gate on required reviews. Walkthrough script rewritten as a candid field-notes assessment; recording instructions written for Bryan's own voice. Built a standalone, self-contained HTML deliverable (deliverable/donor-data-review.html, ADR 0021): verified-result summary, annotated pipeline diagram, and a searchable/editable/exportable table of all 50 donors, dataset built from the real pipeline output. Found and fixed a real bug during browser testing (donors filed with tier "Lapsed" were wrongly flagged as mismatches); added a Node-based test that executes the page's own JavaScript against the fixture so the bug class cannot return unnoticed. Suite at 95, all passing. |

Remaining before submission: assessment docx export, letter-quality pass on generated letters, final proofread, email draft to Doug, push to GitHub after validation sign-off, Bryan's recorded walkthrough audio.

**Total: 9.75**
