# Hexaghost Boss Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Act 1 引入独立 Boss 池并落地一个带 `Burn` 机制的低保真 `Hexaghost`，同时保持现有单 Act 主循环、奖励和胜利终局稳定。

**Architecture:** 保持当前 `move_table + intent_policy` 的内容驱动敌人结构，只做两类最小系统扩展：一个通用塞牌效果 `add_card_to_discard`，以及一个由回合流转处理的 `Burn` 结算阶段。Boss 内容、地图 `boss_pool_id`、战斗规则和 E2E 回归分成独立任务，按 TDD 顺序逐步落地。

**Tech Stack:** Python 3.12、`uv`、`pytest`、Rich 终端 UI、JSON 内容目录

---

## File Map

- Modify: `content/acts/act1_map.json`
- Modify: `src/slay_the_spire/data/content/acts/act1_map.json`
- Create: `content/enemies/act1_bosses.json`
- Create: `src/slay_the_spire/data/content/enemies/act1_bosses.json`
- Modify: `content/cards/curses.json`
- Modify: `src/slay_the_spire/data/content/cards/curses.json`
- Modify: `src/slay_the_spire/domain/effects/effect_types.py`
- Modify: `src/slay_the_spire/domain/effects/effect_resolver.py`
- Modify: `src/slay_the_spire/domain/combat/turn_flow.py`
- Modify: `src/slay_the_spire/use_cases/enter_room.py`
- Modify: `src/slay_the_spire/adapters/terminal/widgets.py`
- Modify: `src/slay_the_spire/adapters/terminal/inspect.py`
- Modify: `tests/content/test_registry_validation.py`
- Modify: `tests/domain/test_effect_resolver.py`
- Modify: `tests/domain/test_combat_flow.py`
- Modify: `tests/e2e/test_single_act_smoke.py`

## Task 1: 注册独立 Boss 池与 Burn 内容

**Files:**
- Modify: `tests/content/test_registry_validation.py`
- Modify: `content/acts/act1_map.json`
- Modify: `src/slay_the_spire/data/content/acts/act1_map.json`
- Create: `content/enemies/act1_bosses.json`
- Create: `src/slay_the_spire/data/content/enemies/act1_bosses.json`
- Modify: `content/cards/curses.json`
- Modify: `src/slay_the_spire/data/content/cards/curses.json`

- [ ] **Step 1: 写失败测试，锁定独立 Boss 池与 Burn 内容**

在 `tests/content/test_registry_validation.py` 增加两个测试：

```python
def test_act1_uses_dedicated_boss_pool() -> None:
    provider = StarterContentProvider(Path(__file__).resolve().parents[2] / "content")
    act = provider.acts().get("act1")

    assert act.boss_pool_id == "act1_bosses"
    assert provider.enemies().get("hexaghost").name == "六火幽魂"


def test_curse_catalog_exposes_burn_as_unplayable_non_shop_card() -> None:
    provider = StarterContentProvider(Path(__file__).resolve().parents[2] / "content")
    burn = provider.cards().get("burn")

    assert burn.name == "灼伤"
    assert burn.playable is False
    assert burn.can_appear_in_shop is False
```

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `uv run pytest tests/content/test_registry_validation.py -v`

Expected:
- `act.boss_pool_id == "act1_elites"` 导致失败
- `hexaghost` 或 `burn` 不存在导致失败

- [ ] **Step 3: 最小实现内容改动**

改动内容：

- `content/acts/act1_map.json` 和 `src/slay_the_spire/data/content/acts/act1_map.json`
  - 将 `"boss_pool_id": "act1_elites"` 改成 `"act1_bosses"`
- 新建 `content/enemies/act1_bosses.json` 与打包目录同名文件，加入：

