# Boss Rewards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Boss 战引入独立奖励规则，包含更高金币、独立 `boss_relics` 池和两级终端菜单，并保证只有金币与遗物都领取完成后才进入胜利终局。

**Architecture:** 保持普通 `combat` / `elite` 奖励仍使用现有 `room_state.rewards`，只为 `boss` 新增 `payload["boss_rewards"]` 结构和对应菜单流转。实现拆成内容注册、Boss 遗物运行时 hook、奖励生成与应用、会话状态机、终端菜单渲染、回归验证和最终整理七个任务，每个任务都先写失败测试，再做最小实现。

**Tech Stack:** Python 3.12、`uv`、`pytest`、Rich 终端 UI、JSON 内容目录

---

## File Map

- Create: `content/relics/boss_relics.json`
- Create: `src/slay_the_spire/data/content/relics/boss_relics.json`
- Modify: `src/slay_the_spire/domain/effects/effect_types.py`
- Modify: `src/slay_the_spire/domain/effects/effect_resolver.py`
- Modify: `src/slay_the_spire/domain/hooks/runtime.py`
- Modify: `src/slay_the_spire/domain/rewards/reward_generator.py`
- Modify: `src/slay_the_spire/use_cases/enter_room.py`
- Modify: `src/slay_the_spire/use_cases/apply_reward.py`
- Modify: `src/slay_the_spire/app/menu_definitions.py`
- Modify: `src/slay_the_spire/app/session.py`
- Modify: `src/slay_the_spire/adapters/terminal/screens/non_combat.py`
- Modify: `tests/content/test_registry_validation.py`
- Modify: `tests/domain/test_effect_resolver.py`
- Modify: `tests/use_cases/test_apply_reward.py`
- Modify: `tests/use_cases/test_start_run.py`
- Modify: `tests/app/test_menu_definitions.py`
- Modify: `tests/use_cases/test_room_recovery.py`
- Modify: `tests/adapters/terminal/test_renderer.py`
- Modify: `tests/e2e/test_single_act_smoke.py`

## Task 1: 注册独立 Boss 遗物池内容

**Files:**
- Modify: `tests/content/test_registry_validation.py`
- Create: `content/relics/boss_relics.json`
- Create: `src/slay_the_spire/data/content/relics/boss_relics.json`

- [ ] **Step 1: 写失败测试，锁定 Boss 遗物池可加载且不进商店**

在 `tests/content/test_registry_validation.py` 增加：

```python
def test_boss_relic_catalog_exposes_black_blood_anchor_and_lantern() -> None:
    provider = StarterContentProvider(Path(__file__).resolve().parents[2] / "content")

    assert provider.relics().get("black_blood").name == "黑色之血"
    assert provider.relics().get("anchor").name == "锚"
    assert provider.relics().get("lantern").name == "灯笼"


def test_boss_relics_do_not_appear_in_shop_pool() -> None:
    provider = StarterContentProvider(Path(__file__).resolve().parents[2] / "content")

    assert provider.relics().get("black_blood").can_appear_in_shop is False
    assert provider.relics().get("anchor").can_appear_in_shop is False
    assert provider.relics().get("lantern").can_appear_in_shop is False
```

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `uv run pytest tests/content/test_registry_validation.py -v`

Expected:
- `KeyError: 'black_blood'`
- `KeyError: 'anchor'`
- `KeyError: 'lantern'`

- [ ] **Step 3: 最小实现 Boss 遗物内容**

创建 `content/relics/boss_relics.json` 与 `src/slay_the_spire/data/content/relics/boss_relics.json`，至少包含：

```json
{
  "relics": [
    {
      "id": "black_blood",
      "name": "黑色之血",
      "trigger_hooks": ["on_combat_end"],
      "passive_effects": [{"type": "heal", "amount": 12}],
      "can_appear_in_shop": false
    },
    {
      "id": "anchor",
      "name": "锚",
      "trigger_hooks": ["on_combat_start"],
      "passive_effects": [{"type": "block", "amount": 10}],
      "can_appear_in_shop": false
    },
    {
      "id": "lantern",
      "name": "灯笼",
      "trigger_hooks": ["on_combat_start"],
      "passive_effects": [{"type": "gain_energy", "amount": 1}],
      "can_appear_in_shop": false
    }
  ]
}
```

