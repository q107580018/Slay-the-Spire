# Hexaghost Boss Design

Date: 2026-03-26
Status: Draft for review

## 1. 背景

当前项目的单 Act 主循环已经基本打通：

- `shop / rest / reward / boss / victory terminal` 已接入真实流程
- 终端菜单、inspect、存读档和 E2E 冒烟测试都能覆盖一整局 run

现阶段的主要短板不再是房间流转，而是 Boss 内容仍然过于薄弱：

- `act1` 的 `boss_pool_id` 仍复用 `act1_elites`
- 当前 Boss 房实际上只是在打 `lagavulin`
- 玩家无法感知“精英战”与“Boss 战”在内容层级上的区别

因此，下一步应按 roadmap 进入 Phase 2：为 Act 1 提供独立 Boss 内容，并先落地 1 个低保真但可玩的原版 Boss。

## 2. 目标

- 为 `act1` 提供独立的 Boss 敌人池，不再复用精英池
- 低保真复刻 1 个原版 Act 1 Boss：`Hexaghost`
- 让 `Hexaghost` 明确区别于当前精英：
  - 有首轮特殊招式
  - 有 `Burn` 塞牌压力
  - 有明显的 Boss 循环节奏
- 保持当前内容驱动结构，不为 1 个 Boss 引入过重的新框架
- 保持 Boss 战后的奖励与胜利终局衔接不回退

## 3. 非目标

- 不追求原版 `Hexaghost` 的逐回合完全等值复刻
- 不在本轮实现多个 Boss
- 不重写敌人 AI 系统
- 不引入完整的状态牌自动时点框架
- 不顺手扩展多角色、多 Act 或更复杂关键词系统

## 4. 设计选择

本次采用：

- **内容驱动 + 小幅扩展战斗效果层**

不采用：

- 在 `turn_flow` 中为 `hexaghost` 写整块硬编码专用逻辑
- 提前抽象一套更重的通用敌人脚本引擎

原因：

- 当前项目已经以 `move_table + intent_policy` 驱动敌人行为
- `Hexaghost` 所需新增能力集中在两个点：
  - `Burn` 塞牌
  - `divider` 的动态多段攻击
- 这两个点都可以通过小幅扩展现有战斗层解决，不需要推翻当前结构

## 5. 范围

### In Scope

- 新增独立 Boss 池 `act1_bosses`
- 新增 Boss 内容 `hexaghost`
- 新增状态牌 `burn`
- 新增通用效果 `add_card_to_discard`
- 在回合结束阶段结算手中 `burn` 的伤害
- 在敌人回合支持 `divider` 的动态多段伤害展开
- 同步补齐内容、领域、E2E 测试

### Out of Scope

- `Hexaghost` 原版全部招式、动画、视觉表现
- 更复杂的 Boss 预告或多轮意图展示
- `Burn` 的更高保真原版细节
- 其他原版 Act 1 Boss

## 6. 内容设计

### 6.1 Boss 敌人池

新增：

- `content/enemies/act1_bosses.json`
- `src/slay_the_spire/data/content/enemies/act1_bosses.json`

`act1` 的 `boss_pool_id` 从：

- `act1_elites`

改为：

- `act1_bosses`

### 6.2 Hexaghost

`Hexaghost` 采用 `scripted` 招式表，低保真版本使用以下循环：

1. `divider`
2. `sear`
3. `tackle`
4. `inferno`
5. `tackle`
6. 回到 `sear` 循环

目的不是复刻原版每一步细节，而是稳定表达三个辨识点：

- 开场伤害取决于玩家当前生命
- 中段会持续往牌堆塞 `Burn`
- 招式节奏明显不同于单一重击精英

### 6.3 Burn

新增卡牌 `burn`，作为不可主动打出的状态牌：

- 进入战斗牌堆循环
- 能被洗牌、抽到手、弃置
- 对玩家形成持续负面压力

`burn` 默认不出现在普通奖励和商店池中，只作为 Boss 机制产物存在。

## 7. 规则设计

### 7.1 Divider

`divider` 为 6 段攻击，单段伤害按玩家当前生命分档：

- `<= 24`：每段 `1`
- `25-48`：每段 `2`
- `49-72`：每段 `3`
- `>= 73`：每段 `4`