```json
{
  "enemies": [
    {
      "id": "hexaghost",
      "name": "六火幽魂",
      "hp": 250,
      "move_table": [
        { "move": "divider" },
        {
          "move": "sear",
          "effects": [
            { "type": "damage", "amount": 6 },
            { "type": "add_card_to_discard", "card_id": "burn", "count": 1 }
          ]
        },
        {
          "move": "tackle",
          "effects": [
            { "type": "damage", "amount": 14 }
          ]
        },
        {
          "move": "inferno",
          "effects": [
            { "type": "add_card_to_discard", "card_id": "burn", "count": 2 }
          ]
        },
        {
          "move": "tackle",
          "effects": [
            { "type": "damage", "amount": 14 }
          ]
        }
      ],
      "intent_policy": "scripted"
    }
  ]
}
```

- `content/cards/curses.json` 与打包目录同名文件新增：

```json
{
  "id": "burn",
  "name": "灼伤",
  "cost": -1,
  "playable": false,
  "can_appear_in_shop": false,
  "effects": []
}
```

- [ ] **Step 4: 运行测试，确认内容注册通过**

Run: `uv run pytest tests/content/test_registry_validation.py -v`

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/content/test_registry_validation.py \
  content/acts/act1_map.json \
  src/slay_the_spire/data/content/acts/act1_map.json \
  content/enemies/act1_bosses.json \
  src/slay_the_spire/data/content/enemies/act1_bosses.json \
  content/cards/curses.json \
  src/slay_the_spire/data/content/cards/curses.json
git commit -m "feat: add hexaghost boss content"
```

## Task 2: 为敌人效果层增加塞 Burn 的通用能力

**Files:**
- Modify: `tests/domain/test_effect_resolver.py`
- Modify: `src/slay_the_spire/domain/effects/effect_types.py`
- Modify: `src/slay_the_spire/domain/effects/effect_resolver.py`
- Optional verify: `src/slay_the_spire/adapters/terminal/widgets.py`
- Optional verify: `src/slay_the_spire/adapters/terminal/inspect.py`

- [ ] **Step 1: 写失败测试，锁定 add_card_to_discard 行为**

在 `tests/domain/test_effect_resolver.py` 增加：

```python
def test_add_card_to_discard_creates_new_instance_ids() -> None:
    state = make_state(
        hand=["burn#1"],
        draw_pile=[],
        discard_pile=["burn#2"],
        effect_queue=[
            {"type": "add_card_to_discard", "card_id": "burn", "count": 2},
        ],
    )

    resolved = resolve_effect_queue(state)

    assert [effect["type"] for effect in resolved] == ["add_card_to_discard"]
    assert state.discard_pile == ["burn#2", "burn#3", "burn#4"]
```

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `uv run pytest tests/domain/test_effect_resolver.py::test_add_card_to_discard_creates_new_instance_ids -v`

Expected: FAIL with `unsupported effect type: add_card_to_discard`

- [ ] **Step 3: 最小实现 add_card_to_discard**

在 `src/slay_the_spire/domain/effects/effect_types.py` 增加常量：

```python
EFFECT_ADD_CARD_TO_DISCARD = "add_card_to_discard"
```

在 `src/slay_the_spire/domain/effects/effect_resolver.py` 增加分支：

```python
if effect_type == EFFECT_ADD_CARD_TO_DISCARD:
    card_id = effect.get("card_id")
    count = max(int(effect.get("count", 1)), 0)
    if not isinstance(card_id, str):
        raise TypeError("card_id must be a string")
    for _ in range(count):
        _append_card_to_zone(
            state,
            zone="discard_pile",
            card_instance_id=_next_card_instance_id(state, card_id),
        )
    return effect
```

如终端效果文案使用了 effect type 映射，同步把 `add_card_to_discard` 格式化成类似：

- `将 1 张灼伤加入弃牌堆`
- `将 2 张灼伤加入弃牌堆`

- [ ] **Step 4: 运行测试，确认通过**

Run: `uv run pytest tests/domain/test_effect_resolver.py -v`

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/domain/test_effect_resolver.py \
  src/slay_the_spire/domain/effects/effect_types.py \
  src/slay_the_spire/domain/effects/effect_resolver.py \
  src/slay_the_spire/adapters/terminal/widgets.py \
  src/slay_the_spire/adapters/terminal/inspect.py
git commit -m "feat: add discard injection effect for burn"
```

## Task 3: 实现 Hexaghost 的 divider 和 Burn 结算

