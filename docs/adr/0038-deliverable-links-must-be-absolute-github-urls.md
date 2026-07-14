# ADR 0038: Every outbound link in the standalone deliverable must be an absolute GitHub URL

Status: accepted. Date: 2026-07-13.

## Problem

The deliverable's brief, architecture, and restraint sections linked out to `ASSESSMENT.md`, the trap registry, `SKILL.md`, and eleven ADRs using paths relative to the file itself (`../docs/adr/0002-....md`, `../assessment/ASSESSMENT.md`, and so on). Those paths resolve correctly when the file is opened locally or served from a checkout of the repository, because the relative path and the repository's own folder structure line up. They do not resolve the same way once the file is hosted on its own origin: on the live GitHub Pages site, the same relative path requests `flyguytestrun.github.io/ASPCA-Case-Study/docs/adr/....md`, which GitHub Pages serves as the raw, unstyled markdown text rather than GitHub's rendered file view. A reviewer clicking any of these links on the deployed page, the version that actually ships to Doug, would land on a wall of unrendered `#`/`##` syntax instead of a readable decision record. Confirmed live: the currently deployed page carries 12 of these relative links, every one of them degrading this way.

The "Scripts on GitHub" panel, built earlier, had already solved this correctly by linking directly to `https://github.com/FlyguyTestRun/ASPCA-Case-Study/blob/main/...`. The newer sections (the brief, the architecture explanation, the restraint list, and the walkthrough's per-step reference links) did not follow that pattern.

## Decision

Every link in `donor-data-review.template.html` that points at another file in the repository is now an absolute `https://github.com/FlyguyTestRun/ASPCA-Case-Study/blob/main/<path>` URL, matching the one pattern that already worked. This applies uniformly regardless of where the page is opened from: locally, from the offline `dist/` copy, or from GitHub Pages, the link always lands on GitHub's own rendered view of the file.

## What this changes going forward

Fixed all eleven relative links in the HTML template (the brief section's assessment and trap-registry links, the architecture section's ADR list, the new restraint section's link to `scale-architecture.md`, and the `SKILL.md` references) plus the four `refHref` values added to the walkthrough's per-step reference links, none of which were caught by the first pass since they are JavaScript string literals, not HTML `href` attributes, and a different sed pattern was needed to find them. Verified by extracting every absolute link from the rebuilt page and checking each one resolves with a real HTTP request against GitHub: 18 of 18 return 200, and one was spot-checked in the browser to confirm it opens GitHub's rendered file view rather than raw text. Any future addition of an outbound link in this file should follow the same absolute pattern; a relative path will pass every local and headless test (since those never leave the local filesystem) and still be broken on the one deployment that matters. `tests/test_deliverable_logic.py` does not currently assert against this class of bug, since it requires an actual HTTP round trip, a link-resolution sweep against the built HTML is worth re-running by hand before any future submission rather than left to the automated suite alone.
