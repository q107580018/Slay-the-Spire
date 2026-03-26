# Act 2 And Multi-Encounter Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有终端版原型上新增可游玩的 `Act 2`，补齐 `Act 1 -> Act 2` 跨幕推进，并把战斗内容从“单怪抽取”升级为“原版风格的多怪遭遇组”。

**Architecture:** 先补底层能力，再灌内容。第一阶段引入“遭遇组”内容类型和跨幕推进，让战斗与地图系统能承载多敌人和多幕流程；第二阶段迁移 `Act 1` 到新遭遇系统，避免只给 `Act 2` 走特殊分支；第三阶段落 `Act 2` 的地图、普通怪、精英、Boss、事件池，并用 E2E 与存读档回归覆盖整条长流程。

**Tech Stack:** Python 3.12、`uv`、`pytest`、Rich 终端 UI、JSON 内容目录

---

## File Map

- Modify: `src/slay_the_spire/content/catalog.py`
- Modify: `src/slay_the_spire/content/provider.py`
- Modify: `src/slay_the_spire/content/registries.py`
- Modify: `src/slay_the_spire/ports/content_provider.py`
- Modify: `src/slay_the_spire/use_cases/enter_room.py`
- Modify: `src/slay_the_spire/use_cases/start_run.py`
- Modify: `src/slay_the_spire/app/session.py`
- Modify: `src/slay_the_spire/domain/models/run_state.py`
- Modify: `src/slay_the_spire/domain/models/act_state.py`
- Modify: `src/slay_the_spire/domain/map/map_generator.py`
- Modify: `src/slay_the_spire/adapters/terminal/screens/non_combat.py`
- Modify: `src/slay_the_spire/adapters/terminal/screens/combat.py`
- Modify: `tests/content/test_registry_validation.py`
- Modify: `tests/domain/test_map_generator.py`
- Modify: `tests/domain/test_combat_flow.py`
- Modify: `tests/use_cases/test_enter_room.py`
- Modify: `tests/use_cases/test_start_run.py`
- Modify: `tests/use_cases/test_room_recovery.py`
- Modify: `tests/e2e/test_single_act_smoke.py`
- Create: `tests/e2e/test_two_act_smoke.py`
- Create: `content/acts/act2_map.json`
- Create: `src/slay_the_spire/data/content/acts/act2_map.json`
- Create: `content/events/act2_events.json`
- Create: `src/slay_the_spire/data/content/events/act2_events.json`
- Create: `content/enemies/act2_basic.json`
- Create: `src/slay_the_spire/data/content/enemies/act2_basic.json`
- Create: `content/enemies/act2_elites.json`
- Create: `src/slay_the_spire/data/content/enemies/act2_elites.json`
- Create: `content/enemies/act2_bosses.json`
- Create: `src/slay_the_spire/data/content/enemies/act2_bosses.json`
- Create: `content/encounters/act1_basic.json`
- Create: `src/slay_the_spire/data/content/encounters/act1_basic.json`
- Create: `content/encounters/act1_elites.json`
- Create: `src/slay_the_spire/data/content/encounters/act1_elites.json`
- Create: `content/encounters/act1_bosses.json`
- Create: `src/slay_the_spire/data/content/encounters/act1_bosses.json`
- Create: `content/encounters/act2_basic.json`
- Create: `src/slay_the_spire/data/content/encounters/act2_basic.json`
- Create: `content/encounters/act2_elites.json`
- Create: `src/slay_the_spire/data/content/encounters/act2_elites.json`
- Create: `content/encounters/act2_bosses.json`
- Create: `src/slay_the_spire/data/content/encounters/act2_bosses.json`

## Task 1: 先接通跨幕推进骨架

