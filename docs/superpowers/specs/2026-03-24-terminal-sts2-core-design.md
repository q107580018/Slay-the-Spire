# Terminal Slay the Spire 2 Core Design

Date: 2026-03-24
Status: Draft for review

## 1. Goal

构建一个基于终端的、单人模式的 `Slay the Spire 2` 风格文字版游戏第一阶段实现。

该阶段目标不是复刻完整 Early Access 内容，也不是追逐当前版本的具体数值，而是建立一个可扩展、可维护的核心爬塔骨架，使后续可以自然接入更多角色、卡牌、敌人、遗物、事件，以及 `Enchantments`、`Ancients`、`Alternate Acts` 等续作系统。

## 2. Scope

### In Scope

- 单人模式
- 单个 Act 的完整流程
- 可游玩的核心爬塔循环
- 终端文字交互
- 存档与读档
- 可测试的规则系统
- 数据驱动的内容定义

### Out of Scope

- 多人合作
- 多 Act 完整正式流程
- 复杂新角色机制，例如 `Necrobinder/Osty`
- 正式版数值对齐
- 图形界面
- 全量卡池、敌人池、事件池

## 3. Product Principles

- 机制保真优先于视觉还原
- 边界清晰优先于快速堆功能
- 内容与规则分离
- 终端展示与游戏规则分离
- 少量内容验证架构，而非大量内容掩盖架构问题

## 4. Architecture Overview

项目采用“领域模型 + 数据驱动”路线。

模块按职责分层：

- `app`
  - CLI 入口
  - 菜单与命令路由
  - 会话启动与退出
- `use_cases`
  - 编排用户操作与游戏流程
  - 调用规则层并组织状态迁移
- `domain`
  - 纯规则层
  - 定义模型、结算逻辑、效果解析、房间与战斗规则
- `content`
  - 角色、卡牌、敌人、遗物、事件、地图模板等声明式数据
- `adapters`
  - 终端渲染
  - 持久化
- `tests`
  - 规则测试
  - 用例测试
  - 内容校验测试

依赖方向必须保持单向：

`app -> use_cases -> domain`

`use_cases -> content`

`adapters -> app/use_cases`

`domain` 不依赖 `app`、`adapters`、终端 I/O。

## 5. Core State Model

第一阶段不使用一个巨大的 `GameState`，而是拆分为四个主状态对象。

### 5.0 State Ownership Rules

必须先定义“唯一真相来源”，避免状态在多个对象中重复存储并漂移。

- `RunState` 是 run 级唯一真相来源
- `ActState` 是当前 Act 级唯一真相来源
- `RoomState` 是当前房间上下文的唯一真相来源
- `CombatState` 是当前战斗态的唯一真相来源

额外约束：

- `RunState` 只保存 `current_act_id`，不直接内嵌或复制 `ActState`
- `ActState` 只保存 `current_node_id` 与地图图结构，不持久化可从图结构推导出的冗余字段
- `reachable_nodes` 属于派生值，运行时计算，不作为存档字段
- `RoomState` 在进入房间时创建，在房间结算完毕后销毁或归档
- `CombatState` 只在战斗房间生命周期中存在
- 任何 ID 引用内容定义时，必须通过注册表重新解析，而不是持久化 Python 对象引用

### 5.0.1 Persistence Identity Rules

为保证存档/读档稳定，状态对象必须遵守：

- 所有实体实例拥有稳定 `instance_id`
- 所有内容定义通过稳定 `content_id` 引用
- 所有状态对象仅保存可序列化原始数据
- 不允许在状态中保存闭包、函数对象或不可重建引用
- 读档后通过注册表按 `content_id` 重建内容绑定
- 任何派生值在读档后重新计算

### 5.1 RunState

保存整个 run 的长期信息：

- 角色 ID
- 当前 HP / 最大 HP
- 金币
- 药水
- 遗物
- 牌组
- 当前 Act ID
- run 种子
- 统计信息
- 进度元数据

