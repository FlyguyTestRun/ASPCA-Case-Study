# ADR 0040: Sortable table columns, and a table header that actually stays put

Status: accepted. Date: 2026-07-14.

## Problem

The donor table had no way to sort by any column: a reviewer wanting to see the largest gifts first, or group every flagged row together, had only the search box and the status filter. Separately, while wiring in a fix for this, the table header's `position: sticky` turned out to have never actually worked. `.table-scroll` sets `overflow-x: auto` for horizontal scrolling on the wide table; per the CSS Overflow spec, setting one overflow axis to anything but `visible` forces the other axis to compute as `auto` too, so the container silently became a vertical scroll context as well. With no height limit, that container always exactly fit its own content, meaning it never had an internal scroll range for anything to stick within: the sticky header had been dead code since it was written, invisible in normal use because nobody had reason to check.

## Decision

Every sortable column header (donor name, region, stated and computed tier, status, largest gift, lifetime, last gift year, ask, confidence, review level, flag, reviewed) is clickable: click once for ascending, again for descending, with an arrow indicator and `aria-sort` for accessibility. Sorting happens after the existing search and status filter, so it composes with them rather than replacing them.

`.table-scroll` now has an explicit `max-height: 70vh` alongside its `overflow-y: auto`, giving it a real, bounded scroll range. The header's `position: sticky; top: 0` now sticks relative to that container's own scrollport, not the page viewport, which also means it never needs to account for the sticky process nav above it ([ADR 0039](0039-guided-process-nav-and-final-snapshot-in-archive.md)): the two no longer occupy the same coordinate space at all, a simpler and more robust fix than trying to offset one against the other's height.

## What this changes going forward

Verified live: clicking a column header sorts ascending then descending correctly (name alphabetically, lifetime giving numerically), `aria-sort` updates on the active header, and scrolling within the bounded table now keeps the header genuinely pinned in place, confirmed by checking a header cell's screen position before and after an internal scroll (unchanged) against a table row's position (changed), so this isn't just everything being frozen. The Node test harness's stub `document.documentElement.style` had no `setProperty` method and crashed every single test the moment production code called it during an earlier draft of this fix (a page-load side effect, not gated behind an event); fixed by extending the shared stub, the same reusable-stub philosophy already established for this test suite. Suite holds at 155 (no behavior needed a new dedicated test beyond what live verification and the existing render tests already cover).
