# 设计规格：红卡（铁甲战士）完整复刻

**日期**：2026-03-31  
**范围**：参考原版《Slay the Spire》1代，将铁甲战士全部红卡复刻进本项目。  
**策略**：完整还原所有机制；先扩展引擎，后补充 JSON 数据。

---

## 一、现状分析

当前已实现 25 张红卡（含升级版共 50 条 JSON 条目）：

- **Basic（3）**：strike, defend, bash
- **Common（10）**：anger, pommel_strike, shrug_it_off, cleave, twin_strike, clothesline, thunderclap, true_grit, armaments, sword_boomerang
- **Uncommon（14）**：whirlwind, inflame, metallicize, hemokinesis, pummel, combust, bloodletting, uppercut, flame_barrier, ghostly_armor, disarm, entrench, battle_trance, terror
- **Rare（4）**：barricade, offering, impervious, demon_form

---

## 二、缺失卡牌清单（43 张）

### Common（10 张）

| ID | 中文名 | 费用 | 效果 |
|---|---|---|---|
| `body_slam` | 身体重击 | 1 | 造成等同于当前格挡的伤害 |
| `clash` | 格斗 | 0 | 造成 14 伤害；**仅当手牌全为攻击牌时可打出** |
| `flex` | 施展 | 0 | 获得 2 力量；回合结束时失去 2 力量 |
| `havoc` | 混乱 | 1 | 打出牌堆顶部的牌（消耗能量） |
| `headbutt` | 头槌 | 1 | 造成 9 伤害；将弃牌堆中的 1 张牌放到牌堆顶 |
| `heavy_blade` | 重刃 | 2 | 造成 14 伤害；力量对此牌的加成是普通的 3 倍 |
| `iron_wave` | 铁波 | 1 | 获得 5 格挡，造成 5 伤害 |
| `perfected_strike` | 精巧打击 | 2 | 造成 6 伤害，每张带有「打击」字样的牌额外 +2 伤害 |
| `warcry` | 战吼 | 0 | 摸 1 张牌；将手中 1 张牌放到牌堆顶；消耗 |
| `wild_strike` | 猛烈打击 | 1 | 造成 12 伤害；将一张「伤口」洗入牌堆 |

### Uncommon（22 张）

| ID | 中文名 | 费用 | 效果 |
|---|---|---|---|
| `blood_for_blood` | 血债血偿 | 4↓ | 造成 18 伤害；每受到 1 次伤害费用 -1 |
| `burning_pact` | 燃烧契约 | 1 | 消耗手中 1 张牌；摸 2 张牌 |
| `carnage` | 大屠杀 | 2 | 造成 20 伤害；**虚空** |
| `dark_embrace` | 黑暗拥抱 | 2 | 能力：每当有牌被消耗，摸 1 张牌 |
| `dropkick` | 飞踢 | 1 | 造成 5 伤害；若目标脆弱，则获得 1 能量并摸 1 张牌 |
| `dual_wield` | 双持 | 1 | 将手中 1 张攻击牌或能力牌复制到手中 |
| `evolve` | 进化 | 1 | 能力：每当摸到状态牌，再摸 1 张牌 |
| `feel_no_pain` | 感受不到痛苦 | 1 | 能力：每当有牌被消耗，获得 3 格挡 |
| `fire_breathing` | 喷火 | 1 | 能力：每当摸到状态牌或诅咒牌，对所有敌人造成 6 伤害 |
| `infernal_blade` | 地狱之刃 | 1 | 将 1 张费用为 0 的随机攻击牌加入手中；消耗 |
| `intimidate` | 恐吓 | 0 | 对所有敌人施加 1 层虚弱；消耗 |
| `power_through` | 勇往直前 | 0 | 将 2 张「伤口」加入手中；获得 15 格挡 |
| `rage` | 狂怒 | 0 | 能力：每当打出攻击牌，获得 3 格挡 |
| `rampage` | 横冲直撞 | 1 | 造成 8 伤害；每次打出此牌，其伤害永久 +5 |
| `reckless_charge` | 鲁莽冲锋 | 0 | 造成 7 伤害；将 1 张「迷糊」洗入牌堆 |
| `rupture` | 破裂 | 1 | 能力：每当你因自己的牌失去 HP，获得 1 力量 |
| `searing_blow` | 灼烧重击 | 2 | 造成 12 伤害；**可无限次升级，每次 +12 伤害** |
| `second_wind` | 第二春 | 1 | 消耗手中所有非攻击牌，每张获得 5 格挡 |
| `seeing_red` | 怒火中烧 | 1 | 获得 2 能量；消耗 |
| `sentinel` | 先锋 | 1 | 获得 5 格挡；若此牌被消耗，获得 2 能量 |
| `sever_soul` | 斩断灵魂 | 2 | 消耗手中所有非攻击牌；造成 16 伤害 |
| `spot_weakness` | 发现弱点 | 1 | 若敌人意图攻击，获得 3 力量 |

