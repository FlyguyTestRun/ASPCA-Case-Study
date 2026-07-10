# ADR 0007: One campaign config supplies every run parameter

Status: accepted. Date: 2026-07-10.

## Problem

The original template shipped placeholders with no data source: DONATION_URL, CHARITY NAME, a letter date, and a RELATIONSHIP_MANAGER_NAME the skill told the model to invent for Platinum donors. An invented staff name in a major-donor letter is a made-up human being a $50,000 donor may try to call. Placeholders without sources get filled by whatever the model finds plausible, differently each run.

## Decision

A required campaign config JSON (schema in references/input_schema.md) is the single source for every run parameter: campaign type, as_of_date, charity name, donation URL, signer name and title, match fields, and optional event and re-engagement details. Validation stops the run with named errors if required keys are missing. Letters are signed by the configured signer, a real person the organization chose. Nothing about the run is invented or remembered from a previous conversation.

## What this changes going forward

A campaign is now an auditable artifact: the config file plus the input file fully determine the output, which is what makes batch runs reviewable and repeatable. New campaigns are launched by writing a config, not by editing instructions. The skill asks the user for missing values instead of improvising them, which converts silent fabrication into a visible question.
