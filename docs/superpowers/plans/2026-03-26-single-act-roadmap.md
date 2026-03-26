# Single-Act Roadmap After Inspect Menus

Date: 2026-03-26
Status: Active TODO priority baseline, updated after Phase 1/2 closure and initial Phase 3 expansion

## 1. 背景

inspect、统一菜单定义层、基础中文化和 CLI 入口已经接入 `main`，当前项目从“只能勉强跑通战斗骨架”进到“已有可检查资料、可存读档、可从终端稳定游玩”的阶段。

下一步不应继续优先做零散修补，而应把后续 TODO 收束到“单 Act 可玩闭环”这条主线上。

这份文档的作用是：

- 作为后续 TODO 的默认优先级基线
- 避免功能开发被局部体验优化反复打断
- 明确什么是当前阶段最值得投入的内容

除非用户明确重新排序，否则后续开发默认按本路线推进。

## 2. 当前判断

结合当前代码与测试，以下事项已经不再是主要短板：

- 单 Act 主流程已经能稳定经过 `combat / event / shop / rest / reward / boss / terminal`
- `boss_pool_id` 已指向独立的 `act1_bosses`，Hexaghost 也已接入真实战斗
- 普通敌人、事件、奖励卡、遗物、药水都已完成过第一轮扩充

当前仍然明显偏薄的部分主要是：

- Boss 奖励仍复用普通战斗奖励逻辑，缺少高潮节点应有的档次感
- 内容池虽然不再是“只有骨架”，但重复游玩差异仍然偏低
- 更接近原版的敌人 AI / 奖励层级 / 内容分层还没补齐

因此，后续开发优先级调整为：

1. 先补齐独立 Boss 的奖励与收尾体验
2. 再继续扩充内容池和体验深度
3. 最后再补更高保真的原版细节

## 3. 优先级原则

未来 TODO 默认遵循以下原则：

- 优先做“能把一局游戏闭环补完整”的功能
- 优先做“能验证现有架构是否站得住”的功能
- 优先做“会显著提升重复游玩差异”的内容
- 不优先做纯视觉微调，除非它阻碍可玩性
- 不优先做高保真原版复刻，先保证可玩闭环

## 4. 路线总览

### Phase 1: 补齐单 Act 主循环

这是最高优先级。

目标：

- 让一局游戏稳定经过 `combat / event / shop / rest / reward / boss / terminal`
- 让地图推进、房间进入、房间离开、奖励领取、终局判定形成真正闭环

为什么先做：

- 这是从“功能集合”走向“完整 run”最关键的一步
- inspect、菜单定义层、存读档、终端渲染都需要在真实长流程下接受验证
- 主循环不完整时，后面加 Boss 和扩内容都容易返工

建议拆分顺序：

- [x] 1.1 接通地图中实际可进入的 `shop / rest` 路径，确保不只是存在独立 use case
- [x] 1.2 补全房间进入后到离开的状态流转，包括返回地图和下一节点选择
- [x] 1.3 补齐奖励房和 boss 后收尾逻辑，避免“打完了但流程没有正式结束”
- [x] 1.4 对终局页、失败页、胜利页做一轮一致性检查，保证菜单、提示和恢复逻辑稳定

完成标准：

- 可以从 `new --seed <n>` 开始稳定玩完一局单 Act
- 过程中能真实经过商店和休息点
- Boss 战后能进入明确的胜利收尾，而不是停留在临时状态
- 存档读档不会破坏当前房间和后续推进

测试锚点：

- `tests/e2e/test_single_act_smoke.py`
- `tests/use_cases/test_room_recovery.py`
- `tests/use_cases/test_shop_and_rest_actions.py`
- 与 `session.py` 菜单路由相关的终端测试

### Phase 2: 引入真正的 Boss 内容

这是第二优先级。

目标：

- 不再让 `boss_pool_id` 复用精英池
- 为 Act 1 提供至少 1 个真正的 Boss 定义和完整战斗体验

为什么排在第二：

- Boss 是单幕闭环最关键的高潮节点
- 但在地图主循环不稳定前，先做 Boss 会把问题掩盖在内容层

建议拆分顺序：

- [x] 2.1 新增独立 Boss content，而不是继续复用 `act1_elites`
- [x] 2.2 为 Boss 增加与普通精英明显不同的招式表与节奏
- [ ] 2.3 补齐 Boss 战前后文案、奖励和终局衔接

完成标准：

- `content/` 和 `src/slay_the_spire/data/content/` 同步存在独立 Boss 数据
- 地图终点真正读取 `boss_pool_id`
- 玩家能明确感知 Boss 与精英不是同一层级内容

测试锚点：

- `tests/content/test_registry_validation.py`
- `tests/domain/test_combat_flow.py`
- `tests/e2e/test_single_act_smoke.py`

### Phase 3: 扩充内容池

这是第三优先级。

目标：

- 提升重复游玩差异
- 让 inspect、奖励、商店、事件这些系统承载更多真实选择

为什么排在第三：

- 内容扩充很重要，但在主循环和 Boss 没立住前，新增内容的验证成本很高
- 先立住流程，再扩内容，能更快发现哪些系统边界还不够

建议拆分顺序：

- [x] 3.1 增加普通敌人
- [x] 3.2 增加事件
- [x] 3.3 增加战斗奖励卡和可购买卡
- [x] 3.4 增加遗物
- [x] 3.5 增加药水

完成标准：

- 普通战斗、事件、商店奖励不再高频重复同一批内容
- inspect 页能稳定展示新增对象的中文说明
- 内容新增不会破坏现有终端菜单和存档流程

测试锚点：

- `tests/content/test_registry_validation.py`
- `tests/use_cases/test_apply_reward.py`
- `tests/use_cases/test_event_actions.py`
- `tests/adapters/terminal/test_widgets.py`

## 5. 当前不优先的事项

以下事项目前不应默认抢占前三阶段：

- inspect 页的纯视觉再美化
- 更复杂的关键词系统
- 更高保真的原版敌人 AI 细节
- 多角色
- 多 Act 串联
- 更复杂的地图算法优化
- 高级商店机制和 campfire 扩展动作

这些内容不是不做，而是默认排在“单 Act 可玩闭环 + 独立 Boss + 内容扩充”之后。

## 6. 执行建议

后续每次开新 TODO，默认先问这三个问题：

1. 这项工作是否直接推进单 Act 主循环闭环？
2. 如果不是，它是否直接推进独立 Boss 落地？
3. 如果还不是，它是否显著提升内容池和重复游玩差异？

如果三个问题都不是，默认说明这项工作不该排在当前最前面。

## 7. 默认下一项

如果没有新的用户重排，下一项默认应是：

- `补齐独立 Boss 的奖励与收尾体验`

更具体地说，优先为 Boss 战补齐更有层级感的奖励、战前后文案与终局收尾一致性，并继续以 e2e 冒烟测试和奖励流转测试作为主要验收锚点。
