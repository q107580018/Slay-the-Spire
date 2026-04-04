# 设计规格：遗物效果全量补齐

**日期**：2026-04-03  
**范围**：将当前仓库中“已经可能通过起始、奖励、商店、事件、Boss 或其他现有流程出现，但效果仍未实现或仅部分实现”的遗物，按现有代码架构逐批补成真实行为。  
**策略**：不按稀有度横切，而按触发域分批实现；优先补已有子系统可稳定承载的行为，并把每一批都落成失败测试、最小实现、回归验证和内容状态回收。

---

## 一、目标

- 让当前仓库内所有已经会出现在实际流程中的遗物，不再只是展示文本，而是具备真实运行时行为。
- 把遗物实现入口收敛到现有系统边界内：`apply_reward`、战斗初始化、回合流、出牌/弃牌/抽牌、伤害结算、房间进入、休息点、商店、奖励生成。
- 继续沿用当前仓库的“局部 Hook + 用例层显式逻辑”混合模式，不为了遗物一次性重做全局框架。
- 对于本轮完成真实行为的遗物，同步把 `content/relics/*.json` 中的 `implementation_status` 更新为 `implemented`；若只落地了当前已有系统能支持的部分，则保留 `partial`。
- 同步更新 `README.md`，使其对“当前遗物实现覆盖范围”的表述与代码事实一致。

## 二、非目标

- 不在本轮强制把所有遗物统一重写成纯数据驱动 DSL。
- 不为了少数角色专属遗物先补完整角色子系统；如果当前仓库没有对应系统能力，只做安全落点，不做失真实现。
- 不默认追求原版全部隐藏交互、动画或复杂 UI 选择器；优先保证规则正确、流程可玩、可回归。

## 三、现状

当前仓库的遗物实现状态有几个关键事实：

- `content/relics/` 已经录入大部分原版遗物，但仍有大量条目标记为 `placeholder`，少数为 `partial`。
- 运行时对遗物的承载方式已经是混合模式：
  - 少量行为直接写在用例层，例如 `apply_reward` 已处理 `ectoplasm`、`golden_idol`、`ceramic_fish`。
  - 一部分战斗内行为可以通过 `src/slay_the_spire/domain/hooks/runtime.py` 中的 `trigger_hooks + passive_effects` 注入。
  - 更多复杂行为仍需落在战斗/房间/商店/奖励等显式 use case 中。
- 当前仍有 170 个未完全实现遗物，分布在 starter / common / uncommon / rare / shop / boss / event 多个入口。
- 用户目标不是“挑一批先做”，而是按稳定批次持续推进，最终把“会出现但没效果”的问题整体消掉。

## 四、遗物行为矩阵

完整的遗物行为域映射表见 [relic-behavior-matrix.md](../relic-behavior-matrix.md)。该矩阵覆盖所有 170 个未完成遗物（169 placeholder + 1 partial），按触发域和主入口分组，为后续分批实现提供索引。

## 五、方案比较

### 方案 A：按内容文件分批

- 例如先清 `common_relics.json`，再清 `uncommon_relics.json`。
- 优点：看起来直观，便于对照内容清单。
- 缺点：实现时会在战斗、奖励、商店、休息点之间频繁跳转，同类机制分散，测试也会被拆碎。

### 方案 B：先做一套统一遗物引擎

- 先抽象所有遗物生命周期、状态、选择器和运行时覆写，再把现有逻辑全部迁入。
- 优点：理论上最整齐。
- 缺点：与仓库现状不匹配，风险和工期都过高；而且很多遗物行为仍要依赖现有 use case 事件，不是真正能靠一层引擎吃掉。

### 方案 C：按触发域分批实现（推荐）

- 先把遗物按“获得时立即生效 / 静态属性修饰 / 战斗开始 / 回合流 / 出牌计数 / 弃牌抽牌 / 伤害结算 / 房间进入 / 商店 / 休息点 / 奖励生成 / 地图流程”分组。
- 每一组在同一批中做完：补失败测试、补最小实现、回归验证、更新内容状态。
- 优点：最贴合当前代码结构，测试面清晰，能持续交付。
- 缺点：单个内容文件会经历多次小改动，但这是可接受的。

**结论**：采用方案 C。

## 六、分批设计

### 6.0 闭合通道：当前遗留目标

在批次一的常规推进之外，存在一次专项"闭合通道"（closure pass），目标是把已知可实现、但尚未落地的少量 `on_acquire` 遗物一次性补齐，同时显式锁定哪些复杂遗物留在 `placeholder` 或 `partial`，不在本通道内碰。