### Rare（11 张）

| ID | 中文名 | 费用 | 效果 |
|---|---|---|---|
| `bludgeon` | 重击 | 3 | 造成 32 伤害 |
| `brutality` | 残忍 | 0 | 能力：每回合开始时，失去 1 HP，摸 1 张牌 |
| `double_tap` | 双击 | 1 | 能力：添加 `double_tap` power（amount=1）；每次打出攻击牌时，将该次攻击的所有效果额外入队一次，并将 amount -1；amount 降至 0 时移除该 power |
| `exhume` | 挖掘 | 1 | 将消耗堆中 1 张牌放入手中；消耗 |
| `feed` | 喂食 | 1 | 造成 10 伤害；若致死，永久获得 3 最大 HP；消耗 |
| `fiend_fire` | 魔鬼火焰 | 2 | 消耗手中所有牌；对目标造成 7 × 消耗牌数 的伤害；消耗 |
| `immolate` | 烈焰焚身 | 2 | 对所有敌人造成 21 伤害；将 1 张「燃烧」加入弃牌堆 |
| `juggernaut` | 主宰 | 2 | 能力：每当你获得格挡，对随机敌人造成 5 伤害 |
| `limit_break` | 极限突破 | 1 | 将力量翻倍；消耗 |
| `offering` | *(已实现)* | — | — |
| `reaper` | 死神镰刀 | 2 | 对所有敌人造成 4 伤害；为造成的未被格挡的伤害恢复 HP；消耗 |

---

## 三、引擎层变更

### 3.1 CardDef 新增字段

文件：`src/slay_the_spire/content/registries.py`

```python
on_exhaust_effects: list[JsonDict] = field(default_factory=list)
# 当该牌被消耗（无论何种途径），立即触发这些效果
# 用于：Sentinel（获得能量）

play_condition: str | None = None
# 出牌前的可玩性检查
# "all_attacks_in_hand"：手牌中其他牌全为攻击牌才可出
# 用于：Clash

cost_reducer: str | None = None
# 动态费用减少机制
# "times_hit_this_combat"：本次战斗被打到次数，每次 -1 费用
# 用于：Blood for Blood
```

### 3.2 CombatState 新增字段

文件：`src/slay_the_spire/domain/models/combat_state.py`

```python
times_hit_this_combat: int = 0
# 本次战斗被攻击次数（每次受到来自敌人的 damage 时递增）
# 持久化：to_dict/from_dict 需新增该字段

card_play_data: dict[str, int] = field(default_factory=dict)
# instance_id → play_count（本次战斗出牌次数）
# 用于 Rampage 的永久伤害累积
# 持久化：to_dict/from_dict 需新增该字段
```

### 3.3 新增效果类型

文件：`src/slay_the_spire/domain/effects/effect_types.py`（新增常量）  
文件：`src/slay_the_spire/domain/effects/effect_resolver.py`（新增处理逻辑）  
文件：`src/slay_the_spire/use_cases/play_card.py`（扩展 `_materialize_card_effects`）

#### 在 effect_resolver.py 处理的效果

