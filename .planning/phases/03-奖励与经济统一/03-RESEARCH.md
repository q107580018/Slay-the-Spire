# Phase 3: 奖励与经济统一 - Research

**Researched:** 2026-04-11  
**Domain:** 奖励标识统一、奖励应用链路统一、经济遗物联动与可验证反馈 [VERIFIED: .planning/ROADMAP.md, .planning/REQUIREMENTS.md]  
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
CONTEXT.md 缺失（本 phase 尚未生成 `03-CONTEXT.md`），无可逐字复制的锁定决策。 [VERIFIED: `.planning/phases/03-奖励与经济统一` 目录扫描]

### Claude's Discretion
无来自 CONTEXT.md 的显式裁量项；本研究按 REQUIREMENTS/ROADMAP/AGENTS/CLAUDE.md 收敛。 [VERIFIED: `.planning/phases/03-奖励与经济统一` 目录扫描]

### Deferred Ideas (OUT OF SCOPE)
无来自 CONTEXT.md 的延期项。 [VERIFIED: `.planning/phases/03-奖励与经济统一` 目录扫描]
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REWARD-01 | 战斗奖励、Boss 奖励、商店、事件、宝箱、Neow、休息点入口统一奖励标识与 apply 流程 | 当前入口分散点和统一切入位已定位：`apply_reward.py`、`session.py`、`shop_action.py`、`event_action.py`、`rest_action.py`、`opening_flow.py`。 [VERIFIED: src code grep] |
| REWARD-02 | 随机池默认不投放 placeholder 遗物 | `start_new_run` 和 Neow 随机遗物已过滤 placeholder；测试已覆盖。 [VERIFIED: `src/slay_the_spire/use_cases/start_run.py`, `src/slay_the_spire/use_cases/opening_flow.py`, `tests/use_cases/test_start_run.py`] |
| REWARD-03 | 金币/卡牌/遗物/药水/移除/升级/转换/复制/跳过可验证与可反馈 | 已实现类型与缺口已映射；“转换/复制”在奖励域未统一为 reward_id。 [VERIFIED: `apply_reward.py`, `session.py`, `menu_definitions.py`, tests grep] |
| REWARD-04 | 奖励经济相关遗物在对应入口生效且可测 | 已实现遗物联动入口和测试点已清单化（战后/Boss/商店/事件/宝箱/Neow/休息点）。 [VERIFIED: reward/session/use_cases/tests] |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Python 相关命令统一走 `uv`。 [CITED: CLAUDE.md]  
- 项目边界是本地单机 Textual TUI，不引入 GUI/Web/server。 [CITED: CLAUDE.md, AGENTS.md]  
- `content/` 是开发期唯一内容真源，`src/slay_the_spire/data/content/` 不手工维护。 [CITED: CLAUDE.md, AGENTS.md]  
- 存档 `schema_version=3`；若改结构需联动 `save_game.py`/`load_game.py`/相关测试。 [CITED: CLAUDE.md, AGENTS.md]  
- 玩家可见文案默认中文。 [CITED: AGENTS.md]  
- 改动奖励链路需优先检查 `reward_generator.py`、`apply_reward.py` 及关联测试。 [CITED: AGENTS.md]

## Summary

当前代码已经有一条“半统一”奖励主链：`room_state.rewards (reward_id)` -> `session._claim_session_reward` -> `apply_reward`，并覆盖 `gold/relic/card_offer/potion/card/event` 这批 ID 前缀。 [VERIFIED: `src/slay_the_spire/app/session.py`, `src/slay_the_spire/use_cases/apply_reward.py`, `src/slay_the_spire/app/menu_definitions.py`]  
但商店买卡/买药、多数事件效果、休息点升级/删牌、Neow 的 potion/targeted 分支仍直接改 `run_state`，没有统一走 `reward_id + apply` 协议。 [VERIFIED: `shop_action.py`, `event_action.py`, `rest_action.py`, `opening_flow.py`]

REWARD-02 的基础已经具备：随机遗物序列（common/uncommon/rare/shop/boss）在开局构建时排除 placeholder，Neow 随机遗物也排除 placeholder，且有 guardrail 测试。 [VERIFIED: `start_run.py`, `opening_flow.py`, `tests/use_cases/test_start_run.py`]  
Phase 3 的关键是“把剩余入口归并到统一奖励语义层”，而不是重写随机生成器。