**必须在本通道内完成的遗物（closure targets）：**

- `vajra`：获得时 +1 力量（永久）
- `oddly_smooth_stone`：获得时 +1 敏捷（永久）
- `war_paint`：获得时随机升级 2 张技能牌
- `whetstone`：获得时随机升级 2 张攻击牌

这四个遗物的逻辑属于最简单的 `apply_reward` 扩展，无需任何新子系统。

**必须在本通道内显式保留为 `placeholder` 或 `partial` 的复杂遗物：**

- `sacred_bark`：依赖药水效果系统，当前未实现 → 保留 `placeholder`
- `bottled_flame` / `bottled_lightning` / `bottled_tornado`：需要卡牌选择 UI → 保留 `placeholder`
- `orrery`：需要卡牌选择 UI → 保留 `placeholder`
- `prismatic_shard`：需要多角色卡池/遗物池支持 → 保留 `placeholder`

上述复杂遗物不得在无真实行为的情况下被提升为 `implemented`。

### 6.1 批次一：获得时立即生效与静态永久修饰

目标：先补最容易验证、跨系统依赖最小的一批遗物。

范围包括：

- 直接修改最大生命或当前生命：`strawberry`、`pear`、`mango`、`leeches_waffle`
- 直接给金币：`old_coin`
- 直接修改基础属性：`vajra`、`oddly_smooth_stone`、`data_disk`
- 获得时随机升级/复制/变形/移除：`war_paint`、`whetstone`、`dollys_mirror`、`empty_cage`、`astrolabe`、`pandoras_box`
- 改变后续获得牌升级策略：`molten_egg_2`、`toxic_egg_2`、`frozen_egg_2`
- 改变后续获得诅咒或药水容量：`omamori`、`darkstone_periapt`、`potion_belt`

实现落点：

- `src/slay_the_spire/use_cases/apply_reward.py`
- 需要时补辅助函数到相邻 use case，而不是新增大框架。

### 6.2 批次二：战斗开局与回合稳定触发

目标：补所有无需复杂交互、但明显应在战斗生命周期内生效的遗物。

范围包括：

- 战斗开始一次性效果：`anchor`、`bag_of_marbles`、`bag_of_preparation`、`lantern`、`clockwork_souvenir`、`thread_and_needle`、`twisted_funnel`、`ninja_scroll`
- 回合开始/结束固定触发：`mercury_hourglass`、`happy_flower`、`captains_wheel`、`horn_cleat`、`stone_calendar`、`brimstone`
- 每回合额外能量或抽牌：`ring_of_the_snake`、`ring_of_the_serpent`、`pocketwatch`、`art_of_war`
- 战斗结束固定触发：`meat_on_the_bone`、`face_of_cleric`

实现落点：

- 战斗初始化和 `turn_flow`
- 现有 hooks 能覆盖的行为优先用 hooks；需要状态计数的，在 `CombatState` 或相关 runtime state 上做最小增量扩展。

### 6.3 批次三：出牌、抽牌、弃牌、消耗、击杀计数

目标：补依赖战斗中玩家动作统计的遗物。

范围包括：

- 攻击计数：`nunchaku`、`pen_nib`、`kunai`、`shuriken`、`ornamental_fan`
- 总出牌数计数：`ink_bottle`
- 技能/能力/攻击联动：`letter_opener`、`bird_faced_urn`、`mummified_hand`、`orange_pellets`
- 弃牌联动：`tingsha`、`tough_bandages`、`hovering_kite`
- 消耗联动：`charons_ashes`、`dead_branch`
- 敌人死亡联动：`gremlin_horn`
- 手牌打空联动：`unceasing_top`

实现落点：

- `play_card`、抽牌/弃牌相关 use case、敌人死亡结算
- 只增加当前这批需要的最小事件记录，不先抽象全套事件总线。

### 6.4 批次四：伤害修正、状态免疫与受伤触发

目标：补伤害结算与状态增减规则上的遗物。

范围包括：

- 伤害下限/减免：`the_boot`、`torii`、`tungsten_rod`
- 受伤触发：`centennial_puzzle`、`self_forming_clay`、`runic_cube`
- 攻击者反伤/破甲触发：`bronze_scales`、`hand_drill`
- debuff 免疫或修饰：`ginger`、`turnip`、`paper_frog`、`paper_krane`、`champion_belt`、`snecko_skull`
- 条件力量/敏捷：`red_skull`、`duvu_doll`

实现落点：

- 伤害解析、状态附加、敌我 effect 应用入口
- 需要保证与已有正负力量/敏捷、易伤、虚弱结算不冲突。

