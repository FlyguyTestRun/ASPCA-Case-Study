# A Complete Run, Stop by Stop

This document runs the real fixture through the real pipeline, one stage at a time, and stops to show exactly what happened at each point: the command, the actual output, and the file it produced. Every number here is real, captured from an actual run against `skill/charity-donor-outreach/assets/sample_donors.csv`, not a mock-up.

Each stop has two explanations. **Plain language** is for anyone: what happened, and why it matters. **Under the hood** is for engineers: the exact code path and the file it reads or writes. Read only the plain-language parts and you will understand the whole system; read both and you will understand how to change it.

Nothing in this run sends anything anywhere. Every stage stops and waits.

## Stop 0: What goes in

A donor file. This run uses the fixture, which is the original case study's own 50-donor table transcribed verbatim, planted errors included ([ADR 0019](adr/0019-data-provenance-and-fixture-fidelity.md)):

```
donor_name,title,tier,region,gifts,largest_gift,lifetime_total,last_gift_year,volunteer
Robert Svensson,,Platinum,Northeast,2010:25000|2013:30000|2016:40000|2020:50000,50000,145000,2020,No
Earl Fontaine,,Platinum,Southeast,2012:50000|2015:60000|2018:75000|2022:90000,90000,275000,2022,Yes
Ruth Andersen,,Silver,Southeast,2019:3000|2020:4000|2021:5000|2022:6000|2023:7000,7000,25000,2023,Yes
```

**Plain language.** This is a spreadsheet: one row per donor, their giving history in a `year:amount` list, and whatever the source system currently believes their tier is. Look at Ruth Andersen's row. Her file says she is Silver. Her own gift history adds up to $25,000 lifetime, which the organization's own tier policy puts in Gold range. Nobody is trying to trick the system; this is exactly the kind of mismatch that accumulates in any real donor database over time, a label that was correct once and never got updated.

**Under the hood.** `references/input_schema.md` and `references/donor.schema.json` define this shape. Nothing downstream reads this file directly again after the next stop; everything else works from what gets recomputed from it.

## Stop 1: Schema and business-rule validation

```
python scripts/validate_input.py --input donors.csv --config campaign.json
```

```
rows in:            50
validated:          46
exceptions:         4
with warnings:      3
suggested fixes:    4 (work/corrections.csv, approve then resubmit)
  EXCEPTION  Ada Yamamoto-Pierce: tier mismatch: file says Silver, lifetime giving of $17,000 computes to Gold
  EXCEPTION  Ruth Andersen: tier mismatch: file says Silver, lifetime giving of $25,000 computes to Gold
  EXCEPTION  Shirley Magnusdottir: tier mismatch: file says Silver, lifetime giving of $22,000 computes to Gold
  EXCEPTION  Arthur Mwangi: tier mismatch: file says Bronze, lifetime giving of $2,600 computes to Silver
  WARNING    Robert Svensson: file states active tier Platinum but donor is lapsed by date policy
  WARNING    Walter Adeyemi: file states active tier Platinum but donor is lapsed by date policy
  WARNING    Susan Nakamura: gift recorded in the as_of year 2024, confirm the as_of_date is intended (loyalty logic counts only the prior full year)
```

**Plain language.** The system never trusts the stated tier. It adds up each donor's actual gift history and checks that against what the file claims. Four donors fail this check, Ruth Andersen among them, each held with the exact reason spelled out. Three more donors pass but get a warning: two Platinum donors whose last gift was years ago (they are lapsed by policy, even though their file still marks them active), and one donor with a gift dated in the same year as the campaign's reference date, which the system flags rather than silently guessing what that means for her loyalty bonus. Nothing here is fixed automatically. Every held record shows up in a report a person reads before anything else happens.

