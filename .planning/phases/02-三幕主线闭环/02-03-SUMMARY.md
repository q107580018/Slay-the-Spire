---
phase: 02-三幕主线闭环
plan: "03"
subsystem: e2e, save-load
tags: [three-act, smoke-test, transition, save-load, guardrail]

# Dependency graph
requires:
  - phase: 02-01
    provides: "Act 3 content pools and Act 2 -> Act 3 link"
  - phase: 02-02
    provides: "Terminal-phase rendering updates"
provides:
  - "Three-act end-to-end smoke coverage"
  - "Act2->Act3 and Act3->Victory boundary assertions"
  - "Act3 save/load round-trip tests under schema_version=3"
affects: [phase-verification]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Boss reward to boss_chest transition tested via deterministic forced boss state helper"]

key-files:
  created:
    - "tests/e2e/test_three_act_smoke.py"
  modified:
    - "tests/e2e/test_two_act_smoke.py"
    - "tests/use_cases/test_save_load.py"
    - "tests/use_cases/test_room_recovery.py"

key-decisions:
  - "Two-act smoke expectation updated: Act2 boss no longer leads directly to victory"
  - "Added dedicated three-act smoke suite instead of overloading existing single/two-act files"
  - "save/load keeps schema_version=3 while validating act3 progression payloads"

requirements-completed: [RUN-01, RUN-03]

# Metrics
duration: 18min
completed: 2026-04-11
---

# Phase 02 Plan 03 Summary

**Three-act gameplay path is now covered end-to-end, and Act3 save/load round-trip behavior is validated under schema version 3.**

## Performance
- **Tasks:** 2
- **Files changed:** 4
- **Verification:**
  - `uv run pytest tests/e2e/ -x -v` passed
  - `uv run pytest tests/use_cases/test_save_load.py -x -v` passed
  - `uv run pytest -m guardrail` passed
  - `uv run pytest -x` passed

## Accomplishments
- Added `tests/e2e/test_three_act_smoke.py` with:
  - full Act1 -> Act2 -> Act3 -> Victory smoke,
  - Act2 -> Act3 boundary test,
  - Act3 -> Victory boundary test.
- Updated `tests/e2e/test_two_act_smoke.py` to assert Act2 boss transition into Act3.
- Added two save/load tests for Act3 round-trip field consistency and schema stability.
- Updated room recovery test to treat Act3 as final act for `完成攀登` expectation.

## Task Commits
1. **Task 1: three-act E2E + transition boundary tests** — `9dfa7f6`
2. **Task 2: act3 save/load round-trip tests** — `2b3b883`

## Deviations from Plan
- While running full regression (`uv run pytest -x`), an existing test in `test_room_recovery.py` still assumed Act2 was final act. Updated it to Act3-final semantics to match the new progression baseline.

## Issues Encountered
- Parallel commit invocation created `.git/index.lock`; resolved by removing lock and committing sequentially.