### 5.2 ActState

保存当前 Act 范围内的信息：

- 地图图结构
- 当前节点
- 已访问节点
- 普通敌人池/精英敌人池/Boss 池引用
- 事件池引用

`当前可到达节点` 由地图图结构和当前节点动态计算，不落盘。

### 5.3 RoomState

表示当前房间上下文：

- 房间类型
- 房间载荷
- 是否已解析
- 奖励信息

房间类型至少包括：

- 普通战斗
- 精英战斗
- 休息点
- 事件
- 商店
- Boss

### 5.4 CombatState

只保存战斗中的临时状态：

- 回合数
- 当前能量
- 手牌
- 抽牌堆
- 弃牌堆
- 消耗堆
- 玩家战斗态
- 敌人实例列表
- 待结算效果队列
- 战斗日志

## 6. Combat Model

### 6.1 Combat Entities

使用统一的战斗实体抽象承载公共属性。

基础字段包括：

- `hp`
- `max_hp`
- `block`
- `statuses`
- `alive`

在此基础上细分：

- `PlayerCombatState`
- `EnemyState`

### 6.2 Status Model

状态效果如 `Weak`、`Vulnerable`、`Poison` 应统一建模为 `StatusInstance`，提供：

- 状态 ID
- 层数或持续时间
- 结算时机
- 叠加规则

### 6.3 Turn Flow

标准战斗回合流程固定为：

1. 回合开始
2. 抽牌与能量恢复
3. 玩家行动阶段
4. 玩家结束回合
5. 敌人行动阶段
6. 回合结束状态结算
7. 胜负判定

### 6.4 Room/Run Flow

单 Act 运行流程固定为：

1. 开始新 run
2. 生成 Act 地图
3. 选择并进入节点
4. 解析房间
5. 若为战斗则进入战斗循环
6. 生成并领取奖励
7. 返回地图推进
8. 打败 Boss
9. 结束该 Act

## 7. Effect Pipeline

### 7.1 Central Rule

战斗与奖励系统中的状态变更，必须统一通过 `Effect` 管线发生。

不允许卡牌、敌人、遗物或事件逻辑绕过规则层直接任意改写状态对象。

### 7.2 Effect Examples

第一阶段 effect 类型至少支持：

- `deal_damage`
- `gain_block`
- `apply_status`
- `draw_cards`
- `discard_cards`
- `heal`
- `modify_energy`
- `add_card_to_deck`
- `add_card_to_hand`
- `add_card_to_discard`
- `gain_gold`
- `choose_one`

### 7.3 Resolver

`EffectResolver` 负责：

- 校验目标是否合法
- 按顺序执行 effect
- 记录日志
- 触发 hooks
- 处理连锁效果

### 7.4 Timing Invariants

战斗时序必须由硬性不变量定义，而不是依赖实现细节。

第一阶段固定以下规则：

1. 单次动作产生的 `effects` 进入一个先进先出的结算队列。
2. `hook` 可以追加新的 `effects`，但只允许追加到当前队列尾部。
3. 不允许同步递归执行 `resolver`；所有连锁效果都必须排队。
4. 单个 `effect` 完成后立即检查死亡，但“战斗结束”只在当前 effect 队列清空后统一判定。
5. 若某实体已死亡，后续以其为目标的 effect 自动失效，记录为 no-op。
6. `on_enemy_defeated` 在敌人死亡确认后入队。
7. `on_combat_end` 只触发一次，且发生在当前结算批次结束之后。
8. 同一时点多个 hooks 的优先级固定为：
   - 状态效果
   - 遗物/被动
   - 卡牌后续效果
   - 全局战斗收尾
9. 同一类别内多个 hook 的 tie-break 顺序固定为：
   - 显式 `priority` 数值，数值越小越先执行
   - 若 `priority` 相同，则按来源类型顺序：玩家状态、玩家遗物、敌人状态、敌人被动、全局效果
   - 若来源类型相同，则按稳定 `instance_id` 字典序