**Files:**
- Modify: `tests/use_cases/test_room_recovery.py`
- Modify: `tests/e2e/test_single_act_smoke.py`
- Create: `tests/e2e/test_two_act_smoke.py`
- Modify: `src/slay_the_spire/app/session.py`
- Modify: `src/slay_the_spire/use_cases/start_run.py`
- Create or Modify: `content/acts/act1_map.json`
- Create: `content/acts/act2_map.json`
- Mirror packaged copies under `src/slay_the_spire/data/content/acts/`

- [ ] **Step 1: 写失败测试，锁定 Boss 奖励后进入下一幕而不是直接 victory**

在 `tests/use_cases/test_room_recovery.py` 增加一个场景：

```python
def test_claiming_final_boss_reward_in_act1_enters_act2_instead_of_victory() -> None:
    session = _boss_reward_ready_session(act_id="act1", next_act_id="act2")

    _running, gold_session, _message = route_menu_choice("1", session=session)
    _running, relic_menu_session, _message = route_menu_choice("2", session=gold_session)
    _running, next_session, _message = route_menu_choice("1", session=relic_menu_session)

    assert next_session.run_phase == "active"
    assert next_session.run_state.current_act_id == "act2"
    assert next_session.act_state.act_id == "act2"
    assert next_session.room_state.payload["act_id"] == "act2"
```

在 `tests/e2e/test_two_act_smoke.py` 增加一个最小冒烟：

```python
def test_act1_boss_reward_transitions_into_act2_start_room() -> None:
    session = _force_act1_boss_reward_complete(start_session(seed=5))

    _running, session, _message = route_menu_choice("1", session=session)
    _running, session, _message = route_menu_choice("2", session=session)
    _running, session, _message = route_menu_choice("1", session=session)

    assert session.run_phase == "active"
    assert session.act_state.act_id == "act2"
    assert session.room_state.room_type == "combat"
```

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `uv run pytest tests/use_cases/test_room_recovery.py tests/e2e/test_two_act_smoke.py -v`

Expected:
- 当前逻辑会把 Boss 奖励领完直接置成 `victory`
- `act2` 内容文件不存在时，相关断言或内容加载失败

- [ ] **Step 3: 最小实现跨幕骨架**

实现方向：

- 在 `content/acts/act1_map.json` 和打包副本里增加 `next_act_id: "act2"`
- 新建最小 `content/acts/act2_map.json` 与打包副本，先只提供可加载的地图骨架
- 在 `src/slay_the_spire/content/registries.py` 的 `ActDef` 中增加可选字段 `next_act_id`
- 在 `src/slay_the_spire/app/session.py` 中把“Boss 奖励领完后的终局判定”改成：
  - 若当前幕有 `next_act_id`，生成下一幕 `act_state`、更新 `run_state.current_act_id`、进入下一幕起点房间
  - 仅当没有 `next_act_id` 时才进入 `victory`

- [ ] **Step 4: 运行测试，确认跨幕骨架通过**

Run: `uv run pytest tests/use_cases/test_room_recovery.py tests/e2e/test_two_act_smoke.py -v`

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/use_cases/test_room_recovery.py \
  tests/e2e/test_two_act_smoke.py \
  src/slay_the_spire/app/session.py \
  src/slay_the_spire/use_cases/start_run.py \
  src/slay_the_spire/content/registries.py \
  content/acts/act1_map.json \
  content/acts/act2_map.json \
  src/slay_the_spire/data/content/acts/act1_map.json \
  src/slay_the_spire/data/content/acts/act2_map.json