这是明确的低保真实现取舍：

- 保留“按当前生命缩放”的核心识别度
- 不追求原版精确公式
- 规则必须稳定、可测试、可从内容层触发

### 7.2 Sear / Inferno / Tackle

- `sear`：单次伤害，并向玩家弃牌堆加入 `1` 张 `burn`
- `inferno`：不直接造成伤害，向玩家弃牌堆加入多张 `burn`
- `tackle`：稳定单次高伤攻击

这样可以形成：

- 立即伤害
- 延迟牌堆压力
- 回合间资源污染

三种不同的 Boss 压力来源。

### 7.3 Burn 结算

`burn` 的低保真规则为：

- 若玩家在回合结束时手中有 `burn`
- 每张 `burn` 对玩家造成固定伤害
- 然后这些 `burn` 跟随正常弃牌流程进入弃牌堆

本轮建议固定为：

- 每张 `burn` 在回合结束造成 `2` 点伤害

这是为了避免一次性引入更复杂的自动触发时点，同时仍让 `Burn` 真正影响抽牌与回合规划。

## 8. 架构改动

### 8.1 内容层

修改：

- `content/acts/act1_map.json`
- `src/slay_the_spire/data/content/acts/act1_map.json`

新增：

- `content/enemies/act1_bosses.json`
- `src/slay_the_spire/data/content/enemies/act1_bosses.json`

并在现有卡牌内容中新增 `burn` 的双份定义。

### 8.2 效果层

新增通用效果类型：

- `add_card_to_discard`

语义：

- 根据 `card_id` 生成新的实例 ID
- 将该卡牌实例加入玩家弃牌堆

该效果设计成通用能力，而不是 `Hexaghost` 专属分支，便于后续其他敌人、事件或遗物复用。

### 8.3 回合流转

在 `end_turn` 流程中补一个固定阶段：

1. 识别玩家手牌中的 `burn`
2. 结算对应伤害
3. 再执行正常弃牌
4. 再继续敌方回合与下回合开始逻辑

这要求实现顺序明确，避免 `burn` 因为先弃牌而漏结算。

### 8.4 敌人回合

现有 `move_table` 保持不变，只补两类小扩展：

- `divider`：从招式定义展开为动态多段伤害效果
- `add_card_to_discard`：通过通用效果解析器把 `burn` 放进弃牌堆

不新增新的 `intent_policy`。

## 9. 测试策略

### 9.1 内容测试

- `act1` 的 `boss_pool_id` 指向独立 Boss 池
- `hexaghost` 与 `burn` 能被内容目录正常加载
- 双份内容目录保持同步

### 9.2 领域测试

- `divider` 在不同玩家 HP 档位下产生正确多段伤害
- `sear` 会把 `burn` 放入弃牌堆
- `inferno` 会放入多张 `burn`
- 手牌中的 `burn` 会在回合结束时正确掉血

### 9.3 流程测试

- Boss 房实际读取独立 Boss 池，而不是 `lagavulin`
- 打赢 `Hexaghost` 后仍进入现有奖励与胜利终局
- 现有单 Act E2E 冒烟不回退

## 10. 验收标准

- `boss_pool_id` 不再复用 `act1_elites`
- `Hexaghost` 能在 Boss 房真实出现
- 玩家能感知其与精英明显不同：
  - 有首轮特殊伤害
  - 会往牌堆塞 `Burn`
  - 有 Boss 节奏而非单招循环
- `Burn` 能真实进入牌堆、被抽到并在回合结束造成伤害
- 全量测试保持通过

## 11. 风险与取舍

### 11.1 Burn 时点仍是简化版

本轮 `Burn` 只在回合结束时结算，不追求原版所有细节。这是为了控制复杂度，并优先把“Boss 污染牌堆”的核心体验做出来。

### 11.2 Divider 不是原版精确公式

本轮采用分档规则而非原版精确算法，但保留了“玩家当前生命越高，首轮越疼”的关键体验。

### 11.3 需要严格保持双份内容同步

任何内容变更都必须同时改：

- `content/`
- `src/slay_the_spire/data/content/`

否则本地开发、默认运行和打包结果会出现不一致。
