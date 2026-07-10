# ADR 0010: Narrow the skill trigger to its actual job

Status: accepted. Date: 2026-07-10.

## Problem

The original description told the assistant to use the skill "whenever a user mentions donors, fundraising, money, emails, letters, charity, nonprofits, campaigns, giving, volunteers, events, reports, grants, sponsorships, or any kind of outreach or communication task." That fires on nearly any business conversation. A user asking for help with a grant report or an event budget would be routed into a donor-letter generator, and in an environment with many skills, over-broad triggers collide with each other.

## Decision

The description now states the one job (generate outreach letters from a donor file for a campaign), the required inputs, and explicit non-triggers (general email, event planning, reporting, grant writing).

## What this changes going forward

The skill activates when it should and stays out of the way otherwise, which is most of what makes a skill library composable. Trigger scope is also now reviewable: the description is a testable claim about when the skill runs, not a keyword net cast as wide as possible.
