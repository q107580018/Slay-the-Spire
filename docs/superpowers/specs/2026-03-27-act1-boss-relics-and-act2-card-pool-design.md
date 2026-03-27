# Act1 Boss Relics And Act2 Card Pool Design

Date: 2026-03-27
Status: Draft for review

## 1. 背景

当前项目已经具备两幕可玩流程，但进入 `act2` 后，现有资源明显不足以支撑稳定通关：

- `act1` Boss 奖励里的遗物池仍是过渡实现，原版辨识度和取舍感都不够
- 奖励选择流程只能看到名字，玩家无法在终端里直接判断遗物或卡牌价值
- 铁甲战士卡池虽然已从最初 starter 扩到少量补充牌，但仍缺少足够的中期成长、AoE、力量联动和自残构筑核心
- 战斗系统尚未提供 `strength` 和可落地的轻量 Power 支持，因此很多真正有价值的原版铁甲牌还无法接入

本轮目标不是“一次性复刻全部原版系统”，而是在不失控扩张的前提下，把最影响 `act2` 生存与输出曲线的内容补齐：

- 用少量但高辨识度的原版 `act1` Boss 遗物替换当前过渡池
- 让玩家在奖励阶段能够查看候选物品完整属性后再选择
- 补足一批真正能改善 `act2` 通关体验的铁甲原版卡
- 为这些卡补上必要的最小机制闭环

## 2. 目标

- 将 `act1` Boss 遗物池切换为少量高优先级原版 Boss 遗物
- Boss 奖励与普通奖励都支持“先查看详情，再做选择”
- 遗物详情中明确展示：
  - 效果
  - 触发时机
  - 负面限制
  - 替换型关系
- 新增 `strength` 机制，支持力量驱动的原版铁甲输出牌
- 新增轻量 Power 支持，覆盖本轮目标卡牌
- 扩充铁甲卡池，使 `act1` 与 `act2` 奖励更像真正的过渡与成长关系
- 奖励生成逻辑按章节分层，不再只从固定小池里抽牌

## 3. 非目标

- 不在本轮引入完整原版全部 Boss 遗物池
- 不在本轮实现完整 Power 框架或所有 Power 牌
- 不在本轮实现 `X` 费体系
- 不在本轮实现“保留手牌”体系
- 不在本轮实现全局费用改写系统
- 不在本轮实现格挡跨回合保留
- 不在本轮把所有奖励页面统一重构成复杂多槽位系统

## 4. 设计选择

### 4.1 Boss 遗物池采用“小而完整”的原版方案

采用：

- 只做 4 个高优先级原版 `act1` Boss 遗物
- 每个遗物都尽量做到真实可玩而不是空有名字

不采用：

- 保留 `anchor / lantern` 继续充当 Boss 遗物
- 一次性做十几个 Boss 遗物但多数只是近似版

原因：

- 当前问题不是池子数量不够，而是关键选择缺乏原版味道和构筑差异
- 小池子可以把每个遗物的正负面约束都真正接进系统
- 这样能直接服务 `act2` 难度，而不是制造更多半成品内容

### 4.2 卡牌机制采用“最小闭环扩展”

采用：

- 增加 `strength`
- 增加轻量 Power 持久效果
- 基于这两项补关键铁甲牌

不采用：

- 一次性引入 `X` 费、费用变更、保留、回收消耗牌、格挡保留等多个系统

原因：

- `act2` 缺的首先是稳定成长与可成型路线，不是系统广度
- `strength + Power` 已能支撑一批中期最关键的铁甲原版牌
- 这样能把复杂度控制在测试与回归仍可接受的范围

## 5. 范围

### In Scope

- 更新 `boss_relics` 内容池
- 为 Boss 遗物详情补充完整说明能力
- 为普通奖励与 Boss 奖励补充详情查看流程
- 新增 `ectoplasm / coffee_dripper / fusion_hammer / black_blood`
- 为奖励、事件、休息点接入新 Boss 遗物限制
- 新增 `strength`
- 新增轻量 Power 支持
- 新增一批铁甲原版卡与对应升级版
- 将卡牌奖励池按 `act_id` 分层
- 补齐终端菜单、渲染、用例和回归测试