git commit -m "feat: add act-to-act progression scaffold"
```

## Task 2: 引入 encounter 内容类型，替代单怪抽取

**Files:**
- Modify: `tests/content/test_registry_validation.py`
- Modify: `tests/use_cases/test_enter_room.py`
- Modify: `tests/use_cases/test_start_run.py`
- Modify: `src/slay_the_spire/content/catalog.py`
- Modify: `src/slay_the_spire/content/provider.py`
- Modify: `src/slay_the_spire/content/registries.py`
- Modify: `src/slay_the_spire/ports/content_provider.py`
- Modify: `src/slay_the_spire/use_cases/enter_room.py`
- Create: `content/encounters/act1_basic.json`
- Create: `src/slay_the_spire/data/content/encounters/act1_basic.json`

- [ ] **Step 1: 写失败测试，锁定 encounter 可注册且能生成多敌人**

在 `tests/content/test_registry_validation.py` 增加：

```python
def test_content_provider_loads_encounter_pool_entries() -> None:
    provider = StarterContentProvider(Path(__file__).resolve().parents[2] / "content")

    entries = provider.encounter_pool_entries("act1_basic")

    assert any(entry.member_id == "double_slime" for entry in entries)
```

在 `tests/use_cases/test_enter_room.py` 增加：

```python
def test_enter_room_builds_multiple_enemy_states_from_encounter() -> None:
    room_state = enter_room(run_state, act_state, node_id="r1c0", registry=provider)
    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    assert [enemy.enemy_id for enemy in combat_state.enemies] == ["slime", "slime"]
    assert [enemy.instance_id for enemy in combat_state.enemies] == ["enemy-1", "enemy-2"]
```

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `uv run pytest tests/content/test_registry_validation.py tests/use_cases/test_enter_room.py tests/use_cases/test_start_run.py -v`

Expected:
- `ContentProviderPort` 没有 `encounter_pool_entries`
- `enter_room` 只会创建一个敌人

- [ ] **Step 3: 最小实现 encounter 注册与战斗入场**

实现方向：

- 在 `src/slay_the_spire/content/registries.py` 新增 `EncounterDef`
  - 字段建议：`id`、`name`、`enemy_ids`、`pool_weight`
- 在 `src/slay_the_spire/content/catalog.py` 新增 `encounters` 目录加载逻辑
- 在 `src/slay_the_spire/ports/content_provider.py` 和 `src/slay_the_spire/content/provider.py` 暴露：

```python
def encounter_pool_entries(self, pool_id: str) -> tuple[WeightedPoolEntry, ...]: ...
def encounters(self) -> "EncounterRegistry": ...
```

- 在 `src/slay_the_spire/use_cases/enter_room.py` 中：
  - 房间不再直接从敌人池选单个 `enemy_id`
  - 改为从 encounter 池抽 `encounter_id`
  - 按 `enemy_ids` 生成多个 `EnemyState`

- [ ] **Step 4: 运行测试，确认多敌人入场通过**

Run: `uv run pytest tests/content/test_registry_validation.py tests/use_cases/test_enter_room.py tests/use_cases/test_start_run.py -v`

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/content/test_registry_validation.py \
  tests/use_cases/test_enter_room.py \
  tests/use_cases/test_start_run.py \
  src/slay_the_spire/content/catalog.py \
  src/slay_the_spire/content/provider.py \
  src/slay_the_spire/content/registries.py \
  src/slay_the_spire/ports/content_provider.py \
  src/slay_the_spire/use_cases/enter_room.py \
  content/encounters/act1_basic.json \
  src/slay_the_spire/data/content/encounters/act1_basic.json
git commit -m "feat: add encounter pool support"
```

## Task 3: 把 Act 1 迁移到 encounter 系统并补多怪回归

**Files:**
- Modify: `tests/e2e/test_single_act_smoke.py`
- Modify: `tests/domain/test_combat_flow.py`
- Create or Modify: `content/encounters/act1_basic.json`
- Create or Modify: `content/encounters/act1_elites.json`
- Create or Modify: `content/encounters/act1_bosses.json`
- Mirror packaged copies under `src/slay_the_spire/data/content/encounters/`

- [ ] **Step 1: 写失败测试，锁定 Act 1 已使用 encounter 池**

在 `tests/e2e/test_single_act_smoke.py` 增加：

