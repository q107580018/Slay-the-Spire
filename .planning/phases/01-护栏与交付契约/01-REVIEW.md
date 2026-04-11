---
phase: 01-护栏与交付契约
reviewed: 2026-04-11T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - pyproject.toml
  - src/slay_the_spire/use_cases/start_run.py
  - src/slay_the_spire/use_cases/opening_flow.py
  - tests/app/test_session.py
  - tests/e2e/test_two_act_smoke.py
  - tests/use_cases/test_apply_reward.py
  - tests/domain/test_effect_resolver.py
  - tests/use_cases/test_save_load.py
  - tests/use_cases/test_start_run.py
  - tests/content/test_registry_validation.py
  - tests/docs/test_readme.py
  - README.md
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: clean
---

# Phase 01: Code Review Report

**Reviewed:** 2026-04-11
**Depth:** standard
**Files Reviewed:** 12
**Status:** clean

## Summary

Phase 01 (护栏与交付契约) spans three sub-plans:

1. **01-01 (GUARD-01):** Registered `guardrail` pytest marker in `pyproject.toml` and annotated 20 critical-path tests across 5 test files. Pure test infrastructure — no production code changed.
2. **01-02 (GUARD-02):** Filtered placeholder relics (`implementation_status == "placeholder"`) from runtime random relic pools in `start_run.py` and `opening_flow.py`. Added content reachability report helper and guardrail tests. Updated test fixtures.
3. **01-03 (GUARD-03):** Added README sections for guardrail command and content batch checklist. Added README drift test with 14 required fragments.

All changes are well-scoped, consistent with summaries, and correctly implemented. The placeholder filtering logic in `start_run.py` (line 21) and `opening_flow.py` (line 273) is clean — applied as the first guard before pool/owner filtering. No bugs, no security issues, no production code quality problems were found.

## Info

### IN-01: Private attribute access in test helper

**File:** `tests/content/test_registry_validation.py:1321`
**Issue:** `_content_reachability_rows` accesses `provider._catalog.potion_pool_ids`, which is a private attribute of `StarterContentProvider`. This creates coupling to the internal implementation detail.
**Fix:** Consider exposing a public `potion_pool_ids` property on `StarterContentProvider` or `ContentProviderPort` if this access pattern is needed in multiple places. Acceptable for now as this is test-only code.

### IN-02: Repeated `# type: ignore[no-redef]` in test helper

**File:** `tests/content/test_registry_validation.py:1273,1320,1374,1398`
**Issue:** The `markers` variable is redefined multiple times within `_content_reachability_rows` with `# type: ignore[no-redef]` comments. This is a mild code smell — the variable shadows previous bindings in the same function scope.
**Fix:** Use distinct variable names per content-type section (e.g., `relic_markers`, `potion_markers`) or restructure the function into sub-functions per content type. Functionally harmless as each section is independent.

---

_Reviewed: 2026-04-11_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
