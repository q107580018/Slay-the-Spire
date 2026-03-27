# Reward Menu Simplification Design

Date: 2026-03-27
Status: Approved for implementation

## 背景

当前奖励与战斗根菜单存在三处体验问题：

- 战斗根菜单中的“查看战场”只会重复展示当前页面，没有独立价值
- 普通奖励根菜单额外包了一层“奖励主页/查看奖励详情”，流程冗余，且返回链路容易卡住
- 领取奖励后无论是否还有未处理奖励，都会直接退回主菜单，打断连续操作

## 目标

- 删除战斗根菜单中的“查看战场”
- 删除普通奖励根菜单中的“查看奖励”
- 删除普通奖励的“奖励主页 / 奖励详情列表 / 奖励详情”整套流程
- 普通奖励在未处理完前持续停留在奖励菜单
- Boss 奖励在未全部处理完前持续停留在 Boss 奖励菜单

## 非目标

- 不重构 inspect 资料页
- 不新增新的奖励类型或奖励槽位
- 不改变 Boss 奖励完成后进入下一幕 / 胜利的既有规则
- 不为 Textual 单独增加与 Rich 渲染不同的奖励交互

## 设计

### 1. 根菜单精简

- 战斗中的根菜单直接从“出牌”开始，不再提供“查看战场”
- 已结算且存在普通奖励的根菜单只保留“领取奖励”
- 已结算且存在待领取 Boss 奖励的根菜单也只保留“领取奖励”

### 2. 普通奖励改为单层领取流

- 根菜单进入后直接进入 `select_reward`
- `select_reward` 继续承担：
  - 逐项领取
  - 跳过卡牌奖励
  - 全部领取
  - 返回上一步
- 删除普通奖励详情相关菜单模式：
  - `inspect_reward_root`
  - `inspect_reward_list`
  - `inspect_reward_detail`

### 3. 领取后的停留规则

普通奖励：

- 若领取后 `room_state.rewards` 仍非空，则保持 `menu_state.mode == "select_reward"`
- 若奖励已清空，则回到根菜单

Boss 奖励：

- 若只领取了金币，且遗物未选，则保持 `menu_state.mode == "select_boss_reward"`
- 若只选择了遗物，且金币未领，则保持在 Boss 奖励流
- 只有当金币与遗物都完成后，才进入既有的 Boss 奖励完成逻辑

## 影响文件

- `src/slay_the_spire/app/menu_definitions.py`
- `src/slay_the_spire/app/session.py`
- `tests/app/test_menu_definitions.py`
- `tests/app/test_inspect_menus.py`

## 验证

- 菜单定义测试覆盖编号与 action 映射
- 奖励流测试覆盖：
  - 根菜单不再暴露“查看战场”和“查看奖励”
  - 普通奖励领取后在未清空前停留在奖励菜单
  - Boss 奖励领取后在未完成前停留在 Boss 奖励菜单
