# Original Act Floor Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让当前项目的 `act1/act2` 对齐原版《Slay the Spire》普通 Act 的固定楼层结构，补齐 `treasure` 和 `boss_chest` 两个房间类型，并把 Boss 后流程改成显式 `Floor 17` 过渡。

**Architecture:** 保持现有 `ActState`、编号菜单和 Textual/Rich 双适配层不变，通过扩展 `ActMapConfig` 内容 schema、地图生成器和 `session` 房间推进逻辑实现对齐。地图内节点只生成到 `Floor 16` 的 Boss 层，`Floor 17` 由 Boss 奖励完成后进入 `boss_chest` 房间来承接跨幕或胜利。

**Tech Stack:** Python 3.12, `uv`, `pytest`, `textual`, `rich`

---

### Task 1: 锁定原版固定楼层的回归点

**Files:**
- Modify: `tests/domain/test_map_generator.py`
- Check: `content/acts/act1_map.json`
- Check: `content/acts/act2_map.json`
- Check: `src/slay_the_spire/domain/map/map_generator.py`

- [ ] **Step 1: Write the failing tests**

在 `tests/domain/test_map_generator.py` 追加固定楼层断言，先把目标行为写死：

```python
def test_act1_uses_original_fixed_floors() -> None:
    provider = _content_provider()
    act_state = generate_act_state("act1", seed=7, registry=provider)

    rows = {node.row: node.room_type for node in act_state.nodes if node.col == 0 or node.room_type == "boss"}

    assert act_state.get_node("start").room_type == "combat"
    assert any(node.row == 8 and node.room_type == "treasure" for node in act_state.nodes)
    assert any(node.row == 14 and node.room_type == "rest" for node in act_state.nodes)
    assert any(node.row == 15 and node.room_type == "boss" for node in act_state.nodes)


def test_act2_uses_original_fixed_floors() -> None:
    provider = _content_provider()
    act_state = generate_act_state("act2", seed=7, registry=provider)

    assert any(node.row == 8 and node.room_type == "treasure" for node in act_state.nodes)
    assert any(node.row == 14 and node.room_type == "rest" for node in act_state.nodes)
    assert any(node.row == 15 and node.room_type == "boss" for node in act_state.nodes)
```

再补一条层数断言，确保地图层数已经扩到 Boss 层：

```python
def test_original_act_maps_generate_sixteen_map_rows_before_post_boss_flow() -> None:
    provider = _content_provider()

    for act_id in ("act1", "act2"):
        act_state = generate_act_state(act_id, seed=11, registry=provider)
        assert max(node.row for node in act_state.nodes) == 15
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/domain/test_map_generator.py -q`

Expected:

- 现有 `act1/act2` 的固定层数断言失败
- 或最后一层 `row` 仍小于 `15`

- [ ] **Step 3: Commit**

```bash
git add tests/domain/test_map_generator.py
git commit -m "test: lock original act floor structure"
```

### Task 2: 扩展 Act 配置 schema 并同步内容文件

**Files:**
- Modify: `src/slay_the_spire/content/registries.py`
- Modify: `content/acts/act1_map.json`
- Modify: `content/acts/act2_map.json`
- Modify: `src/slay_the_spire/data/content/acts/act1_map.json`
- Modify: `src/slay_the_spire/data/content/acts/act2_map.json`
- Test: `tests/content/test_registry_validation.py`

- [ ] **Step 1: Write the failing tests**

在 `tests/content/test_registry_validation.py` 增加 schema 断言，要求新字段能被正确读取：

```python
def test_act_map_config_supports_fixed_floor_and_post_boss_room_type() -> None:
    provider = StarterContentProvider(Path(__file__).resolve().parents[2] / "content")
    act = provider.acts().get("act1")

    assert act.map_config.fixed_floor_room_types[1] == "combat"
    assert act.map_config.fixed_floor_room_types[9] == "treasure"
    assert act.map_config.fixed_floor_room_types[15] == "rest"
    assert act.map_config.fixed_floor_room_types[16] == "boss"
    assert act.map_config.post_boss_room_type == "boss_chest"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/content/test_registry_validation.py -q`