### Out of Scope

- Textual 专用奖励交互重设计
- 遗物稀有度系统
- 多角色差异化奖励池
- 完整原版 Boss 奖励三卡一遗物多槽复刻
- 全局战斗资源系统重构

## 6. Boss 遗物设计

### 6.1 遗物池

`act1` Boss 遗物池替换为以下 4 个：

- `black_blood`
- `ectoplasm`
- `coffee_dripper`
- `fusion_hammer`

以下遗物移出 Boss 池：

- `anchor`
- `lantern`

它们后续如需保留，应回到普通遗物语义，而不是继续作为 Boss 奖励。

### 6.2 遗物效果定义

#### `black_blood`

- 战斗结束后回复 12 点生命
- 若玩家已有 `burning_blood`，选择时必须替换而非叠加
- 详情页要明确显示“替换燃烧之血”

#### `ectoplasm`

- 每场战斗开始时获得 1 点额外能量
- 获得后不能再取得金币

系统含义：

- 普通奖励里的金币无效
- 事件给金无效
- 其他明确加金币的后续入口也必须统一失效

详情页文案应强调“无法再获得金币”，而不是只写“金币奖励失效”。

#### `coffee_dripper`

- 每场战斗开始时获得 1 点额外能量
- 在休息点不能选择回复生命

系统含义：

- 休息点菜单中 `rest` 动作不可用
- 不只是提示文案，实际路由也必须阻止执行

#### `fusion_hammer`

- 每场战斗开始时获得 1 点额外能量
- 在休息点不能选择锻造

系统含义：

- 休息点菜单中 `smith` 动作不可用
- 若房间状态已经进入升级选卡流程，也必须从前置动作入口阻止进入

## 7. 奖励查看与交互设计

### 7.1 目标

当前奖励流程的问题不是“选项不够多”，而是玩家缺乏信息。需要做到：

- 可以查看候选项
- 查看后还能返回继续选择
- 详情层级不打乱现有编号菜单操作习惯

### 7.2 Boss 奖励交互

Boss 奖励主菜单保留现有两槽位语义：

1. 领取金币
2. 选择遗物
3. 返回上一步

当玩家进入 `选择遗物` 后，不直接用“选名字即领取”的单层菜单，而改为两层：

- 候选列表页：列出候选遗物，附一行短摘要
- 详情页：显示完整信息并允许确认选择

建议流程：

1. 进入 Boss 遗物列表
2. 选择某个遗物
3. 进入遗物详情页
4. 可执行：
   - 确认选择该遗物
   - 返回候选列表
   - 返回 Boss 奖励主菜单

### 7.3 普通奖励交互

普通奖励至少覆盖卡牌详情查看，后续若奖励中出现遗物，也复用同样流程。

建议流程：

- 奖励页显示：
  - 领取奖励
  - 查看奖励详情
  - 返回上一步
- 详情列表页列出当前可领奖励
- 选择某一奖励后进入详情页
- 从详情页可返回详情列表或奖励主页

对于卡牌奖励，详情展示应尽量复用现有卡牌 inspect 风格，避免出现两套不同口径。

### 7.4 文案原则

- 奖励列表页使用短摘要，便于编号菜单快速浏览
- 详情页提供完整中文说明
- 避免把负面限制藏在短摘要外的地方
- 替换型、限制型效果必须显式展示

## 8. 数据与内容结构

### 8.1 内容文件

以下文件必须同步维护：

- `content/relics/boss_relics.json`
- `src/slay_the_spire/data/content/relics/boss_relics.json`
- `content/cards/ironclad_starter.json`
- `src/slay_the_spire/data/content/cards/ironclad_starter.json`

本轮不重命名 `ironclad_starter.json`，避免扩大加载器变更范围。

### 8.2 遗物定义扩展

现有 `RelicDef` 只有：

- `id`
- `name`
- `trigger_hooks`
- `passive_effects`
- `can_appear_in_shop`

