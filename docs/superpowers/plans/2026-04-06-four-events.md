# Four New Events Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add four original Slay the Spire events (老乞丐, 冒险者尸体, 奇怪的铁匠, 碎夹薄泥) with their correct mechanics.

**Architecture:** Content-only changes for three events (JSON + new curse card); one system change adds a `min_gold` appearance-condition field to `WeightedPoolEntry` and the event-sampling filter. All tests follow the TDD pattern established in `test_event_actions.py` and `test_enter_room.py`.

**Tech Stack:** Python 3.12, pytest, uv, JSON content files.

---

## File Map

| Action | Path |
|---|---|
| Modify | `content/cards/curses.json` |
| Modify | `content/events/act1_events.json` |
| Modify | `content/events/act2_events.json` |
| Modify | `src/slay_the_spire/content/catalog.py` |
| Modify | `src/slay_the_spire/use_cases/enter_room.py` |
| Modify | `tests/use_cases/test_event_actions.py` |
| Modify | `tests/use_cases/test_enter_room.py` |

---

## Task 1: 新增 `pain` 诅咒牌

**Files:**
- Modify: `content/cards/curses.json`
- Test: `tests/content/test_registry_validation.py` (existing validation tests auto-cover new cards)

- [ ] **Step 1: 在 `content/cards/curses.json` 中新增 `pain` 诅咒**

  打开 `content/cards/curses.json`，在 `injury` 条目之后插入：

  ```json
  {
    "id": "pain",
    "name": "痛苦",
    "cost": -1,
    "rarity": "curse",
    "playable": false,
    "effects": [],
    "card_type": "curse",
    "acquisition_tags": [
      "event",
      "curse"
    ]
  },
  ```

  完整位置：现有 `injury` 对象（id 为 `"injury"`，约第 17-28 行）之后，`burn` 对象之前。

- [ ] **Step 2: 运行内容校验测试，确认通过**

  ```bash
  uv run pytest tests/content/ -v
  ```

  预期：全部 PASS。

- [ ] **Step 3: 提交**

  ```bash
  git add content/cards/curses.json
  git commit -m "feat: add pain curse card (placeholder, no combat hook yet)"
  ```

---

## Task 2: 新增 `min_gold` 出现条件系统

**Files:**
- Modify: `src/slay_the_spire/content/catalog.py`（`WeightedPoolEntry` 和 `_load_event_pools`）
- Modify: `src/slay_the_spire/use_cases/enter_room.py`（`_build_event_payload`）
- Test: `tests/use_cases/test_enter_room.py`

### Step 1: 写失败测试

- [ ] **Step 1: 在 `tests/use_cases/test_enter_room.py` 末尾添加 `min_gold` 条件测试**

  找到文件末尾（当前最后一个测试函数结束后），追加：

  ```python
  def test_enter_event_room_skips_events_when_gold_below_min_gold() -> None:
      # old_beggar requires min_gold=75; run_state has gold=50 → should be skipped
      room_state = enter_room(
          _run_state(seed=37, gold=50),
          _act_state(node_id="r1c0", room_type="event"),
          "r1c0",
          _content_provider(),
      )

      assert room_state.payload["event_id"] != "old_beggar"


  def test_enter_event_room_includes_event_when_gold_meets_min_gold() -> None:
      # Force a state where only old_beggar would be selected by marking all others seen.
      # We use a run_state with enough gold and all other act2 events already seen.
      from slay_the_spire.domain.models.act_state import ActNodeState, ActState

      run_state = _run_state(
          seed=37,
          gold=75,
          seen_event_ids=["ancient_writing", "masked_bandits", "forgotten_altar"],
          current_act_id="act2",
      )
      act_state = ActState(
          act_id="act2",
          nodes={
              "r1c0": ActNodeState(
                  node_id="r1c0",
                  room_type="event",
                  next_node_ids=["r2c0"],
                  is_resolved=False,
              )
          },
          room_payloads={},
          combat_count=0,
          boss_id="hexaghost",
      )
      room_state = enter_room(run_state, act_state, "r1c0", _content_provider())

      assert room_state.payload["event_id"] == "old_beggar"
  ```

  > **Note:** `_run_state` in `test_enter_room.py` currently has fixed signature. Check that it accepts `gold`, `seen_event_ids`, and `current_act_id` kwargs — if not, use `replace()` instead.
  >
  > Look at the existing `_run_state` helper in `test_enter_room.py` to confirm. If it only accepts `seed`, rewrite the test body using `replace(base, gold=75, ...)`.

