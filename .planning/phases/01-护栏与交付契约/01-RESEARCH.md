# Phase 01: 护栏与交付契约 - Research

**Researched:** 2026-04-11 [VERIFIED: system date]
**Domain:** Python pytest guardrails, content reachability reporting, delivery checklist contracts [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md]
**Confidence:** HIGH [VERIFIED: local codebase inspection + targeted pytest run]

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
## Implementation Decisions

### 回归测试包边界
- **D-01:** Phase 1 的必跑护栏采用关键链路最小集，覆盖 session 菜单模式、跨幕推进、reward generate/apply、effect queue/hook 时序和 save/load round-trip。
- **D-02:** E2E 只要求固定 seed 的短路径 smoke，覆盖跨幕、奖励和存读档关键节点；不在 Phase 1 提前追求完整三幕通关，完整 Act 1 -> Act 3 -> Boss Chest -> Victory 留给 Phase 2。
- **D-03:** `effect_resolver.py` 护栏重点是时序契约，包括 queue tail 顺序、hook 入队顺序、dead target noop 和 combat end 触发顺序；不要把 Phase 1 扩成逐张卡牌效果补全。
- **D-04:** 回归护栏要能用 `pytest` 子集运行，优先通过 marker 或集中测试文件组织。

### 内容可触达校验口径
- **D-05:** “已录入”定义为 registry 能加载；“可触达”定义为被角色、幕、奖励池、事件池、遭遇池等运行入口引用。
- **D-06:** placeholder 遗物单独列出；凡进入随机奖励池的 placeholder 都应让校验失败，不在随机池的 placeholder 只列入报告。
- **D-07:** 未接入奖励池/运行入口的判定要按内容类型检查：卡牌查角色奖励池，遗物查 standard/boss/shop/event/Neow 等池，药水查 potion pool，敌人和事件查 act pool。
- **D-08:** 校验输出采用 pytest 断言 + 可读摘要。测试失败给最小缺口列表，helper/report 文本便于人工区分“已录入 vs 可触达”。

### 新增内容批次验收清单格式
- **D-09:** 验收清单采用 README 模板 + 测试守护：README 写开发者清单，测试验证关键事实，避免清单变成无人维护的独立文档。
- **D-10:** 每批新增内容的清单覆盖全链路最小项：`content/`、registry/content validation、domain/use case、session route、presentation/Textual、README。
- **D-11:** 关键入口缺失即视为未交付。内容 JSON 已新增但 registry 校验、触达池、应用链路或玩家反馈缺任一关键项，不能算完成。
- **D-12:** 新增 placeholder 必须明确策略：有 `implementation_status`，不进入随机投放池，并且在 README 或覆盖报告中可见。

### 测试执行入口与开发者体验
- **D-13:** 护栏测试入口使用 pytest marker + README 命令，例如 `uv run pytest -m guardrail`。
- **D-14:** 失败输出优先服务开发者定位，直接列出缺口 ID、内容类型、池/入口和建议检查文件。
- **D-15:** Phase 1 不引入 coverage 百分比阈值，避免用行覆盖率制造噪音；重点是关键链路行为。
- **D-16:** README 需要记录 guardrail 命令、适用场景、失败含义，以及内容批次如何使用验收清单。