**Primary recommendation:** 定义并落地统一 `reward_id` 协议（含 shop/event/rest/neow 专有动作），让所有奖励入口都先产出 `reward_id`，再由一个可扩展 `apply_reward`/`apply_reward_batch` 执行并返回玩家反馈。 [ASSUMED]

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12.12 (`uv run`) | 运行时与领域逻辑载体 | 仓库约束 `>=3.12` 且当前 `uv` 环境已落在 3.12。 [VERIFIED: `pyproject.toml`, `uv run python --version`] |
| textual | 8.1.1 | 唯一 TUI 交互界面 | phase 涉及奖励反馈展示，必须走现有 Textual 菜单/面板。 [VERIFIED: `pyproject.toml`, `uv run importlib.metadata version`, `src/slay_the_spire/adapters/textual/`] |
| rich | 14.3.3 | 共享渲染与奖励文案展示 | 奖励标签与 inspect/room 渲染依赖 rich 组件。 [VERIFIED: `pyproject.toml`, `uv run importlib.metadata version`, `adapters/presentation/`] |
| pytest | 9.0.2 (env) / `>=8.0` (constraint) | 回归与 guardrail 验证 | phase 需求明确“可验证”，现有奖励测试集中在 pytest。 [VERIFIED: `pyproject.toml`, `uv run pytest --version`, tests/] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| dataclasses | stdlib | 不可变风格状态更新（`replace`） | 奖励 apply 需要可预测状态演进。 [VERIFIED: `apply_reward.py`, `session.py`] |
| pathlib/json | stdlib | 内容与存档路径/序列化 | 奖励改动涉及 content 与 save/load 回归。 [VERIFIED: `save_files.py`, `save_game.py`, `load_game.py`] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `reward_id` 字符串协议 | 结构化 `RewardEffect` dataclass/TypedDict 协议 | 结构化更安全，但当前系统广泛依赖前缀字符串，迁移成本更高；本 phase 建议先兼容字符串协议再迭代。 [ASSUMED] |

**Installation:**
```bash
uv sync --dev
```

**Version verification:**
```bash
uv run python --version
uv run python - <<'PY'
from importlib.metadata import version
print(version("textual"))
print(version("rich"))
print(version("pytest"))
PY
```

## Architecture Patterns

### Recommended Project Structure
```text
src/slay_the_spire/
├── use_cases/               # 入口动作（shop/rest/event/neow/claim）
├── domain/rewards/          # 战后/Boss奖励生成策略
├── app/session.py           # 统一路由与奖励领取时序
└── app/menu_definitions.py  # 奖励展示与交互选项
```

### Pattern 1: Reward-ID First
**What:** 各入口先产出 `reward_id`（或 reward batch），由统一 apply 层执行。 [VERIFIED: `session._claim_session_reward` + `apply_reward`]  
**When to use:** 战斗结算、Boss、宝箱、Neow、事件、商店、休息点全部入口。 [ASSUMED]  
**Example:**
```python
# Source: src/slay_the_spire/app/session.py + src/slay_the_spire/use_cases/apply_reward.py
for reward_id in room_state.rewards:
    run_state = apply_reward(run_state=run_state, reward_id=reward_id, registry=registry)
```

### Pattern 2: Sequence-Backed Random Relic Pools
**What:** 遗物随机来自 `run_state.relic_sequences` + `relic_sequence_positions`，避免重复且可回放。 [VERIFIED: `start_run.py`, `reward_generator.py`, `enter_room.py`]  
**When to use:** 战后精英/Boss/宝箱/商店/Neow 遗物发放。 [VERIFIED: code locations above]

### Anti-Patterns to Avoid
- **入口内直接改 `run_state` 且绕过 reward 协议：** 会导致规则重复和反馈不一致（例如 `event_action` 金币逻辑与 `apply_reward` 金币逻辑各自维护）。 [VERIFIED: `event_action.py`, `apply_reward.py`]  
- **复制粘贴奖励后处理逻辑：** `_room_with_rewards_claimed` 与 `use_cases/claim_reward.py` 语义重叠，易漂移。 [VERIFIED: `session.py`, `use_cases/claim_reward.py`]  
- **让 placeholder 进入随机池：** 会破坏“奖励可信”。 [VERIFIED: `start_run.py` 过滤 + guardrail tests]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 各入口自行实现金币/遗物/药水结算 | 每个 use case 内自写一套结算分支 | 统一走 `apply_reward`（扩展 reward_id 类型） | 减少规则分叉，便于测试覆盖。 [VERIFIED: `apply_reward.py` + 多入口重复逻辑] |
| 随机遗物“临时随机” | 临时 `random.choice(all_relics)` | `relic_sequences + position` | 已有可回放与去重语义。 [VERIFIED: `start_run.py`, `enter_room.py`, `reward_generator.py`] |
| 奖励 UI 文案各处拼接 | 多处硬编码显示逻辑 | `menu_definitions._reward_label` 统一标签 | 玩家反馈一致、可测试。 [VERIFIED: `menu_definitions.py`] |

