# Boss Rewards Design

Date: 2026-03-26
Status: Draft for review

## 1. 背景

当前项目已经具备从开局、走图、战斗、事件到 Boss 房与终局的单 Act 可玩流程，但奖励层仍有一个明显缺口：

- 普通战斗、精英战、Boss 战目前都复用 `room_state.rewards: list[str]`
- Boss 战后并没有独立的奖励规则，只是沿用普通掉落形态
- 这与原版《Slay the Spire》“Boss 奖励显著高于普通战斗”的方向不一致

本轮目标不是一次性重做整个奖励系统，而是在不打断当前单 Act 流程的前提下，先把 Boss 奖励拆成一套单独规则：

- 更高金币
- 独立 Boss 遗物池
- 明确的专属奖励位
- 终端菜单下的两级选择流程

## 2. 目标

- Boss 战后不再复用普通 `rewards` 列表语义
- 引入独立的 Boss 奖励数据结构
- Boss 奖励包含：
  - 单独金币位
  - 单独遗物位
- Boss 遗物位使用独立 `boss_relics` 池
- 终端交互改为两级菜单：
  - 主菜单：`领取金币 / 选择遗物`
  - 次级菜单：三选一 Boss 遗物
- 当且仅当 Boss 金币已领且 Boss 遗物已选时，Boss 房结束并进入 `victory`

## 3. 非目标

- 不统一重构普通战斗、事件、Boss 的全部奖励模型
- 不在本轮加入药水位、钥匙位、卡牌位等更多 Boss 奖励槽
- 不追求完整原版全部 Boss 遗物池规模
- 不在本轮引入遗物稀有度框架
- 不为普通奖励房新增“多层级奖励菜单”

## 4. 设计选择

本轮采用：

- **Boss 奖励独立建模，但不重构普通奖励系统**

不采用：

- 继续把 Boss 奖励硬塞进 `room_state.rewards`
- 一次性把所有奖励房都改造成统一槽位系统

原因：

- 继续复用 `rewards: list[str]` 会让 Boss 奖励与普通奖励在语义上进一步纠缠
- 当前项目的普通奖励流程已可用，没有必要为了 Boss 奖励去扩大为全局重构
- 先把 Boss 奖励拆出来，既能满足当前设计目标，也能为后续扩展保留空间

## 5. 范围

### In Scope

- 为 Boss 战新增独立奖励生成逻辑
- 为 Boss 房 `payload` 新增结构化 `boss_rewards`
- 新增独立 `boss_relics` 内容池
- 新增至少 3 个可选 Boss 遗物
- 为 Boss 奖励新增两级菜单与终端渲染
- 为 Boss 奖励补充会话流转、存档恢复和测试覆盖

### Out of Scope

- 普通 `combat` / `elite` 奖励模型重构
- 全局奖励槽系统抽象
- 多幕、多角色差异化 Boss 奖励
- 遗物详情弹窗、确认弹窗、悬浮预览等附加 UI

## 6. 奖励模型

### 6.1 普通奖励与 Boss 奖励分离

普通房间保持现状：

- `combat` / `elite` 仍使用 `generate_combat_rewards()`
- 奖励仍写入 `room_state.rewards`

Boss 房改为：

- Boss 战胜利后不再写 `room_state.rewards`
- 改为写入 `room_state.payload["boss_rewards"]`

这意味着：

- `room_state.rewards` 只保留“普通逐项领取奖励”的语义
- Boss 奖励走独立结构，不再混入普通奖励字符串列表

### 6.2 Boss 奖励结构

建议 `payload["boss_rewards"]` 结构如下：

```python
{
    "generated_by": "boss_reward_generator",
    "gold_reward": 108,
    "claimed_gold": False,
    "boss_relic_offers": ["black_blood", "anchor", "lantern"],
    "claimed_relic_id": None,
}
```

字段语义：

- `gold_reward`：本次 Boss 奖励的金币数
- `claimed_gold`：金币位是否已领取
- `boss_relic_offers`：可选 Boss 遗物 ID 列表
- `claimed_relic_id`：玩家最终选定的遗物；未选择时为 `None`
- `generated_by`：用于存档恢复与调试，标识奖励来源

本轮不额外增加 `claimed_slots` 之类的冗余字段，以最小结构表达完整状态。

## 7. 交互与状态流转

### 7.1 Boss 奖励主菜单

Boss 奖励主菜单固定为两项动作：

1. `领取金币`
2. `选择遗物`

另加通用返回项：

3. `返回上一步`

状态变化后，菜单标签应显式反映当前进度：

- 金币已领后，第 1 项显示 `已领取金币`
- 遗物已选后，第 2 项显示 `已选择遗物`

### 7.2 Boss 遗物次级菜单

玩家在主菜单选择 `选择遗物` 后，进入次级菜单：

1. `黑色之血`
2. `锚`
3. `灯笼`
4. `返回上一步`

若 `boss_relic_offers` 少于 3 个，则只显示实际候选数。

### 7.3 完成条件

Boss 房奖励领取不再等价于“清空一个字符串列表”，而采用显式完成条件：

- `claimed_gold is True`
- `claimed_relic_id is not None`

只有同时满足以上两点时：

- Boss 奖励阶段结束
- Boss 房视为已完全结算
- `run_phase` 切换为 `victory`

因此：

- 先领金币不会直接结束 Boss 房
- 先选遗物不会直接结束 Boss 房
- 必须两个奖励位都完成，才进入终局