### Claude's Discretion
- pytest marker 的具体命名、集中测试文件拆分、helper/report 的内部实现结构由 planner/researcher 根据现有测试布局决定。
- 固定 seed 短路径 smoke 的具体 seed 和构造方式可由实现阶段选择，但不得扩大为完整三幕主线交付。

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within Phase 1 scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GUARD-01 | 开发者可以运行覆盖 session 菜单模式、跨幕推进、reward generate/apply、effect 时序和 save/load round-trip 的回归测试。 | Use pytest `guardrail` marker, mark existing critical-path tests, and add a compact cross-path save/load smoke where needed. [VERIFIED: .planning/REQUIREMENTS.md] [VERIFIED: tests/app/test_session.py, tests/e2e/test_two_act_smoke.py, tests/use_cases/test_apply_reward.py, tests/domain/test_effect_resolver.py, tests/use_cases/test_save_load.py] |
| GUARD-02 | 内容覆盖校验能区分“已录入内容”和“运行时可触达内容”，并能暴露 placeholder 遗物或未接入奖励池的内容。 | Add a content reachability report helper driven by `StarterContentProvider`, `ContentCatalog` pool metadata, card `acquisition_tags`, relic `pools`, and `start_new_run` relic sequences. [VERIFIED: .planning/REQUIREMENTS.md] [VERIFIED: src/slay_the_spire/content/catalog.py] [VERIFIED: src/slay_the_spire/use_cases/start_run.py] |
| GUARD-03 | 新增内容批次有一致的验收清单，覆盖 `content/`、registry、domain/use case、session、presentation/Textual 和 README 更新。 | Document checklist in README and back it with a README test so the guardrail command fails if the checklist disappears. [VERIFIED: .planning/REQUIREMENTS.md] [VERIFIED: tests/docs/test_readme.py] |
</phase_requirements>

## Summary

Phase 1 should not add gameplay content; it should create a stable regression contract around existing critical paths and a content delivery contract for later content batches. [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md] The project already has strong local test assets for session routing, reward generation/application, effect ordering, save/load, content registry validation, README assertions, and short E2E flows, and a targeted local run of the relevant subset passed with `223 passed in 2.20s`. [VERIFIED: tests/app/test_session.py] [VERIFIED: tests/use_cases/test_apply_reward.py] [VERIFIED: tests/domain/test_effect_resolver.py] [VERIFIED: tests/use_cases/test_save_load.py] [VERIFIED: tests/e2e/test_two_act_smoke.py] [VERIFIED: uv run pytest targeted subset 2026-04-11]

The main implementation gap is not the existence of tests; it is a stable selector and report contract. [VERIFIED: pyproject.toml] There is currently no registered `guardrail` marker in pytest config and `uv run pytest --markers` only lists built-in markers. [VERIFIED: uv run pytest --markers 2026-04-11] Add `guardrail` to `[tool.pytest.ini_options]`, mark the relevant tests rather than creating a custom runner, and document `uv run pytest -m guardrail` in README. [CITED: docs.pytest.org/en/stable marker documentation] [VERIFIED: pyproject.toml]

The highest-risk Phase 1 finding is GUARD-02: the current runtime relic sequences include placeholder relics. [VERIFIED: uv run python content inventory 2026-04-11] The local inventory found 180 loaded relics, 98 marked `placeholder`, and placeholder entries in runtime sequences for `common`, `uncommon`, `rare`, `shop`, and `boss`. [VERIFIED: uv run python content inventory 2026-04-11] The planner should split this into a report helper plus a failing guardrail test for placeholder relics in random reward pools; do not silently filter without an explicit implementation task. [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md]

**Primary recommendation:** Use pytest markers plus small report helpers; do not introduce a separate coverage tool, CLI, or external dependency. [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md] [VERIFIED: pyproject.toml]

## Project Constraints (from CLAUDE.md)