- [ ] **Step 2: 运行测试，确认失败**

  ```bash
  uv run pytest tests/use_cases/test_enter_room.py::test_enter_event_room_skips_events_when_gold_below_min_gold tests/use_cases/test_enter_room.py::test_enter_event_room_includes_event_when_gold_meets_min_gold -v
  ```

  预期：FAIL（`old_beggar` 尚不在池中，测试暂无意义或 KeyError）。  
  此步骤只是确认测试文件语法无误、测试确实运行。

### Step 2: 实现

- [ ] **Step 3: 在 `src/slay_the_spire/content/catalog.py` 中给 `WeightedPoolEntry` 增加 `min_gold` 字段**

  找到 `WeightedPoolEntry` 定义（约第 56-60 行）：

  ```python
  @dataclass(slots=True, frozen=True)
  class WeightedPoolEntry:
      member_id: str
      weight: int
      once_per_run: bool = False
  ```

  改为：

  ```python
  @dataclass(slots=True, frozen=True)
  class WeightedPoolEntry:
      member_id: str
      weight: int
      once_per_run: bool = False
      min_gold: int = 0
  ```

- [ ] **Step 4: 在 `_load_event_pools` 中读取 `min_gold`**

  找到 `_load_event_pools` 中构建事件 `WeightedPoolEntry` 的代码（约第 154-158 行）：

  ```python
  WeightedPoolEntry(
      member_id=_require_str(_require_mapping(record, "event").get("id"), "event.id"),
      weight=int(_require_mapping(record, "event").get("pool_weight", 1)),
      once_per_run=bool(_require_mapping(record, "event").get("once_per_run", False)),
  )
  ```

  改为：

  ```python
  WeightedPoolEntry(
      member_id=_require_str(_require_mapping(record, "event").get("id"), "event.id"),
      weight=int(_require_mapping(record, "event").get("pool_weight", 1)),
      once_per_run=bool(_require_mapping(record, "event").get("once_per_run", False)),
      min_gold=int(_require_mapping(record, "event").get("min_gold", 0)),
  )
  ```

- [ ] **Step 5: 在 `_build_event_payload` 中增加 `min_gold` 过滤**

  找到 `enter_room.py` 中的 `_build_event_payload`（约第 453-474 行）：

  ```python
  event_entries = [
      entry
      for entry in registry.event_pool_entries(event_pool_id)
      if not (entry.once_per_run and entry.member_id in run_state.seen_event_ids)
  ]
  ```

  改为：

  ```python
  event_entries = [
      entry
      for entry in registry.event_pool_entries(event_pool_id)
      if not (entry.once_per_run and entry.member_id in run_state.seen_event_ids)
      and run_state.gold >= entry.min_gold
  ]
  ```

- [ ] **Step 6: 运行全部测试，确认无回归**

  ```bash
  uv run pytest tests/ -v
  ```

  预期：全部现有测试 PASS（新增两个测试暂时可能 FAIL，因为 `old_beggar` 还未加入 JSON，继续即可）。

- [ ] **Step 7: 提交**

  ```bash
  git add src/slay_the_spire/content/catalog.py src/slay_the_spire/use_cases/enter_room.py tests/use_cases/test_enter_room.py
  git commit -m "feat: add min_gold appearance condition to event pool entries"
  ```

---

## Task 3: 新增 Act 1 三个事件 JSON

**Files:**
- Modify: `content/events/act1_events.json`
- Test: `tests/use_cases/test_event_actions.py`

### Step 1: 写失败测试

