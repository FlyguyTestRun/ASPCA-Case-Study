# ADR 0009: File outputs, a review manifest, and human gates

Status: accepted. Date: 2026-07-10.

## Problem

The original skill returned letters as HTML in the chat window. At 5 donors that is awkward; at 50 it is unusable; at 500 it is a wall of markup nobody reviews, which means nobody reviews the letters at all. There was no review step, no record of what was generated, and nothing stopping generated text from being treated as ready to send.

## Decision

Letters are written to output/letters/ as one file per donor, alongside output/manifest.csv: one row per donor with tier, status, ask, confidence, review level, warnings, and the letter path. Review levels are policy: every Platinum letter is individually reviewed, any warning triggers recommended review, low confidence or a routing reason makes review mandatory. Lapsed Gold and Platinum donors get no automated letter at all; the manifest routes them to personal outreach, because a form letter is the wrong instrument for a lapsed major donor. Nothing is ever sent by the skill.

## What this changes going forward

The manifest is the QA surface: a fundraising manager works down a spreadsheet, not a chat scrollback. Output scales linearly with donor count without degrading reviewability. The human-in-the-loop gate is structural rather than aspirational, and "what went out last March" has a durable answer: the manifest and letters from that run.
