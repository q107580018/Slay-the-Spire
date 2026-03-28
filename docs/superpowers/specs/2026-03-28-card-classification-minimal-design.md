# 卡牌分类最小升级设计

## 目标

在不扩展到多职业、无色牌池、完整奖励规则重写和 `CardInstance` 结构重构的前提下，补齐当前卡牌模型缺失的基础分类维度，并确保 `rich` / `textual` 界面渲染不出现错误。

## 范围

- 为 `CardDef` 新增显式 `card_type`
- 为 `CardDef` 新增轻量 `acquisition_tags`
- 区分 `status` 和 `curse`
- 将现有查看页、详情页、奖励筛选接到新字段
- 保持现有 `rarity`、`playable`、`can_appear_in_shop`、`exhausts` 兼容

## 非目标

- 不新增 `Colorless`
- 不新增多职业抽象
- 不重写完整奖励系统
- 不把字符串实例 id 重构为完整 `CardInstance`

## 数据模型

- `card_type` 允许值：
  - `attack`
  - `skill`
  - `power`
  - `status`
  - `curse`
- `acquisition_tags` 允许值：
  - `starter`
  - `combat_reward`
  - `shop`
  - `event`
  - `generated`
  - `status`
  - `curse`

## 内容映射

- 铁甲战士普通牌补齐 `card_type`
- `doubt` / `injury` 标记为 `curse`
- `burn` 标记为 `status`
- 奖励池中的普通卡标记 `combat_reward`
- 起始套牌相关卡标记 `starter`

## 逻辑调整

- UI 不再从效果推导卡牌类型，统一读取 `card_type`
- 普通战斗奖励只从带 `combat_reward` 的卡中抽取
- 商店逻辑仍沿用 `can_appear_in_shop`

## 验证

- 内容校验测试覆盖新字段合法性
- `rich` inspect / renderer 测试覆盖类型渲染
- `textual` 预览测试覆盖类型渲染一致性
- 奖励测试覆盖 `status` / `curse` 不进入普通战斗奖励

## 后续 TODO

- 将商店卡牌筛选从 `can_appear_in_shop` 逐步迁移到 `acquisition_tags`，并在迁移完成后删除重复来源开关
- 将普通战斗奖励之外的来源规则继续并入 `acquisition_tags` / 独立来源配置，覆盖精英、Boss、事件和生成牌，而不是继续依赖隐式约定
- 当项目开始接入第二职业或无色牌池时，让奖励和商店真正按角色/牌池过滤，而不是只靠全局卡表 + 标签
- 当战斗内开始需要临时费用、保留、临时生成、战斗后移除等状态时，引入真正的 `CardInstance` 结构，替代纯字符串实例 id