**Key insight:** 这个 phase 的核心是“统一协议 + 复用现有链路”，不是新增更复杂随机算法。 [ASSUMED]

## Common Pitfalls

### Pitfall 1: 只统一战后奖励，漏掉非战斗入口
**What goes wrong:** 商店/事件/Neow/休息点仍绕过 `apply_reward`，行为不一致。 [VERIFIED: `shop_action.py`, `event_action.py`, `opening_flow.py`, `rest_action.py`]  
**How to avoid:** 先做“入口清单 -> reward_id 映射表”，逐个收口。 [ASSUMED]

### Pitfall 2: Gold 规则重复实现
**What goes wrong:** `ectoplasm/golden_idol` 在 `apply_reward` 与 `event_action` 分别维护，未来易偏差。 [VERIFIED: `apply_reward._gold_amount`, `event_action._event_gold_bonus`]  
**How to avoid:** 抽单一 gold 结算函数并在所有入口复用。 [ASSUMED]

### Pitfall 3: Boss/宝箱流程状态机被破坏
**What goes wrong:** 奖励清空与 `boss -> boss_chest -> next act` 时序不一致，造成卡死或跳幕错误。 [VERIFIED: `session._resolve_boss_reward_completion`, e2e smoke tests]  
**How to avoid:** 保持 `_has_pending_boss_rewards` 判定不变，先迁移奖励 ID，再改流程。 [ASSUMED]

### Pitfall 4: “转换/复制”被当成战斗效果而非奖励能力
**What goes wrong:** REWARD-03 要求的转换/复制没有进入奖励域可验证口径。 [VERIFIED: `apply_reward.py` 未支持 transform/duplicate；`effect_resolver.py` 的 copy/upgrade 仅战斗域]  
**How to avoid:** 为奖励域定义 `reward_id`（如 `transform_card:*`, `duplicate_card:*`）并配套菜单与测试。 [ASSUMED]

## Code Examples

### 统一领取入口（已存在）
```python
# Source: src/slay_the_spire/app/session.py
updated_run_state = apply_reward(
    run_state=session.run_state,
    reward_id=reward_id,
    registry=provider,
)
```

### 随机池排除 placeholder（已存在）
```python
# Source: src/slay_the_spire/use_cases/start_run.py
if relic.implementation_status == "placeholder":
    return False
```

### 奖励菜单统一反馈（已存在）
```python
# Source: src/slay_the_spire/app/menu_definitions.py
if reward_id.startswith("gold:"):
    return f"金币 +{reward_id.split(':', 1)[1]}"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `inspect_reward_*` 旧菜单模式 | 统一到 `select_reward` 并做 legacy normalize | 已在当前代码落地 | 奖励菜单流程更一致，降低历史分支干扰。 [VERIFIED: `session._normalize_legacy_reward_inspect_mode`, `tests/app/test_inspect_menus.py`] |
| placeholder 可误入随机池（历史风险） | `start_new_run`/Neow 随机逻辑默认过滤 placeholder | 已在当前代码落地 | 降低“不可实现奖励”破坏流程风险。 [VERIFIED: `start_run.py`, `opening_flow.py`, `tests/use_cases/test_start_run.py`] |

**Deprecated/outdated:**
- `use_cases/claim_reward.py` 的 `room_type=="reward"` 单房间模型在主流程中非核心路径，当前主链是 session 奖励路由。 [VERIFIED: `use_cases/claim_reward.py`, references from tests only]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Phase 3 应先做协议统一（reward_id 扩展）再做行为补完，是最小风险路径 | Summary / Architecture | 若现网约束要求一次性重构为结构化对象，会导致计划拆分不合理 |
| A2 | 将 gold 结算抽单点可降低维护风险且不破坏现有流程 | Common Pitfalls | 若存在特殊入口需要独立规则，抽象过度会引入回归 |

## Open Questions

1. **REWARD-03 的“转换/复制”奖励是否要求在本 phase 完整落地？**
   - What we know: 当前奖励 apply 不支持 transform/duplicate，战斗域有 copy/upgrade 效果。 [VERIFIED: `apply_reward.py`, `effect_resolver.py`]
   - What's unclear: 是要求“奖励域新增”还是“沿用事件/战斗现有实现即可”。
   - Recommendation: 在计划前先锁定验收口径（至少定义 1-2 个可测入口）。 [ASSUMED]

2. **placeholder 遗物在“非随机固定奖励”出现时的 UI 策略是否需要本 phase 覆盖？**
   - What we know: 随机池已过滤 placeholder；固定 reward 仍可能被内容引用。 [VERIFIED: `start_run.py` filtering scope]
   - What's unclear: 是否要求对固定奖励也做“明确未实现标记 + 不破流程”。
   - Recommendation: 若要求严格，可在 `apply_reward` 返回结构中加入 `status=placeholder` 并落地提示。 [ASSUMED]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` | 依赖同步、测试执行、Python 版本统一 | ✓ | 0.11.3 | — [VERIFIED: `uv --version`] |