**Under the hood.** `scripts/validate_input.py` first checks each row against `references/donor.schema.json` (shape: are the columns present, is the gifts field even parseable), then recomputes tier, lifetime total, and lapsed status from the gift history and compares against the stated values, per `references/policy.md`. Writes `work/validated.csv`, `work/validated.jsonl`, `work/exceptions.csv`, `work/corrections.csv`, `work/validation_report.json`. Decision record: [ADR 0002](adr/0002-verify-inputs-never-trust-them.md), [ADR 0024](adr/0024-donor-schema-validation-layer.md).

The exceptions report, in full:

| row | donor | error | suggested fix |
|---|---|---|---|
| 23 | Ada Yamamoto-Pierce | tier mismatch: file says Silver, lifetime giving of $17,000 computes to Gold | set tier to Gold |
| 25 | Ruth Andersen | tier mismatch: file says Silver, lifetime giving of $25,000 computes to Gold | set tier to Gold |
| 27 | Shirley Magnusdottir | tier mismatch: file says Silver, lifetime giving of $22,000 computes to Gold | set tier to Gold |
| 51 | Arthur Mwangi | tier mismatch: file says Bronze, lifetime giving of $2,600 computes to Silver | set tier to Silver |

## Stop 2 (the gate): a person decides

The system does not fix the four held records itself. It computed what it believes the correct value is and put it in front of a person:

```
row_number,donor_name,field,current_value,suggested_value,reason
23,Ada Yamamoto-Pierce,tier,Silver,Gold,"lifetime giving of $17,000 places this donor in Gold"
25,Ruth Andersen,tier,Silver,Gold,"lifetime giving of $25,000 places this donor in Gold"
27,Shirley Magnusdottir,tier,Silver,Gold,"lifetime giving of $22,000 places this donor in Gold"
51,Arthur Mwangi,tier,Bronze,Silver,"lifetime giving of $2,600 places this donor in Silver"
```

**Plain language.** This is the actual stop. Nothing proceeds until a person looks at this list and approves it. In this run, all four suggestions were approved:

```
python scripts/apply_corrections.py --input donors.csv \
  --corrections work/corrections.csv --output donors_corrected.csv \
  --decision-log docs/decision-log --approved-by "Bryan Shaw"
```

```
APPLIED row 23 (Ada Yamamoto-Pierce): tier 'Silver' -> 'Gold' (lifetime giving of $17,000 places this donor in Gold)
APPLIED row 25 (Ruth Andersen): tier 'Silver' -> 'Gold' (lifetime giving of $25,000 places this donor in Gold)
APPLIED row 27 (Shirley Magnusdottir): tier 'Silver' -> 'Gold' (lifetime giving of $22,000 places this donor in Gold)
APPLIED row 51 (Arthur Mwangi): tier 'Bronze' -> 'Silver' (lifetime giving of $2,600 places this donor in Silver)
decision recorded:   docs/decision-log/0001-applied-4-data-correction-s-to-donors-csv.md
corrections applied: 4
```

**Under the hood.** `scripts/apply_corrections.py` writes the approved values into a corrected copy of the input file; it never touches the original. Because `--decision-log` and `--approved-by` were passed, `donor_rules.record_decision` also wrote a numbered, human-readable entry naming who approved what and why, the same ADR-style record this repository uses for its own architecture decisions. Design record: [ADR 0014](adr/0014-suggested-corrections-resubmit-loop.md), [ADR 0020](adr/0020-operational-decision-log.md).

## Stop 3: resubmit, and prove it

The corrected file goes back through Stop 1, exactly the same command, on the corrected data:

```
python scripts/validate_input.py --input donors_corrected.csv --config campaign.json
```

```
rows in:            50
validated:          50
exceptions:         0
with warnings:      3
```

**Plain language.** Zero exceptions. All fifty donors now pass, because the tier labels agree with the giving history that produced them. The three warnings from Stop 1 are still there (they are not data errors, they are things a reviewer should notice), and that is correct: a warning does not get cleared by fixing something else.

## Stop 4: the math

```
python scripts/calculate_ask.py --config campaign.json
```

