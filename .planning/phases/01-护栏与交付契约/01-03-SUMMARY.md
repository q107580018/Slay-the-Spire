---
phase: 01-护栏与交付契约
plan: "03"
subsystem: testing, docs
tags: [pytest, guardrail, readme, drift-test, content-checklist]

# Dependency graph
requires:
  - phase: 01-01
    provides: "pytest guardrail marker infrastructure and pyproject.toml marker registration"
provides:
  - "README guardrail command documentation (uv run pytest -m guardrail)"
  - "README content batch checklist with exact stable strings"
  - "README drift test guarding 14 key fragments with @pytest.mark.guardrail"
affects: [02-content-batches, future-content-plans]

# Tech tracking
tech-stack:
  added: []
  patterns: ["README drift test pattern: assert exact string fragments, avoid brittle counts"]

key-files:
  created: []
  modified:
    - "README.md"
    - "tests/docs/test_readme.py"

key-decisions:
  - "Updated relic coverage sentence to remove stale placeholder counts; assert runtime pool filtering instead"
  - "Fixed existing README test (batch-five assertion) to match updated implementation_status wording"
  - "Avoided asserting placeholder counts (102/98) in drift test per research guidance on instability"

patterns-established:
  - "README drift test: use required_fragments list + loop assertion for maintainable multi-string checks"

requirements-completed: [GUARD-03]

# Metrics
duration: 3min
completed: 2026-04-11
---

# Phase 01 Plan 03: README Guardrail Command and Content Batch Checklist Summary

**README documents `uv run pytest -m guardrail` command with scope list and content batch checklist, locked by 14-fragment pytest drift test**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-11T09:10:15Z
- **Completed:** 2026-04-11T09:13:18Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `### Guardrail 回归护栏` section to README with exact command and 6 guardrail scope areas
- Added `### 新增内容批次验收清单` section with 8 checklist items covering content through README updates
- Updated relic coverage sentence to reflect active placeholder filtering (no stale counts)
- Added `@pytest.mark.guardrail` drift test asserting 14 exact README fragments

## Task Commits

Each task was committed atomically:

1. **Task 1: Add README guardrail command and batch checklist** - `27b9f38` (feat)
2. **Task 2: Add README guardrail drift test** - `20c395e` (test)

## Files Created/Modified
- `README.md` - Added guardrail command section, content batch checklist, updated relic coverage sentence
- `tests/docs/test_readme.py` - Added `import pytest`, `@pytest.mark.guardrail` drift test with 14-fragment assertion loop, fixed existing batch-five test assertion

## Decisions Made
- Updated relic coverage sentence to remove stale "78/102" placeholder counts — these are unstable across content batches and should not be maintained as README facts
- Fixed existing `test_readme_mentions_batch_five_relic_coverage_without_claiming_full_completion` to assert `"占位遗物不进入随机投放池"` instead of the old `"基于 \`implementation_status\` 的过滤"` which no longer exists after plan 01-02 implemented the filtering
- Used fragment-loop pattern (`for fragment in required_fragments`) instead of individual assert lines for maintainability

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed existing README drift test broken by Task 1 edits**
- **Found during:** Task 1 (README edits)
- **Issue:** Existing test asserted `'基于 \`implementation_status\` 的过滤' in readme` but Task 1 replaced that sentence with updated wording about placeholder relics not entering random pools
- **Fix:** Changed assertion to `"占位遗物不进入随机投放池" in readme` and removed the now-contradictory negative assertion about pool filtering
- **Files modified:** `tests/docs/test_readme.py`
- **Verification:** `uv run pytest tests/docs/test_readme.py -v` — both tests pass
- **Committed in:** `27b9f38` (part of Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary fix — Task 1 edits broke existing test. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 01 guardrail infrastructure is complete (markers, tests, README documentation)
- Ready for Phase 02 content batch delivery — checklist in README defines the acceptance contract
- Future content plans can reference `uv run pytest -m guardrail` as the regression gate

---
*Phase: 01-护栏与交付契约*
*Completed: 2026-04-11*