- [ ] **Step 1: 在 `test_event_actions.py` 末尾追加三个新事件的测试**

  ```python
  # ── 冒险者尸体 ───────────────────────────────────────────────────────────────

  def test_dead_adventurer_search_grants_gold() -> None:
      session = _event_session("dead_adventurer")

      _running, session, _message = route_menu_choice("1", session=session)
      _running, session, _message = route_menu_choice("1", session=session)

      assert session.room_state.is_resolved is True
      assert session.run_state.gold == 129   # 99 + 30
      assert session.run_state.current_hp == 80


  def test_dead_adventurer_leave_does_nothing() -> None:
      session = _event_session("dead_adventurer")

      _running, session, _message = route_menu_choice("1", session=session)
      _running, session, _message = route_menu_choice("2", session=session)

      assert session.room_state.is_resolved is True
      assert session.run_state.gold == 99
      assert session.run_state.current_hp == 80


  # ── 奇怪的铁匠 ───────────────────────────────────────────────────────────────

  def test_ominous_forge_forge_enters_upgrade_subflow() -> None:
      session = _event_session("ominous_forge")

      _running, session, _message = route_menu_choice("1", session=session)
      _running, session, _message = route_menu_choice("1", session=session)

      assert session.menu_state.mode == "event_upgrade_card"
      assert session.room_state.stage == "select_event_upgrade_card"


  def test_ominous_forge_rummage_grants_warped_tongs_and_pain_curse() -> None:
      session = _event_session("ominous_forge")

      _running, session, _message = route_menu_choice("1", session=session)
      _running, session, _message = route_menu_choice("2", session=session)

      assert session.room_state.is_resolved is True
      assert "warped_tongs" in session.run_state.relics
      assert any(c.startswith("pain#") for c in session.run_state.deck)


  def test_ominous_forge_leave_does_nothing() -> None:
      session = _event_session("ominous_forge")

      _running, session, _message = route_menu_choice("1", session=session)
      _running, session, _message = route_menu_choice("3", session=session)

      assert session.room_state.is_resolved is True
      assert "warped_tongs" not in session.run_state.relics
      assert not any(c.startswith("pain#") for c in session.run_state.deck)


  # ── 碎夹薄泥 ─────────────────────────────────────────────────────────────────

  def test_scrap_ooze_reach_in_grants_relic_and_loses_hp() -> None:
      session = _event_session("scrap_ooze")

      _running, session, _message = route_menu_choice("1", session=session)
      _running, session, _message = route_menu_choice("1", session=session)

      assert session.room_state.is_resolved is True
      assert "cultist_headpiece" in session.run_state.relics
      assert session.run_state.current_hp == 77   # 80 - 3


  def test_scrap_ooze_leave_does_nothing() -> None:
      session = _event_session("scrap_ooze")

      _running, session, _message = route_menu_choice("1", session=session)
      _running, session, _message = route_menu_choice("2", session=session)

      assert session.room_state.is_resolved is True
      assert "cultist_headpiece" not in session.run_state.relics
      assert session.run_state.current_hp == 80
  ```

- [ ] **Step 2: 运行测试，确认失败**

  ```bash
  uv run pytest tests/use_cases/test_event_actions.py::test_dead_adventurer_search_grants_gold tests/use_cases/test_event_actions.py::test_ominous_forge_rummage_grants_warped_tongs_and_pain_curse tests/use_cases/test_event_actions.py::test_scrap_ooze_reach_in_grants_relic_and_loses_hp -v
  ```

  预期：FAIL（事件 ID 不存在）。

### Step 2: 实现