Expected: FAIL，`ActMapConfig` 还没有这些字段，内容 JSON 也没有对应配置。

- [ ] **Step 3: Write minimal implementation**

在 `src/slay_the_spire/content/registries.py`：

- 扩展 `ActMapConfig`：

```python
@dataclass(slots=True, frozen=True)
class ActMapConfig:
    floor_count: int
    starting_columns: int
    min_branch_choices: int
    max_branch_choices: int
    boss_room_type: str
    room_rules: JsonDict
    fixed_floor_room_types: dict[int, str] = field(default_factory=dict)
    post_boss_room_type: str | None = None
```

- 在 Act 配置解析时读取并校验：
  - `fixed_floor_room_types`
  - `post_boss_room_type`

在四份 Act JSON 中同步新增配置：

- `floor_count: 16`
- `fixed_floor_room_types`
- `post_boss_room_type: "boss_chest"`

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/content/test_registry_validation.py tests/domain/test_map_generator.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/content/registries.py content/acts/act1_map.json content/acts/act2_map.json src/slay_the_spire/data/content/acts/act1_map.json src/slay_the_spire/data/content/acts/act2_map.json tests/content/test_registry_validation.py tests/domain/test_map_generator.py
git commit -m "feat: add original act floor config fields"
```

### Task 3: 让地图生成器尊重固定楼层规则

**Files:**
- Modify: `src/slay_the_spire/domain/map/map_generator.py`
- Test: `tests/domain/test_map_generator.py`

- [ ] **Step 1: Write the failing tests**

在 `tests/domain/test_map_generator.py` 再补两条规则优先级测试：

```python
def test_fixed_floor_room_types_override_weighted_generation() -> None:
    provider = _content_provider()
    act_state = generate_act_state("act1", seed=99, registry=provider)

    assert {node.room_type for node in act_state.nodes if node.row == 8} == {"treasure"}
    assert {node.room_type for node in act_state.nodes if node.row == 14} == {"rest"}


def test_boss_row_remains_single_boss_node() -> None:
    provider = _content_provider()
    act_state = generate_act_state("act1", seed=99, registry=provider)

    boss_nodes = [node for node in act_state.nodes if node.row == 15]
    assert len(boss_nodes) == 1
    assert boss_nodes[0].room_type == "boss"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/domain/test_map_generator.py -q`

Expected: FAIL，当前生成器仍只按随机权重和最后一层 Boss 规则分配房间类型。

- [ ] **Step 3: Write minimal implementation**

在 `src/slay_the_spire/domain/map/map_generator.py`：

- 增加 helper：

```python
def _fixed_room_type_for_row(row: int, config: ActMapConfig) -> str | None:
    return config.fixed_floor_room_types.get(row + 1)
```

- 在 `_assign_room_types()` 中优先应用固定楼层：
  - 起始层仍是 `combat`
  - 若当前楼层在 `fixed_floor_room_types` 中，直接使用配置值
  - 未命中时才走现有权重逻辑
- 调整最小数量修补逻辑，禁止覆写固定楼层
- 保持 Boss 层单节点拓扑不变

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/domain/test_map_generator.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/domain/map/map_generator.py tests/domain/test_map_generator.py
git commit -m "feat: enforce original fixed floors in map generation"
```

### Task 4: 为 `treasure` 房间补最小遗物掉落链路

**Files:**
- Modify: `src/slay_the_spire/app/session.py`
- Modify: `src/slay_the_spire/app/menu_definitions.py`
- Modify: `src/slay_the_spire/adapters/rich_ui/screens/non_combat.py`
- Modify: `content/relics/*.json`
- Modify: `src/slay_the_spire/data/content/relics/*.json`
- Test: `tests/app/test_menu_definitions.py`
- Test: `tests/use_cases/test_room_recovery.py`
- Test: `tests/e2e/test_single_act_smoke.py`

- [ ] **Step 1: Write the failing tests**

先在菜单和流程测试里锁定 `treasure` 行为：

