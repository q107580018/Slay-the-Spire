# RNG, Rewards, And Map Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `act1` 引入更接近原版《Slay the Spire》的随机系统，包括统一 RNG 派生、地图房型分布约束、敌人与事件权重抽样，以及普通战/精英战的三选一卡牌奖励。

**Architecture:** 保留现有终端原型、内容 JSON 和 `seed` 驱动结构，在 `shared` / `content` / `use_cases` / `app` 四层做增量升级。随机逻辑统一收口到稳定派生 helper，地图、遭遇、事件、奖励全部改为配置驱动，菜单和测试随奖励结构同步扩展。

**Tech Stack:** Python 3.12, `uv`, `pytest`, `rich`, JSON content catalogs

---

### Task 1: 盘点当前随机与内容入口

**Files:**
- Modify: `docs/superpowers/plans/2026-03-26-rng-rewards-map-implementation.md`
- Check: `src/slay_the_spire/shared/rng.py`
- Check: `src/slay_the_spire/domain/map/map_generator.py`
- Check: `src/slay_the_spire/use_cases/enter_room.py`
- Check: `src/slay_the_spire/domain/rewards/reward_generator.py`
- Check: `src/slay_the_spire/content/catalog.py`

- [ ] **Step 1: 记录当前随机入口与缺口**

在本计划对应 task 下补一段执行备注，列出：

- `map_generator.py` 当前直接 `Random(seed + attempt)`
- `enter_room.py` 当前 `_offer_rng(run_state, room_id, category)`
- `reward_generator.py` 当前没有统一 RNG helper，仍靠自定义 hash / seed 计算
- `catalog.py` 当前池结构不支持权重成员

- [ ] **Step 2: 核对无额外阻塞**

Run: `uv run pytest tests/domain/test_map_generator.py tests/use_cases/test_apply_reward.py -q`

Expected:

- 当前基线通过
- 没有与未提交工作区改动直接冲突的失败

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-03-26-rng-rewards-map-implementation.md
git commit -m "docs: add rng rewards implementation plan"
```

### Task 2: 建立统一 RNG helper

**Files:**
- Modify: `src/slay_the_spire/shared/rng.py`
- Modify: `src/slay_the_spire/domain/map/map_generator.py`
- Modify: `src/slay_the_spire/use_cases/enter_room.py`
- Modify: `src/slay_the_spire/domain/rewards/reward_generator.py`
- Test: `tests/shared/test_rng.py`

- [ ] **Step 1: Write the failing test**

在 `tests/shared/test_rng.py` 新增测试：

```python
from random import Random

from slay_the_spire.shared.rng import rng_for_room, rng_for_run


def test_rng_for_run_is_deterministic_for_same_seed_and_category() -> None:
    left = rng_for_run(seed=7, category="map:topology")
    right = rng_for_run(seed=7, category="map:topology")

    assert [left.randint(1, 100) for _ in range(5)] == [right.randint(1, 100) for _ in range(5)]


def test_rng_for_room_isolated_by_room_and_category() -> None:
    combat_rng = rng_for_room(seed=7, room_id="act1:r1c0", category="encounter:combat")
    reward_rng = rng_for_room(seed=7, room_id="act1:r1c0", category="reward:card")

    assert [combat_rng.randint(1, 100) for _ in range(3)] != [reward_rng.randint(1, 100) for _ in range(3)]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/shared/test_rng.py -v`

Expected: FAIL with import error or missing `rng_for_run` / `rng_for_room`

- [ ] **Step 3: Write minimal implementation**

在 `src/slay_the_spire/shared/rng.py` 实现：

```python
from __future__ import annotations

from random import Random


def _seed_key(*parts: object) -> str:
    return ":".join(str(part) for part in parts)


def rng_for_run(*, seed: int, category: str) -> Random:
    return Random(_seed_key(seed, category))


def rng_for_room(*, seed: int, room_id: str, category: str) -> Random:
    return Random(_seed_key(seed, room_id, category))