- [ ] **Step 3: 在 `content/events/act1_events.json` 的 `events` 数组末尾追加三个事件**

  打开 `content/events/act1_events.json`，在最后一个事件 `}` 之后、外层 `]` 之前插入（用逗号分隔）：

  ```json
  {
    "id": "dead_adventurer",
    "pool_weight": 1,
    "text": "一具冒险者的尸体躺在路边，看起来死去不久。也许他身上还有些值钱的东西。",
    "choices": [
      {"id": "search", "label": "搜寻尸体（获得 30 金）"},
      {"id": "leave",  "label": "绕道而行，离开"}
    ],
    "outcomes": [
      {
        "choice_id": "search",
        "result": "dead_adventurer_search",
        "result_text": "你翻遍了尸体，找到了一些金币。",
        "effect": {"type": "gain_gold", "gain_gold": 30}
      },
      {
        "choice_id": "leave",
        "result": "nothing",
        "result_text": "你不想打扰逝者，默默离开。",
        "effect": {"type": "nothing"}
      }
    ]
  },
  {
    "id": "ominous_forge",
    "pool_weight": 1,
    "once_per_run": true,
    "text": "一个古旧的铁匠铺矗立在路边，炉火依然燃烧。一把弯曲的铁钳挂在墙上。",
    "choices": [
      {"id": "forge",   "label": "锻造（升级 1 张牌）"},
      {"id": "rummage", "label": "翻找（获得弯曲铁钳，并受到诅咒：痛苦）"},
      {"id": "leave",   "label": "离开"}
    ],
    "outcomes": [
      {
        "choice_id": "forge",
        "result": "ominous_forge_forge",
        "result_text": "熊熊炉火让你的武器更加锋利。",
        "effect": {"type": "upgrade_card_selection"}
      },
      {
        "choice_id": "rummage",
        "result": "ominous_forge_rummage",
        "result_text": "你抓起那把弯曲铁钳，却感到一阵莫名的痛苦袭来。",
        "effect": {"type": "gain_relic_and_add_curse", "relic_id": "warped_tongs", "curse_id": "pain"}
      },
      {
        "choice_id": "leave",
        "result": "nothing",
        "result_text": "你感觉这里有些不对劲，决定离开。",
        "effect": {"type": "nothing"}
      }
    ]
  },
  {
    "id": "scrap_ooze",
    "pool_weight": 1,
    "text": "一坨发光的史莱姆趴在废铁堆里，似乎吞噬了某个旅人的遗物。你可以试着将其取回，但这并不安全。",
    "choices": [
      {"id": "reach_in", "label": "伸手取遗物（失去 3 HP，获得邪教徒头罩）"},
      {"id": "leave",    "label": "不值得冒险，离开"}
    ],
    "outcomes": [
      {
        "choice_id": "reach_in",
        "result": "scrap_ooze_reach",
        "result_text": "黏液灼烧了你的手臂，但你成功取出了一件遗物。",
        "effect": {"type": "gain_relic_and_lose_hp", "relic_id": "cultist_headpiece", "lose_hp": 3}
      },
      {
        "choice_id": "leave",
        "result": "nothing",
        "result_text": "你决定不冒这个险，绕道而行。",
        "effect": {"type": "nothing"}
      }
    ]
  }
  ```

- [ ] **Step 4: 运行 Task 3 全部测试**

  ```bash
  uv run pytest tests/use_cases/test_event_actions.py -k "dead_adventurer or ominous_forge or scrap_ooze" -v
  ```

  预期：全部 PASS。

- [ ] **Step 5: 运行全部测试，确认无回归**

  ```bash
  uv run pytest tests/ -v
  ```

  预期：全部 PASS（除 `old_beggar` 相关测试，因 Task 4 尚未完成）。

- [ ] **Step 6: 提交**

  ```bash
  git add content/events/act1_events.json tests/use_cases/test_event_actions.py
  git commit -m "feat: add dead_adventurer, ominous_forge, scrap_ooze events (act1)"
  ```

---

## Task 4: 新增 Act 2 老乞丐事件 JSON

**Files:**
- Modify: `content/events/act2_events.json`
- Test: `tests/use_cases/test_event_actions.py`（已在 Task 3 测试文件中追加，这里只补老乞丐测试）

### Step 1: 写失败测试

