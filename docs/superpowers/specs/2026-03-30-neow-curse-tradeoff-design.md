# 设计规范：Neow 诅咒代价高价值奖励修正

**日期：** 2026-03-30  
**状态：** 已确认，待实现

---

## 背景

当前 opening 阶段的 `Neow` tradeoff 选项里，`curse_card` 被建模为一种“奖励类型”：

- 奖励侧会发 1 张诅咒牌
- 代价侧又会再加入 1 张固定诅咒牌

这会产生“奖励和代价都是诅咒”的错误语义，与原版《Slay the Spire》不一致，也会让悬浮预览和面板文案误导玩家。

本次只修正这一点，不重做整个 `Neow` 奖励系统。

---

## 目标

将当前 tradeoff 中的诅咒相关选项改为：

- `诅咒` 只作为代价出现
- 一旦代价是 `诅咒`，奖励必须是“高价值奖励”
- 保持现有 opening 会话结构、编号菜单、Textual 悬浮预览和单步结算流程

---

## 非目标

- 不把整个 `Neow` 流程改成原版完整四槽规则
- 不新增 `Neow's Lament`
- 不实现“选择 1 张稀有牌三选一”
- 不实现“变形 2 张牌”之类新的多目标 opening 交互
- 不把 `Neow` 奖励改为 content JSON 驱动

---

## 推荐方案

保留当前 `2` 个 free offer + `2` 个 tradeoff offer 的整体结构，只替换 tradeoff 中错误的 `curse_card` 语义。

具体做法：

1. 用新的 reward kind 表达“诅咒代价换高价值奖励”，例如 `curse_bonus`
2. `curse_bonus` 固定带 `cost_kind == "curse"`
3. `curse_bonus` 的奖励从现有项目已经支持的高价值奖励池中抽取
4. 渲染层和 hover preview 直接按“高价值奖励 + 诅咒代价”展示

这样能用最小改动修正行为，又不会把本次任务扩成 Neow 全量重构。

---

## 奖励模型

### 现状问题

当前 `reward_kind == "curse_card"` 时：

- `reward_payload` 是 1 张诅咒牌
- `cost_payload` 也是 1 张诅咒牌

这一定要被移除。

### 新模型

将当前的诅咒分支改为：

- `reward_kind == "curse_bonus"`
- `cost_kind == "curse"`
- `cost_payload["card_id"]` 为加入牌组的诅咒
- `reward_payload` 为一个高价值奖励的实际内容

`curse_bonus` 的 `summary` 不应再写成“获得诅咒牌”，而应直接写成奖励本体，例如：

- `获得 250 金币`
- `获得稀有遗物`
- `获得稀有牌`

并在 detail/preview 中额外写明代价：

- `牌组中加入诅咒牌：<名称>`

---

## 高价值奖励池

本次高价值奖励只允许从当前项目已经有能力稳定承接的奖励里选择，避免引入新的 UI 或 use case。

建议奖励池：

- `250 金币`
- `1` 个随机稀有遗物
- `1` 张随机稀有牌

不纳入本次范围的奖励：

- 选择 1 张稀有牌
- 选择 1 张稀有无色牌
- 变形 2 张牌
- 移除 2 张牌
- 大幅增加最大生命

原因是这些要么缺少 opening 交互支持，要么会把这次修复扩大成新的系统设计。

---

## 代价规则

诅咒代价保持当前 opening 的简单模型：

- 代价类型仍为 `cost_kind == "curse"`
- 结算时将对应诅咒实例加入 `run_blueprint.deck`

诅咒来源规则：

- 可以沿用当前实现的固定 `doubt`
- 也可以改为从 curse 池随机抽 1 张

本次推荐沿用固定 `doubt`，因为这样改动更小、测试更稳定，也不影响“诅咒只能作为代价”的目标。

---

## 生成逻辑

`_pick_tradeoff_reward_kind()` 不再返回 `curse_card`，而返回 `curse_bonus`。

`_build_offer()` 对 `curse_bonus` 的处理规则：

- `_build_reward_payload()` 从高价值奖励池抽取一个实际奖励
- `_build_cost_payload()` 返回固定诅咒代价
- `requires_target` 为 `None`

这意味着诅咒 tradeoff 仍然是一步结算，不进入目标卡子菜单。

---

## 奖励结算

`_apply_reward()` 需要支持 `curse_bonus`。

其行为应当是：

1. 先由 `_apply_cost()` 把诅咒加入牌组
2. 再按 `reward_payload` 里记录的真实奖励结算收益

为了避免把逻辑写散，推荐让 `reward_payload` 显式携带底层奖励类型，例如：

- `reward_type: "gold"`
- `reward_type: "relic"`
- `reward_type: "card"`

以及对应字段：

- `amount`
- `reward_id`
- `relic_id`
- `card_id`

这样 `curse_bonus` 在结算时只需要分发到现有 `apply_reward()` 或现有 potion/card/relic 写回逻辑。

---

## 文案与渲染

需要同步修正：

- `opening_renderer.py` 中的 opening 面板详情
- `slay_app.py` 中的 hover preview

显示原则：

- 奖励首行写实际收益，而不是“获得诅咒牌”
- 代价单独标明“牌组中加入诅咒牌：xxx”
- 中文文案保持与现有 opening 文案风格一致

示例文案：

- `获得 250 金币`
- `代价：牌组中加入诅咒牌：疑虑`

或

- `获得稀有遗物：黑血`
- `代价：牌组中加入诅咒牌：疑虑`

---

## 测试策略

先写失败测试，再改实现。

至少补这些测试：

1. `tests/use_cases/test_opening_flow.py`
   - `curse_bonus` offer 的 `cost_kind` 是 `curse`
   - `curse_bonus` 的奖励不是诅咒牌
   - 应用后牌组新增 1 张诅咒，同时获得高价值奖励

2. `tests/adapters/textual/test_slay_app.py`
   - `curse_bonus` 的 hover preview 展示真实奖励
   - preview 同时展示诅咒代价，不再把诅咒写成奖励本体

3. 如有必要，补 `tests/adapters/presentation/test_presentation_renderer.py`
   - opening 内联面板中的详情文案正确区分奖励与代价

---

## 风险与约束

主要风险不是结算，而是语义残留：

- 旧的 `curse_card` 命名如果残留在 summary、测试名或分支里，后续容易再次误读
- 如果 `reward_payload` 结构设计得不清楚，`curse_bonus` 会变成一个新的特殊分支泥团

因此本次实现要避免“名字没改、只是把内部逻辑偷偷换掉”这种半修复状态。

---

## 验收标准

满足以下条件即可视为完成：

1. opening 中不会再出现“奖励是诅咒牌，代价还是诅咒牌”的 `Neow` 选项
2. 诅咒相关 tradeoff 一定表现为“加入诅咒牌 + 获得高价值奖励”
3. 奖励与代价在 opening 面板和 hover preview 中都能被明确区分
4. 相关测试覆盖生成、结算和展示
5. `README.md` 与 `AGENTS.md` 同步更新为最新行为描述