```

随后把：

- `map_generator.py`
- `enter_room.py`
- `reward_generator.py`

里的直接 `Random(...)` 调用替换为 helper，但不改变行为。

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/shared/test_rng.py tests/domain/test_map_generator.py tests/use_cases/test_apply_reward.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/shared/test_rng.py src/slay_the_spire/shared/rng.py src/slay_the_spire/domain/map/map_generator.py src/slay_the_spire/use_cases/enter_room.py src/slay_the_spire/domain/rewards/reward_generator.py
git commit -m "refactor: unify seeded rng helpers"
```

### Task 3: 为内容池增加权重读取能力

**Files:**
- Modify: `src/slay_the_spire/content/catalog.py`
- Modify: `src/slay_the_spire/content/provider.py`
- Modify: `src/slay_the_spire/ports/content_provider.py`
- Modify: `content/enemies/act1_basic.json`
- Modify: `content/enemies/act1_elites.json`
- Modify: `content/enemies/act1_bosses.json`
- Modify: `content/events/act1_events.json`
- Modify: `src/slay_the_spire/data/content/enemies/act1_basic.json`
- Modify: `src/slay_the_spire/data/content/enemies/act1_elites.json`
- Modify: `src/slay_the_spire/data/content/enemies/act1_bosses.json`
- Modify: `src/slay_the_spire/data/content/events/act1_events.json`
- Test: `tests/content/test_registry_validation.py`
- Test: `tests/use_cases/test_enter_room.py`

- [ ] **Step 1: Write the failing test**

在 `tests/content/test_registry_validation.py` 增加测试，断言 provider 能返回带权重成员，例如：

```python
def test_enemy_pool_entries_preserve_weight_metadata() -> None:
    provider = _content_provider()

    pool = provider.enemy_pool_entries("act1_basic")

    assert pool
    assert all(entry.member_id for entry in pool)
    assert all(entry.weight > 0 for entry in pool)
```

再在 `tests/use_cases/test_enter_room.py` 新增一条最小测试，断言 `event` 房会从池成员元数据读取事件，而不是只读 id 列表。

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/content/test_registry_validation.py tests/use_cases/test_enter_room.py -q`

Expected: FAIL with missing provider API or unsupported JSON shape

- [ ] **Step 3: Write minimal implementation**

在内容层引入轻量池成员结构，例如：

```python
@dataclass(frozen=True, slots=True)
class WeightedPoolEntry:
    member_id: str
    weight: int
    once_per_run: bool = False
```

并在 `catalog.py` 中：

- 为敌人池与事件池加载成员对象
- 保留现有 `enemy_ids_for_pool()` / `event_ids_for_pool()` 兼容接口
- 新增 `enemy_pool_entries()` / `event_pool_entries()`

同时把相关 JSON 改成显式成员结构，例如：

```json
{
  "enemies": [
    { "id": "jaw_worm", "weight": 3 },
    { "id": "slime", "weight": 2 }
  ]
}
```

```json
{
  "events": [
    { "id": "shining_light", "weight": 2, "once_per_run": true }
  ]
}
```

根目录 `content/` 与 `src/slay_the_spire/data/content/` 必须同步。

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/content/test_registry_validation.py tests/use_cases/test_enter_room.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/content/catalog.py src/slay_the_spire/content/provider.py src/slay_the_spire/ports/content_provider.py content/enemies/act1_basic.json content/enemies/act1_elites.json content/enemies/act1_bosses.json content/events/act1_events.json src/slay_the_spire/data/content/enemies/act1_basic.json src/slay_the_spire/data/content/enemies/act1_elites.json src/slay_the_spire/data/content/enemies/act1_bosses.json src/slay_the_spire/data/content/events/act1_events.json tests/content/test_registry_validation.py tests/use_cases/test_enter_room.py
git commit -m "feat: add weighted encounter and event pools"
```