- [ ] **Step 4: 运行测试，确认内容注册通过**

Run: `uv run pytest tests/content/test_registry_validation.py -v`

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/content/test_registry_validation.py \
  content/relics/boss_relics.json \
  src/slay_the_spire/data/content/relics/boss_relics.json
git commit -m "feat: add boss relic content pool"
```

## Task 2: 接通 Anchor / Lantern 的战斗开始效果

**Files:**
- Modify: `tests/domain/test_effect_resolver.py`
- Modify: `tests/use_cases/test_start_run.py`
- Modify: `src/slay_the_spire/domain/effects/effect_types.py`
- Modify: `src/slay_the_spire/domain/effects/effect_resolver.py`
- Modify: `src/slay_the_spire/domain/hooks/runtime.py`
- Modify: `src/slay_the_spire/use_cases/enter_room.py`

- [ ] **Step 1: 写失败测试，锁定 Boss 遗物运行时效果**

在 `tests/domain/test_effect_resolver.py` 增加：

```python
def test_gain_energy_effect_increases_combat_energy() -> None:
    state = make_state(energy=3, effect_queue=[{"type": "gain_energy", "amount": 1}])

    resolved = resolve_effect_queue(state)

    assert resolved == [{"type": "gain_energy", "amount": 1, "gained_energy": 1}]
    assert state.energy == 4
```

在 `tests/use_cases/test_start_run.py` 增加：

```python
def test_enter_room_applies_anchor_block_on_combat_start() -> None:
    provider = _content_provider()
    run_state = replace(start_new_run("ironclad", seed=5, registry=provider), relics=["anchor"])
    act_state = generate_act_state("act1", seed=5, registry=provider)

    room_state = enter_room(run_state, act_state, node_id="start", registry=provider)
    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    assert combat_state.player.block == 10


def test_enter_room_applies_lantern_energy_on_combat_start() -> None:
    provider = _content_provider()
    run_state = replace(start_new_run("ironclad", seed=5, registry=provider), relics=["lantern"])
    act_state = generate_act_state("act1", seed=5, registry=provider)

    room_state = enter_room(run_state, act_state, node_id="start", registry=provider)
    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    assert combat_state.energy == 4
```

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `uv run pytest tests/domain/test_effect_resolver.py tests/use_cases/test_start_run.py -v`

Expected:
- `unsupported effect type: gain_energy`
- `on_combat_start` 尚未在进战斗时触发

- [ ] **Step 3: 最小实现 Boss 遗物开场效果**

在 `src/slay_the_spire/domain/effects/effect_types.py` 增加：

```python
EFFECT_GAIN_ENERGY = "gain_energy"
```

在 `src/slay_the_spire/domain/effects/effect_resolver.py` 增加：

```python
if effect_type == EFFECT_GAIN_ENERGY:
    gained_energy = max(int(effect.get("amount", 0)), 0)
    state.energy += gained_energy
    return _with_result(effect, gained_energy=gained_energy)
```

在 `src/slay_the_spire/domain/hooks/runtime.py` 的 `_materialize_relic_effects()` 中，把未显式指定目标的 `block` 也补到玩家实例上：

```python
if effect.get("type") in {"heal", "block"} and "target_instance_id" not in effect:
    effect["target_instance_id"] = target_instance_id
```

在 `src/slay_the_spire/use_cases/enter_room.py` 的 `_build_combat_state()` 中，在 `start_turn(state)` 后补一次 `on_combat_start` 派发：

```python
state = start_turn(state)
registrations = build_runtime_hook_registrations(run_state, registry)
dispatch_hook(state, "on_combat_start", registrations)
resolve_effect_queue(state, hook_registrations=registrations)
return state
```

若你不想在 `enter_room.py` 直接调度 hook，也可以抽一个小辅助函数，但不要把普通奖励或菜单逻辑混进这里。

- [ ] **Step 4: 运行测试，确认通过**

Run: `uv run pytest tests/domain/test_effect_resolver.py tests/use_cases/test_start_run.py -v`

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/domain/test_effect_resolver.py \
  tests/use_cases/test_start_run.py \
  src/slay_the_spire/domain/effects/effect_types.py \
  src/slay_the_spire/domain/effects/effect_resolver.py \
  src/slay_the_spire/domain/hooks/runtime.py \
  src/slay_the_spire/use_cases/enter_room.py
git commit -m "feat: add combat start boss relic hooks"
```