| 效果类型常量 | JSON 字段 | 逻辑 |
|---|---|---|
| `EFFECT_DAMAGE_EQUAL_TO_BLOCK` | — | 伤害量 = source 当前格挡值 |
| `EFFECT_DAMAGE_WITH_STRENGTH_MULTIPLIER` | `base`, `multiplier` | amount = base + strength × multiplier（代替 +1x） |
| `EFFECT_DAMAGE_PER_STRIKE_IN_DECK` | `base`, `per_strike` | 统计手牌+牌堆+弃牌堆+消耗堆中，card_id 以 `strike` 开头（如 `strike`、`perfected_strike` 本身不算，仅计 `strike` 家族：id == "strike" 或 id 以 "strike_" 开头）的牌数，amount = base + per_strike × count；实际 Slay the Spire 1代规则：统计所有牌区中名称含「打击」的牌（含所有角色的打击变体），代码层面检查 id 是否包含 "strike" 子串，但排除 perfected_strike 自身 |
| `EFFECT_WEAK_ALL_ENEMIES` | `stacks` | 对每个存活敌人施加 stacks 层虚弱 |
| `EFFECT_ADD_CARD_TO_DRAW_PILE` | `card_id`, `count` | 将 count 张 card_id 随机插入牌堆 |
| `EFFECT_ADD_CARDS_TO_HAND` | `card_id`, `count` | 将 count 张 card_id 加入手牌 |
| `EFFECT_EXHAUST_ALL_NON_ATTACKS_GAIN_BLOCK` | `amount_per_card` | 消耗手中所有非攻击牌，每张获得 amount_per_card 格挡 |
| `EFFECT_EXHAUST_ALL_NON_ATTACKS_IN_HAND` | — | 消耗手中所有非攻击牌（不获得格挡） |
| `EFFECT_EXHAUST_ALL_IN_HAND` | — | 消耗手中所有牌，返回消耗数量于 result |
| `EFFECT_DOUBLE_STRENGTH` | — | 当前力量 × 2 |
| `EFFECT_DAMAGE_LIFESTEAL_ALL_ENEMIES` | `amount` | 对所有敌人造成 amount 伤害；为实际造成的未被格挡伤害之和回复 HP |
| `EFFECT_PLAY_TOP_OF_DECK` | — | 将牌堆顶牌移至手中，立即执行（插入 effect_queue 前端） |
| `EFFECT_ADD_RANDOM_ATTACK_ZERO_COST_TO_HAND` | — | 从 registry 中随机选一张攻击牌，费用设为 0，加入手牌 |
| `EFFECT_RAMPAGE_DAMAGE` | `base_amount`, `per_play_bonus` | 查 card_play_data[instance_id] 得出历史出牌次数 N，实际伤害 = base_amount + per_play_bonus × N；随后 card_play_data[instance_id] += 1 |
| `EFFECT_DAMAGE_ON_KILL_GAIN_MAX_HP` | `damage_amount`, `hp_gain` | 造成伤害；若目标因此死亡，player.max_hp += hp_gain（不回血，仅提上限）。max_hp 增加后通过 combat_state 最终持久化到游戏存档，无需额外操作 |
| `EFFECT_SPOT_WEAKNESS_STRENGTH` | `amount` | 若所有存活敌人中存在意图为「攻击」的敌人，获得 amount 力量 |
| `EFFECT_DROPKICK_EFFECT` | `damage`, `bonus_energy`, `bonus_draw` | 造成 damage 伤害；若目标有脆弱，再获得 bonus_energy 能量并摸 bonus_draw 张牌 |

#### 在 play_card.py 的 `_materialize_card_effects` 处理的效果（需要 target_id）

| 效果类型常量 | target_id 来自 | 逻辑 |
|---|---|---|
| `EFFECT_PUT_TOP_OF_DECK_FROM_DISCARD` | 弃牌堆中玩家选择的牌 | 将该牌从弃牌堆移到牌堆顶 |
| `EFFECT_PUT_TOP_OF_DECK_FROM_HAND` | 手牌中玩家选择的牌 | 将该手牌移到牌堆顶（不是当前打出的牌） |
| `EFFECT_SELECT_FROM_EXHAUST_TO_HAND` | 消耗堆中玩家选择的牌 | 将该牌从消耗堆移到手中 |
| `EFFECT_COPY_CARD_TO_HAND` | 手牌中玩家选择的攻击或能力牌 | 将该牌复制一份加入手中 |

以上 4 种交互效果与现有 `exhaust_target_card` / `upgrade_target_card` 处理方式完全一致：由 UI 层传入 `target_id`，在 `_materialize_card_effects` 填充 `target_card_instance_id`。

### 3.4 新增 Power 类型

在 `turn_flow.py` 和 `effect_resolver.py` 中以硬编码方式实现（与 combust / metallicize / flame_barrier 风格一致）。

| Power ID | 触发时机 | 实现位置 |
|---|---|---|
| `dark_embrace` | 任意牌被消耗后 | `effect_resolver.py`：在处理任何消耗效果后检查 |
| `feel_no_pain` | 任意牌被消耗后 | 同上 |
| `evolve` | `_draw_cards` 摸到状态牌时 | `effect_resolver.py`：`_draw_cards` 内 |
| `fire_breathing` | `_draw_cards` 摸到状态/诅咒牌时 | 同上 |
| `rage` | 打出攻击牌后 | `play_card.py`：在卡牌移入弃牌堆后，如为攻击牌则检查 |
| `juggernaut` | 玩家获得格挡时 | `effect_resolver.py`：`EFFECT_BLOCK` 处理后，若 source 为玩家，检查 juggernaut |
| `brutality` | 回合开始时 | `turn_flow.py`：`_apply_start_turn_powers` |
| `rupture` | `EFFECT_LOSE_HP` target 为玩家且 source 为玩家自身卡牌时 | `effect_resolver.py`：`EFFECT_LOSE_HP` 处理后 |
| `double_tap` | 打出攻击牌后 | `play_card.py`：若 double_tap active，额外入队本次出牌的所有效果，然后 amount -= 1（amount 为 0 时移除） |
| `flex_power` | 回合结束时 | `turn_flow.py`：`_active_power_end_turn_effects` |

