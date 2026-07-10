# ADR 0001: Separate donor data from skill instructions

Status: accepted. Date: 2026-07-10.

## Problem

The original skill embedded the full 50-donor giving history as a table inside SKILL.md, while step 1 of its own workflow said to read donors from an uploaded file. Two sources of truth, and both wrong in different ways: the embedded table goes stale the day it is written, bloats the model's context on every invocation, leaks donor PII into every prompt, and caps the donor list at whatever fits in an instruction file. "Scalable to a growing donor list" is impossible under this design.

## Decision

The skill holds zero donor data. It operates only on the file the user provides, validated against a published schema (references/input_schema.md). The 50 donors were transcribed verbatim, planted errors included, into assets/sample_donors.csv, which is labeled a test fixture and used by the test suite and CI, never as a data source.

## What this changes going forward

Donor volume no longer affects instruction size: 50 donors or 50,000 process identically. Data corrections happen in the source system, not in a prompt file. PII stays out of model context except for the specific fields a letter needs. The fixture doubles as a permanent regression test because its planted errors must always be caught.