## Task 3: 实现 Boss 奖励生成与遗物领取规则

**Files:**
- Modify: `tests/use_cases/test_apply_reward.py`
- Modify: `src/slay_the_spire/domain/rewards/reward_generator.py`
- Modify: `src/slay_the_spire/use_cases/apply_reward.py`

- [ ] **Step 1: 写失败测试，锁定 Boss 奖励生成与 Black Blood 替换**

在 `tests/use_cases/test_apply_reward.py` 增加：

```python
def test_generate_boss_rewards_returns_high_gold_and_three_unique_relics() -> None:
    rewards = generate_boss_rewards(
        room_id="act1:boss",
        seed=37,
        run_state=_run_state(),
        registry=_content_provider(),
    )

    assert rewards["gold_reward"] == 106
    assert rewards["boss_relic_offers"] == ["black_blood", "anchor", "lantern"]
    assert rewards["claimed_gold"] is False
    assert rewards["claimed_relic_id"] is None


def test_generate_boss_rewards_filters_owned_relics() -> None:
    run_state = replace(_run_state(), relics=["burning_blood", "anchor"])

    rewards = generate_boss_rewards(
        room_id="act1:boss",
        seed=37,
        run_state=run_state,
        registry=_content_provider(),
    )

    assert "anchor" not in rewards["boss_relic_offers"]


def test_apply_reward_black_blood_replaces_burning_blood() -> None:
    updated = apply_reward(
        run_state=_run_state(),
        reward_id="relic:black_blood",
        registry=_content_provider(),
    )

    assert "burning_blood" not in updated.relics
    assert "black_blood" in updated.relics
```

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `uv run pytest tests/use_cases/test_apply_reward.py -v`

Expected:
- `generate_boss_rewards` 不存在
- `apply_reward` 尚不支持 `relic:` 奖励

- [ ] **Step 3: 最小实现 Boss 奖励生成与遗物应用**

在 `src/slay_the_spire/domain/rewards/reward_generator.py` 增加：

```python
def generate_boss_rewards(*, room_id: str, seed: int, run_state: RunState, registry: ContentProviderPort) -> dict[str, object]:
    normalized_seed = _require_seed(seed)
    gold_reward = 90 + (normalized_seed % 21)
    boss_pool = [
        relic.id
        for relic in registry.relics().all()
        if relic.id in {"black_blood", "anchor", "lantern"} and relic.id not in run_state.relics
    ]
    return {
        "generated_by": "boss_reward_generator",
        "gold_reward": gold_reward,
        "claimed_gold": False,
        "boss_relic_offers": boss_pool[:3],
        "claimed_relic_id": None,
    }
```

在 `src/slay_the_spire/use_cases/apply_reward.py` 增加 `relic:` 分支：

```python
if reward_id == "relic:black_blood":
    relics = [relic_id for relic_id in run_state.relics if relic_id != "burning_blood"]
    return replace(run_state, relics=[*relics, "black_blood"])
if reward_id.startswith("relic:"):
    relic_id = reward_id.split(":", 1)[1]
    registry.relics().get(relic_id)
    if relic_id in run_state.relics:
        return run_state
    return replace(run_state, relics=[*run_state.relics, relic_id])
```

如需要稳定候选顺序，可在生成器中按固定列表顺序筛选，而不要依赖 registry 注册顺序。

- [ ] **Step 4: 运行测试，确认通过**

Run: `uv run pytest tests/use_cases/test_apply_reward.py -v`

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/use_cases/test_apply_reward.py \
  src/slay_the_spire/domain/rewards/reward_generator.py \
  src/slay_the_spire/use_cases/apply_reward.py