### 7.4 与现有根菜单衔接

Boss 房战斗胜利后：

- 根菜单仍应保留 `查看奖励 / 领取奖励`
- 进入奖励界面时，若房间存在 `boss_rewards`，则走 Boss 奖励菜单而不是普通奖励菜单

这样可以尽量保持现有菜单层级不变，仅在奖励分支内区分 Boss 与非 Boss。

## 8. 内容设计

### 8.1 独立 Boss 遗物池

新增内容文件：

- `content/relics/boss_relics.json`
- `src/slay_the_spire/data/content/relics/boss_relics.json`

两份文件必须保持同步，因为默认运行优先读取打包内容目录。

### 8.2 首批 Boss 遗物

首轮建议先放 3 个可实际生效的 Boss 遗物：

- `black_blood`
- `anchor`
- `lantern`

目标不是完整复刻原版全部池子，而是先满足：

- 奖励池独立存在
- 三选一流程完整可玩
- 遗物效果确实能在运行时体现

### 8.3 特殊遗物规则

`black_blood` 为升级型起始遗物，应采用替换规则：

- 若玩家拥有 `burning_blood`
- 选择 `black_blood` 时应移除 `burning_blood`
- 再把 `black_blood` 加入 `run_state.relics`

不应简单叠加，否则会造成起始遗物与升级遗物并存。

## 9. 生成规则

### 9.1 生成入口

保留现有：

- `generate_combat_rewards(room_id, seed)`

新增：

- `generate_boss_rewards(room_id, seed, run_state, registry)`

用途区分：

- 普通战斗和精英战继续使用现有生成器
- Boss 战只使用新的 Boss 奖励生成器

### 9.2 金币规则

Boss 金币不再复用普通战斗掉落公式。

本轮建议使用一个稳定、可测试、明显高于普通战斗的规则，例如：

- `90 + (seed % 21)`

也就是稳定落在 `90-110` 区间。

这里的重点不是完美复刻原版数值，而是先建立“Boss 金币显著更高”的规则边界。

### 9.3 Boss 遗物抽样规则

Boss 遗物生成采用以下规则：

- 候选来源必须是独立 `boss_relics` 池
- 默认排除玩家当前已拥有的遗物
- 最多抽取 3 个不同候选
- 若可选遗物数量不足 3，则返回当前可选数量
- 不强行补重复项

这样可以保证：

- 候选有效
- 结果可预测、可测试
- 不会生成明显无意义的重复奖励

## 10. 代码落点

### 10.1 领域与用例

修改：

- `src/slay_the_spire/domain/rewards/reward_generator.py`
- `src/slay_the_spire/use_cases/apply_reward.py`

职责：

- 新增 Boss 奖励生成器
- 新增 Boss 遗物应用逻辑
- 支持升级型遗物替换规则

### 10.2 会话流转

修改：

- `src/slay_the_spire/app/session.py`

职责：

- Boss 战胜利后写入 `payload["boss_rewards"]`
- 新增 Boss 奖励主菜单与遗物次级菜单路由
- 在 Boss 金币/遗物领取后刷新房间状态
- 仅在两个奖励位都完成时切换 `run_phase="victory"`

### 10.3 菜单与渲染

修改：

- `src/slay_the_spire/app/menu_definitions.py`
- `src/slay_the_spire/adapters/terminal/screens/non_combat.py`

职责：

- 新增 Boss 奖励主菜单定义
- 新增 Boss 遗物次级菜单定义
- 在奖励面板中按“金币位 + 遗物位”展示 Boss 奖励状态

## 11. 存档兼容

本轮建议保持保守兼容：

- 不升级 `RoomState.schema_version`
- 不改变旧房间对 `rewards` 的依赖
- 仅在新的 Boss 结算房间中写入 `payload["boss_rewards"]`

兼容结果应为：

- 旧存档没有 `boss_rewards` 时，普通流程仍可正常加载
- 新存档中的 Boss 奖励状态可被恢复，并继续完成奖励领取

## 12. 测试策略

### 12.1 领域测试

- `generate_boss_rewards()` 会返回更高金币
- Boss 遗物候选来自 `boss_relics` 池
- 已持有遗物不会重复进入候选
- 候选数量不足时不会生成重复项

### 12.2 用例 / 会话测试

- Boss 战胜利后生成 `payload["boss_rewards"]`，且 `room_state.rewards == []`
- 领取 Boss 金币后不会直接进入 `victory`
- 选择 Boss 遗物后若金币未领，仍停留在 Boss 奖励阶段
- 两个奖励位都完成后才进入 `victory`
- `black_blood` 会正确替换 `burning_blood`
- Boss 奖励状态在保存 / 读取后不丢失

### 12.3 终端 / 菜单测试

- Boss 奖励主菜单编号正确
- Boss 遗物次级菜单编号正确
- 金币已领 / 遗物已选时菜单文案正确
- 通过 inspect 往返后，Boss 奖励菜单编号不漂移

## 13. 验收标准

- Boss 战后不再复用普通 `room_state.rewards` 流程
- Boss 房奖励能显示为“领取金币 / 选择遗物”的两级菜单
- 玩家能从独立 `boss_relics` 池中三选一
- Boss 金币和 Boss 遗物都完成后才进入 `victory`
- `black_blood` 等升级型遗物不会与 `burning_blood` 并存
- 内容双目录同步，默认运行与打包结果一致