**Files:**
- Modify: `tests/domain/test_combat_flow.py`
- Modify: `src/slay_the_spire/domain/combat/turn_flow.py`

- [ ] **Step 1: 写失败测试，锁定 divider 分档伤害**

在 `tests/domain/test_combat_flow.py` 增加参数化测试：

```python
@pytest.mark.parametrize(
    ("player_hp", "expected_damage"),
    [(20, 6), (40, 12), (60, 18), (80, 24)],
)
def test_hexaghost_divider_scales_with_player_hp(player_hp: int, expected_damage: int) -> None:
    registry = _Registry()
    registry.enemies().register(
        {
            "id": "hexaghost",
            "name": "Hexaghost",
            "hp": 250,
            "move_table": [{"move": "divider"}],
            "intent_policy": "scripted",
        }
    )
    state = _combat_state()
    state.player.hp = player_hp
    state.player.max_hp = 80
    state.enemies[0].enemy_id = "hexaghost"
    state.enemies[0].hp = 250
    state.enemies[0].max_hp = 250

    resolved = end_turn(state, registry)

    assert [effect["type"] for effect in resolved] == ["damage"] * 6
    assert state.player.hp == player_hp - expected_damage
```

- [ ] **Step 2: 写失败测试，锁定回合结束 Burn 掉血**

继续在 `tests/domain/test_combat_flow.py` 增加：

```python
def test_end_turn_burn_in_hand_deals_damage_before_discarding() -> None:
    registry = _enemy_registry()
    state = _combat_state()
    state.player.hp = 30
    state.hand = ["burn#1", "strike#1"]

    resolved = end_turn(state, registry)

    assert state.player.hp == 23
    assert "burn#1" in state.discard_pile
    assert any(effect["type"] == "damage" for effect in resolved)
```

说明：
- 这里期望 7 点伤害 = `burn` 的 2 点 + 训练史莱姆的 5 点
- 测试名称要强调时序：先结算 burn，再正常弃牌并执行敌方回合

- [ ] **Step 3: 运行测试，确认当前失败**

Run: `uv run pytest tests/domain/test_combat_flow.py -v`

Expected:
- `divider` 测试失败，因为当前没有动态多段展开
- `burn` 测试失败，因为当前回合结束前不会处理手牌中的 `burn`

- [ ] **Step 4: 最小实现 divider 与 burn 时序**

在 `src/slay_the_spire/domain/combat/turn_flow.py` 增加三个小函数：

```python
def _divider_segment_damage(player_hp: int) -> int:
    if player_hp <= 24:
        return 1
    if player_hp <= 48:
        return 2
    if player_hp <= 72:
        return 3
    return 4


def _burn_damage_from_hand(state: CombatState) -> int:
    return sum(2 for card in state.hand if card_id_from_instance_id(card) == "burn")


def _queue_divider_effects(state: CombatState, *, source_instance_id: str) -> None:
    for _ in range(6):
        state.effect_queue.append(
            damage_effect(
                source_instance_id=source_instance_id,
                target_instance_id=state.player.instance_id,
                amount=_divider_segment_damage(state.player.hp),
            )
        )
```

在 `run_enemy_turn()` 中识别 `move.get("move") == "divider"` 时直接调用 `_queue_divider_effects()`，其他招式继续走 `_effects_from_payload()`。

在 `end_turn()` 最开始加入：

```python
burn_damage = _burn_damage_from_hand(state)
if burn_damage > 0:
    state.effect_queue.append(
        damage_effect(
            source_instance_id="status:burn",
            target_instance_id=state.player.instance_id,
            amount=burn_damage,
        )
    )
    resolve_effect_queue(state, hook_registrations=hook_registrations)
    if state.player.hp <= 0:
        return [{"type": "damage", "amount": burn_damage, "target_instance_id": state.player.instance_id}]
```

然后再继续现有弃牌与敌方回合逻辑。实现时不要硬编码返回假效果列表；应把 burn 结算得到的 `resolved` 与敌方回合 `resolved` 拼接返回。

- [ ] **Step 5: 运行测试，确认通过**