git commit -m "feat: add boss reward generation and relic claims"
```

## Task 4: 接通 Boss 房奖励状态机与胜利条件

**Files:**
- Modify: `tests/use_cases/test_room_recovery.py`
- Modify: `src/slay_the_spire/app/session.py`

- [ ] **Step 1: 写失败测试，锁定 Boss 奖励状态流转**

在 `tests/use_cases/test_room_recovery.py` 增加：

```python
def test_boss_victory_generates_payload_boss_rewards_instead_of_room_rewards() -> None:
    session = start_session(seed=37)
    boss_rewards = generate_boss_rewards(
        room_id="act1:boss",
        seed=session.run_state.seed,
        run_state=session.run_state,
        registry=StarterContentProvider(session.content_root),
    )

    assert boss_rewards["gold_reward"] == 106


def test_claiming_boss_gold_only_does_not_enter_victory() -> None:
    session = replace(
        start_session(seed=7),
        room_state=RoomState(
            room_id="act1:boss",
            room_type="boss",
            stage="completed",
            payload={
                "node_id": "boss",
                "next_node_ids": [],
                "boss_rewards": {
                    "generated_by": "boss_reward_generator",
                    "gold_reward": 99,
                    "claimed_gold": False,
                    "boss_relic_offers": ["black_blood", "anchor", "lantern"],
                    "claimed_relic_id": None,
                },
            },
            is_resolved=True,
            rewards=[],
        ),
        menu_state=MenuState(mode="select_boss_reward"),
    )

    _running, next_session, _message = route_menu_choice("1", session=session)

    assert next_session.run_phase == "active"
    assert next_session.room_state.payload["boss_rewards"]["claimed_gold"] is True
    assert next_session.run_state.gold == 198


def test_claiming_boss_relic_after_gold_enters_victory() -> None:
    session = replace(
        start_session(seed=7),
        room_state=RoomState(
            room_id="act1:boss",
            room_type="boss",
            stage="completed",
            payload={
                "node_id": "boss",
                "next_node_ids": [],
                "boss_rewards": {
                    "generated_by": "boss_reward_generator",
                    "gold_reward": 99,
                    "claimed_gold": True,
                    "boss_relic_offers": ["black_blood", "anchor", "lantern"],
                    "claimed_relic_id": None,
                },
            },
            is_resolved=True,
            rewards=[],
        ),
        menu_state=MenuState(mode="select_boss_relic"),
    )

    _running, next_session, _message = route_menu_choice("1", session=session)

    assert next_session.run_phase == "victory"
    assert next_session.room_state.payload["boss_rewards"]["claimed_relic_id"] == "black_blood"
```

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `uv run pytest tests/use_cases/test_room_recovery.py -v`

Expected:
- `select_boss_reward` / `select_boss_relic` 尚未支持
- Boss 房仍依赖 `room_state.rewards`

- [ ] **Step 3: 最小实现 Boss 奖励状态机**

在 `src/slay_the_spire/app/session.py`：

- Boss 战胜利后，把：

```python
rewards=generate_combat_rewards(...)
```

改成：

```python
payload = dict(session.room_state.payload)
payload["boss_rewards"] = generate_boss_rewards(
    room_id=session.room_state.room_id,
    seed=session.run_state.seed,
    run_state=updated_run_state,
    registry=_content_provider(session),
)
room_state = RoomState(
    ...,
    payload=payload,
    is_resolved=True,
    rewards=[],
)
```

- 新增辅助函数：
  - `_boss_rewards(room_state) -> dict[str, object] | None`
  - `_boss_rewards_complete(room_state) -> bool`
  - `_claim_boss_gold(session) -> SessionState`
  - `_claim_boss_relic(session, relic_id) -> SessionState`

- `run_phase="victory"` 只在 `_boss_rewards_complete(room_state)` 为真时触发
- 普通奖励房现有逻辑保持不变

- [ ] **Step 4: 运行测试，确认通过**

Run: `uv run pytest tests/use_cases/test_room_recovery.py -v`

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/use_cases/test_room_recovery.py \
  src/slay_the_spire/app/session.py
git commit -m "feat: add boss reward session flow"
```

## Task 5: 增加 Boss 奖励两级菜单与终端面板

