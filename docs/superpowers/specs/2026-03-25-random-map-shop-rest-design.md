# Random Map, Shop, and Rest Design

Date: 2026-03-25
Status: Draft for review

## 1. 背景

当前项目已经具备单 Act、可战斗、可领奖励、可进事件、可存读档的中文终端版本，但爬塔流程仍然偏“骨架态”：

- 地图仍是静态节点图
- 房间类型实际上只接通了 `combat / elite / event / boss`
- `shop` 与 `rest` 只有独立用例文件，尚未接入主流程
- 地图选择只能处理当前固定分支，不能表达完整随机分层地图

本次设计目标是把单 Act 爬塔流程补成更接近 Slay the Spire 的可玩闭环，同时保持当前项目的规则层和终端层边界清晰。

## 2. 参考项目

本设计现在以 **公开可得的 Slay the Spire 2 Early Access 资料** 为主锚点，并用 [`sts2-cli`](https://github.com/wuhao21/sts2-cli) 作为“运行真实 STS2 引擎的终端参考”。

主要参考来源：

- [`sts2-cli`](https://github.com/wuhao21/sts2-cli)
- [STS2 Wiki Acts](https://sts2.wiki/acts/)
- [STS2 Wiki Relics](https://sts2.wiki/relics/)
- [Pro Game Guides: Slay the Spire 2 Beginner's Guide](https://progameguides.com/slay-the-spire-2/slay-the-spire-2-beginners-guide/)

其中明确影响本次设计的公开信息包括：

- `sts2-cli` 已公开暴露 `shop` 的 `cards / relics / potions / remove` 交互
- `sts2-cli` 已公开暴露 `rest_site` 的可扩展选项模型，而不是永久写死只有两个动作
- PGG 当前公开写明 STS2 休息点的基础动作仍是 `Rest / Smith`，其中 `Rest` 为回复 `30%` 最大生命值
- PGG 当前公开写明 STS2 的删牌服务首个价格为 `75`
- STS2 Wiki 当前列出的四个 Act 房间规模为 `13 / 14 / 15 / 15`
- STS2 Wiki 当前列出的 relic 效果已经显示休息点行为可以被 relic 扩展，例如 `Girya` 与 `Miniature Tent`

本设计明确参考 `sts2-cli` 的地图外部表现与交互方式，尤其是：

- 地图使用运行时生成的分层图，而不是手写死路线
- 地图节点以 `row / col / type / children` 的图结构暴露
- 当前决策点只允许选择“当前可达节点”
- 完整地图单独查看，不要求每次决策都展示整张图

本项目不会照搬 `sts2-cli` 的真实游戏引擎实现，也不会追求与实时 Early Access 构建逐字段完全一致。因为 STS2 仍在频繁更新，本次设计采用：

- 能公开确认的机制，尽量对齐
- 公开资料不足的细节，保守简化
- 一旦简化，就在文档中明确标注为“实现取舍”，而不是假装等同于原版

## 3. 目标

- 将地图从静态节点图升级为基于种子的随机分支图
- 在当前单 Act 流程中正式接入 `shop` 与 `rest`
- 让 `shop` 包含 STS2 风格的卡、遗物、药水、删牌服务
- 支持查看完整分层地图，同时在决策时只允许选择当前可达节点
- 让商店、休息点在多步交互下保持稳定状态
- 让休息点与商店的动作模型可以继续承载 STS2 风格的扩展动作
- 为后续增加更多房型、更多地图规则和更复杂奖励系统留出边界

## 4. 非目标

- 不追求复刻真实 STS 或 `sts2-cli` 的地图生成算法
- 不实现 `treasure`、`unknown`、`ancient` 等额外房型
- 不实现商店刷新、药水商店、打折、会员卡等高级商店机制
- 不实现假商店、Ancients、Act 变体专属地图逻辑或 campfire relic 全量交互
- 不兼容旧存档 schema

旧存档处理策略明确为：

- 旧 schema 在 `load` 时直接拒绝加载
- 返回明确错误信息，提示当前版本需要新开 run
- 本轮不做自动迁移

## 5. 范围

### In Scope

- 房型：`combat / event / elite / shop / rest / boss`
- 随机地图生成与完整地图查看
- 地图选择与房间流转重构
- 商店：买牌、买遗物、买药水、删牌、离开
- 休息点：回血、强化
- 必要的终端 UI 扩展与测试补齐

### Out of Scope

- 新角色
- 多 Act 串联
- 新状态、新遗物 hook、大量战斗机制扩展
- 旧档迁移

## 6. 设计原则

### 6.1 地图生成结果是状态，不是即时视图

随机地图一旦生成，就应完整写入 `ActState`，后续选择、查看、存档都基于这份结果，而不是每次临时重算。

### 6.2 当前可选路径与完整地图分离

当前回合只允许操作“从当前位置可达的节点”，但终端可以独立展示完整地图。这与参考项目的交互模型一致，也能避免把渲染逻辑和规则判断混在一起。

### 6.3 房间载荷必须稳定

商店库存、价格、删牌服务可用性、休息点的子状态都必须进入 `RoomState.payload`。这些信息不允许在渲染时重新随机，否则会破坏多步交互和存档一致性。

### 6.4 优先做可玩的闭环，而不是高保真模拟

本次优先做“地图可走、商店可买、休息点可用、能回到地图继续推进”的完整体验，不在第一轮引入真实 STS 的复杂概率表和例外规则。

### 6.5 动作模型优先于动作数量

STS2 的休息点和商店都不是“永远只有固定两个按钮”的系统。第一轮虽然只实现基础子集，但状态模型必须允许：

- 休息点拥有多个动态动作
- 商店拥有多种商品类别
- 某些 relic 或事件改变房间可执行动作

## 7. 架构概览

本次改动主要影响以下模块：

```text
content/
  registries.py
  catalog.py
domain/
  models/act_state.py
  map/map_generator.py
use_cases/
  enter_room.py
  shop_action.py
  rest_action.py
app/
  session.py
adapters/terminal/
  renderer.py
  screens/non_combat.py
  widgets.py
tests/
  domain/
  use_cases/
  adapters/terminal/
  e2e/
```

依赖方向不变：

- 地图生成仍属于 `domain`
- 房间进入与动作属于 `use_cases`
- `session.py` 只编排状态切换
- 终端层只消费状态，不直接改写规则数据

## 8. Act 内容与地图配置

当前 `ActDef` 直接保存静态 `nodes`。本次将其改为保存地图配置，而不是完整节点图。

建议新增 `map_config`，至少包含：

- `floor_count`
- `starting_columns`
- `min_branch_choices`
- `max_branch_choices`
- `room_rules`
- `boss_room_type`

其中 `room_rules` 描述每层房型约束，而不是精确概率脚本。第一轮只需要支持能稳定生成下列结果：

- 第 0 层为起点
- 最后一层为 boss
- 中间层只出现 `combat / event / elite / shop / rest`
- `elite / shop / rest` 不能出现在过早楼层
- 每个 Act 至少出现 1 个 `shop`
- 每个 Act 至少出现 1 个 `rest`
- 整张图从起点到 boss 至少有一条合法路径

`enemy_pool_id / elite_pool_id / boss_pool_id / event_pool_id` 继续保留在 `ActDef` 中，不需要因为地图重构而移动位置。

一个最小可执行的 `map_config` 示例：

```json
{
  "floor_count": 13,
  "starting_columns": 1,
  "min_branch_choices": 1,
  "max_branch_choices": 2,
  "boss_room_type": "boss",
  "room_rules": {
    "early_floors": ["combat", "event"],
    "mid_floors": ["combat", "event", "shop", "rest"],
    "late_floors": ["combat", "event", "elite", "shop", "rest"],
    "min_floor_for_elite": 3,
    "min_floor_for_shop": 2,
    "min_floor_for_rest": 2
  }
}
```

这里的意图是：

- 采用更接近 STS2 当前公开 Act 规模的长度
- 早期楼层避免过早刷出高风险房型
- 中后期逐步开放 `shop / rest / elite`
- 具体概率和抽样策略由 `map_generator` 内部定义，但必须满足这些下限约束

这里有一个明确的实现取舍：

- STS2 Wiki 当前公开的是每个 Act 的 `Rooms 13 / 14 / 15 / 15`
- 本项目第一轮把这个信息**解释为目标地图层级规模**
- 因为当前终端版本仍采用“每层一个决策行”的简化模型，所以默认取 `floor_count = 13` 作为 MVP

这是一条实现层推断，不是宣称 STS2 内部一定使用与本项目完全相同的地图层定义。

字段语义在本次实现中明确为：

- `floor_count`：总层数，包含起点层和 boss 层
- `starting_columns`：第 0 层生成的起点节点数；第一轮固定允许为 `1`
- `min_branch_choices`：每个非 boss 节点最少出边数下限
- `max_branch_choices`：每个非 boss 节点最多出边数上限
- `boss_room_type`：最后一层唯一节点的房型，第一轮固定为 `boss`
- `room_rules`：各楼层房型池约束，不是概率权重表

生成规则约定为：

1. 第 0 层生成 `starting_columns` 个起点节点
2. 第 `floor_count - 1` 层生成 1 个 boss 节点
3. 先生成图拓扑，再分配房型；两步分开处理
4. 拓扑生成时，中间每层节点数由上一层出边汇总得到，但单层节点数上限固定为 `3`
5. 每个非 boss 节点按 `[min_branch_choices, max_branch_choices]` 随机生成出边数
6. 出边只能连接下一层节点，不允许跨层或回边
7. 同一节点的出边不重复
8. 房型分配时，`room_rules` 只决定“某层允许出现哪些房型”，具体从允许集合中按均匀随机抽样
9. 若房型分配结果违反楼层最低限制或该层无合法房型，则只重抽该层房型，不改动已生成拓扑
10. 若拓扑生成本身无法满足“起点可达 boss、非 boss 至少一条出边、单层不超过 3 个节点”，则整张图从头重生

这意味着本次地图生成器是：

- 有限宽度的分层 DAG
- 每层最多 3 个节点
- 每个节点最多 2 个后继
- 房型按合法集合均匀抽样

额外放置约束：

- 若初次房型分配结果中没有 `shop`，则在满足楼层限制的合法节点中强制替换 1 个非 boss 节点为 `shop`
- 若初次房型分配结果中没有 `rest`，则在满足楼层限制的合法节点中强制替换 1 个非 boss 节点为 `rest`
- 强制替换不能覆盖已存在的 `shop/rest/boss`

重抽边界因此明确为：

- 拓扑不合法：整张图重生
- 房型不合法：只重抽当前层房型
- 不允许“上一层连边和当前层房型一起局部回溯”的中间策略

一个示意生成图：

```text
floor 0:  (0,0) start
             |
floor 1:  (1,0) combat   (1,1) event
           /    \            |
floor 2: (2,0) combat  (2,1) shop
            \          /
floor 3:     (3,0) elite   (3,1) rest
                \          /
floor 4:         (4,0) combat
                    |
floor 5:           (5,0) event
                    |
floor 6:           (6,0) boss
```

## 9. ActState 与节点模型

`ActNodeState` 从“只有 `node_id + next_node_ids`”扩展为：

- `node_id`
- `row`
- `col`
- `room_type`
- `next_node_ids`

`ActState` 继续保存：

- `act_id`
- `current_node_id`
- `nodes`
- `visited_node_ids`
- `enemy_pool_id`
- `elite_pool_id`
- `boss_pool_id`
- `event_pool_id`

并新增只读派生能力：

- 当前可达节点列表
- 完整地图行视图
- 当前坐标

这里不额外持久化 `reachable_nodes` 或“显示层 map rows”，因为都可以从 `nodes + current_node_id` 推导。

由于本次不兼容旧档，`ActState` 与 `ActNodeState` 的 `schema_version` 可以直接提升。

`visited_node_ids` 的更新时机明确为：

- 用户完成地图选择并成功进入某节点对应房间时，立即将该节点写入 `visited_node_ids`
- 不等待房间结算后再写入

这样完整地图中的“已访问节点”表示“已经进入过的节点”，不是“已经完全清空的节点”。

## 9.1 数据模型增量

为支撑 STS2 风格的商店、休息点和 run 终局，本次状态模型增量明确如下。

### RunState

在现有字段基础上，新增长期 run 级真相源：

- `gold`
- `deck`
- `relics`
- `potions`
- `card_removal_count`

可选但推荐：

- `run_status`，取值如 `in_progress / victory / defeat`

语义约定：

- 长期牌组、金币、遗物、药水都属于 `RunState`
- 房间内临时可选项、库存、候选列表不放进 `RunState`
- 商店购买、删牌、休息点强化都直接改写 `RunState`

### ActState

`ActState` 仍只负责：

- 当前 Act 地图图结构
- 当前节点位置
- 已访问节点
- 当前 Act 的内容池引用

不把金币、牌组、药水、遗物复制到 `ActState`。

### RoomState

`RoomState` 负责当前房间生命周期内的状态：

- 当前房间类型
- 当前房间阶段
- 当前房间载荷
- 当前房间奖励

商店库存、删牌候选、强化候选、事件中间结果，都只存在于 `RoomState.payload`。

推荐字段草图：

```json
{
  "shop_inventory": {
    "cards": [{"entry_id": "card-1", "content_id": "strike_plus", "price": 50, "kind": "card"}],
    "relics": [{"entry_id": "relic-1", "content_id": "anchor", "price": 150, "kind": "relic"}],
    "potions": [{"entry_id": "potion-1", "content_id": "fire_potion", "price": 60, "kind": "potion"}]
  },
  "remove_candidates": ["strike#1", "defend#2"],
  "upgrade_options": ["bash#3"],
  "purchased_ids": ["card-1"],
  "remove_used": false
}
```

药水购买后的运行态表示遵循与遗物、牌组相同的原则：购买结果直接写入 `RunState.potions`，不在 `RoomState` 中额外保存长期副本。

### SessionState

`SessionState` 继续承担编排职责，并新增 session 级转场语义：

- `run_phase`，取值建议为 `active / game_over / victory`

语义约定：

- `run_phase = active` 时，允许正常房间与地图交互
- `run_phase = victory` 时，渲染通关页，不再允许继续推进
- `run_phase = game_over` 时，渲染失败页，不再允许继续推进

如果实现时不想新增 `run_phase`，则至少要新增等价的布尔或枚举字段，不能把终局状态隐含在 renderer 分支里。

## 10. 地图生成

### 10.1 生成输入

地图生成输入为：

- `act_id`
- `seed`
- `ActDef.map_config`

### 10.2 生成输出

生成器返回完整 `ActState`，其中所有节点都已经带有：

- 层级坐标
- 房间类型
- 出边关系

### 10.3 约束

第一轮生成器至少保证：

- 相同 `seed + act_id + config` 生成完全一致的图
- 起点存在且唯一
- boss 节点存在且唯一
- 所有 `next_node_ids` 指向合法节点
- 每个非 boss 节点至少有一条出边
- 从 `current_node_id` 出发总能走到 boss
- `visited_node_ids` 初始为空

### 10.4 复杂度边界

不引入真实 STS 那种复杂的交叉线消除、强约束回溯或多轮修图算法。允许生成规则偏简单，只要满足：

- 路径数大于 1
- 房型有基本变化
- 路线可读
- 测试可稳定验证

## 11. 地图查看与选择接口

对外暴露两个概念：

### 11.1 当前可选节点

地图决策仍只允许选择当前节点的子节点，保持现有“从 reachable nodes 里选”的安全模型。

### 11.2 完整地图视图

终端可以单独调用一个 map view 数据结构，结构参考 `sts2-cli`：

- `rows`
- `current_coord`
- `boss`
- `visited`

但这里仍然由本项目自己的 `ActState` 推导，不引入额外“地图 DTO 真相源”。

### 11.3 选择接口

现有代码按 `node_id` 选择即可，不强制改成 `(row, col)` 输入协议。对内只要节点有 `row/col`，终端渲染完整地图就足够；交互层仍可以对用户显示序号菜单，以降低实现成本。

换句话说：

- 状态模型学习 `sts2-cli`
- 交互输入继续保留当前项目的数字菜单风格

## 12. 房间流转

`enter_room()` 将从“少数房型的特例初始化”改为“所有受支持房型的统一入口”。

支持房型：

- `combat`
- `elite`
- `event`
- `shop`
- `rest`
- `boss`

### 12.1 战斗类房间

`combat / elite / boss` 进入时生成 `combat_state`，战斗结束后进入奖励阶段，奖励领取完成后返回地图。

### 12.2 事件房间

事件房间仍绑定一个 `event_id`，但后续可以自然扩展为“事件结果修改牌组、金币或 HP”，不再把事件结果只当作字符串标签。

### 12.3 休息点

休息点进入时生成操作列表与必要子状态：

- `heal`
- `smith`

第一轮只实现上述两个基础动作，但动作结构必须允许后续扩展出更多 STS2 风格选项，例如：

- `lift`
- `dig`
- `recall`
- 其他由 relic 或事件解锁的特殊选项

`heal` 为一步结算；`smith` 进入选牌子状态，完成后房间结束并返回地图。

### 12.4 商店

商店进入时生成一次性的库存和价格快照。玩家可以在同一房间内执行多步操作，直到主动离开。

商品类别第一轮至少包括：

- cards
- relics
- potions
- card removal

### 12.5 返回地图

房间不再依赖“结算完立刻自动前进”的隐式推进逻辑。统一改为：

1. 进入房间
2. 执行动作
3. 房间标记为 `resolved` 或仍处于交互中
4. 用户明确离开房间或领取完奖励后返回地图

这样更适合商店停留、休息点选牌和完整地图查看。

### 12.6 房间交互子状态归属

本次明确区分：

- `RoomState.stage`：规则层的房间阶段真相源
- `RoomState.payload`：房间内多步交互所需的持久化数据
- `MenuState`：终端当前菜单焦点与临时选择，不作为规则真相源

也就是说：

- 是否处于 `smith` 选牌、商店根菜单、奖励阶段，属于 `RoomState.stage`
- 当前商店库存、可升级牌列表、已购项目、删牌是否已用，属于 `RoomState.payload`
- UI 当前高亮项、最近一次输入、底部菜单模式，属于 `MenuState`

这样可以保证：

- 存档/读档只依赖 `RoomState`
- renderer 只消费规则状态
- `MenuState` 不承担业务语义

### 12.7 统一阶段约定

本次所有房间统一使用以下阶段语义：

- `waiting_input`：房间已进入，等待用户做当前阶段动作
- `select_upgrade_card`：休息点强化选牌子阶段
- `select_remove_card`：商店删牌选牌子阶段
- `completed`：房间核心动作已完成，等待返回地图或进入奖励后续

`is_resolved` 语义统一为：

- `False`：房间仍在交互中，不能安全返回地图
- `True`：房间主要规则动作已完成，可以进入下一步返回地图或奖励领取

房型状态迁移表：

| 房型 | 进入时 `stage` | 交互中阶段 | 完成后 `stage` | 完成后 `is_resolved` | 返回地图前额外步骤 |
|---|---|---|---|---|---|
| `combat` | `waiting_input` | `waiting_input` | `completed` | `True` | 奖励领取 |
| `elite` | `waiting_input` | `waiting_input` | `completed` | `True` | 奖励领取 |
| `boss` | `waiting_input` | `waiting_input` | `completed` | `True` | Boss 奖励领取后结束 run，不返回地图 |
| `event` | `waiting_input` | `waiting_input` | `completed` | `True` | 领取事件后续结果 |
| `rest` | `waiting_input` | `select_upgrade_card` 可选 | `completed` | `True` | 返回地图 |
| `shop` | `waiting_input` | `select_remove_card` 可选 | `completed` | `True` | 返回地图 |

统一路由规则：

1. `enter_room()` 创建房间时，除特殊奖励页外一律进入 `waiting_input`
2. 房间内部子流程只允许切换到该房型定义的中间阶段
3. 一旦房间切到 `completed` 且 `is_resolved = True`，只允许执行“领取奖励/返回地图”类动作
4. `session.py` 不允许绕过 `RoomState.stage` 直接跳房间

## 13. 商店设计

### 13.1 进入商店时生成快照

`RoomState.payload` 保存：

- `shop_inventory.cards`
- `shop_inventory.relics`
- `shop_inventory.potions`
- `remove_service`
- `purchased_ids`
- `remove_used`

需要时也可以保存价格字段：

- `price`
- `kind`
- `content_id`

第一轮将商店快照具体化为：

- `cards`: 3 张可买卡
- `relics`: 1 个可买遗物
- `potions`: 2 个可买药水
- `remove_service`: 1 次删牌服务

这里也是明确的实现取舍：

- 公开资料能确认 STS2 商店包含 `cards / relics / potions / remove`
- 但公开资料不足以稳定确认当前 live build 的精确商品数量
- 因此第一轮保留商品类别完整，对商品数量做保守简化

生成规则采用保守固定版：

- 卡牌从角色可用卡池中抽取 3 个不重复条目
- 遗物从当前遗物池中抽取 1 个未持有条目
- 药水从药水池中抽取 2 个不重复条目
- 若池子不足，则按实际可生成数量展示，不强行补齐
- 商店一旦生成，在离开前不刷新

随机性与存档稳定性约定：

- 所有房间级随机载荷都必须由 `run seed + room_id + payload kind` 派生
- 商店库存和价格只在第一次进入该房间时生成一次，并持久化到 `RoomState.payload`
- 读档后不得重新抽取商店库存
- 事件、奖励、商店等房间级随机结果都遵循同一原则：一旦进入房间并生成结果，就以房间 payload 为唯一真相源

### 13.2 商店支持的动作

- 买牌
- 买遗物
- 买药水
- 删牌
- 离开

### 13.3 稳定性约束

- 库存在进入商店后固定
- 价格在离开前固定
- 已购买项目不能再次购买
- 删牌服务只能使用一次
- 金币不足时动作失败但不改变房间状态

第一轮价格规则明确为：

- 卡牌：`50`
- 遗物：`150`
- 药水：`60`
- 删牌：按 run 级递增价格计算，初始 `75`

删牌价格规则对齐当前公开 STS2 指南信息：

- 本 run 第 1 次删牌：`75`
- 本 run 第 2 次删牌：`100`
- 第一轮不再继续外推更高档位，后续若要严格对齐 live build 再补

为支持这条规则，`RunState` 需要新增类似：

- `card_removal_count`
- 或 `next_card_removal_cost`

失败动作规则明确为：

- 金币不足：返回当前商店，不改 `RunState`，记录错误消息到房间或会话输出
- 目标已被购买：返回当前商店，不改状态
- 删牌已使用：返回当前商店，不改状态
- 删牌目标不存在：返回当前商店，不改状态

### 13.4 运行态修改

购买与删牌会直接修改 `RunState`：

- `gold`
- `deck`
- `relics`

商店本身不直接修改 `ActState`，只在离开时交还控制给地图流程。

## 14. 休息点设计

### 14.1 动作

- `heal`
- `smith`

### 14.2 Heal

`heal` 直接修改 `RunState.current_hp`，本次规则固定为：

- 回复 `30%` 最大生命值
- 回复后不超过 `RunState.max_hp`
- 不受遗物、事件或其他修正影响

这里与公开 STS2 指南对齐。后续如果引入 campfire 相关 relic，再单独扩展。

### 14.3 Smith

`smith` 进入 `select_upgrade_card` 子状态，列出当前牌组内所有可升级卡。选择后升级目标牌，并结束房间。

这里明确状态机：

1. `RoomState.stage = "waiting_input"`，展示 `heal / smith / leave`
2. 选择 `smith` 后，切换到 `RoomState.stage = "select_upgrade_card"`
3. `payload["upgrade_options"]` 保存当前可升级实例列表
4. 用户选择一张牌后执行升级，房间切到 `stage = "completed"`
5. 用户返回地图

取消行为明确为：

- 在 `select_upgrade_card` 阶段允许返回休息点根菜单
- 返回不会消耗休息点机会
- 一旦升级完成，不能再次进入 `smith`

### 14.5 Boss 结算终点

本项目当前目标是单 Act 闭环，因此 boss 的最终流转明确为：

1. 打败 boss 后进入 boss 奖励阶段
2. 领取完奖励后不返回地图
3. `RunState` 标记为胜利完成，`SessionState.run_phase` 切到 `victory`
4. renderer 渲染胜利/通关画面

也就是说：

- `boss` 房间仍然有奖励阶段
- 但 boss 不是“回地图的另一种战斗房”
- boss 奖励领取完毕就是当前 run 终点

### 14.4 升级模型

优先复用现有 `CardDef.upgrades_to` 字段。升级逻辑定义为：

- 卡牌定义声明升级目标
- 运行态牌组保存卡牌实例 ID 列表
- 强化时把该实例对应的 card id 替换为升级后的 card id，并保留稳定实例后缀或按新规则生成实例 ID

本次推荐保留实例后缀，仅替换 card id 前缀，以减少对现有牌组与手牌逻辑的冲击。

## 15. 卡牌与牌组约束

这轮商店删牌和休息点强化都会直接触碰 `RunState.deck`。因此需要明确：

- 内容定义是 `card_id`
- 运行态牌组是实例 ID 列表
- 买牌是向牌组加入新实例
- 删牌是移除一个实例
- 强化是将某个实例的 card id 替换为其 `upgrades_to`

第一轮不处理“已在当前战斗牌堆中的同名实例同步升级”这种复杂情况，因为 campfire 只发生在非战斗房间，影响的是长期牌组，不影响当前 `CombatState`。

## 16. 终端 UI 影响

### 16.1 地图

新增两个展示层能力：

- 当前可走节点列表
- 完整地图视图

完整地图不要求复杂 ASCII 美术，但至少要能看出：

- 每层节点
- 节点房型
- 当前所在位置
- 已访问节点
- 从当前节点出发的可达选择

### 16.2 商店

商店屏幕分区建议为：

- 顶部摘要：金币、角色 HP、当前 Act / 楼层
- 中部：卡牌区、遗物区、药水区、删牌服务区
- 底部：可执行操作

### 16.3 休息点

休息点至少支持两层画面：

- 根菜单：回血 / 强化 / 离开
- 强化选牌：列出可升级卡

商店也采用明确的最小状态机：

1. `RoomState.stage = "waiting_input"`，展示库存与根菜单
2. 选择买牌、买遗物或买药水时直接结算，成功后留在当前商店
3. 选择删牌时切到 `RoomState.stage = "select_remove_card"`
4. `payload["remove_candidates"]` 保存当前可删实例列表
5. 完成删牌后回到商店根菜单，但 `remove_used = true`
6. 用户选择离开后，房间 `stage = "completed"` 并返回地图

`select_remove_card` 阶段也允许取消并返回商店根菜单，且取消不消耗删牌服务。

### 16.4 交互风格

继续保持中文文案和数字菜单，不切换到坐标输入协议。即使底层节点有 `row/col`，用户仍然输入序号即可。

## 17. 测试策略

### 17.1 Domain

新增或改造测试覆盖：

- 相同种子生成相同地图
- 地图总能从起点到达 boss
- 非 boss 节点至少有一条出边
- 房型约束生效
- 当前可达节点计算正确

### 17.2 Use Cases

新增测试覆盖：

- 进入 `shop/rest`
- 商店购买牌、遗物与药水
- 商店删牌一次性约束
- 商店删牌 run 级价格递增
- 休息点回血
- 休息点强化
- 离开房间后返回地图

### 17.3 Terminal / E2E

补充终端和 e2e 覆盖：

- 完整地图查看
- 从地图进入商店
- 从地图进入休息点
- 商店多步交互后返回地图
- 商店药水购买
- 休息点强化后继续推进 run

## 18. 实施顺序

建议按以下顺序实现：

1. 重构 `ActDef / ActState / map_generator`
2. 接通地图选择与完整地图视图
3. 扩展 `RunState / SessionState` 数据模型
4. 扩展 `enter_room`，正式支持 `shop/rest`
5. 完成 `shop_action` 的库存、价格、删牌逻辑
6. 完成 `rest_action` 的回血与强化逻辑
7. 更新 `session.py` 流转与 run 终局
8. 更新 Rich 终端渲染
9. 补齐测试并跑全量验证

## 19. 风险与缓解

### 19.1 地图生成过于随意导致不可玩

缓解：先做保守规则和强约束测试，不追求高随机度。

### 19.2 商店和休息点把 `RoomState` 搞成大杂烩

缓解：将各房型 payload 控制为各自的小结构，不把通用字段和房型专用字段混写成平铺大字典。

### 19.3 UI 改动反向污染规则层

缓解：地图全图视图与商店列表都从状态推导，不允许 renderer 直接决定规则结果。

### 19.4 内容文件修改遗漏

缓解：若本轮新增药水、升级卡、商店遗物或地图配置字段，需要同时更新源码内容目录与打包内容目录，避免测试环境和打包运行时读取不同数据。

## 20. 推荐方案总结

本次采用“模板 + 生成器”的中间路线：

- Act 内容文件定义地图规则，不定义完整路径
- 运行时用 seed 生成完整分层图
- `ActState` 保存生成后的图
- 地图决策只允许选当前可达节点
- UI 额外支持完整地图查看
- 商店与休息点都以稳定的房间 payload 驱动多步交互
- 商店类别与休息点动作模型优先向 STS2 Early Access 的公开表现靠拢

这条路线最适合当前仓库现状：改动集中、实现成本可控、能显著提升可玩性，并且为后续继续加房型、地图规则、内容池和奖励系统留下自然扩展位。