- [ ] **Step 1: 在 `test_event_actions.py` 末尾追加老乞丐测试**

  ```python
  # ── 老乞丐 ────────────────────────────────────────────────────────────────────

  def test_old_beggar_give_spends_75_gold_and_enters_remove_subflow() -> None:
      session = _event_session("old_beggar")

      _running, session, _message = route_menu_choice("1", session=session)
      _running, session, _message = route_menu_choice("1", session=session)

      # gold_cost=75 triggers remove_card_selection subflow before resolving
      assert session.menu_state.mode == "event_remove_card"
      assert session.room_state.stage == "select_event_remove_card"
      assert session.run_state.gold == 24   # 99 - 75


  def test_old_beggar_leave_does_nothing() -> None:
      session = _event_session("old_beggar")

      _running, session, _message = route_menu_choice("1", session=session)
      _running, session, _message = route_menu_choice("2", session=session)

      assert session.room_state.is_resolved is True
      assert session.run_state.gold == 99
  ```

  > **Note:** `_event_session` sets `room_id` with `act1:` prefix — for `old_beggar` the prefix is cosmetic and doesn't affect routing. The test is valid as-is.

- [ ] **Step 2: 运行测试，确认失败**

  ```bash
  uv run pytest tests/use_cases/test_event_actions.py::test_old_beggar_give_spends_75_gold_and_enters_remove_subflow tests/use_cases/test_event_actions.py::test_old_beggar_leave_does_nothing -v
  ```

  预期：FAIL（事件 ID 不存在）。

### Step 2: 实现

- [ ] **Step 3: 在 `content/events/act2_events.json` 的 `events` 数组末尾追加老乞丐事件**

  打开 `content/events/act2_events.json`，在最后一个事件 `}` 之后、外层 `]` 之前插入：

  ```json
  {
    "id": "old_beggar",
    "pool_weight": 1,
    "min_gold": 75,
    "text": "一个老乞丐坐在路边，衣衫褴褛，神情憔悴。他向你伸出手，希望你能施舍一些金币。",
    "choices": [
      {"id": "give",  "label": "施舍金币（失去 75 金，移除 1 张牌）"},
      {"id": "leave", "label": "无视他，继续前行"}
    ],
    "outcomes": [
      {
        "choice_id": "give",
        "result": "old_beggar_give",
        "result_text": "老乞丐接过金币，感激地帮你从牌组里剔去一张你不需要的牌。",
        "effect": {"type": "remove_card_selection", "gold_cost": 75}
      },
      {
        "choice_id": "leave",
        "result": "nothing",
        "result_text": "你无视了他，继续前行。",
        "effect": {"type": "nothing"}
      }
    ]
  }
  ```

- [ ] **Step 4: 运行 Task 4 全部测试**

  ```bash
  uv run pytest tests/use_cases/test_event_actions.py -k "old_beggar" -v
  ```

  预期：全部 PASS。

- [ ] **Step 5: 运行全部测试，确认无回归**

  ```bash
  uv run pytest tests/ -v
  ```

  预期：全部 PASS。

- [ ] **Step 6: 运行内容校验测试**

  ```bash
  uv run pytest tests/content/ -v
  ```

  预期：全部 PASS。

- [ ] **Step 7: 运行 enter_room 的 min_gold 测试**

  ```bash
  uv run pytest tests/use_cases/test_enter_room.py -k "min_gold" -v
  ```

  预期：全部 PASS（Task 2 的测试此时也应通过，因为 `old_beggar` 已加入 JSON）。

- [ ] **Step 8: 提交**

  ```bash
  git add content/events/act2_events.json tests/use_cases/test_event_actions.py
  git commit -m "feat: add old_beggar event (act2) with min_gold=75 appearance condition"
  ```

---

## Self-Review

**Spec coverage：**
- ✅ `pain` 诅咒 → Task 1
- ✅ `min_gold` 系统 → Task 2
- ✅ `dead_adventurer` → Task 3
- ✅ `ominous_forge` → Task 3
- ✅ `scrap_ooze` → Task 3
- ✅ `old_beggar` → Task 4
- ✅ `min_gold` 过滤测试 → Task 2 Step 1

**Placeholder scan：** 无 TBD / TODO。

**Type consistency：**
- `WeightedPoolEntry.min_gold: int = 0` — 在 catalog.py（Task 2 Step 3）和 enter_room.py（Task 2 Step 5）中一致引用。
- `remove_card_selection` / `gain_relic_and_lose_hp` / `gain_relic_and_add_curse` / `gain_gold` / `upgrade_card_selection` — 均为已有 effect 类型，无新增。
