# ADR 0005: Titles come from data, never from guessing

Status: accepted. Date: 2026-07-10.

## Problem

The original salutation rules said to guess a title from the first name if it "seems obvious," with examples ("Elizabeth is probably Ms., Robert is probably Mr."). Inferring gender from names misgenders real people, fails across cultures, and does it in the first line of a letter asking for money. It is also a quiet data-quality failure: the guess gets baked into output with no record that it was a guess.

## Decision

A title is used only when the donor file provides one, rendered exactly as provided. Otherwise the salutation is the neutral "Dear {First Name} {Last Name}," for every tier. The lapsed gimmick greeting ("We've missed you!") was removed for the same reason: donors get one respectful register regardless of segment. The re-engagement message lives in the letter body.

## What this changes going forward

Zero misgendered donors, mechanically guaranteed; the test suite asserts that no generated letter contains an honorific the file did not supply. If the organization wants title-based salutations, the fix is collecting titles in the CRM, which is the correct place, and the letters improve automatically the day that data arrives.
