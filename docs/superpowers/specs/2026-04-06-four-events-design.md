# 设计文档：四个原版事件实现

**日期**：2026-04-06  
**状态**：待实现

---

## 目标

新增 4 个原版《杀戮尖塔》事件，严格复刻 1 代内容：老乞丐、冒险者尸体、奇怪的铁匠、碎夹薄泥。

---

## 设计决策总览

| 事件 | 英文名 | Act | 关键取舍 |
|---|---|---|---|
| 老乞丐 | Old Beggar | Act 2 | 新增 `min_gold` 出现条件系统 |
| 冒险者尸体 | Dead Adventurer | Act 1 | 简化：去掉概率战斗，只保留搜寻/离开 |
| 奇怪的铁匠 | Ominous Forge | Act 1 | 翻找选项新增 `pain` 诅咒牌 |
| 碎夹薄泥 | Scrap Ooze | Act 1 | 简化：固定消耗 HP 获得遗物，不做概率机制 |

---

## 一、老乞丐 (Old Beggar) — Act 2

### 原版机制
- 出现条件：玩家金币 ≥ 75
- 选项：[施舍金币] 失去 75 金，移除 1 张牌 | [离开] 无效果

### 实现设计

#### 1. 新增 `min_gold` 出现条件字段（系统改动）

**`content/registries.py`**：`WeightedPoolEntry` 增加字段：
```python
@dataclass(frozen=True)
class WeightedPoolEntry:
    member_id: str
    weight: int
    once_per_run: bool = False
    min_gold: int = 0          # 新增：出现所需最低金币
```

**`content/catalog.py`**：`_load_event_pools` 读取 `min_gold`：
```python
min_gold=int(_require_mapping(record, "event").get("min_gold", 0)),
```

**`use_cases/enter_room.py`**：`_build_event_payload` 过滤时加入金币条件：
```python
event_entries = [
    entry
    for entry in registry.event_pool_entries(event_pool_id)
    if not (entry.once_per_run and entry.member_id in run_state.seen_event_ids)
    and run_state.gold >= entry.min_gold        # 新增条件
]
```

#### 2. 事件 JSON（`content/events/act2_events.json`）

```json
{
  "id": "old_beggar",
  "pool_weight": 1,
  "min_gold": 75,
  "text": "一个老乞丐坐在路边，他看起来很虚弱。他向你乞讨，你或许能为他做些什么。",
  "choices": [
    {"id": "give", "label": "施舍金币（失去 75 金，移除 1 张牌）"},
    {"id": "leave", "label": "无视他，离开"}
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

> **注**：`remove_card_selection` 的 `gold_cost` 字段已支持扣金，正好复用。

---

## 二、冒险者尸体 (Dead Adventurer) — Act 1

### 原版机制（完整）
- 每次搜寻有 X% 概率遭遇战斗（概率随搜寻次数递增）；
- 若战斗胜利，可获得遗物；
- 若从未触发战斗，可能直接获得遗物或金币。

### 取舍
概率触发战斗超出当前事件系统边界，**简化为**：搜寻 → 随机获得遗物或金币；离开 → 无效果。

### 实现设计

使用现有 effect 类型：
- 搜寻结果 A：`gain_relic_and_lose_hp`（lose_hp=0，相当于免费获得遗物）—— 不，更好的方式是直接用 `gain_relic_and_lose_hp`，hp_loss=0
- 实际上：现有 `gain_relic_and_lose_hp` 需要指定遗物 ID；随机遗物没有现成 effect 类型。
- **退而求其次**：搜寻 → 获得固定金币（`gain_gold`），或参考其他事件用 `gain_gold_and_lose_hp`（hp=0）。

> **结论**：两个搜寻结果——一个获得金币，一个离开。保留两个选项：[搜寻] 获得 30 金 | [离开]。

### 事件 JSON（`content/events/act1_events.json`）

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
}
```

---

## 三、奇怪的铁匠 (Ominous Forge) — Act 1，一次性

### 原版机制
- [锻造] 升级 1 张牌
- [翻找] 获得遗物"弯曲铁钳"(Warped Tongs) + 诅咒"痛苦"(Pain)
- [离开] 无效果

### 取舍
- `warped_tongs` 遗物已存在（`content/relics/event_relics.json`，状态 `placeholder`）
- `pain` 诅咒不存在 → **新增 `pain` 诅咒牌**（占位实现，无战斗效果）

### 实现设计

#### 1. 新增 `pain` 诅咒（`content/cards/curses.json`）

```json
{
  "id": "pain",
  "name": "痛苦",
  "cost": -1,
  "rarity": "curse",
  "playable": false,
  "effects": [],
  "card_type": "curse",
  "acquisition_tags": ["event", "curse"]
}
```

> 原版痛苦效果（每次打出一张牌受到 1 点伤害）需要战斗 Hook，当前为占位实现，行为与 `doubt` 相同（不可打出，仅占牌组位置）。

#### 2. 事件 JSON（`content/events/act1_events.json`）

```json
{
  "id": "ominous_forge",
  "pool_weight": 1,
  "once_per_run": true,
  "text": "一个古旧的铁匠铺矗立在路边，炉火依然燃烧。一把奇怪的铁钳挂在墙上。",
  "choices": [
    {"id": "forge",  "label": "锻造（升级 1 张牌）"},
    {"id": "rummage","label": "翻找（获得弯曲铁钳，并受到诅咒：痛苦）"},
    {"id": "leave",  "label": "离开"}
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
}
```

---

## 四、碎夹薄泥 (Scrap Ooze) — Act 1

### 原版机制（完整）
- 每次点击消耗一定 HP，X% 概率获得随机遗物；失败可重试直至死亡或获得。

### 取舍
概率+重试机制超出现有系统，**简化为**：消耗固定 HP 直接获得事件遗物（`cultist_headpiece`，"邪教徒头罩"）。

> 原版随机遗物不可静态绑定，选取池中已有的 event 遗物 `cultist_headpiece` 作为固定奖励，风格接近（神秘感）。

### 实现设计

使用现有 `gain_relic_and_lose_hp` effect：

```json
{
  "id": "scrap_ooze",
  "pool_weight": 1,
  "text": "一坨发光的史莱姆趴在废铁堆里，似乎吞噬了某个旅人的遗物。你可以试着将其取回，但这并不安全。",
  "choices": [
    {"id": "reach_in", "label": "伸手取遗物（失去 3 HP，获得遗物）"},
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

---

## 变更联动清单

| 变更项 | 文件 |
|---|---|
| 新增 `pain` 诅咒 | `content/cards/curses.json` |
| 新增 `min_gold` 字段 | `src/slay_the_spire/content/registries.py`（`WeightedPoolEntry`） |
| 读取 `min_gold` | `src/slay_the_spire/content/catalog.py`（`_load_event_pools`） |
| 过滤 `min_gold` | `src/slay_the_spire/use_cases/enter_room.py`（`_build_event_payload`） |
| 新增事件 JSON × 3 | `content/events/act1_events.json`（dead_adventurer、ominous_forge、scrap_ooze） |
| 新增事件 JSON × 1 | `content/events/act2_events.json`（old_beggar） |
| 新增测试 | `tests/use_cases/test_event_actions.py` |
| 新增事件池条件测试 | `tests/use_cases/test_enter_room.py` 或新文件 |

---

## 不在本次范围内

- `warped_tongs` 遗物的实际战斗 Hook 效果（每回合升级手牌）
- `pain` 诅咒的实际战斗 Hook 效果（每次打牌受 1 伤）
- 冒险者尸体的概率战斗机制
- 碎夹薄泥的概率+重试机制
