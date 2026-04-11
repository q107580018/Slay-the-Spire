---
phase: 01-护栏与交付契约
plan: "02"
subsystem: testing
tags: [guardrail, content-reachability, placeholder-filtering, relic-pools, tdd]

# Dependency graph
requires:
  - phase: 01-护栏与交付契约/01
    provides: "@pytest.mark.guardrail marker and pytest config for guardrail suite"
provides:
  - "Runtime placeholder relic filtering in _is_rewardable_relic and _choose_relic_id"
  - "ReachabilityRow dataclass and _content_reachability_rows helper for loaded-vs-reachable content audit"
  - "Guardrail tests for placeholder exclusion and content reachability contract"
affects: [content-expansion, relic-implementation, reward-generation]

# Tech tracking
tech-stack:
  added: []
  patterns: ["implementation_status guard in runtime pool filters", "upgrade_of reachability chain for card variants"]

key-files:
  created: []
  modified:
    - src/slay_the_spire/use_cases/start_run.py
    - src/slay_the_spire/use_cases/opening_flow.py
    - tests/use_cases/test_start_run.py
    - tests/content/test_registry_validation.py

key-decisions:
  - "Upgraded card variants (_plus) tracked via upgrade_of:{base_id} reachability markers rather than acquisition_tags"
  - "Existing test fixtures changed from implementation_status=placeholder to implemented so inclusion tests remain valid after filtering"

patterns-established:
  - "implementation_status == placeholder as first guard in relic pool filters"
  - "ReachabilityRow with content_type/content_id/loaded/reachable_via/status/suggested_file for content audit"
  - "upgrade_of:{base_card_id} marker for tracking card upgrade-path reachability"

requirements-completed: [GUARD-02]

# Metrics
duration: 8min
completed: 2026-04-11
---

# Phase 01 Plan 02: GUARD-02 Content Reachability Contract Summary

**Placeholder relics filtered from runtime random reward pools with loaded-vs-reachable content audit covering cards, relics, potions, enemies, encounters, and events**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-11T09:00:53Z
- **Completed:** 2026-04-11T09:08:13Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Placeholder relics (`implementation_status == "placeholder"`) now excluded from all runtime random relic sequences (common/uncommon/rare/shop/boss) and Neow random relic offers
- Content reachability report helper (`_content_reachability_rows`) audits all 6 content types: cards via starter_deck/acquisition_tags/upgrade_of chains, relics via runtime sequences/neow pool/starter relics, potions via pool membership, enemies/encounters/events via act pool entries
- Zero `loaded_not_reachable` content across the entire content corpus — all loaded content is reachable through at least one runtime acquisition path

## Task Commits

Each task was committed atomically:

1. **Task 1: Filter placeholder relics from random runtime pools**
   - `b1b9adf` (test) — add failing guardrail tests for placeholder relic exclusion
   - `ae2cb0a` (feat) — filter placeholder relics from runtime random reward pools
2. **Task 2: Add loaded-vs-reachable report assertions** — `6f3ce9b` (test) — add content reachability guardrail with upgrade-path tracking

## Files Created/Modified
- `src/slay_the_spire/use_cases/start_run.py` — Added `implementation_status == "placeholder"` guard as first check in `_is_rewardable_relic`
- `src/slay_the_spire/use_cases/opening_flow.py` — Added `implementation_status != "placeholder"` filter in `_choose_relic_id` list comprehension
- `tests/use_cases/test_start_run.py` — Updated fixture payloads to `"implemented"`, added 2 guardrail tests for placeholder exclusion (sequences + Neow), updated pool membership assertion
- `tests/content/test_registry_validation.py` — Added `ReachabilityRow` dataclass, `_format_reachability_failures` helper, `_content_reachability_rows` helper with upgrade-path tracking, and guardrail test asserting loaded-vs-reachable contract

## Decisions Made
- **Upgrade-path reachability:** Card `_plus` variants aren't in any acquisition pool directly — they're reachable via the `upgrades_to` field on base cards. Added `upgrade_of:{base_id}` marker to correctly track these as reachable content rather than flagging them as unreachable.
- **Existing test fixture updates:** Two existing tests (`test_start_new_run_auto_includes_new_relic_entries_by_pool`, `test_neow_random_relic_selection_uses_neow_pool_membership`) had fixtures using `implementation_status: "placeholder"`. Changed to `"implemented"` since these tests verify inclusion behavior, and placeholder relics are now correctly excluded.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed upgrade card reachability false positives**
- **Found during:** Task 2 (content reachability report)
- **Issue:** All `_plus` card variants were reported as `loaded_not_reachable` because the reachability helper only checked `starter_deck` and `acquisition_tags`, not the `upgrades_to` upgrade chain
- **Fix:** Built `upgrade_targets` index mapping upgraded card IDs to their base card IDs, then added `upgrade_of:{base_id}` markers for any card that is an upgrade target
- **Files modified:** tests/content/test_registry_validation.py
- **Verification:** `uv run pytest -m guardrail tests/content/test_registry_validation.py -q` exits 0 with zero loaded_not_reachable rows
- **Committed in:** 6f3ce9b

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential for correctness — the plan's reachability helper spec didn't account for upgrade-path cards. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- GUARD-02 content reachability contract is in place; future content additions will be caught if not wired to a runtime acquisition path
- Placeholder relics are safely excluded from all random reward pools while remaining visible in the registry for reporting
- Ready for Plan 03 or subsequent content expansion phases

## Self-Check: PASSED

All 5 files verified present. All 3 task commits (b1b9adf, ae2cb0a, 6f3ce9b) verified in git log.

---
*Phase: 01-护栏与交付契约*
*Completed: 2026-04-11*