```python
def test_treasure_room_root_menu_offers_open_chest() -> None:
    room_state = replace(start_session(seed=5).room_state, room_type="treasure", stage="waiting_input", is_resolved=False)

    menu = build_root_menu(room_state=room_state)

    assert resolve_menu_action("1", menu) == "open_treasure"


def test_opening_treasure_marks_room_resolved_and_adds_relic() -> None:
    session = _session_in_treasure_room()

    next_session = route_menu_choice("1", session=session).session

    assert next_session.room_state.room_type == "treasure"
    assert next_session.room_state.is_resolved is True
    assert len(next_session.run_state.relics) == len(session.run_state.relics) + 1
```

再补一条 E2E，确保单幕流程里能经过 `treasure` 并继续推进。

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/app/test_menu_definitions.py tests/use_cases/test_room_recovery.py tests/e2e/test_single_act_smoke.py -q`

Expected: FAIL，当前没有 `treasure` 分支和菜单动作。

- [ ] **Step 3: Write minimal implementation**

实现内容：

- 在 `session.py` 中为 `treasure` 房间生成最小 payload，例如 `treasure_relic_id`
- 新增菜单动作 `open_treasure`
- 领取时把遗物写回 `run_state`
- 标记 `room_state.is_resolved = True`
- 在 Rich 非战斗渲染中补宝箱说明和遗物预览

如果缺普通掉落池，先补最小可掉落遗物集并限制只给 `treasure` 使用。

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/app/test_menu_definitions.py tests/use_cases/test_room_recovery.py tests/e2e/test_single_act_smoke.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/app/session.py src/slay_the_spire/app/menu_definitions.py src/slay_the_spire/adapters/rich_ui/screens/non_combat.py content src/slay_the_spire/data/content tests/app/test_menu_definitions.py tests/use_cases/test_room_recovery.py tests/e2e/test_single_act_smoke.py
git commit -m "feat: add treasure room flow"
```

### Task 5: 插入 Boss 后的 `boss_chest` 过渡房间

**Files:**
- Modify: `src/slay_the_spire/app/session.py`
- Modify: `src/slay_the_spire/app/menu_definitions.py`
- Modify: `src/slay_the_spire/adapters/rich_ui/screens/non_combat.py`
- Test: `tests/app/test_inspect_menus.py`
- Test: `tests/use_cases/test_room_recovery.py`
- Test: `tests/e2e/test_two_act_smoke.py`

- [ ] **Step 1: Write the failing tests**

补 Boss 奖励后的流程测试：

```python
def test_claiming_final_boss_reward_enters_boss_chest_instead_of_switching_act_immediately() -> None:
    session = _session_after_boss_with_pending_rewards()

    session = _claim_all_boss_rewards(session)

    assert session.room_state.room_type == "boss_chest"
    assert session.run_phase == "active"


def test_boss_chest_can_advance_to_next_act() -> None:
    session = _session_in_boss_chest(act_id="act1")

    next_session = route_menu_choice("1", session=session).session

    assert next_session.act_state.act_id == "act2"
    assert next_session.room_state.room_type == "combat"
```

再补一条 `act2` 终局测试，确认 `boss_chest` 后才进入 `victory`。

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/app/test_inspect_menus.py tests/use_cases/test_room_recovery.py tests/e2e/test_two_act_smoke.py -q`

Expected: FAIL，当前 Boss 奖励完成后仍直接切幕或胜利。

- [ ] **Step 3: Write minimal implementation**

在 `src/slay_the_spire/app/session.py`：

- 把 `_resolve_boss_reward_completion()` 改成进入 `boss_chest`
- 新增 `boss_chest` 的 payload 和推进动作，例如 `advance_from_boss_chest`
- 在 `boss_chest` 执行动作时：
  - 有 `next_act_id` 则生成下一幕起始房间
  - 没有 `next_act_id` 则切 `victory`

同时在菜单和 Rich 渲染里补：

- `boss_chest` 标题与说明
- “前往下一幕” / “完成攀登” 按钮文案

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/app/test_inspect_menus.py tests/use_cases/test_room_recovery.py tests/e2e/test_two_act_smoke.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/app/session.py src/slay_the_spire/app/menu_definitions.py src/slay_the_spire/adapters/rich_ui/screens/non_combat.py tests/app/test_inspect_menus.py tests/use_cases/test_room_recovery.py tests/e2e/test_two_act_smoke.py
git commit -m "feat: add boss chest transition flow"
```

