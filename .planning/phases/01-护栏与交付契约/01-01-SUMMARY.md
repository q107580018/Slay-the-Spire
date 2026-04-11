---
phase: 01-护栏与交付契约
plan: "01"
subsystem: testing
tags: [pytest, markers, guardrail, regression-contract]

# Dependency graph
requires: []
provides:
  - "pytest guardrail marker registered in pyproject.toml"
  - "20 function-level @pytest.mark.guardrail annotations across 5 test files"
  - "uv run pytest -m guardrail selects session/reward/effect/save-load/e2e critical path"
affects: [01-02, 02-*, 03-*]

# Tech tracking
tech-stack:
  added: []
  patterns: ["function-level @pytest.mark.guardrail for critical regression contract"]

key-files:
  created: []
  modified:
    - pyproject.toml
    - tests/app/test_session.py
    - tests/e2e/test_two_act_smoke.py
    - tests/use_cases/test_apply_reward.py
    - tests/domain/test_effect_resolver.py
    - tests/use_cases/test_save_load.py

key-decisions:
  - "Function-level decorators only, no module-level pytestmark — avoids sweeping in all tests from large files"
  - "Exactly 20 tests selected across 5 files covering the 5 critical subsystems identified in D-01 through D-04"

patterns-established:
  - "guardrail marker: add @pytest.mark.guardrail to any test that guards a critical regression path"
  - "import placement: import pytest after stdlib, before project imports"

requirements-completed: [GUARD-01]

# Metrics
duration: 5min
completed: 2026-04-11
---

# Phase 01 Plan 01: GUARD-01 Guardrail Marker Summary

**Registered pytest `guardrail` marker and annotated 20 critical-path tests spanning session routing, cross-act E2E smoke, reward generation/application, effect queue/hook timing, and save/load round-trips**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-11T08:53:25Z
- **Completed:** 2026-04-11T08:58:56Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Registered `guardrail` custom pytest marker in `pyproject.toml` with descriptive text
- Marked 20 existing tests with `@pytest.mark.guardrail` across 5 test files (4 session, 2 e2e, 5 reward, 6 effect, 3 save/load)
- `uv run pytest -m guardrail` now selects exactly these 20 tests, all passing in 0.6s

## Task Commits

Each task was committed atomically:

1. **Task 1: Register the guardrail marker** - `2a26779` (chore)
2. **Task 2: Mark representative GUARD-01 tests** - `9e42094` (test)

## Files Created/Modified
- `pyproject.toml` - Added `markers` array under `[tool.pytest.ini_options]` with guardrail marker description
- `tests/app/test_session.py` - Added `import pytest` and `@pytest.mark.guardrail` on 4 session routing tests
- `tests/e2e/test_two_act_smoke.py` - Added `import pytest` and `@pytest.mark.guardrail` on 2 cross-act transition tests
- `tests/use_cases/test_apply_reward.py` - Added `import pytest` and `@pytest.mark.guardrail` on 5 reward generation/application tests
- `tests/domain/test_effect_resolver.py` - Added `import pytest` and `@pytest.mark.guardrail` on 6 effect queue/hook timing tests
- `tests/use_cases/test_save_load.py` - Added `@pytest.mark.guardrail` on 3 save/load round-trip tests (already had pytest import)

## Decisions Made
- Used function-level `@pytest.mark.guardrail` decorators instead of module-level `pytestmark` to avoid sweeping all tests from large files into the guardrail subset
- Selected exactly 20 tests across the 5 critical subsystems identified by research decisions D-01 through D-04, without adding coverage thresholds (per D-15)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The guardrail marker is ready for use by all subsequent phases
- Future phases can add `@pytest.mark.guardrail` to new critical-path tests
- `uv run pytest -m guardrail` provides a fast (<1s) critical regression check

---
*Phase: 01-护栏与交付契约*
*Completed: 2026-04-11*