```python
def test_single_act_smoke_act1_combat_can_spawn_multi_enemy_encounter() -> None:
    session = start_session(seed=23)
    combat_state = CombatState.from_dict(session.room_state.payload["combat_state"])

    assert len(combat_state.enemies) >= 1
    assert session.room_state.payload["encounter_id"] in {"single_jaw_worm", "double_slime", "slime_plus_worm"}
```

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `uv run pytest tests/e2e/test_single_act_smoke.py tests/domain/test_combat_flow.py -v`

Expected:
- `payload` 中还没有 `encounter_id`
- Act 1 没有多怪内容

- [ ] **Step 3: 最小迁移 Act 1 encounter 内容**

新增 `content/encounters/act1_basic.json` 与打包副本，内容类似：

```json
{
  "encounters": [
    { "id": "single_jaw_worm", "name": "单颚虫", "pool_weight": 3, "enemy_ids": ["jaw_worm"] },
    { "id": "double_slime", "name": "双史莱姆", "pool_weight": 2, "enemy_ids": ["slime", "slime"] },
    { "id": "slime_plus_worm", "name": "史莱姆与颚虫", "pool_weight": 2, "enemy_ids": ["slime", "jaw_worm"] }
  ]
}
```

同理补 `act1_elites`、`act1_bosses` 的 encounter 池，并在 `enter_room` 的 payload 中记录：

```python
payload["encounter_id"] = encounter_id
```

- [ ] **Step 4: 运行测试，确认 Act 1 迁移通过**

Run: `uv run pytest tests/e2e/test_single_act_smoke.py tests/domain/test_combat_flow.py -v`

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/e2e/test_single_act_smoke.py \
  tests/domain/test_combat_flow.py \
  src/slay_the_spire/use_cases/enter_room.py \
  content/encounters/act1_basic.json \
  content/encounters/act1_elites.json \
  content/encounters/act1_bosses.json \
  src/slay_the_spire/data/content/encounters/act1_basic.json \
  src/slay_the_spire/data/content/encounters/act1_elites.json \
  src/slay_the_spire/data/content/encounters/act1_bosses.json
git commit -m "feat: migrate act1 battles to encounter pools"
```

## Task 4: 落地 Act 2 地图与房间生态

**Files:**
- Modify: `tests/domain/test_map_generator.py`
- Modify: `tests/content/test_registry_validation.py`
- Create: `content/acts/act2_map.json`
- Create: `src/slay_the_spire/data/content/acts/act2_map.json`

- [ ] **Step 1: 写失败测试，锁定 Act 2 可加载且地图压力高于 Act 1**

在 `tests/content/test_registry_validation.py` 增加：

```python
def test_registry_loads_act2_definition() -> None:
    provider = StarterContentProvider(Path(__file__).resolve().parents[2] / "content")
    act = provider.acts().get("act2")

    assert act.name == "第二幕"
    assert act.event_pool_id == "act2_events"
```

在 `tests/domain/test_map_generator.py` 增加：

```python
def test_generate_act2_state_guarantees_two_elites_across_sampled_seeds() -> None:
    provider = StarterContentProvider(Path(__file__).resolve().parents[2] / "content")

    for seed in range(1, 21):
        act_state = generate_act_state("act2", seed=seed, registry=provider)
        elite_count = sum(1 for node in act_state.nodes if node.room_type == "elite")
        assert elite_count >= 2
```

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `uv run pytest tests/content/test_registry_validation.py tests/domain/test_map_generator.py -v`

Expected:
- `act2` 尚未注册
- 采样生成找不到 `act2`

- [ ] **Step 3: 最小实现 Act 2 地图配置**

在 `content/acts/act2_map.json` 与打包副本新增：

- `id: "act2"`
- `name: "第二幕"`
- `event_pool_id: "act2_events"`
- `next_act_id` 先留空或不提供
- `map_config` 相对 `act1` 增强：
  - 更高 `floor_count`
  - 更高 `minimum_counts.elite`
  - 更低 `event` 权重
  - 更高 `elite`、`shop`、`rest` 中后段权重

- [ ] **Step 4: 运行测试，确认 Act 2 地图规则通过**

Run: `uv run pytest tests/content/test_registry_validation.py tests/domain/test_map_generator.py -v`

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/content/test_registry_validation.py \
  tests/domain/test_map_generator.py \
  content/acts/act2_map.json \
  src/slay_the_spire/data/content/acts/act2_map.json
git commit -m "feat: add act2 map and room ecology"
```