**Sentinel 的 on_exhaust_effects 触发**：
- 在 `effect_resolver.py` 中，每次处理任何消耗效果时，检查被消耗的牌的 `on_exhaust_effects`，将其入队。
- Sentinel JSON 示例：`"on_exhaust_effects": [{"type": "gain_energy", "amount": 2}]`

### 3.5 play_card.py 其他扩展

**Blood for Blood 动态费用**：
```python
# 在计算 energy_spent 之前
if card_def.cost_reducer == "times_hit_this_combat":
    actual_cost = max(0, card_def.cost - combat_state.times_hit_this_combat)
```

**Clash 可玩性检查**：
```python
if card_def.play_condition == "all_attacks_in_hand":
    other_cards = [c for c in combat_state.hand if c != card_instance_id]
    for c in other_cards:
        if registry.cards().get(card_id_from_instance_id(c)).card_type != "attack":
            raise ValueError("手牌中存在非攻击牌，无法打出格斗。")
```

**times_hit_this_combat 递增**：
在 `effect_resolver.py` 的 `EFFECT_DAMAGE` 处理逻辑中：当 target 为 player，source 为 EnemyState 时，`state.times_hit_this_combat += 1`。

### 3.6 Searing Blow 无限升级

使用链式 `upgrades_to` 机制，预定义 12 个升级档（足够覆盖实际游戏需求）：

| ID | 名称 | 伤害 | upgrades_to |
|---|---|---|---|
| `searing_blow` | 灼烧重击 | 12 | `searing_blow_plus` |
| `searing_blow_plus` | 灼烧重击+ | 24 | `searing_blow_plus2` |
| `searing_blow_plus2` | 灼烧重击+2 | 36 | `searing_blow_plus3` |
| `searing_blow_plus3` | 灼烧重击+3 | 48 | `searing_blow_plus4` |
| `searing_blow_plus4` | 灼烧重击+4 | 60 | `searing_blow_plus5` |
| `searing_blow_plus5` | 灼烧重击+5 | 72 | `searing_blow_plus6` |
| `searing_blow_plus6` | 灼烧重击+6 | 84 | `searing_blow_plus7` |
| `searing_blow_plus7` | 灼烧重击+7 | 96 | `searing_blow_plus8` |
| `searing_blow_plus8` | 灼烧重击+8 | 108 | `searing_blow_plus9` |
| `searing_blow_plus9` | 灼烧重击+9 | 120 | `searing_blow_plus10` |
| `searing_blow_plus10` | 灼烧重击+10 | 132 | `searing_blow_plus11` |
| `searing_blow_plus11` | 灼烧重击+11 | 144 | `searing_blow_plus12` |
| `searing_blow_plus12` | 灼烧重击+12 | 156 | `null` |

---

## 四、卡牌 JSON 数据规范

### 新增文件位置

所有新红卡数据追加到：`content/cards/ironclad_starter.json`  
（已有文件，追加到 `"cards"` 数组中）

### 新字段说明

| JSON 字段 | 类型 | 对应功能 |
|---|---|---|
| `on_exhaust_effects` | list | Sentinel 被消耗时触发 |
| `play_condition` | string \| null | Clash 出牌条件 |
| `cost_reducer` | string \| null | Blood for Blood 动态费用 |

### 代表性卡牌 JSON 示例