**Files:**
- Modify: `tests/app/test_menu_definitions.py`
- Modify: `tests/adapters/terminal/test_renderer.py`
- Modify: `src/slay_the_spire/app/menu_definitions.py`
- Modify: `src/slay_the_spire/adapters/terminal/screens/non_combat.py`

- [ ] **Step 1: 写失败测试，锁定 Boss 奖励菜单和渲染**

在 `tests/app/test_menu_definitions.py` 增加：

```python
def test_build_boss_reward_menu_binds_gold_relic_and_back() -> None:
    menu = build_boss_reward_menu(
        boss_rewards={
            "gold_reward": 99,
            "claimed_gold": False,
            "boss_relic_offers": ["black_blood", "anchor", "lantern"],
            "claimed_relic_id": None,
        }
    )

    assert format_menu_lines(menu) == [
        "Boss奖励:",
        "1. 领取金币",
        "2. 选择遗物",
        "3. 返回上一步",
    ]
    assert resolve_menu_action("1", menu) == "claim_boss_gold"
    assert resolve_menu_action("2", menu) == "choose_boss_relic"


def test_build_boss_relic_menu_lists_relic_choices() -> None:
    registry = StarterContentProvider(start_session(seed=5).content_root)
    menu = build_boss_relic_menu(
        relic_ids=["black_blood", "anchor", "lantern"],
        registry=registry,
    )

    assert format_menu_lines(menu) == [
        "选择Boss遗物:",
        "1. 黑色之血",
        "2. 锚",
        "3. 灯笼",
        "4. 返回上一步",
    ]
```

在 `tests/adapters/terminal/test_renderer.py` 增加一个 Boss 奖励渲染测试，断言画面包含：

- `Boss奖励`
- `金币奖励：+99`
- `可选遗物：3`

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `uv run pytest tests/app/test_menu_definitions.py tests/adapters/terminal/test_renderer.py -v`

Expected:
- `build_boss_reward_menu` / `build_boss_relic_menu` 不存在
- 终端未显示 Boss 奖励专属文案

- [ ] **Step 3: 最小实现菜单与渲染**

在 `src/slay_the_spire/app/menu_definitions.py` 新增：

```python
def build_boss_reward_menu(*, boss_rewards: Mapping[str, object]) -> MenuDefinition:
    gold_label = "已领取金币" if boss_rewards.get("claimed_gold") is True else "领取金币"
    relic_label = "已选择遗物" if boss_rewards.get("claimed_relic_id") else "选择遗物"
    return build_menu(
        title="Boss奖励",
        options=[
            ("claim_boss_gold", gold_label),
            ("choose_boss_relic", relic_label),
            ("back", "返回上一步"),
        ],
    )


def build_boss_relic_menu(*, relic_ids: list[str], registry: ContentProviderPort) -> MenuDefinition:
    return build_menu(
        title="选择Boss遗物",
        options=[
            *[(f"claim_boss_relic:{relic_id}", registry.relics().get(relic_id).name) for relic_id in relic_ids],
            ("back", "返回上一步"),
        ],
    )
```

在 `src/slay_the_spire/adapters/terminal/screens/non_combat.py`：

- 当 `payload["boss_rewards"]` 存在时，渲染 Boss 奖励专属面板
- 显示金币数、金币领取状态、遗物选择状态
- `select_boss_reward` 用主菜单
- `select_boss_relic` 用遗物次级菜单

- [ ] **Step 4: 运行测试，确认通过**

Run: `uv run pytest tests/app/test_menu_definitions.py tests/adapters/terminal/test_renderer.py -v`

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/app/test_menu_definitions.py \
  tests/adapters/terminal/test_renderer.py \
  src/slay_the_spire/app/menu_definitions.py \
  src/slay_the_spire/adapters/terminal/screens/non_combat.py