## Task 5: 扩充 Act 2 普通怪与多怪遭遇池

**Files:**
- Modify: `tests/use_cases/test_start_run.py`
- Modify: `tests/use_cases/test_enter_room.py`
- Create: `content/enemies/act2_basic.json`
- Create: `src/slay_the_spire/data/content/enemies/act2_basic.json`
- Create: `content/encounters/act2_basic.json`
- Create: `src/slay_the_spire/data/content/encounters/act2_basic.json`

- [ ] **Step 1: 写失败测试，锁定 Act 2 普通房可抽到原版风格多怪**

在 `tests/use_cases/test_start_run.py` 增加：

```python
def test_enter_act2_combat_room_uses_act2_basic_encounters() -> None:
    act_state = generate_act_state("act2", seed=17, registry=provider)
    node_id = _node_id_for_room_type(act_state, "combat")

    room_state = enter_room(run_state, act_state, node_id=node_id, registry=provider)
    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    assert room_state.payload["encounter_id"] in {
        "chosen_plus_byrd",
        "double_chosen",
        "spheric_guardian_plus_slaver",
    }
    assert len(combat_state.enemies) >= 2
```

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `uv run pytest tests/use_cases/test_start_run.py tests/use_cases/test_enter_room.py -v`

Expected: FAIL because `act2_basic` content and encounter pool do not exist

- [ ] **Step 3: 最小实现 Act 2 普通怪与遭遇**

内容建议优先级：

- 普通敌人：`chosen`、`byrd`、`spheric_guardian`、`slaver_red`
- 遭遇组：
  - `chosen_plus_byrd`
  - `double_chosen`
  - `spheric_guardian_plus_slaver`
  - `triple_byrd`

每个敌人先用当前引擎能表达的低保真 `move_table` 落地，优先复刻：

- 攻击
- 加格挡
- 易伤 / 虚弱
- 睡眠 / 蓄力这类已有状态

- [ ] **Step 4: 运行测试，确认 Act 2 普通遭遇通过**

Run: `uv run pytest tests/use_cases/test_start_run.py tests/use_cases/test_enter_room.py -v`

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/use_cases/test_start_run.py \
  tests/use_cases/test_enter_room.py \
  content/enemies/act2_basic.json \
  content/encounters/act2_basic.json \
  src/slay_the_spire/data/content/enemies/act2_basic.json \
  src/slay_the_spire/data/content/encounters/act2_basic.json
git commit -m "feat: add act2 basic enemies and encounters"
```

## Task 6: 扩充 Act 2 精英与 Boss 内容池

**Files:**
- Modify: `tests/domain/test_combat_flow.py`
- Modify: `tests/e2e/test_two_act_smoke.py`
- Create: `content/enemies/act2_elites.json`
- Create: `src/slay_the_spire/data/content/enemies/act2_elites.json`
- Create: `content/enemies/act2_bosses.json`
- Create: `src/slay_the_spire/data/content/enemies/act2_bosses.json`
- Create: `content/encounters/act2_elites.json`
- Create: `src/slay_the_spire/data/content/encounters/act2_elites.json`
- Create: `content/encounters/act2_bosses.json`
- Create: `src/slay_the_spire/data/content/encounters/act2_bosses.json`

- [ ] **Step 1: 写失败测试，锁定第二幕精英和 Boss 池可真实进入**

在 `tests/e2e/test_two_act_smoke.py` 增加：

```python
def test_act2_boss_room_uses_act2_boss_encounters() -> None:
    session = _advance_session_to_act2_boss(seed=7)

    assert session.room_state.room_type == "boss"
    assert session.room_state.payload["encounter_id"] in {
        "bronze_automaton",
        "champ",
        "the_collector",
    }