```jsonc
// Iron Wave - 用现有效果，无需新引擎支持
{ "id": "iron_wave", "name": "铁波", "cost": 1, "rarity": "common",
  "acquisition_tags": ["combat_reward"],
  "effects": [
    {"type": "block", "amount": 5},
    {"type": "damage", "amount": 5}
  ],
  "upgrades_to": "iron_wave_plus" }

// Body Slam - 新效果类型
{ "id": "body_slam", "name": "身体重击", "cost": 1, "rarity": "common",
  "acquisition_tags": ["combat_reward"],
  "effects": [{"type": "damage_equal_to_block"}],
  "upgrades_to": "body_slam_plus" }

// Clash - 条件出牌
{ "id": "clash", "name": "格斗", "cost": 0, "rarity": "common",
  "play_condition": "all_attacks_in_hand",
  "acquisition_tags": ["combat_reward"],
  "effects": [{"type": "damage", "amount": 14}],
  "upgrades_to": "clash_plus" }

// Flex - Power 型效果
{ "id": "flex", "name": "施展", "cost": 0, "rarity": "common",
  "acquisition_tags": ["combat_reward"],
  "effects": [{"type": "add_power", "power_id": "flex_power", "amount": 2}],
  "upgrades_to": "flex_plus" }

// Dark Embrace - 能力牌
{ "id": "dark_embrace", "name": "黑暗拥抱", "cost": 2, "rarity": "uncommon",
  "acquisition_tags": ["combat_reward"],
  "effects": [{"type": "add_power", "power_id": "dark_embrace", "amount": 1}],
  "upgrades_to": "dark_embrace_plus" }

// Sentinel - on_exhaust_effects
{ "id": "sentinel", "name": "先锋", "cost": 1, "rarity": "uncommon",
  "acquisition_tags": ["combat_reward"],
  "effects": [{"type": "block", "amount": 5}],
  "on_exhaust_effects": [{"type": "gain_energy", "amount": 2}],
  "upgrades_to": "sentinel_plus" }

// Blood for Blood - 动态费用
{ "id": "blood_for_blood", "name": "血债血偿", "cost": 4, "rarity": "uncommon",
  "cost_reducer": "times_hit_this_combat",
  "acquisition_tags": ["combat_reward"],
  "effects": [{"type": "damage", "amount": 18}],
  "upgrades_to": "blood_for_blood_plus" }

// Rampage - 累积伤害
{ "id": "rampage", "name": "横冲直撞", "cost": 1, "rarity": "uncommon",
  "acquisition_tags": ["combat_reward"],
  "effects": [{"type": "rampage_damage", "base_amount": 8, "per_play_bonus": 5}],
  "upgrades_to": "rampage_plus" }
```

---

## 五、测试规范

### 新增单元测试

| 文件 | 测试内容 |
|---|---|
| `tests/domain/test_effect_resolver.py` | 每个新 effect 类型的基本行为 |
| `tests/domain/test_turn_flow.py` | 每个新 power 类型的触发时机 |
| `tests/domain/test_play_card.py`（新建） | Clash 条件检查、Blood for Blood 动态费用、Double Tap 双击 |
| `tests/content/test_registry_validation.py` | 已有注册表验证，新卡加入后自动覆盖 |

### 测试样例

```python
# dark_embrace: 被消耗时摸牌
def test_dark_embrace_draws_on_exhaust():
    state = make_combat_state_with_power("dark_embrace", amount=1)
    state.hand.append("bash#1")
    state.effect_queue.append({"type": "exhaust_random_hand", "count": 1, ...})
    resolve_effect_queue(state)
    # 手牌应该多一张（摸了一张）

# Clash: 手牌有非攻击牌时无法打出
def test_clash_blocked_when_non_attack_in_hand():
    # hand: ["clash#1", "defend#1"]
    # 应 raise ValueError

# Rampage: 每次打出伤害 +5
def test_rampage_damage_accumulates():
    # 第1次打出: 8 伤害
    # 第2次打出: 13 伤害
    # 第3次打出: 18 伤害
```

---

## 六、实现顺序（引擎先，数据后）

1. **CardDef / CombatState 数据模型扩展**（新字段 + to_dict/from_dict）
2. **effect_types.py**：新增 ~20 个效果类型常量
3. **effect_resolver.py**：实现所有新效果处理逻辑
4. **turn_flow.py**：brutality、flex_power、times_hit_this_combat 递增
5. **play_card.py**：交互效果 materialize、Clash 检查、Blood for Blood 动态费用、Rage / Double Tap / Rupture 触发
6. **ironclad_starter.json**：追加全部 43 × 2 = 86 条卡牌定义
7. **单元测试**：覆盖所有新效果和新 power
8. **全量测试**：`uv run pytest` 确保无回归

---

## 七、不在本次范围内

- Textual UI 层对交互效果（Headbutt/Warcry/Dual Wield/Exhume）的选卡界面升级（需单独迭代）
- 2代卡牌或跨角色内容
- 存档兼容性处理（当前开发阶段不需要兼容旧存档）