- Use `uv` for all Python dependency and command execution. [VERIFIED: CLAUDE.md]
- The project is Python 3.12+, Textual, Rich, local single-player, menu-driven, save/load capable, and not a GUI/server project. [VERIFIED: CLAUDE.md]
- Treat `app/session.py` as the ground truth for flow and menu routing. [VERIFIED: CLAUDE.md]
- Edit only root `content/` for content changes; `src/slay_the_spire/data/content/` is generated for packaging and should not be hand-edited. [VERIFIED: CLAUDE.md]
- Current save schema version is 3; save schema changes must update `save_game.py`, `load_game.py`, and related tests together. [VERIFIED: CLAUDE.md]
- Player-facing UI text defaults to Chinese; code identifiers, commands, paths, and necessary proper nouns stay in original language. [VERIFIED: CLAUDE.md]
- When game design sources conflict, follow current codebase Gen-1 baseline plus landed behavior over Gen-2 materials or old design docs. [VERIFIED: CLAUDE.md]
- README must be updated after code, content, command, flow, test baseline, or release changes; AGENTS.md changes are only for collaboration constraints or repository facts. [VERIFIED: CLAUDE.md]

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | Requires `>=3.12`; local `python3` is 3.14.3 under `uv run` | Runtime and tests | Project package declares Python `>=3.12`; local environment satisfies it. [VERIFIED: pyproject.toml] [VERIFIED: python3 --version 2026-04-11] |
| pytest | Installed 9.0.2; project dev dependency `pytest>=8.0` | Regression guardrail runner | Existing tests use pytest assertions, parametrization, `monkeypatch`, and tmp paths; pytest supports marker selection via `-m`. [VERIFIED: pyproject.toml] [VERIFIED: importlib.metadata 2026-04-11] [CITED: docs.pytest.org/en/stable marker documentation] |
| uv | 0.11.3 | Dependency and command execution | Project instructions and README require uv for Python work. [VERIFIED: CLAUDE.md] [VERIFIED: uv --version 2026-04-11] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| textual | Installed 8.1.1; project dependency `textual>=8.1.1` | Existing TUI app and `run_test` UI checks | Only use for tests that must verify Textual behavior; Phase 1 should not add a new UI framework. [VERIFIED: pyproject.toml] [VERIFIED: tests/adapters/textual/test_slay_app.py] |
| rich | Installed 14.3.3; project dependency `rich>=14.3.3` | Shared renderables and inspect output | Use through existing presentation adapters when guardrails inspect player-visible text. [VERIFIED: pyproject.toml] [VERIFIED: src/slay_the_spire/adapters/presentation] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytest marker | Separate shell script or custom runner | Reject for Phase 1: the user locked the command shape around pytest marker and README documentation. [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md] |
| pytest assertions + readable summaries | Coverage percentage threshold | Reject for Phase 1: coverage thresholds were explicitly excluded. [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md] |
| Local helper functions | New reporting package/dependency | Reject for Phase 1: no dependency gap exists and pyproject has only pytest as dev dependency. [VERIFIED: pyproject.toml] |

**Installation:** No new packages are required for Phase 1. [VERIFIED: pyproject.toml]

```bash
uv sync --dev
```

**Version verification:** Versions were verified with `uv --version`, `python3 --version`, and `uv run python -c "from importlib.metadata import version"`. [VERIFIED: local command 2026-04-11]

## Architecture Patterns

### Recommended Project Structure
```text
pyproject.toml                                      # register pytest guardrail marker [VERIFIED: pyproject.toml]
README.md                                           # document guardrail command and content batch checklist [VERIFIED: CLAUDE.md]
tests/app/test_session.py                           # mark session menu/routing guardrails [VERIFIED: tests/app/test_session.py]
tests/e2e/test_single_act_smoke.py                  # mark fixed-seed short path smoke where relevant [VERIFIED: tests/e2e/test_single_act_smoke.py]
tests/e2e/test_two_act_smoke.py                     # mark cross-act boss chest/victory smoke [VERIFIED: tests/e2e/test_two_act_smoke.py]
tests/use_cases/test_apply_reward.py                # mark reward generate/apply guardrails [VERIFIED: tests/use_cases/test_apply_reward.py]
tests/domain/test_effect_resolver.py                # mark effect queue/hook timing guardrails [VERIFIED: tests/domain/test_effect_resolver.py]
tests/use_cases/test_save_load.py                   # mark save/load round-trip guardrails [VERIFIED: tests/use_cases/test_save_load.py]
tests/content/test_registry_validation.py           # keep registry metadata checks and add/mark reachability checks [VERIFIED: tests/content/test_registry_validation.py]
tests/docs/test_readme.py                           # extend README checklist guard [VERIFIED: tests/docs/test_readme.py]
```