10. 任意 hook 注册结果都必须可序列化为稳定顺序，不允许依赖 Python 容器遍历偶然顺序。

这些规则必须在实现前转化为测试，不允许边写边猜。

## 8. Data-Driven Content

### 8.1 Content Definitions

绝大多数内容采用声明式定义。

示例对象：

- `CardDef`
  - `id`
  - `name`
  - `cost`
  - `target_rule`
  - `rarity`
  - `tags`
  - `upgrades_to`
  - `effects`
- `RelicDef`
  - `id`
  - `name`
  - `trigger_hooks`
  - `passive_effects`
- `EnemyDef`
  - `id`
  - `base_stats`
  - `move_table`
  - `intent_policy`
- `EventDef`
  - `id`
  - `text`
  - `choices`
  - `outcomes`

### 8.2 Content Strategy

采用“90% 数据驱动 + 10% 特例脚本”策略：

- 常规卡牌、敌人和事件由数据描述
- 少数无法自然表达的复杂内容允许注册专用规则处理器

该策略用于避免每张卡都写成一个独立 Python 子类，降低维护成本。

### 8.3 Content Registry Contract

内容层不能靠随意 import 形成隐式耦合，必须通过注册契约暴露。

需要提供统一注册表：

- `CardRegistry`
- `EnemyRegistry`
- `RelicRegistry`
- `EventRegistry`
- `ActRegistry`

注册表职责：

- 通过 ID 提供内容定义
- 校验内容唯一性
- 在启动时完成完整性检查
- 为读档恢复提供反查

`use_cases` 不应直接 import 某张卡或某个敌人的具体实现文件，而是只依赖注册表接口。

### 8.4 Special Rule Handler Contract

“10% 特例脚本”必须是受控扩展点，而不是任意逃生口。

约束如下：

- 每个特例处理器必须绑定明确 `content_id`
- 必须声明适用阶段：卡牌解析、效果前置、效果后置、事件选择、敌人 AI 等
- 必须通过统一注册机制接入
- 必须有对应测试
- 若通用 effect 已可表达，禁止引入特例脚本

目标是让特例处理器成为少量、显式、可审查的例外。

## 9. Hook System

为了给未来的 relic、status、enchantment、ancient 等系统预留挂点，第一阶段即设计统一 hooks。

首批 hooks：

- `on_combat_start`
- `on_turn_start`
- `on_card_played`
- `on_attack_resolved`
- `on_turn_end`
- `on_enemy_defeated`
- `on_combat_end`

第一阶段不需要所有内容都使用 hooks，但主流程应围绕 hooks 构造，而不是事后补丁式插入。

## 10. Terminal Adapter

终端适配层负责：

- 渲染主界面、地图、战斗状态、奖励选择
- 接收玩家输入
- 输出战斗日志

终端适配层不得直接实现战斗规则。

规则层只返回：

- 当前可执行动作
- 状态快照
- 日志事件
- 错误信息

这样后续切换为 TUI 或 Web 界面时，无需重写领域逻辑。

## 10.5 Ports and Protocols

为进一步稳定边界，适配层与用例层通过端口协议通信，而不是彼此依赖具体实现。

建议端口包括：

- `RendererPort`
- `InputPort`
- `SaveRepositoryPort`
- `ContentProviderPort`
- `RngPort`

这样可以在测试中替换终端输入、渲染输出、内容提供和存档实现。

## 11. Persistence

第一阶段必须支持：

- 新建存档
- 读取存档
- 在 run 中途保存
- 恢复到地图态或战斗态

持久化建议：

- 使用可序列化状态对象
- 避免在状态中存放无法稳定还原的运行时闭包
- 内容定义与状态实例通过 ID 关联
- 保存格式需要有 `schema_version`
- 读档流程必须包含迁移或兼容检查入口

### 11.1 Persistence Invariants

必须验证以下不变量：