### Task 4: 在共享层实现加权抽样 helper

**Files:**
- Modify: `src/slay_the_spire/shared/rng.py`
- Test: `tests/shared/test_rng.py`

- [ ] **Step 1: Write the failing test**

在 `tests/shared/test_rng.py` 增加：

```python
from slay_the_spire.shared.rng import weighted_choice


def test_weighted_choice_returns_only_configured_member_ids() -> None:
    choice = weighted_choice(
        [
            ("jaw_worm", 3),
            ("slime", 1),
        ],
        rng=rng_for_room(seed=9, room_id="act1:r1c0", category="encounter:combat"),
    )

    assert choice in {"jaw_worm", "slime"}


def test_weighted_choice_rejects_non_positive_total_weight() -> None:
    with pytest.raises(ValueError):
        weighted_choice([("jaw_worm", 0)], rng=rng_for_run(seed=1, category="encounter"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/shared/test_rng.py -q`

Expected: FAIL with missing `weighted_choice`

- [ ] **Step 3: Write minimal implementation**

在 `src/slay_the_spire/shared/rng.py` 增加：

```python
def weighted_choice(options: list[tuple[str, int]], *, rng: Random) -> str:
    total = sum(weight for _member_id, weight in options)
    if total <= 0:
        raise ValueError("weighted_choice requires positive total weight")
    roll = rng.randint(1, total)
    running = 0
    for member_id, weight in options:
        if weight <= 0:
            continue
        running += weight
        if roll <= running:
            return member_id
    raise AssertionError("weighted_choice failed to select an option")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/shared/test_rng.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/shared/rng.py tests/shared/test_rng.py
git commit -m "feat: add weighted rng sampling"
```

### Task 5: 让 `enter_room` 使用加权遭遇与事件抽样

**Files:**
- Modify: `src/slay_the_spire/use_cases/enter_room.py`
- Modify: `src/slay_the_spire/domain/models/run_state.py`
- Modify: `tests/use_cases/test_enter_room.py`
- Modify: `tests/domain/test_state_serialization.py`
- Modify: `tests/use_cases/test_save_load.py`

- [ ] **Step 1: Write the failing test**

在 `tests/use_cases/test_enter_room.py` 写 3 条测试：

```python
def test_enter_combat_room_uses_weighted_enemy_pool_entries() -> None:
    ...
    assert enemy_id == "jaw_worm"


def test_enter_event_room_uses_weighted_event_pool_entries() -> None:
    ...
    assert room_state.payload["event_id"] == "golden_shrine"


def test_enter_event_room_skips_once_per_run_events_already_seen() -> None:
    ...
    assert room_state.payload["event_id"] != "shining_light"
```

最后一条需要给 `RunState` 增加已见事件记录字段，例如 `seen_event_ids`。

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/use_cases/test_enter_room.py tests/domain/test_state_serialization.py tests/use_cases/test_save_load.py -q`

Expected: FAIL with missing `seen_event_ids` or weighted selection not used

- [ ] **Step 3: Write minimal implementation**

实现内容：

- `RunState` 增加 `seen_event_ids: list[str] = []`
- `to_dict()` / `from_dict()` / 相关迁移逻辑支持新字段
- `enter_room.py`：
  - 从 provider 读取权重成员
  - 使用 `weighted_choice()`
  - 事件候选先过滤 `once_per_run and member_id in run_state.seen_event_ids`
  - 若过滤后为空，回退到不过滤的事件池或抛清晰错误，二选一后保持测试固定

注意：

- 这里只负责抽到哪个事件
- 标记事件已见可放在进入事件房即写入，或事件完成后写入；计划推荐“进入事件房即写入”，因为这是最接近玩家感知的 once-per-run 语义

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/use_cases/test_enter_room.py tests/domain/test_state_serialization.py tests/use_cases/test_save_load.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/use_cases/enter_room.py src/slay_the_spire/domain/models/run_state.py tests/use_cases/test_enter_room.py tests/domain/test_state_serialization.py tests/use_cases/test_save_load.py
git commit -m "feat: use weighted room encounter selection"
```