### Pattern 1: Marker-First Guardrail Selector
**What:** Register `guardrail` in `pyproject.toml`, then mark a small set of existing and new tests with `@pytest.mark.guardrail` or module-local `pytestmark`. [VERIFIED: pyproject.toml] [CITED: docs.pytest.org/en/stable marker documentation]

**When to use:** Use for GUARD-01 and GUARD-02 tests that should run with `uv run pytest -m guardrail`. [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md]

**Example:**
```python
# Source: pytest marker pattern verified against pytest docs and local test style.
import pytest

pytestmark = pytest.mark.guardrail

def test_save_load_round_trips_extended_combat_state(tmp_path):
    ...
```

### Pattern 2: Content Reachability Report as Test Helper
**What:** Build a small helper that returns structured rows with `content_type`, `content_id`, `loaded`, `reachable_via`, `status`, and `suggested_file`; assert on the rows and format failures with newline-joined concise details. [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md] [VERIFIED: tests/content/test_registry_validation.py]

**When to use:** Use for GUARD-02 to distinguish registry-loaded content from runtime-reachable content. [VERIFIED: .planning/REQUIREMENTS.md]

**Example:**
```python
# Source: local ContentProviderPort and pytest assertion style.
@pytest.mark.guardrail
def test_placeholder_relics_do_not_enter_random_relic_sequences() -> None:
    provider = StarterContentProvider(Path(__file__).resolve().parents[2] / "content")
    run_state = start_new_run("ironclad", seed=7, registry=provider)
    offenders = [
        f"{pool_id}:{relic_id}"
        for pool_id, relic_ids in run_state.relic_sequences.items()
        for relic_id in relic_ids
        if provider.relics().get(relic_id).implementation_status == "placeholder"
    ]
    assert not offenders, "placeholder relics in random pools:\n" + "\n".join(offenders[:50])
```

### Pattern 3: README Checklist Backed by Tests
**What:** Add the human checklist to README and assert key strings in `tests/docs/test_readme.py`. [VERIFIED: tests/docs/test_readme.py] [VERIFIED: CLAUDE.md]

**When to use:** Use for GUARD-03 because the user locked README template plus test guard rather than a standalone document. [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md]

**Example:**
```python
# Source: tests/docs/test_readme.py
def test_readme_documents_guardrail_command_and_content_batch_checklist() -> None:
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text(encoding="utf-8")
    assert "uv run pytest -m guardrail" in readme
    assert "content/" in readme
    assert "presentation/Textual" in readme
```