```

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `uv run pytest tests/domain/test_combat_flow.py tests/e2e/test_two_act_smoke.py -v`

Expected: FAIL because `act2_elites` and `act2_bosses` content are missing

- [ ] **Step 3: 最小实现精英与 Boss 内容**

建议优先落地：

- 精英：`book_of_stabbing`、`gremlin_leader`、`taskmaster` / `slaver_blue` / `slaver_red`
- Boss：`bronze_automaton`、`champ`、`the_collector`

建议遭遇池：

- `act2_elites`
  - `book_of_stabbing`
  - `gremlin_leader`
  - `slavers`
- `act2_bosses`
  - `bronze_automaton`
  - `champ`
  - `the_collector`

对当前引擎暂不支持的高保真机制，在 JSON 中先做低保真替代，并在文档顶部注记“后续细化”。

- [ ] **Step 4: 运行测试，确认精英与 Boss 池通过**

Run: `uv run pytest tests/domain/test_combat_flow.py tests/e2e/test_two_act_smoke.py -v`

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/domain/test_combat_flow.py \
  tests/e2e/test_two_act_smoke.py \
  content/enemies/act2_elites.json \
  content/enemies/act2_bosses.json \
  content/encounters/act2_elites.json \
  content/encounters/act2_bosses.json \
  src/slay_the_spire/data/content/enemies/act2_elites.json \
  src/slay_the_spire/data/content/enemies/act2_bosses.json \
  src/slay_the_spire/data/content/encounters/act2_elites.json \
  src/slay_the_spire/data/content/encounters/act2_bosses.json
git commit -m "feat: add act2 elite and boss content"
```

## Task 7: 扩充 Act 2 事件池与中文终端文案

**Files:**
- Modify: `tests/content/test_registry_validation.py`
- Modify: `tests/use_cases/test_event_actions.py`
- Modify: `tests/adapters/terminal/test_renderer.py`
- Create: `content/events/act2_events.json`
- Create: `src/slay_the_spire/data/content/events/act2_events.json`

- [ ] **Step 1: 写失败测试，锁定 Act 2 事件池可进入且文案中文化**

在 `tests/use_cases/test_event_actions.py` 增加：

```python
def test_act2_event_pool_contains_multiple_distinct_events() -> None:
    provider = StarterContentProvider(Path(__file__).resolve().parents[2] / "content")
    event_ids = {entry.member_id for entry in provider.event_pool_entries("act2_events")}

    assert {"masked_bandits", "vampires", "colosseum"}.issubset(event_ids)
```

在 `tests/adapters/terminal/test_renderer.py` 增加：

```python
def test_act2_event_screen_uses_chinese_player_copy() -> None:
    session = _act2_event_session(event_id="masked_bandits")
    rendered = render_session(session)

    assert "蒙面强盗" in _strip_ansi(rendered)
    assert "付钱" in _strip_ansi(rendered)
```

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `uv run pytest tests/use_cases/test_event_actions.py tests/adapters/terminal/test_renderer.py tests/content/test_registry_validation.py -v`

Expected: FAIL because `act2_events` does not exist

- [ ] **Step 3: 最小实现 Act 2 事件池**

首批建议事件：

- `masked_bandits`
- `vampires`
- `colosseum`
- `the_joust`
- `woman_in_blue`

要求：

- 面向玩家的 `text`、`choices` 默认写中文
- 事件结果优先复用现有能力：金币变化、加牌、删牌、升级牌、掉血、获得遗物
- 暂不支持的复杂分支先省掉，不单独为单个事件扩一套系统

- [ ] **Step 4: 运行测试，确认 Act 2 事件通过**