Run: `uv run pytest tests/domain/test_combat_flow.py -v`

Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add tests/domain/test_combat_flow.py src/slay_the_spire/domain/combat/turn_flow.py
git commit -m "feat: add hexaghost divider and burn turn damage"
```

## Task 4: 让 Boss 房实际生成 Hexaghost，并补流程回归

**Files:**
- Modify: `tests/e2e/test_single_act_smoke.py`
- Modify: `src/slay_the_spire/use_cases/enter_room.py`

- [ ] **Step 1: 写失败测试，锁定 Boss 房读取独立池**

在 `tests/e2e/test_single_act_smoke.py` 增加一个针对 Boss 房的最小流程测试：

```python
def test_boss_room_uses_hexaghost_from_dedicated_boss_pool() -> None:
    session = start_session(seed=1)
    path = _path_with_shop_and_rest(session.act_state)

    for next_node_id in path[1:]:
        session = _complete_or_leave_room_for_path(session)
        session = _advance_to(session, next_node_id)

    combat_state = CombatState.from_dict(session.room_state.payload["combat_state"])

    assert session.room_state.room_type == "boss"
    assert session.room_state.payload["enemy_pool_id"] == "act1_bosses"
    assert combat_state.enemies[0].enemy_id == "hexaghost"
```

如果 `_complete_or_leave_room_for_path()` 不存在，就沿用文件里已有的分支逻辑抽一个小 helper，保证测试保持可读。

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `uv run pytest tests/e2e/test_single_act_smoke.py -v`

Expected: FAIL，因为当前 Boss 房仍读到 `lagavulin`

- [ ] **Step 3: 最小实现 Boss 房选择逻辑**

优先检查 `src/slay_the_spire/use_cases/enter_room.py` 是否已经天然支持独立 `boss_pool_id`。

如果 `Task 1` 改完内容后这里已经能工作：
- 不改业务逻辑
- 只做必要的测试 helper 清理

如果仍有耦合：
- 仅修正 `room_kind == "boss"` 分支，确保读取 `act_state.boss_pool_id`

- [ ] **Step 4: 运行流程测试**

Run: `uv run pytest tests/e2e/test_single_act_smoke.py -v`

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/e2e/test_single_act_smoke.py src/slay_the_spire/use_cases/enter_room.py
git commit -m "test: cover dedicated hexaghost boss room flow"
```

## Task 5: 全量回归并收尾

**Files:**
- Verify only unless failure requires edits

- [ ] **Step 1: 跑内容、领域、流程重点回归**

Run:

```bash
uv run pytest \
  tests/content/test_registry_validation.py \
  tests/domain/test_effect_resolver.py \
  tests/domain/test_combat_flow.py \
  tests/e2e/test_single_act_smoke.py -v
```

Expected: PASS

- [ ] **Step 2: 跑全量测试**

Run: `uv run pytest`

Expected:
- Exit code 0
- 全部测试通过

- [ ] **Step 3: 检查工作区内容同步**

Run:

```bash
git diff -- content src/slay_the_spire/data/content
```

Expected:
- `content/` 与 `src/slay_the_spire/data/content/` 的相关改动成对出现
- 没有只改一份的遗漏

- [ ] **Step 4: 最终提交**

```bash
git add content src/slay_the_spire/data/content src/slay_the_spire tests
git commit -m "feat: add hexaghost as act 1 boss"
```

- [ ] **Step 5: 记录验证结果**

在执行汇报中明确写出：

- `uv run pytest` 的结果
- Boss 房是否读到 `hexaghost`
- `Burn` 的结算方式是本轮简化版：回合结束每张 2 点伤害

## Notes for Workers

- 严格按 `@superpowers/test-driven-development` 执行，每一条行为都先写失败测试
- 不要在 `Task 4` 之前顺手改更多终端表现；本轮目标是规则与闭环
- 如需补终端文案，只改最小必要范围，并保持中文
- 所有内容 JSON 改动都必须双写：
  - `content/`
  - `src/slay_the_spire/data/content/`
- 若发现 `Burn` 的终端效果文案未覆盖，再补 `widgets.py` / `inspect.py` 的最小显示支持，不要发散到整套 UI 重构
