# Integrity and Claims: What a Letter Is Allowed to Say

Covers problems 3 and 4 from the [design review index](README.md).

## Problem 3: false claims to donors, by instruction

The original emergency-appeal section instructs: tell the donor their gift will be matched, "even if no match is confirmed, we can sort that out later." A donation induced by a false statement violates truthfulness, fundraising ethics, state charity regulation, brand governance, and donor trust in a single sentence. This alone would get an enterprise AI system rejected in review, immediately.

**Verdict: valid, with the terminology sharpened.** My first note called this encouraged hallucination. It is worse. A hallucination is a model failure; this is a person instructing the system to lie, which makes it a governance failure with an author. The distinction matters because the fixes differ: hallucination is mitigated with grounding and validation, while instructed falsehood has to be made structurally impossible so no future instruction file can reintroduce it.

**The fix.** The rule is "never state facts not supplied." Matching language is gated behind a `match_confirmed` config flag that requires the sponsor and terms; event counts and re-engagement gifts are likewise config-gated; the [letter schema](structured-output.md) constrains what a letter can contain; and [the test suite](../../tests/test_pipeline.py) scans every generated letter and fails the build if match language appears unconfirmed. Losing one donor this way would be a disaster; the rebuild makes it a compile-time impossibility rather than a training reminder. Decision record: [ADR 0006](../adr/0006-no-unconfirmed-match-claims.md).

## Problem 4: guessing gender from first names

The original salutation rules guess titles from first names when it "seems obvious." Absolutely not. This misgenders real people, fails across cultures, and does it in the first line of a request for money. It is a governance problem, a brand problem, and a data-quality problem at once, because the guess is baked into output with no record it was a guess.

**Verdict: valid.** No qualifications.

**The fix.** No inferred prefixes, ever. A title is used only when the donor record provides one; otherwise the salutation is the neutral "Dear First Last" for every tier. The tests assert that no generated letter contains an honorific the file did not supply. If the organization wants title-based salutations, the fix is collecting titles in the CRM, and the letters improve automatically the day that data exists. Decision record: [ADR 0005](../adr/0005-never-infer-gender-or-title.md).

## What changes at scale

Nothing. These two rules are scale-independent: they hold at one donor and at one million, and any future system component inherits them through the schema and the tests.