Run: `uv run pytest tests/use_cases/test_event_actions.py tests/adapters/terminal/test_renderer.py tests/content/test_registry_validation.py -v`

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/use_cases/test_event_actions.py \
  tests/adapters/terminal/test_renderer.py \
  tests/content/test_registry_validation.py \
  content/events/act2_events.json \
  src/slay_the_spire/data/content/events/act2_events.json
git commit -m "feat: add act2 event pool"
```

## Task 8: 做两幕长流程、存读档和终端回归

**Files:**
- Create or Modify: `tests/e2e/test_two_act_smoke.py`
- Modify: `tests/use_cases/test_save_load.py`
- Modify: `tests/use_cases/test_room_recovery.py`
- Modify: `tests/adapters/terminal/test_renderer.py`
- Modify: `src/slay_the_spire/app/session.py`

- [ ] **Step 1: 写失败测试，锁定两幕长流程与恢复**

在 `tests/e2e/test_two_act_smoke.py` 增加：

```python
def test_two_act_smoke_can_clear_act1_and_enter_mid_act2_path() -> None:
    session = _play_to_act2(seed=11)
    assert session.act_state.act_id == "act2"

    path = _path_with_shop_rest_and_elite(session.act_state)
    assert len(path) > 4
```

在 `tests/use_cases/test_save_load.py` 增加：

```python
def test_save_load_preserves_act2_progress_and_multi_enemy_room(tmp_path) -> None:
    session = _act2_multi_enemy_session(tmp_path)
    restored = _roundtrip_session(session, tmp_path)

    combat_state = CombatState.from_dict(restored.room_state.payload["combat_state"])
    assert restored.act_state.act_id == "act2"
    assert len(combat_state.enemies) >= 2
```

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `uv run pytest tests/e2e/test_two_act_smoke.py tests/use_cases/test_save_load.py tests/use_cases/test_room_recovery.py tests/adapters/terminal/test_renderer.py -v`

Expected:
- 路径推进或跨幕恢复在某个环节失败
- 某些终端面板对第二幕或多敌人显示不稳定

- [ ] **Step 3: 最小修复两幕回归缺口**

重点检查：

- `session.py` 是否在跨幕后重置了正确的 `menu_state`
- `render_room` 是否能正确渲染第二幕标题、多敌人列表、路径选择
- `save_game` / `load_game` 是否完整保存 Act 2 的 `act_state` 与多敌人 `combat_state`

- [ ] **Step 4: 跑完整回归**

Run: `uv run pytest`

Expected: 全绿

- [ ] **Step 5: 提交**

```bash
git add tests/e2e/test_two_act_smoke.py \
  tests/use_cases/test_save_load.py \
  tests/use_cases/test_room_recovery.py \
  tests/adapters/terminal/test_renderer.py \
  src/slay_the_spire/app/session.py
git commit -m "test: cover two-act progression and multi-encounter recovery"
```

## Execution Notes

- 先做 `Task 1` 和 `Task 2`，不要先堆 `Act 2` 内容；没有跨幕和 encounter 底座，后面的内容文件都是返工源头。
- 每次修改 `content/` 后必须同步更新 `src/slay_the_spire/data/content/`。
- 终端用户可见文案默认写中文；代码标识、原版敌人 ID、命令和路径保留英文。
- 如果某个原版怪物机制需要新的效果类型或状态，再单开最小任务，不要在内容任务里顺手扩一大串底层能力。

## Recommended Execution Order

- [ ] Task 1: 跨幕推进骨架
- [ ] Task 2: encounter 内容类型
- [ ] Task 3: Act 1 迁移到 encounter
- [ ] Task 4: Act 2 地图与生态
- [ ] Task 5: Act 2 普通怪与多怪遭遇
- [ ] Task 6: Act 2 精英与 Boss
- [ ] Task 7: Act 2 事件池
- [ ] Task 8: 两幕 E2E / 存读档 / 终端回归
