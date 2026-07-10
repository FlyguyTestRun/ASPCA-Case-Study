# Input Schema

Two inputs are required for every run: a donor file and a campaign config. The skill holds no donor data of its own. `assets/sample_donors.csv` is a test fixture, not a data source.

## Donor file (CSV or XLSX)

One row per donor. Column order does not matter; header names do.

| Column | Required | Type | Notes |
|--------|----------|------|-------|
| donor_name | yes | text | Full name. Used for salutation split (last token is the family name). A real deployment should join on a CRM donor ID instead; see the assessment doc. |
| title | no | text | Honorific exactly as the donor provided it (Ms., Dr., Rev., ...). Never inferred. Blank is fine. |
| tier | no | text | Stated tier, if the source system has one. It is verified against the computed tier, never trusted. `Lapsed` is accepted here for backward compatibility with legacy exports and is treated as a status claim. |
| region | no | text | Used only for optional personalization. |
| gifts | yes | text | Pipe-separated `year:amount` pairs, for example `2019:500|2021:1200`. Amounts may include `$` and commas. This column is the source of truth for all derived numbers. |
| largest_gift | no | number | If present, must equal the maximum gift amount in `gifts`, or the row goes to exceptions. |
| lifetime_total | no | number | If present, must equal the sum of `gifts`, or the row goes to exceptions. |
| last_gift_year | no | number | If present, must equal the maximum year in `gifts`, or the row goes to exceptions. |
| volunteer | no | Yes/No | Defaults to No when blank. |

Validation behavior:

- Missing or unparseable required fields send the row to `work/exceptions.csv` with a specific reason. The pipeline never guesses and never fabricates.
- Gift years later than the config `as_of_date` year are an error (future-dated gift). A gift dated in the `as_of` year itself is legal but attaches a warning, because "gave last year" logic is sensitive to it.
- Duplicate donor names are flagged to exceptions, since name is the join key in this fixture-scale design.

## Campaign config (JSON)

See `assets/campaign_config.example.json` for a complete example.

| Key | Required | Notes |
|-----|----------|-------|
| campaign_type | yes | One of `emergency_appeal`, `annual_fund`, `capital_campaign`, `event_fundraiser`. Anything else stops the run. |
| as_of_date | yes | `YYYY-MM-DD`. The reference date for every date calculation (lapsed status, loyalty uplift, future-gift checks). Explicit on purpose: donor files have their own internal clock and the wall clock is the wrong instrument. |
| charity_name | yes | Rendered in every letter. |
| donation_url | yes | Rendered in every letter. |
| signer_name | yes | The human who signs the letters. Never invented. |
| signer_title | yes | Signer's title. |
| match_confirmed | yes | Boolean. Matching language is only permitted when `true`. |
| match_sponsor | when match_confirmed | Who is matching. |
| match_terms | when match_confirmed | For example "doubled up to $100,000 through August 31". |
| event_name | for event_fundraiser | Required for event campaigns. |
| event_registered_count | no | Integer. Only cited if present. |
| reengagement_gift | no | For example "a welcome-back tote". Only mentioned if present. |