### Anti-Patterns to Avoid
- **Custom coverage gate:** It contradicts the explicit Phase 1 decision to avoid coverage percentage thresholds. [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md]
- **Full three-act E2E in Phase 1:** It contradicts the locked boundary; Act 1 -> Act 3 -> victory is deferred to Phase 2. [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md]
- **Hand-editing `src/slay_the_spire/data/content/`:** Project constraints say root `content/` is the development source. [VERIFIED: CLAUDE.md]
- **A vague content report:** GUARD-02 requires listing content ID, type, pool/entry point, and actionable file hints. [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Test subset selection | Custom shell runner | pytest marker `guardrail` and `uv run pytest -m guardrail` | pytest already supports marker selection and the phase decision requires this command shape. [CITED: docs.pytest.org/en/stable marker documentation] [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md] |
| Content loading | JSON directory walker duplicated in tests | `StarterContentProvider` and `ContentCatalog` | Existing provider loads registries, pools, and validates startup integrity. [VERIFIED: src/slay_the_spire/content/provider.py] [VERIFIED: src/slay_the_spire/content/catalog.py] |
| Reward reachability | Reimplement reward generation | `start_new_run`, `generate_combat_rewards`, `generate_boss_rewards`, `apply_reward` | Existing code is the runtime contract for relic sequences and reward application. [VERIFIED: src/slay_the_spire/use_cases/start_run.py] [VERIFIED: src/slay_the_spire/domain/rewards/reward_generator.py] [VERIFIED: src/slay_the_spire/use_cases/apply_reward.py] |
| Save/load validation | Manual JSON equivalence script | Existing `save_game`/`load_game` tests and `JsonFileSaveRepository` | Existing tests already cover schema version, combat state consistency, boss chest, treasure, act cache, and relic sequence round-trips. [VERIFIED: tests/use_cases/test_save_load.py] |

**Key insight:** Phase 1 is a contract phase; the planner should connect existing runtime APIs and pytest mechanisms rather than inventing separate validation infrastructure. [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md] [VERIFIED: local codebase inspection]

## Common Pitfalls

### Pitfall 1: Marking Too Much as Guardrail
**What goes wrong:** `uv run pytest -m guardrail` becomes nearly as slow and noisy as the full suite. [ASSUMED]
**Why it happens:** Existing files contain broad regression tests, especially `tests/use_cases/test_apply_reward.py` and `tests/content/test_registry_validation.py`. [VERIFIED: tests/use_cases/test_apply_reward.py] [VERIFIED: tests/content/test_registry_validation.py]
**How to avoid:** Mark only representative critical-path tests and add small new guardrail tests for missing contracts. [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md]
**Warning signs:** The marker is applied to entire large modules without confirming all tests are Phase 1 guardrails. [ASSUMED]

### Pitfall 2: Treating Registry Load as Runtime Reachability
**What goes wrong:** A card/relic/event appears in `provider.*().all()` but never appears through a player-facing reward, act, encounter, event, or pool path. [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md]
**Why it happens:** `ContentCatalog` loads all JSON into registries, while runtime reachability depends on tags, pools, act references, and generated sequences. [VERIFIED: src/slay_the_spire/content/catalog.py] [VERIFIED: src/slay_the_spire/use_cases/start_run.py]
**How to avoid:** Report `loaded` separately from `reachable_via` and assert on missing runtime entry points by type. [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md]
**Warning signs:** A test only calls `provider.relics().get(id)` or `provider.cards().get(id)` and claims content is delivered. [VERIFIED: tests/content/test_registry_validation.py]

### Pitfall 3: Placeholder Relics in Random Pools
**What goes wrong:** Placeholder relics can be included in random runtime relic sequences. [VERIFIED: uv run python content inventory 2026-04-11]
**Why it happens:** `_build_relic_sequences` filters by `relic.pools` and character ownership, but not by `implementation_status`. [VERIFIED: src/slay_the_spire/use_cases/start_run.py]
**How to avoid:** Add a guardrail failure for placeholder relics in random pools and plan any filter behavior as a deliberate code change. [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md]
**Warning signs:** Runtime sequences contain placeholder relics in `common`, `uncommon`, `rare`, `shop`, or `boss`. [VERIFIED: uv run python content inventory 2026-04-11]

### Pitfall 4: README Drift
**What goes wrong:** README claims coverage or random-pool behavior that the code does not enforce. [VERIFIED: README.md] [VERIFIED: tests/docs/test_readme.py]
**Why it happens:** README currently mentions relic counts and implementation-status filtering, while local inventory found a different placeholder count than the README text. [VERIFIED: README.md] [VERIFIED: uv run python content inventory 2026-04-11]
**How to avoid:** Update README in the same phase and test for the exact command and checklist wording, while avoiding brittle count assertions unless the count is intentionally maintained. [VERIFIED: CLAUDE.md] [VERIFIED: tests/docs/test_readme.py]
**Warning signs:** README states placeholder filtering is solved before the guardrail/code change lands. [VERIFIED: tests/docs/test_readme.py]

## Code Examples

### Register the Guardrail Marker
```toml
# Source: pyproject.toml + pytest marker docs
[tool.pytest.ini_options]
pythonpath = ["src"]
markers = [
  "guardrail: critical regression contract for session/reward/effect/save-load/content reachability",
]
```

### Minimal Reachability Row
```python
# Source: local dataclass/test helper style
from dataclasses import dataclass

@dataclass(frozen=True)
class ReachabilityRow:
    content_type: str
    content_id: str
    loaded: bool
    reachable_via: tuple[str, ...]
    status: str
    suggested_file: str
```

### Failure Message Shape
```python
# Source: Phase decision D-14
def _format_reachability_failures(rows: list[ReachabilityRow]) -> str:
    return "\n".join(
        f"{row.content_type}:{row.content_id} status={row.status} "
        f"reachable_via={','.join(row.reachable_via) or '-'} "
        f"check={row.suggested_file}"
        for row in rows
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Unregistered ad-hoc test subset | Registered pytest marker plus `uv run pytest -m guardrail` | Phase 1 decision on 2026-04-11 | Gives developers one stable command. [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md] |
| Registry-only content checks | Loaded vs reachable report | Phase 1 decision on 2026-04-11 | Prevents JSON-only content from being counted as delivered. [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md] |
| Standalone acceptance doc | README checklist plus README test | Phase 1 decision on 2026-04-11 | Keeps the human-facing checklist in the maintained project docs. [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md] |

**Deprecated/outdated:**
- README's relic placeholder count should be treated as needing refresh during Phase 1 because local inventory found 98 placeholder relics while README currently states 102. [VERIFIED: README.md] [VERIFIED: uv run python content inventory 2026-04-11]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A too-broad `guardrail` marker would be slow/noisy if applied wholesale. | Common Pitfalls | Low; planner can validate by timing `uv run pytest -m guardrail` after marking. |
| A2 | Applying the marker to entire large modules without selection is a warning sign. | Common Pitfalls | Low; implementation can choose representative function-level markers. |

## Open Questions (RESOLVED)

1. **RESOLVED: Placeholder filtering will be implemented now, alongside the report.** [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md] [VERIFIED: .planning/phases/01-护栏与交付契约/01-02-PLAN.md]
   - What we know: placeholder relics in random reward pools should fail the GUARD-02 guardrail. [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md]
   - Resolution: Phase 1 includes an explicit scoped code task to filter `implementation_status == "placeholder"` out of `common`, `uncommon`, `rare`, `shop`, `boss`, and Neow random relic selection paths; placeholder relics remain registry-loadable and report-visible. [VERIFIED: .planning/phases/01-护栏与交付契约/01-02-PLAN.md]

2. **RESOLVED: The guardrail marker set will use representative function-level tests.** [VERIFIED: .planning/phases/01-护栏与交付契约/01-01-PLAN.md]
   - What we know: the targeted related subset currently passes with 223 tests, but that subset is broader than a minimal guardrail. [VERIFIED: uv run pytest targeted subset 2026-04-11]
   - Resolution: Phase 1 marks named representative tests with function-level `@pytest.mark.guardrail` decorators and avoids module-level markers on large files, coverage thresholds, or a full three-act E2E. [VERIFIED: .planning/phases/01-护栏与交付契约/01-01-PLAN.md]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | All Python commands | yes | 0.11.3 | None; project requires uv workflow. [VERIFIED: uv --version 2026-04-11] |
| Python | Runtime/tests | yes | 3.14.3 local; project requires `>=3.12` | None needed. [VERIFIED: python3 --version 2026-04-11] [VERIFIED: pyproject.toml] |
| pytest | Guardrail tests | yes | 9.0.2 installed; project requires `>=8.0` | None needed. [VERIFIED: importlib.metadata 2026-04-11] [VERIFIED: pyproject.toml] |
| textual | Existing TUI tests | yes | 8.1.1 | Avoid new UI scope if unavailable elsewhere. [VERIFIED: importlib.metadata 2026-04-11] |
| rich | Existing presentation layer | yes | 14.3.3 | Avoid new rendering dependency. [VERIFIED: importlib.metadata 2026-04-11] |

**Missing dependencies with no fallback:** None found for Phase 1. [VERIFIED: local command 2026-04-11]

**Missing dependencies with fallback:** None found for Phase 1. [VERIFIED: local command 2026-04-11]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Local single-player TUI has no account/auth feature in this phase. [VERIFIED: CLAUDE.md] |
| V3 Session Management | no | No web session/cookie/token system exists in this phase. [VERIFIED: CLAUDE.md] |
| V4 Access Control | no | No multi-user authorization boundary exists in this phase. [VERIFIED: CLAUDE.md] |
| V5 Input Validation | yes | Use existing registry/model validation and pytest failures for JSON content shape and save data. [VERIFIED: src/slay_the_spire/content/registries.py] [VERIFIED: tests/use_cases/test_save_load.py] |
| V6 Cryptography | no | No cryptographic feature or secret handling is in scope. [VERIFIED: AGENTS.md] |

### Known Threat Patterns for Local Content/Test Guardrails

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Invalid or misleading content JSON | Tampering | Keep registry validation and add reachability assertions over loaded content and pools. [VERIFIED: src/slay_the_spire/content/registries.py] |
| Accidental README misrepresentation | Repudiation | Add README tests for command/checklist claims. [VERIFIED: tests/docs/test_readme.py] |
| Unexpected save/load state mismatch | Tampering | Keep round-trip and mismatched combat-state rejection tests in guardrail subset. [VERIFIED: tests/use_cases/test_save_load.py] |

## Sources

### Primary (HIGH confidence)
- `.planning/phases/01-护栏与交付契约/01-CONTEXT.md` - locked Phase 1 decisions, boundaries, and command shape. [VERIFIED: local file]
- `.planning/REQUIREMENTS.md` - GUARD-01, GUARD-02, GUARD-03 definitions. [VERIFIED: local file]
- `.planning/STATE.md` - current phase state and known concerns. [VERIFIED: local file]
- `CLAUDE.md` and `AGENTS.md` - project constraints, uv workflow, content source, save schema, and docs rules. [VERIFIED: local files]
- `pyproject.toml` - Python requirement, dependencies, pytest config, and lack of marker registration. [VERIFIED: local file]
- `src/slay_the_spire/content/catalog.py`, `src/slay_the_spire/content/provider.py`, `src/slay_the_spire/content/registries.py` - registry and pool loading behavior. [VERIFIED: local files]
- `src/slay_the_spire/use_cases/start_run.py` - runtime relic sequence generation. [VERIFIED: local file]
- `src/slay_the_spire/domain/rewards/reward_generator.py` and `src/slay_the_spire/use_cases/apply_reward.py` - reward generation/application contracts. [VERIFIED: local files]
- `tests/app/test_session.py`, `tests/e2e/test_single_act_smoke.py`, `tests/e2e/test_two_act_smoke.py`, `tests/use_cases/test_apply_reward.py`, `tests/domain/test_effect_resolver.py`, `tests/use_cases/test_save_load.py`, `tests/content/test_registry_validation.py`, `tests/docs/test_readme.py` - reusable test assets. [VERIFIED: local files]
- Local commands: `uv --version`, `python3 --version`, `uv run python importlib.metadata`, `uv run pytest --markers`, targeted pytest subset. [VERIFIED: local commands 2026-04-11]

### Secondary (MEDIUM confidence)
- pytest official documentation on marker registration and `-m` selection: https://docs.pytest.org/en/stable/example/markers.html [CITED: docs.pytest.org/en/stable/example/markers.html]

### Tertiary (LOW confidence)
- None. [VERIFIED: this research]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - versions and dependencies verified from pyproject and local environment. [VERIFIED: pyproject.toml] [VERIFIED: local commands 2026-04-11]
- Architecture: HIGH - recommendations map to existing files and locked decisions. [VERIFIED: local codebase inspection] [VERIFIED: .planning/phases/01-护栏与交付契约/01-CONTEXT.md]
- Pitfalls: MEDIUM - content reachability and placeholder facts are verified, but exact final marker granularity is an implementation choice. [VERIFIED: uv run python content inventory 2026-04-11] [ASSUMED]

**Research date:** 2026-04-11 [VERIFIED: system date]
**Valid until:** 2026-05-11 for local architecture and dependencies, or earlier if `pyproject.toml`, content metadata, or Phase 1 decisions change. [ASSUMED]