### Task 6: 为地图房型分配增加权重与约束配置

**Files:**
- Modify: `src/slay_the_spire/content/registries.py`
- Modify: `src/slay_the_spire/domain/map/map_generator.py`
- Modify: `content/acts/act1_map.json`
- Modify: `src/slay_the_spire/data/content/acts/act1_map.json`
- Test: `tests/domain/test_map_generator.py`
- Test: `tests/content/test_registry_validation.py`

- [ ] **Step 1: Write the failing test**

在 `tests/domain/test_map_generator.py` 追加测试：

```python
def test_generate_act_state_respects_min_floor_constraints() -> None:
    ...
    assert all(node.row >= 3 for node in elites)
    assert all(node.row >= 2 for node in shops)
    assert all(node.row >= 2 for node in rests)


def test_generate_act_state_guarantees_minimum_special_room_counts() -> None:
    ...
    assert len(events) >= 2
    assert len(elites) >= 1


def test_generate_act_state_avoids_long_special_room_streaks_on_paths() -> None:
    ...
    assert longest_streak <= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/domain/test_map_generator.py -q`

Expected: FAIL because current assignment is uniform and unconstrained

- [ ] **Step 3: Write minimal implementation**

在 `content/acts/act1_map.json` 与打包副本中扩展配置，例如：

```json
"room_type_rules": {
  "weights": {
    "early": { "combat": 6, "event": 4 },
    "mid": { "combat": 5, "event": 3, "shop": 1, "rest": 1 },
    "late": { "combat": 4, "event": 3, "elite": 2, "shop": 1, "rest": 1 }
  },
  "minimum_counts": { "event": 2, "shop": 1, "rest": 1, "elite": 1 },
  "min_floor": { "shop": 2, "rest": 2, "elite": 3 },
  "max_path_special_streak": 2
}
```

然后在 `registries.py` 增加对应 schema 字段，在 `map_generator.py` 中：

- 按楼层段权重抽房型
- 先应用最早楼层约束
- 再进行 streak 修正
- 最后进行最低数量兜底

实现上保持现有拓扑算法不动，只替换房型分配阶段。

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/domain/test_map_generator.py tests/content/test_registry_validation.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/content/registries.py src/slay_the_spire/domain/map/map_generator.py content/acts/act1_map.json src/slay_the_spire/data/content/acts/act1_map.json tests/domain/test_map_generator.py tests/content/test_registry_validation.py
git commit -m "feat: add weighted map room distribution rules"
```

### Task 7: 为卡牌内容引入奖励池语义

**Files:**
- Modify: `content/cards/ironclad_starter.json`
- Modify: `src/slay_the_spire/data/content/cards/ironclad_starter.json`
- Modify: `src/slay_the_spire/content/catalog.py`
- Modify: `src/slay_the_spire/content/registries.py`
- Test: `tests/content/test_registry_validation.py`

- [ ] **Step 1: Write the failing test**

在 `tests/content/test_registry_validation.py` 增加：

```python
def test_reward_card_pool_contains_enough_unique_ironclad_cards() -> None:
    provider = _content_provider()

    reward_cards = [card.id for card in provider.cards().all() if card.can_appear_in_rewards]

    assert len(reward_cards) >= 6
    assert "anger" in reward_cards
    assert "pommel_strike" in reward_cards
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/content/test_registry_validation.py -q`

Expected: FAIL with missing reward metadata or insufficient content

- [ ] **Step 3: Write minimal implementation**

在卡牌定义中加入显式字段，例如：

- `can_appear_in_rewards`
- `reward_weight`

并补齐一批最小可玩的铁甲奖励卡内容，确保至少有 6 张以上奖励候选。  
如果同一文件已承载 starter 与奖励卡，则仅增量扩充，不拆文件。

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/content/test_registry_validation.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add content/cards/ironclad_starter.json src/slay_the_spire/data/content/cards/ironclad_starter.json src/slay_the_spire/content/catalog.py src/slay_the_spire/content/registries.py tests/content/test_registry_validation.py
git commit -m "feat: add reward card pool metadata"
```