```
asks computed:      50
review mandatory:   5
review recommended: 1
blocked (confidence fail band): 0
escalation events:  6 (work/escalations.jsonl)
no letter (routed to a person): 2
```

**Plain language.** Every donor's suggested gift amount is calculated the same way, every time, by a fixed formula, never by a model guessing. Two examples, worked out in full:

**Earl Fontaine, Platinum, volunteer, Emergency Appeal:**
```
base: Platinum 40% of largest gift $90,000 = $36,000.00
  -> volunteer uplift: +$100 = $36,100.00
  -> emergency multiplier: x1.2 = $43,320.00
  -> rounded once to nearest $50: $43,300
```

**Ada Yamamoto-Pierce, now Gold after Stop 2's correction, volunteer, gave last year:**
```
base: Gold 25% of largest gift $5,000 = $1,250.00
  -> loyalty uplift: gave in 2023, x1.10 = $1,375.00
  -> volunteer uplift: +$100 = $1,475.00
  -> emergency multiplier: x1.2 = $1,770.00
  -> rounded once to nearest $50: $1,750
```

Notice the correction from Stop 2 flows all the way through: Ada's ask is calculated at the Gold rate (25%) because her tier is now correct, not the Silver rate (15%) the original mislabeled file would have used. That is the entire cost of Stop 1 and 2 existing: a donor who could give thousands more was one silent label away from being asked for the wrong amount.

**And one donor who gets no ask at all.** Robert Svensson is Platinum, and his last gift was 2020, four years before this run's reference date. He is lapsed by policy, and policy says a lapsed major donor never gets an automated ask:

```
lapsed major donor, ask calculation skipped by policy
```

**Under the hood.** `scripts/calculate_ask.py` applies the formula in `references/policy.md` via `donor_rules.compute_ask`, one fixed order of operations, one rounding step at the very end. Every donor also gets a confidence score (1.00 minus 0.10 per warning) and a band: below 0.70 is blocked outright, below 0.90 is held for mandatory review, at or above 0.90 with no warnings needs no review. Held or blocked records write a structured event to `work/escalations.jsonl`. Design records: [ADR 0003](adr/0003-deterministic-arithmetic.md), [ADR 0011](adr/0011-confidence-scoring-feedback-loop.md).

## Stop 5: a letter is data before it is a letter

```
python scripts/generate_letters.py --config campaign.json
```

```
letters written:    48
schema rejections:  0
manifest rows:      50
```

Forty-eight, not forty-four: this run applies Stop 2's corrections first, so all 50 donors validate and only the two lapsed Platinum donors are held back. The 44 letters committed in [output/](../output/) come from a separate, uncorrected run kept as evidence of the raw fixture's first pass, with its 4 exceptions still unresolved (50 minus 4 exceptions minus 2 lapsed).

Before Earl Fontaine's letter becomes HTML, it exists as a structured object, and that object is checked against a schema:

```json
{
  "donor_id": "earl-fontaine",
  "letter_date": "June 30, 2024",
  "salutation": "Dear Earl Fontaine,",
  "opening_paragraph": "On behalf of everyone at ASPCA, thank you for your generous support. Your giving of $275,000 over the years, including your most recent gift in 2022, has made a real difference for animals in need.",
  "campaign_paragraph": "Right now, animals rescued from cruelty and neglect need emergency shelter, veterinary care, and a safe place to recover. Your gift today goes to work immediately, funding rescue operations and urgent medical treatment for animals with nowhere else to turn.",
  "ask_paragraph": "Today, I would like to invite you to consider a gift of $43,300. We would also welcome a conversation about naming and recognition opportunities that celebrate your leadership in this work.",
  "closing_phrase": "With gratitude",
  "ps_line": "",
  "signer_name": "Jordan Ellis",
  "signer_title": "Director of Development",
  "charity_name": "ASPCA",
  "donation_url": "https://www.aspca.org/donate"
}
```

