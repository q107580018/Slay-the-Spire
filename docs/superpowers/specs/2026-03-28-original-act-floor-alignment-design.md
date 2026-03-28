# Original Act Floor Alignment Design

Date: 2026-03-28
Status: Draft for review

## 1. 背景

当前项目的 `act1` 和 `act2` 已经支持分支地图、战斗、事件、商店、休息点、精英、Boss 和跨幕推进，但地图层数与原版《Slay the Spire》1 代并不一致：

- `act1` 当前 `floor_count = 13`
- `act2` 当前 `floor_count = 15`
- 地图最后一层直接是 Boss
- Boss 奖励领取完成后直接切下一幕或胜利

这与原版普通 Act 的固定楼层结构不一致。用户本轮明确要求只对齐现有 `act1/act2`，不补 `act3`，并按原版口径补齐固定楼层和 Boss 后流程。

## 2. 目标

- 让当前项目的 `act1` 和 `act2` 采用原版普通 Act 的固定楼层口径
- 对齐以下固定楼层规则：
  - `Floor 1` 普通战
  - `Floor 9` 宝箱
  - `Floor 15` 休息点
  - `Floor 16` Boss
  - `Floor 17` Boss Chest / 过幕
- 新增真实可交互的 `treasure` 房间
- 新增 Boss 后的 `boss_chest` 过渡房间
- 保持当前项目仍只做到 `act1 -> act2 -> victory`

## 3. 非目标

- 不在本轮补 `act3`
- 不实现原版 `Act 4`
- 不实现原版宝箱钥匙、不同宝箱档位、蓝宝箱、诅咒宝箱等扩展规则
- 不重写整个会话状态机或菜单系统
- 不把地图层和所有非地图层拆成全新的大型状态机

## 4. 设计选择

本轮采用：

- **数据驱动的固定楼层与 Boss 后流程配置**

不采用：

- 直接在生成器里写死多个原版常量分支
- 只把 `floor_count` 改大，不补 `treasure` 和 `boss_chest`
- 一次性重构整套地图外流程模型

原因：

- 当前项目已将 Act 地图配置放在内容 JSON 中，继续用配置扩展更符合现有结构
- 固定楼层与 Boss 后房间属于规则层，不应散落在 `session.py` 和生成器的硬编码条件里
- 数据驱动方案更方便后续补 `act3`，也便于测试

## 5. 总体方案

### 5.1 Act 配置扩展

扩展 `ActMapConfig`，在现有 `floor_count`、`boss_room_type`、`room_rules` 之外新增两类配置：

- 地图内固定楼层规则
- Boss 后固定房间类型

建议的配置语义：

- `fixed_floor_room_types`
  - 例如 `{1: "combat", 9: "treasure", 15: "rest", 16: "boss"}`
- `post_boss_room_type`
  - 当前统一为 `"boss_chest"`

`act1_map.json` 和 `act2_map.json` 都会改成相同的固定楼层口径，并同步更新到 `src/slay_the_spire/data/content/acts/`。

### 5.2 地图层数口径

地图生成器继续只负责“地图内节点”，但地图内节点需要覆盖到 Boss 层。

本轮口径：

- 地图节点层包含 `Floor 1` 到 `Floor 16`
- `Floor 16` 是地图顶层 Boss 节点
- `Floor 17` 不进入 `ActState.nodes`，而是由会话流程在 Boss 奖励完成后生成 `boss_chest` 房间

这样既能保留当前 `ActState` 结构，也能表达原版“Boss 后还有一层过幕”的流程。

### 5.3 固定楼层覆盖规则

地图生成器先按现有拓扑生成分支结构，再在房间类型分配阶段对指定楼层执行强制覆盖：

- `row 0` 对应 `Floor 1`，固定 `combat`
- `row 8` 对应 `Floor 9`，固定 `treasure`
- `row 14` 对应 `Floor 15`，固定 `rest`
- `row 15` 对应 `Floor 16`，固定 `boss`

其中：

- `Floor 9 treasure` 应保持单层、单节点语义，不允许在同层混出其他房间类型
- `Floor 15 rest` 同样固定为休息点
- `Floor 16 boss` 继续保持单节点终点

固定楼层优先级高于权重抽样和最小数量补洞逻辑。

## 6. 房间与流程设计

### 6.1 `treasure` 房间

新增 `treasure` 房间类型，作为 `Floor 9` 使用。

行为设计：

- 进入房间时生成 1 个遗物奖励
- 菜单提供“打开宝箱”或等价领取动作
- 领取遗物后房间标记为 `is_resolved=True`
- 玩家随后通过现有 `next_room` 继续推进

首版掉落策略：

- 使用单独的普通遗物掉落池
- 不复用 Boss 遗物池
- 不混入仅商店出售或起始专属遗物

如果当前仓库尚无普通遗物掉落池概念，需要补最小内容和选择逻辑，但只做足以支撑 `treasure` 的那一层，不扩写完整原版稀有度体系。

### 6.2 `boss_chest` 房间

新增 `boss_chest` 房间类型，作为 `Floor 17` 使用。

