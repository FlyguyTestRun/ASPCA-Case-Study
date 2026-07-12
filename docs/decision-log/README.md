# Decision History

This folder is written by the system, not by hand. Every persistent
operational change leaves a numbered, ADR-style entry here with the problem,
the decision, the effect going forward, and the named person who approved it:

- **Applied corrections**: a batch of data fixes approved in the review app's
  findings step, or via `apply_corrections.py --decision-log ... --approved-by ...`
- **Style adoptions**: a letter-style preference adopted after repeated
  reviewer edits passed the guardrails
- **Review sign-offs**: a batch cleared for delivery after every required
  record was individually reviewed

Authored architecture decisions live separately in [docs/adr/](../adr/): that
folder records how the system was designed; this one records how it has been
governed since. Design record: [ADR 0020](../adr/0020-operational-decision-log.md).