### 6.5 批次五：奖励、商店、休息点、地图与房间流程

目标：补非战斗系统内的遗物。

范围包括：

- 奖励修饰：`question_card`、`prayer_wheel`、`busted_crown`、`white_beast_statue`、`sozu`
- 商店修饰：`membership_card`、`the_courier`、`smiling_mask`、`meal_ticket`、`maw_bank`
- 休息点新增选项或强化：`dream_catcher`、`regal_pillow`、`eternal_feather`、`girya`、`peace_pipe`、`shovel`
- 地图/房间修饰：`juzu_bracelet`、`tiny_chest`、`matryoshka`、`black_star`、`preserved_insect`、`ssserpent_head`、`wing_boots`

实现落点：

- 奖励生成器、商店生成与购买逻辑、休息点菜单与路由、地图进入与房间解析。

### 6.6 批次六：高复杂度或依赖缺失系统的遗物

目标：最后处理需要额外系统支持的遗物，并显式区分“可完整实现”和“当前系统只能 partial”。

典型范围：

- 充能球/专注/静心/真言相关：`cracked_core`、`frozen_core`、`nuclear_battery`、`runic_capacitor`、`inserter`、`gold_plated_cables`、`damaru`、`teardrop_locket`、`violet_lotus`
- 药水翻倍/无色牌选择/牌费用随机化等高复杂行为：`sacred_bark`、`toolbox`、`snecko_eye`、`chemical_x`
- 需要新 UI 选择流程的瓶装系列或星象仪：`bottled_flame`、`bottled_lightning`、`bottled_tornado`、`orrery`
- 明显依赖当前未落地角色/卡池的遗物：`prismatic_shard` 等

处理原则：

- 当前系统缺少必要子系统时，不做假实现。
- 能安全落地一部分时，将状态标成 `partial`，并在 README 中说明。

## 七、架构约束

### 7.1 继续沿用混合模式

- 简单固定触发可以继续使用 `trigger_hooks + passive_effects`。
- 需要跨阶段记忆、计数器、条件判断或 UI 选择的遗物，放在显式 use case 中实现。
- 不为了“统一感”把所有已有清晰逻辑硬塞进 hook。

### 7.2 遗物状态来源只保留两层

- 静态真源：`content/relics/*.json`
- 运行时状态：`RunState`、`CombatState` 及其已有附属状态

不新增第三套“遗物运行时缓存”文件，除非某一批确实需要最小化持久化字段。

### 7.3 内容状态要说真话

- 真正可用：`implemented`
- 当前已有一部分真实行为，但仍依赖缺失系统：`partial`
- 仍未落地行为：`placeholder`

严禁只改文案或挂空 hook 就把状态改成 `implemented`。

## 八、测试设计

### 8.1 测试分布

- 获得时与非战斗行为：`tests/use_cases/`
- 战斗生命周期与结算：`tests/domain/` 与 `tests/use_cases/`
- 菜单与休息点/商店流程：`tests/app/`、`tests/adapters/presentation/`、必要时 `tests/adapters/textual/`
- 内容状态和元数据回收：`tests/content/test_registry_validation.py`

### 8.2 测试原则

- 每件遗物或每组同机制遗物先写失败测试。
- 尽量测用户可观察行为，不测内部实现细节。
- 同一机制如果由多个遗物复用，先测一个代表遗物，再补一个边界遗物，避免 170 个遗物都写重复测试模板。
- 完成一批后跑该批相关测试，再补一次针对性回归，最后再做一轮更大范围回归。

## 九、README 更新策略

- 当批次一到批次五有实质推进后，更新 `README.md` 中关于遗物实现进度的描述。
- 不写“全部完成”，而是写明“哪些触发域已覆盖，哪些高复杂度遗物仍在继续补齐”。

## 十、风险与应对

- 风险一：批次过大导致回归面失控。
  - 应对：每批内再按 5-15 个遗物拆成小提交，测试通过后再继续。

- 风险二：少数遗物需要持久化或新 UI 流程。
  - 应对：只在真正需要时扩 `RunState` / 菜单状态，并同步测试，不预扩。

- 风险三：部分原版行为依赖当前未实现角色或机制。
  - 应对：显式保留 `partial`，不做伪实现。

## 十一、验收标准

- 玩家在当前仓库可进入的实际流程中，不再拿到“只显示文本但完全没行为”的已承诺实现遗物。
- 每一批已完成遗物都有对应测试覆盖，且测试先失败后通过。
- `content/relics/*.json` 的 `implementation_status` 与代码事实一致。
- `README.md` 对遗物实现覆盖范围的表述与当前仓库一致。