行为设计：

- Boss 战打赢后仍照常生成 Boss 奖励
- 当 Boss 奖励全部领取完成时，不再直接切下一幕或胜利
- 会话改为进入 `boss_chest`
- `boss_chest` 提供明确的推进动作：
  - 当前幕有 `next_act_id` 时，进入下一幕
  - 当前幕没有 `next_act_id` 时，完成攀登并进入 `victory`

这样可以把原版“Boss 奖励”和“过幕”拆成两个明确阶段，减少 `session.py` 里的隐式跳转。

## 7. UI 与菜单设计

### 7.1 菜单

沿用当前编号菜单模型，不引入自由文本命令。

新增菜单语义：

- `treasure`
  - 打开宝箱
  - 查看资料
  - 保存游戏
  - 读取存档
  - 退出游戏
- `boss_chest`
  - 前往下一幕 / 完成攀登
  - 查看资料
  - 保存游戏
  - 读取存档
  - 退出游戏

### 7.2 Rich / Textual 展示

两个新房间类型都走现有非战斗房间渲染链路：

- 在共享 Rich 渲染层新增 `treasure` 和 `boss_chest` 的文案与状态展示
- 在 Textual 侧复用现有右侧面板与悬停预览机制

本轮不新增新的 UI 框架或特殊页面模式。

### 7.3 玩家文案

面向玩家的新增文案默认统一用中文：

- 宝箱
- 打开宝箱
- 获得遗物
- 前往下一幕
- 完成攀登

## 8. 存档与恢复

新增 `treasure` 和 `boss_chest` 后，需要保证以下场景仍可恢复：

- 尚未打开宝箱的 `treasure`
- 已打开宝箱但未离开的 `treasure`
- 已打完 Boss 且奖励未领完
- 已领完 Boss 奖励并进入 `boss_chest`
- `boss_chest` 中尚未执行推进动作

因此需要同步检查：

- `RoomState.payload` 的最小字段设计
- 房间恢复与菜单恢复逻辑
- 相关测试中对 `room_type` 分支的覆盖

## 9. 风险与约束

### 9.1 遗物池边界

当前仓库已有起始遗物、Boss 遗物、商店出售遗物等语义，但未必已有“普通宝箱遗物池”这一层。若直接混用现有池，容易出现掉落不合理的问题。

本轮应优先补一个最小普通遗物池，并限定 `treasure` 仅从该池抽取。

### 9.2 固定楼层与最小数量规则冲突

当前地图生成器还带有 `minimum_counts` 和特殊房间连击限制。引入 `treasure` 和固定 `rest` 后，最小数量修补逻辑不能再把这些固定层覆盖掉，也不能因为补洞导致固定楼层失真。

### 9.3 测试连带面

本轮虽然不算大重构，但会碰到：

- 内容 schema
- 地图生成
- 会话推进
- 菜单
- 非战斗渲染
- 存档恢复

因此测试补点要覆盖主流程，不然很容易出现“能生成但不能存档恢复”的回归。

## 10. 测试策略

重点测试三层：

### 10.1 地图生成

- `act1` 和 `act2` 的固定楼层房间类型正确
- Boss 仍是地图最后一层的唯一节点
- `Floor 9` 和 `Floor 15` 被强制为 `treasure` / `rest`

### 10.2 会话流程

- `treasure` 可生成遗物并成功领取
- Boss 奖励完成后进入 `boss_chest`
- `boss_chest` 可正确触发下一幕或胜利

### 10.3 E2E 与恢复

- 单幕流程可以走到宝箱层并继续推进
- 双幕流程可以在 `act1` Boss 后进入 `boss_chest` 再到 `act2`
- `act2` Boss 后进入 `boss_chest` 再到 `victory`
- 存档恢复不会因新增 `room_type` 失效

## 11. 影响文件

预计主要修改：

- `content/acts/act1_map.json`
- `content/acts/act2_map.json`
- `src/slay_the_spire/data/content/acts/act1_map.json`
- `src/slay_the_spire/data/content/acts/act2_map.json`
- `src/slay_the_spire/content/registries.py`
- `src/slay_the_spire/domain/map/map_generator.py`
- `src/slay_the_spire/app/session.py`
- `src/slay_the_spire/app/menu_definitions.py`
- `src/slay_the_spire/adapters/rich_ui/screens/non_combat.py`
- 可能涉及 `use_cases/` 中的房间动作或奖励逻辑

对应测试重点：

- `tests/domain/test_map_generator.py`
- `tests/use_cases/test_room_recovery.py`
- `tests/e2e/test_single_act_smoke.py`
- `tests/e2e/test_two_act_smoke.py`
- `tests/app/test_menu_definitions.py`
- `tests/adapters/textual/test_slay_app.py`

## 12. 结论

本轮应以“固定楼层 + 新房间类型 + Boss 后显式过渡房间”为核心，按数据驱动方式把 `act1/act2` 对齐到原版普通 Act 的结构口径，同时控制范围，不把问题扩展到 `act3`、钥匙体系或完整遗物稀有度系统。