本轮建议为遗物定义增加可选展示/规则字段，例如：

- `summary`
- `description`
- `replaces_relic_id`
- `disabled_actions`
- `blocks_gold_gain`

原则：

- 展示字段用于详情页文案，避免硬编码到渲染层
- 规则字段用于逻辑判断，避免只靠 `id` 分支散落在多处

若不想扩大 registry 结构，也可在本轮先用约定字段透传到 `passive_effects` 或额外 metadata，但推荐直接加可选字段，代码会更清楚。

### 8.3 卡池内容扩展

本轮在现有基础上新增以下铁甲卡及升级版：

- `cleave / cleave_plus`
- `twin_strike / twin_strike_plus`
- `inflame / inflame_plus`
- `metallicize / metallicize_plus`
- `hemokinesis / hemokinesis_plus`
- `sword_boomerang / sword_boomerang_plus`
- `pummel / pummel_plus`
- `combust / combust_plus`

已存在且继续保留：

- `anger`
- `pommel_strike`
- `shrug_it_off`
- `bloodletting`
- `true_grit`
- `armaments`
- `bash`
- `strike`
- `defend`

本轮刻意不加入：

- `whirlwind`
- `offering`
- `fiend_fire`
- `reaper`
- `corruption`
- `barricade`
- `exhume`

原因是这些牌会显著扩大机制面。

## 9. 战斗机制设计

### 9.1 `strength`

新增 `strength` 状态，用于玩家与敌人伤害修正。

规则：

- 每段 `damage` 效果按 `base_damage + strength` 结算
- 最终伤害最低为 0
- 多段伤害逐段结算并逐段吃力量
- 现有 `weak`、`vulnerable` 修正需与力量共同工作，结算顺序保持统一

本轮重点保证：

- 玩家打出的多段伤害牌正确吃力量
- 敌人的多段攻击也能正确吃力量
- inspect 和日志中能体现状态存在

### 9.2 Power

本轮不做完整原版 Power 框架，只做轻量持久战斗效果。

需要支持：

- 打出后不进入洗牌循环
- 在本场战斗内持续生效
- inspect 可查看当前生效 Power

建议做法：

- 在 `CombatState` 中增加一个轻量战斗持久效果区
- 每个 Power 条目记录：
  - `power_id`
  - `stacks` 或 `amount`
- 通过现有回合流程与 hook 接口，在必要时触发效果

### 9.3 本轮支持的 Power

#### `inflame`

- 打出后获得力量
- 不需要额外回合触发

#### `metallicize`

- 回合结束时获得固定格挡

#### `combust`

- 回合结束时对所有敌人造成伤害
- 同时令玩家失去生命

本轮不支持需要额外触发链的 Power，如：

- `dark_embrace`
- `feel_no_pain`
- `rupture`

## 10. 卡牌设计边界

### 10.1 稳定强度层

用于提升过渡稳定性：

- `cleave`
- `twin_strike`
- `inflame`
- `metallicize`

### 10.2 构筑核心层

用于形成更像原版的中期路线：

- `hemokinesis`
- `sword_boomerang`
- `pummel`
- `combust`

### 10.3 奖励池分层

现有 `generate_combat_rewards()` 写死固定卡池，不足以支撑双幕节奏。

本轮改为：

- `act1` 奖励池：
  - 偏基础强度
  - 可出现少量轻构筑起点
- `act2` 奖励池：
  - 保留基础强度
  - 明显提高力量、自残、Power 路线核心出现概率

目标不是复杂稀有度模拟，而是让 `act2` 奖励比 `act1` 更像“成型补强”。

## 11. 用例与规则接入

### 11.1 金币获取统一判定

`ectoplasm` 不能只在 `apply_reward(gold:...)` 内生效。

需要统一金币入口，例如：

- 普通奖励金币
- 事件金币
- 金神像加成前的基础加金

建议新增统一判定函数，例如：

- `can_gain_gold(run_state)`
- 或 `apply_gold_gain(run_state, amount)`

这样：

- `golden_idol` 仍在允许得金时加成
- `ectoplasm` 则在更前层直接拦截