| `python` (`uv run`) | 运行与测试 | ✓ | 3.12.12 | — [VERIFIED: `uv run python --version`] |
| `pytest` (`uv run`) | 回归测试 | ✓ | 9.0.2 | — [VERIFIED: `uv run pytest --version`] |
| `rg` | 快速代码检索 | ✓ | 15.1.0 | `grep` [VERIFIED: `rg --version`] |

**Missing dependencies with no fallback:**
- None. [VERIFIED: environment probe]

**Missing dependencies with fallback:**
- None. [VERIFIED: environment probe]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 本项目为本地单机，无账号体系。 [VERIFIED: AGENTS.md/CLAUDE.md 边界] |
| V3 Session Management | no | 非网络会话；仅本地 `SessionState`。 [VERIFIED: `app/session.py`] |
| V4 Access Control | no | 无多用户权限面。 [VERIFIED: project boundary docs] |
| V5 Input Validation | yes | dataclass/registry/use case 层类型和值校验（`TypeError`/`ValueError`）。 [VERIFIED: `domain/models/*`, `content/registries.py`, `use_cases/*`] |
| V6 Cryptography | no | phase 不涉及加密需求。 [VERIFIED: codebase grep 无 crypto 依赖] |

### Known Threat Patterns for Python TUI Reward Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 非法 reward_id 注入导致状态异常 | Tampering | `apply_reward` 前缀分派 + registry lookup + menu action 白名单。 [VERIFIED: `apply_reward.py`, `menu_definitions.py`, `session.py`] |
| 菜单编号误触发非法动作 | Tampering | `resolve_menu_action` 索引边界检查 + `_invalid_menu_choice`。 [VERIFIED: `menu_definitions.py`, `session.py`] |
| 存档字段漂移导致恢复失败 | Tampering/DoS | `SAVE_SCHEMA_VERSION=3` 校验 + round-trip 测试。 [VERIFIED: `save_game.py`, `load_game.py`, `tests/use_cases/test_save_load.py`] |

## Sources

### Primary (HIGH confidence)
- `src/slay_the_spire/use_cases/apply_reward.py` - 统一奖励 apply 入口与已支持 reward_id  
- `src/slay_the_spire/domain/rewards/reward_generator.py` - 战后/Boss奖励生成与经济遗物触发  
- `src/slay_the_spire/app/session.py` - 全入口奖励路由与状态机  
- `src/slay_the_spire/use_cases/{shop_action,rest_action,event_action,opening_flow,start_run,enter_room}.py` - 非战斗入口行为与随机池策略  
- `src/slay_the_spire/app/menu_definitions.py` - 奖励标签与玩家反馈文案  
- `tests/use_cases/{test_apply_reward,test_shop_and_rest_actions,test_event_actions,test_opening_flow,test_start_run,test_enter_room}.py` - 奖励与经济验证基线  
- `tests/app/{test_menu_definitions,test_inspect_menus}.py`, `tests/e2e/*_smoke.py` - 菜单与主线流程验收  
- `.planning/{REQUIREMENTS.md,ROADMAP.md,STATE.md,config.json}` + `AGENTS.md` + `CLAUDE.md` - phase 目标与约束

### Secondary (MEDIUM confidence)
- None.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - 全部来自项目配置与本机环境探测。  
- Architecture: HIGH - 全部来自现有源码与测试。  
- Pitfalls: MEDIUM - 风险判断基于现状推断，改造策略存在实现自由度。

**Research date:** 2026-04-11  
**Valid until:** 2026-05-11