### Task 8: 把普通战 / 精英战奖励升级为三选一卡牌

**Files:**
- Modify: `src/slay_the_spire/domain/rewards/reward_generator.py`
- Modify: `src/slay_the_spire/use_cases/apply_reward.py`
- Modify: `src/slay_the_spire/domain/models/room_state.py`
- Modify: `tests/use_cases/test_apply_reward.py`
- Modify: `tests/domain/test_state_serialization.py`

- [ ] **Step 1: Write the failing test**

在 `tests/use_cases/test_apply_reward.py` 增加：

```python
from slay_the_spire.domain.rewards.reward_generator import generate_combat_rewards


def test_generate_combat_rewards_returns_three_unique_card_offers() -> None:
    rewards = generate_combat_rewards(
        room_id="act1:r3c0",
        seed=7,
        room_type="combat",
        run_state=_run_state(),
        registry=_content_provider(),
    )

    card_rewards = [reward for reward in rewards if reward.startswith("card_offer:")]
    assert len(card_rewards) == 3
    assert len(set(card_rewards)) == 3


def test_generate_elite_rewards_include_relic_offer() -> None:
    rewards = generate_combat_rewards(
        room_id="act1:r7c0",
        seed=7,
        room_type="elite",
        run_state=_run_state(),
        registry=_content_provider(),
    )

    assert any(reward.startswith("relic:") for reward in rewards)
```

再加一条 `apply_reward` 测试，断言 `card_offer:<card_id>` 被领取后会转成真实 deck 实例。

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/use_cases/test_apply_reward.py tests/domain/test_state_serialization.py -q`

Expected: FAIL because reward generator and reward id schema still是旧版

- [ ] **Step 3: Write minimal implementation**

在 `reward_generator.py` 中：

- `generate_combat_rewards()` 改签名，接收 `room_type`、`run_state`、`registry`
- 用 `rng_for_room(..., category="reward:gold")` 生成金币
- 用 `rng_for_room(..., category="reward:card")` 从奖励卡池无放回抽 3 张
- 用 `rng_for_room(..., category="reward:potion")` 决定是否掉药水
- 精英战额外加入遗物奖励

奖励 id 结构建议改为：

- `gold:<amount>`
- `card_offer:<card_id>`
- `potion:<potion_id>`
- `relic:<relic_id>`

在 `apply_reward.py` 中支持 `card_offer:` 与旧 `card:` 并存，保证兼容。

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/use_cases/test_apply_reward.py tests/domain/test_state_serialization.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/domain/rewards/reward_generator.py src/slay_the_spire/use_cases/apply_reward.py src/slay_the_spire/domain/models/room_state.py tests/use_cases/test_apply_reward.py tests/domain/test_state_serialization.py
git commit -m "feat: add three-card combat rewards"
```

### Task 9: 让奖励菜单支持三选一卡牌与跳过

**Files:**
- Modify: `src/slay_the_spire/app/menu_definitions.py`
- Modify: `src/slay_the_spire/app/session.py`
- Modify: `src/slay_the_spire/use_cases/claim_reward.py`
- Modify: `src/slay_the_spire/adapters/terminal/screens/non_combat.py`
- Modify: `tests/app/test_menu_definitions.py`
- Modify: `tests/adapters/terminal/test_renderer.py`

- [ ] **Step 1: Write the failing test**

在 `tests/app/test_menu_definitions.py` 增加：

```python
def test_build_reward_menu_lists_three_card_offers_and_skip() -> None:
    ...
    lines = format_menu_lines(build_reward_menu(room_state=room_state, registry=_content_provider()))

    assert any("卡牌" in line for line in lines)
    assert any("跳过卡牌" in line for line in lines)
```