**Plain language.** This is what "schema-validate the letter" means concretely: before rendering, the system checks that this object has every required field filled in, and that the ask paragraph contains exactly one dollar figure, no more, no fewer. Only after that check passes does it become a letter. Only then:

```html
<p>Dear Earl Fontaine,</p>
<p>On behalf of everyone at ASPCA, thank you for your generous support. Your
giving of $275,000 over the years, including your most recent gift in 2022,
has made a real difference for animals in need.</p>
<p>Right now, animals rescued from cruelty and neglect need emergency
shelter, veterinary care, and a safe place to recover. ...</p>
<p>Today, I would like to invite you to consider a gift of $43,300. ...</p>
<p>With gratitude,<br><strong>Jordan Ellis</strong><br>
Director of Development, ASPCA</p>
```

Notice what is not in this letter: no gift-matching claim (the campaign config has no confirmed match, so the system cannot say one exists), no guessed title, no invented staff name, no number anywhere that was not computed at Stop 4.

**Under the hood.** `scripts/generate_letters.py` assembles the object above, checks it with `donor_rules.validate_letter_model` against `references/letter_schema.json`, and only then substitutes it into `assets/template.html`. Writes `output/letters/<donor_id>.html`, `output/manifest.csv`, `work/letter_models.jsonl`. Design record: [ADR 0017](adr/0017-letter-schema-validation.md).

## Stop 6: the review queue

Fifty donors went in. Here is what a human reviewer actually sees, from the manifest:

**Every Platinum donor is mandatory review, no exceptions, regardless of score:**

| donor | status | ask | why it is held |
|---|---|---|---|
| Robert Svensson | lapsed | none | lapsed Platinum donor, no automated letter, route to personal outreach |
| Earl Fontaine | active | $43,300 | Platinum tier: always reviewed |
| Walter Adeyemi | lapsed | none | lapsed Platinum donor, no automated letter, route to personal outreach |
| Ralph Osei-Bonsu | active | $42,350 | Platinum tier: always reviewed |
| Victor Ambrosius | active | $26,400 | Platinum tier: always reviewed |

**Plain language.** Two of the five Platinum donors get no letter at all, by policy, not by accident: a form letter is the wrong instrument for a donor who has not given in years and gives at this level. They go to personal outreach instead. The other three get a letter, and it is still marked mandatory review before anyone sends it, because that is the review policy for the organization's largest donors regardless of how clean the data looked. Everyone else in this run (44 donors) needed either no review or a lighter, recommended review.

**Under the hood.** `donor_rules.review_level`: Platinum tier or any routing reason forces `mandatory`; any warning with no routing reason is `recommended`; a clean record needs `none`. This is a policy decision, not a byproduct of the confidence score. Design record: [ADR 0009](adr/0009-file-outputs-and-review-gates.md).

## What happens after this document ends

Nothing. That is the point. `output/manifest.csv` and `output/letters/*.html` sit there for a person to open, read, and decide about. This pipeline does not have a send button. Getting a letter out the door is a decision a human makes through the organization's existing channels, every time.

## Run it yourself

```bash
cd skill/charity-donor-outreach
python scripts/validate_input.py --input assets/sample_donors.csv --config assets/campaign_config.example.json
python scripts/apply_corrections.py --input assets/sample_donors.csv \
  --corrections work/corrections.csv --output work/donors_corrected.csv
python scripts/validate_input.py --input work/donors_corrected.csv --config assets/campaign_config.example.json
python scripts/calculate_ask.py --config assets/campaign_config.example.json
python scripts/generate_letters.py --config assets/campaign_config.example.json
```

Every number in this document will reproduce exactly, because every stage is deterministic. Full technical reference for every file and script: [`docs/components.md`](components.md). The same commands, followed verbatim from a scratch directory with no prior context, are what [ADR 0028](adr/0028-verified-as-an-agent-skill.md) verified.
