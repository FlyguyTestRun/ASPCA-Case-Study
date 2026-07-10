# ADR 0012: A review interface for non-technical operators

Status: accepted. Date: 2026-07-10.

## Problem

The pipeline's outputs are CSVs and a JSON report. That is the right substrate for automation and audit, but the people who run donor outreach are fundraising staff, not engineers. Asking them to read validation_report.json quietly re-creates the original skill's failure: results nobody actually reviews. Tooling should meet people where they are and teach as it goes, not punish them for what they do not know.

## Decision

A local web interface (app/review_app.py, Streamlit) wraps the same pipeline scripts with zero logic of its own. An operator uploads a donor CSV or XLSX, picks the campaign settings, and sees every data problem listed by donor with the exact reason, every warning, every confidence score, and every computed ask with its calculation trace, plus letter previews and download buttons. The UI imports the same donor_rules module the scripts use, so it can never disagree with the pipeline.

## What this changes going forward

Exception handling becomes self-service: the person who knows the donors sees "file says Silver, gifts compute to Gold" in plain language and can fix the source data without an engineer in the loop. The interface doubles as a training aid, because every flag explains the rule behind it. And because the UI is a thin shell over the scripts, automation, tests, CI, and the interface can never drift apart.