- 存档后立刻读档，状态等价
- 地图态存档恢复后，可继续正确进入下一房间
- 战斗态存档恢复后，抽牌堆/弃牌堆/手牌/敌人状态不丢失
- 非战斗房间态存档恢复后，可继续完成当前交互，不重复结算已执行步骤
- 同一随机种子与同一路径选择，在无额外输入扰动时行为可复现

### 11.2 RoomState Save/Restore Rules

既然 `RoomState` 是独立真相源，就必须明确其持久化策略。

第一阶段规则：

- 所有房间类型都允许在“等待玩家输入”的稳定点保存
- 战斗房间可在玩家行动阶段的等待输入点保存
- 事件房间可在选项展示后保存
- 商店房间可在购买/移除/离开操作前保存
- 奖励选择房间可在奖励展示后保存
- 休息点可在操作菜单展示后保存
- 不允许在单个 effect 或单个交易的半执行状态中保存

恢复规则：

- 恢复后回到最近一个稳定输入点
- 已提交并完成的操作不得重复执行
- 未提交的输入选择必须重新输入
- `RoomState` 需记录该房间的交互阶段与已完成动作标记，以支持精确恢复

## 12. Testing Strategy

### 12.1 Domain Tests

覆盖：

- 伤害与格挡结算
- 状态应用与回合结算
- 抽牌/洗牌/弃牌
- 敌人死亡判定
- 奖励生成

### 12.2 Use Case Tests

覆盖：

- 开始新 run
- 进入房间
- 完成战斗
- 领取奖励
- 保存并恢复进度
- 非法动作拒绝，例如费用不足、目标非法、房间状态不允许

### 12.3 Content Validation Tests

校验：

- 所有内容 ID 唯一
- 所有 effect 类型合法
- 所有 target_rule 合法
- 升级引用存在
- 敌人 move table 完整
- 事件分支结果合法

### 12.4 Invariant and Regression Tests

额外必须覆盖：

- effect 队列顺序稳定
- hook 触发顺序稳定
- 死亡判定与战斗结束时机稳定
- 随机种子决定性
- 存档/读档 round-trip
- 序列化版本兼容性
- 房间态与战斗态切换一致性

## 13. Milestone 1 Content

首个可玩版本只包含最小必要内容：

- 1 个角色
- 1 套基础起始牌组
- 1 个 Act 地图生成器
- 普通战斗、精英、休息点、事件、商店、Boss 六类房间
- 1 个 Boss
- 6 到 10 个普通敌人
- 2 到 3 个事件
- 少量基础遗物
- 20 到 30 张基础卡
- 完整战斗日志
- 完整存档/读档

## 14. Non-Goals for Milestone 1

以下内容明确不进入首个可玩里程碑：

- 第二角色
- 多 Act 内容
- 联机协作
- `Necrobinder/Osty`
- `Enchantments`
- `Ancients`
- `Alternate Acts`

但架构应为这些系统保留扩展点。

## 15. Risks

### Risk 1: Data Model Too Weak

如果 effect 语义过于贫弱，后续会被迫回到硬编码。

Mitigation:

- 尽早定义通用 effect 语义
- 在最小内容阶段覆盖多种常见牌效

### Risk 2: Domain and Terminal Coupling

如果规则层直接打印文本，后续扩展 UI 和测试都会受阻。

Mitigation:

- 规则层只产出结构化结果
- 文本化渲染放到 adapter 层

### Risk 3: Python Dynamic Drift

Python 易于快速开发，但也容易缺少边界约束。

Mitigation:

- 全量类型标注
- 保持分层依赖单向
- 为关键规则补测试

## 16. Recommended Next Step

在本设计获批后，进入实现计划阶段，输出：

- 项目初始化方案
- 目录与模块创建顺序
- 第一批核心模型清单
- 第一批测试清单
- 第一批最小内容数据清单

## 17. Notes

- 当前目录尚未初始化为 Git 仓库，因此本阶段无法按规范提交 spec commit。
- 如果后续用户希望，下一步可在该设计基础上直接生成详细 implementation plan。