### 11.2 休息点动作封锁

`coffee_dripper` 与 `fusion_hammer` 不能只靠说明文案。

需要：

- 菜单层把被封锁动作标成不可选
- 路由层即使收到非法输入，也不能执行对应动作

推荐：

- 提供统一的“可用休息点动作”过滤函数
- 渲染与路由共享同一规则源

### 11.3 Boss 遗物替换规则

`black_blood` 选择时：

- 若有 `burning_blood`，先移除
- 再加入 `black_blood`
- 重复领取时保持幂等

## 12. UI 与渲染落点

### 12.1 终端菜单

需要修改的核心区域：

- `menu_definitions.py`
- `session.py`
- `adapters/terminal/screens/non_combat.py`
- `adapters/terminal/inspect.py`
- 可能新增奖励详情专用渲染/菜单辅助

### 12.2 详情展示

卡牌详情尽量复用现有卡牌 inspect 展示。

遗物详情需要补充：

- 完整效果
- 触发时机
- 负面限制
- 替换关系

Boss 遗物候选列表页则显示简短摘要，例如：

- `每场战斗开始时，获得 1 点能量；无法再获得金币`

### 12.3 战斗内 inspect

若新增 Power 区，本轮 inspect 需要最少支持：

- 在战场资料页能看到当前生效 Power

否则玩家会打出 Power 后失去可见性。

## 13. 测试策略

### 13.1 奖励与菜单

新增或更新测试覆盖：

- Boss 遗物列表可进入详情
- Boss 遗物详情可返回列表与主页
- 普通奖励可进入详情
- 奖励查看后不破坏既有编号流转
- 存档恢复后仍能回到正确奖励详情/选择流程

### 13.2 遗物副作用

新增测试覆盖：

- `black_blood` 替换 `burning_blood`
- `ectoplasm` 阻止普通奖励加金
- `ectoplasm` 阻止事件加金
- `coffee_dripper` 禁止休息点回复
- `fusion_hammer` 禁止休息点锻造
- 新 Boss 遗物池不再包含 `anchor / lantern`

### 13.3 战斗机制

新增测试覆盖：

- `strength` 提高单段伤害
- `strength` 提高多段伤害
- 敌人多段伤害吃力量
- `inflame` 正确给力量
- `metallicize` 在回合结束给格挡
- `combust` 在回合结束对群体与自身结算

### 13.4 卡牌与奖励池

新增测试覆盖：

- 新卡可正常进入牌组
- 奖励生成可根据 `act_id` 选不同池
- `act2` 奖励中能出现新增构筑牌
- E2E 冒烟至少覆盖一次：
  - `act1` Boss 奖励查看并选择
  - 进入 `act2`
  - 新卡加入牌组并在战斗中成功结算

## 14. 实施顺序

推荐顺序如下：

1. 奖励查看菜单与详情页
2. Boss 遗物内容与真实副作用
3. `strength` 基础设施
4. 轻量 Power 基础设施
5. 新卡接入与奖励池分层
6. 全量回归测试与数值微调

## 15. 风险与缓解

### 风险 1：奖励菜单状态爆炸

缓解：

- 奖励详情流程与现有 inspect 分离
- 详情页只服务奖励，不混入角色资料页状态机

### 风险 2：Power 与既有回合流程耦合过深

缓解：

- 只实现本轮需要的最小 Power
- 优先通过现有 hook/回合节点接入，不做全局大重构

### 风险 3：卡牌内容扩得太快导致测试缺口

缓解：

- 先补机制测试，再补卡牌
- 每类新增机制至少要有 1 到 2 个行为测试后才继续扩卡

## 16. 结论

本轮采用：

- 少量但尽量完整的原版 `act1` Boss 遗物
- 可查看详情的奖励选择流程
- 以 `strength + 轻量 Power` 为核心的最小机制扩展
- 围绕 `act2` 难度需求补强的铁甲原版卡池

这样可以在不把项目一次性拖入“大系统重构”的前提下，显著改善 `act2` 的可玩性、原版感和选择信息密度。