git commit -m "feat: add boss reward menus and screen"
```

## Task 6: 回归整条 Boss 奖励链路并验证存读档

**Files:**
- Modify: `tests/use_cases/test_room_recovery.py`
- Modify: `tests/e2e/test_single_act_smoke.py`

- [ ] **Step 1: 写失败测试，锁定 Boss 奖励存读档和单 Act 冒烟**

在 `tests/use_cases/test_room_recovery.py` 增加：

```python
def test_boss_reward_progress_survives_save_and_load(tmp_path: Path) -> None:
    session = replace(
        start_session(seed=7),
        room_state=RoomState(
            room_id="act1:boss",
            room_type="boss",
            stage="completed",
            payload={
                "node_id": "boss",
                "next_node_ids": [],
                "boss_rewards": {
                    "generated_by": "boss_reward_generator",
                    "gold_reward": 99,
                    "claimed_gold": True,
                    "boss_relic_offers": ["black_blood", "anchor", "lantern"],
                    "claimed_relic_id": None,
                },
            },
            is_resolved=True,
            rewards=[],
        ),
    )
    repository = JsonFileSaveRepository(tmp_path / "boss_reward.json")
    save_game(
        repository=repository,
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
    )

    restored = load_game(repository=repository)["room_state"]

    assert restored.payload["boss_rewards"]["claimed_gold"] is True
    assert restored.payload["boss_rewards"]["claimed_relic_id"] is None
```

在 `tests/e2e/test_single_act_smoke.py` 增加或调整 Boss 段断言：

- Boss 战后 `room_state.rewards == []`
- `room_state.payload["boss_rewards"]` 存在
- 先领金币后仍未胜利
- 选完遗物后进入 `victory`

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `uv run pytest tests/use_cases/test_room_recovery.py tests/e2e/test_single_act_smoke.py -v`

Expected:
- Boss 奖励状态尚未完整保存或恢复
- E2E 仍按旧 `room_state.rewards` 断言

- [ ] **Step 3: 最小修正回归点**

如前几任务实现后仍有失败，优先检查：

- `RoomState.to_dict()` / `from_dict()` 是否已自然承载 `boss_rewards`
- `load_session()` 是否能把 Boss 奖励房恢复到正确菜单模式
- Boss 根菜单是否在奖励完成前保持 `查看奖励 / 领取奖励`
- E2E 路径是否先进入 `select_boss_reward` 再进入 `select_boss_relic`

- [ ] **Step 4: 运行回归测试**

Run: `uv run pytest tests/use_cases/test_room_recovery.py tests/e2e/test_single_act_smoke.py -v`

Expected: PASS

- [ ] **Step 5: 运行完整测试并提交**

Run: `uv run pytest`

Expected: 全绿

```bash
git add tests/use_cases/test_room_recovery.py tests/e2e/test_single_act_smoke.py
git commit -m "test: cover boss reward recovery and e2e flow"
```

## Task 7: 最终整理与验证

**Files:**
- Verify only: `content/relics/boss_relics.json`
- Verify only: `src/slay_the_spire/data/content/relics/boss_relics.json`
- Verify only: `src/slay_the_spire/app/session.py`
- Verify only: `src/slay_the_spire/adapters/terminal/screens/non_combat.py`

- [ ] **Step 1: 检查双目录内容同步**

Run:

```bash
diff -u content/relics/boss_relics.json src/slay_the_spire/data/content/relics/boss_relics.json
```

Expected: 无输出

- [ ] **Step 2: 运行一次手动 Boss 奖励流程**

Run: `uv run python -m slay_the_spire.app.cli new --seed 5`

Expected:
- 到达 Boss 房后，胜利界面前先进入 Boss 奖励
- 主菜单只有 `领取金币 / 选择遗物`
- 次级菜单为三选一遗物
- 两项完成后进入胜利终局

- [ ] **Step 3: 最终提交**

```bash
git status --short
git add content/relics/boss_relics.json \
  src/slay_the_spire/data/content/relics/boss_relics.json \
  src/slay_the_spire/domain/rewards/reward_generator.py \
  src/slay_the_spire/use_cases/apply_reward.py \
  src/slay_the_spire/app/menu_definitions.py \
  src/slay_the_spire/app/session.py \
  src/slay_the_spire/adapters/terminal/screens/non_combat.py \
  tests/content/test_registry_validation.py \
  tests/use_cases/test_apply_reward.py \
  tests/app/test_menu_definitions.py \
  tests/use_cases/test_room_recovery.py \
  tests/adapters/terminal/test_renderer.py \
  tests/e2e/test_single_act_smoke.py
git commit -m "feat: add dedicated boss reward flow"
```