再在 `tests/adapters/terminal/test_renderer.py` 增加奖励屏渲染测试，确保 3 张卡都可见。

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/app/test_menu_definitions.py tests/adapters/terminal/test_renderer.py -q`

Expected: FAIL because reward menu still只有旧结构

- [ ] **Step 3: Write minimal implementation**

实现内容：

- `build_reward_menu()` 为每个 `card_offer:` 渲染卡名
- 增加 `skip_card_rewards` 菜单项
- `claim_reward.py` 支持跳过卡牌时仅移除全部 `card_offer:`，保留金币/药水/遗物
- `session.py` 路由新增跳过动作
- `non_combat.py` 奖励屏支持 3 张候选展示

注意不要破坏：

- 事件奖励
- Boss 奖励菜单
- 已有 `claim_all`

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/app/test_menu_definitions.py tests/adapters/terminal/test_renderer.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/app/menu_definitions.py src/slay_the_spire/app/session.py src/slay_the_spire/use_cases/claim_reward.py src/slay_the_spire/adapters/terminal/screens/non_combat.py tests/app/test_menu_definitions.py tests/adapters/terminal/test_renderer.py
git commit -m "feat: support card reward choice menus"
```

### Task 10: 补齐奖励与地图的端到端冒烟路径

**Files:**
- Modify: `tests/e2e/test_single_act_smoke.py`
- Modify: `tests/use_cases/test_room_recovery.py`

- [ ] **Step 1: Write the failing test**

在 `tests/e2e/test_single_act_smoke.py` 增加或改写 1 条路径，断言：

```python
def test_single_act_smoke_shows_three_card_reward_choices_after_combat() -> None:
    session = start_session(seed=5)
    ...
    assert len([reward for reward in session.room_state.rewards if reward.startswith("card_offer:")]) == 3
    _running, session, _message = route_menu_choice("2", session=session)
    _running, session, _message = route_menu_choice("1", session=session)
    assert any(card_id.startswith("anger#") for card_id in session.run_state.deck)
```

另在 `tests/use_cases/test_room_recovery.py` 追加一条恢复测试，断言存档恢复后 card offers 不丢失。

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/e2e/test_single_act_smoke.py tests/use_cases/test_room_recovery.py -q`

Expected: FAIL because奖励结构与路由尚未完成闭环

- [ ] **Step 3: Write minimal implementation**

补齐缺失的恢复与流转细节，使以下路径完整：

- 战斗结算后进入奖励房
- 显示 3 张卡牌候选
- 选择其中 1 张或跳过
- `run_state.deck` 正确写回
- 奖励清空后返回地图

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/e2e/test_single_act_smoke.py tests/use_cases/test_room_recovery.py -q`

Expected: PASS

- [ ] **Step 5: Run final verification**

Run: `uv run pytest`

Expected: 全量 PASS

- [ ] **Step 6: Commit**

```bash
git add tests/e2e/test_single_act_smoke.py tests/use_cases/test_room_recovery.py
git commit -m "test: cover weighted map and combat reward flow"
```

### Task 11: 最终同步与回归检查

**Files:**
- Check: `content/`
- Check: `src/slay_the_spire/data/content/`
- Check: `dist/` (only if packaging is run)

- [ ] **Step 1: Verify content copies stay in sync**

Run: `diff -ru content src/slay_the_spire/data/content`

Expected: 无差异

- [ ] **Step 2: Optional packaging verification**

Run: `uv build`

Expected:

- `dist/` 产出新的 wheel / sdist
- 包内仍包含更新后的内容资源

- [ ] **Step 3: Commit if packaging artifacts are intentionally updated**

```bash
git add dist
git commit -m "build: refresh package artifacts"
```

仅在本仓库确实跟踪 `dist/` 且用户需要时执行。