### Task 6: 补 Textual、恢复链路和全量回归

**Files:**
- Modify: `tests/adapters/textual/test_slay_app.py`
- Modify: `tests/use_cases/test_save_load.py`
- Modify: `tests/use_cases/test_room_recovery.py`
- Check: `src/slay_the_spire/adapters/textual/slay_app.py`
- Check: `src/slay_the_spire/adapters/rich_ui/screens/non_combat.py`

- [ ] **Step 1: Write the failing tests**

追加两个新房间类型的 Textual / 存档恢复断言：

```python
def test_hover_preview_supports_treasure_room_actions() -> None:
    session = replace(start_session(seed=5), room_state=RoomState(room_id="r1", room_type="treasure", stage="waiting_input", payload={}, is_resolved=False, rewards=[]))

    preview = _hover_preview_renderable(session, "open_treasure")
    assert preview is not None


def test_save_load_round_trips_boss_chest_room_state() -> None:
    session = _session_in_boss_chest(act_id="act1")
    _save_session(session)
    loaded = load_session(save_path=session.save_path, content_root=session.content_root)

    assert loaded.room_state.room_type == "boss_chest"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py tests/use_cases/test_save_load.py tests/use_cases/test_room_recovery.py -q`

Expected: FAIL，当前 UI 预览和存档恢复还不认识两个新房间类型。

- [ ] **Step 3: Write minimal implementation**

补齐：

- Textual hover preview 和菜单文案
- 房间恢复对 `treasure` / `boss_chest` 的支持
- 存读档 round-trip 的最小 payload 兼容

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py tests/use_cases/test_save_load.py tests/use_cases/test_room_recovery.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/adapters/textual/test_slay_app.py tests/use_cases/test_save_load.py tests/use_cases/test_room_recovery.py src/slay_the_spire/adapters/textual/slay_app.py src/slay_the_spire/adapters/rich_ui/screens/non_combat.py
git commit -m "test: cover treasure and boss chest recovery"
```

### Task 7: 运行全量验证并更新文档

**Files:**
- Check: `docs/superpowers/specs/2026-03-28-original-act-floor-alignment-design.md`
- Check: `docs/superpowers/plans/2026-03-28-original-act-floor-alignment-implementation.md`
- Check: `pyproject.toml`

- [ ] **Step 1: Run the focused verification suite**

Run:

```bash
uv run pytest \
  tests/content/test_registry_validation.py \
  tests/domain/test_map_generator.py \
  tests/app/test_menu_definitions.py \
  tests/app/test_inspect_menus.py \
  tests/use_cases/test_room_recovery.py \
  tests/use_cases/test_save_load.py \
  tests/e2e/test_single_act_smoke.py \
  tests/e2e/test_two_act_smoke.py \
  tests/adapters/textual/test_slay_app.py -q
```

Expected: PASS

- [ ] **Step 2: Run the full suite**

Run: `uv run pytest`

Expected: PASS

- [ ] **Step 3: Sanity-check gameplay entry points**

Run:

```bash
uv run slay-the-spire new --seed 5
```

Manual checks:

- 能走到 `Floor 9 treasure`
- 能打开宝箱并继续推进
- 能在 Boss 奖励后进入 `boss_chest`
- `act1` 可从 `boss_chest` 进入 `act2`
- `act2` 可从 `boss_chest` 进入胜利

- [ ] **Step 4: Update docs if implementation scope drifted**

如果实际实现与设计文档有偏差，同步修订：

- `docs/superpowers/specs/2026-03-28-original-act-floor-alignment-design.md`

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-03-28-original-act-floor-alignment-design.md docs/superpowers/plans/2026-03-28-original-act-floor-alignment-implementation.md
git commit -m "docs: finalize original act floor alignment plan"
```
