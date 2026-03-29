# Opening Flow Design

Date: 2026-03-29
Status: Draft for review

## 1. 背景

当前项目的新游戏入口会直接：

- 调用 `start_new_run()`
- 生成 Act 地图
- 立刻进入 Act1 第一层房间

这意味着现有流程缺少两段原版开局体验：

- 角色选择
- `Neow` 开局奖励

同时，当前 CLI 的 `new` 子命令虽然支持 `--character`，但它只是把角色 ID 直接传给 `start_session()`，没有“交互式选择角色”和“跳过角色页直达 `Neow`”的区分能力。

本轮目标不是完整复刻原版全部开局系统，而是在保持当前 Textual 单机菜单结构的前提下，先补齐一条稳定、可回放、可扩展的开局主链路：

- 新游戏
- 角色选择
- `Neow` 开局奖励
- Act1 第一层

## 2. 目标

- 为 `new` 流程新增独立的开局阶段
- 在未显式传 `--character` 时，先进入真正的角色选择页
- 在显式传 `--character` 时，跳过角色选择页，直接进入 `Neow`
- `Neow` 候选基于 `seed` 和角色确定性生成，同局可回放
- `Neow` 结算完成后，才生成正式的地图与第一层房间
- 保持 `load` 入口不变，不经过开局流程
- 保持当前 Textual 编号菜单和鼠标点击交互模型不变

## 3. 非目标

- 不完整复刻原版全部 `Neow` 候选池、代价池和分层规则
- 不为开局阶段增加存档兼容或半开局恢复能力
- 不引入 Ascension、连胜、历史奖励或额外 meta progression
- 不把角色选择或 `Neow` 伪装成地图房间
- 不在本轮新增更多角色内容
- 不为旧 `menu_state` 或旧存档路径保留兼容逻辑

## 4. 设计选择

本轮采用：

- **Session 级开局流程**

不采用：

- 把角色选择和 `Neow` 伪装成特殊 `room_type`
- 在 CLI/Textual 外侧再包一层独立向导 UI

原因：

- 开局阶段本质上不属于地图房间，不应污染 `room_state` 语义
- 当前 `route_menu_choice()` 和 Textual `OptionList` 已经是稳定的菜单驱动结构，继续沿用最稳
- 单独建模 opening 状态，比让地图、奖励、房间渲染承担开局职责更容易扩展到后续多角色

## 5. 范围

### In Scope

- 新增 opening 状态模型
- 新增角色选择页
- 新增 `Neow` 候选页
- 新增 `Neow` 升级牌/删牌子菜单
- 新增确定性 `Neow` 候选生成与结算逻辑
- 调整 CLI `new --character` 语义
- 调整 Session/渲染/Textual/测试以支持 opening 阶段

### Out of Scope

- 复杂的原版 `Neow` 规则分组、胜场补偿和底层权重系统
- 更大规模遗物池和专属角色候选差异
- 开局阶段的 `save/load`
- 角色立绘、动画或额外确认弹窗

## 6. 总体流程

`new` 命令进入以下链路：

1. 解析 CLI 参数
2. 若未显式传 `--character`，创建 opening session 并进入角色选择页
3. 若显式传 `--character`，创建 opening session 并直接进入 `Neow`
4. 在 `Neow` 中完成一次奖励选择与必要的目标卡选择
5. 应用 `Neow` 代价与奖励
6. 生成正式 `run_state`
7. 生成 `act_state`
8. 进入 Act1 第一层 `room_state`
9. 切换到现有正常游戏流程

`load` 命令保持现状：

- 直接恢复正式 `run_state / act_state / room_state`
- 不进入 opening 阶段

## 7. 会话与状态模型

### 7.1 SessionState 扩展

为了让 opening 阶段不再假装自己已经在地图内，`SessionState` 需要支持“开局前”和“正式运行中”两种状态。

建议新增：

```python
@dataclass(slots=True)
class OpeningState:
    available_character_ids: list[str]
    selected_character_id: str | None
    run_blueprint: RunState | None
    neow_offers: list[NeowOffer]
    pending_neow_offer_id: str | None = None
```

同时把 `SessionState` 的正式运行字段改成可空：

```python
@dataclass(slots=True)
class SessionState:
    run_state: RunState | None
    act_state: ActState | None
    room_state: RoomState | None
    content_root: Path
    save_path: Path
    run_phase: str = "opening"
    menu_state: MenuState = field(default_factory=MenuState)
    opening_state: OpeningState | None = None
    command_history: list[str] | None = None
```

状态约束：

- opening 阶段：
  - `opening_state is not None`
  - `act_state is None`
  - `room_state is None`
- 正式运行阶段：
  - `opening_state is None`
  - `run_state / act_state / room_state` 全部存在

### 7.2 Run Blueprint

本轮保留一个必要的中间态：`run_blueprint`。

语义：

- 它不是已经进入地图的正式 run
- 但它是一个足够完整的 `RunState`
- 仅用于在 `Neow` 阶段执行删牌、升级牌、加金币、扣血、加最大生命、加遗物等结算

创建时机：

- 角色选择页未确认前：`run_blueprint is None`
- 选定角色后：立刻根据角色基础数据创建 `run_blueprint`
- `Neow` 结算完成后：把 `run_blueprint` 作为正式 `run_state`，再继续生成地图和第一层房间

该设计兼顾了两点：

- 正式地图不会在 `Neow` 前生成
- `Neow` 的卡牌与数值修改不需要发明另一套伪 `run_state` 数据模型

### 7.3 MenuState 新模式

新增以下 `menu_state.mode`：

- `opening_character_select`
- `opening_neow_offer`
- `opening_neow_upgrade_card`
- `opening_neow_remove_card`

这些模式只在 `run_phase == "opening"` 时出现。

## 8. CLI 行为

### 8.1 `--character` 语义调整

当前 `argparse` 把 `--character` 默认值设成 `"ironclad"`，这会导致程序无法分辨：

- 用户没有传 `--character`
- 用户显式传了 `--character ironclad`

本轮需要改成：

- `new_parser.add_argument("--character")`

也就是默认值为 `None`。

之后在 `main()` 中：

- `args.character is None`：进入角色选择页
- `args.character` 为具体角色 ID：跳过角色选择页，直接进入 `Neow`

### 8.2 入口职责

新增一个 opening session 工厂，例如：

- `start_new_game_session(seed, preferred_character_id, ...)`

它只负责构建 opening session，不再在 CLI 里直接调用当前的“立刻进入第一层”的 `start_session()` 语义。

现有的“正式 run 立即开始”逻辑可以下沉为内部 helper，例如：

- `_start_active_session_from_run_state(...)`

## 9. 角色选择页

### 9.1 页面行为

角色选择页是真正的角色选择界面，即使当前只有 `ironclad`，仍然保留：

- 角色列表
- 角色摘要
- 选择后进入下一步

不把它降级成“只有一个按钮的确认页”。

### 9.2 菜单动作

角色选择菜单动作格式：

- `select_character:<character_id>`
- `quit`

当前只有 `ironclad`，但页面结构和路由必须天然支持未来多角色扩展。

### 9.3 角色摘要

左侧摘要或正文中至少展示：

- 角色名
- 起始生命
- 起始遗物
- 起始套牌摘要
- 起始幕

## 10. Neow 候选模型

### 10.1 候选数量与来源

第一版固定展示 `4` 个候选：

- `2` 个无代价候选
- `2` 个带代价候选

全部候选由：

- `seed`
- `character_id`
- 固定分类字符串（如 `"opening:neow"`）

共同驱动确定性 RNG 生成，保证：

- 同 seed + 同角色 = 同一组候选
- 不同 seed 通常产生不同候选

### 10.2 NeowOffer 结构

建议引入结构化的候选对象，而不是继续用字符串奖励 ID 叠加临时解析。

```python
@dataclass(frozen=True, slots=True)
class NeowOffer:
    offer_id: str
    category: str  # "free" | "tradeoff"
    reward_kind: str
    cost_kind: str | None
    reward_payload: dict[str, object]
    cost_payload: dict[str, object]
    requires_target: str | None  # None | "upgrade_card" | "remove_card"
    summary: str
    detail_lines: tuple[str, ...]
```

字段语义：

- `offer_id`：稳定候选 ID，用于菜单路由和回放
- `category`：无代价或带代价候选
- `reward_kind` / `cost_kind`：统一路由到结算逻辑
- `reward_payload` / `cost_payload`：具体参数
- `requires_target`：是否需要进子菜单
- `summary` / `detail_lines`：直接用于中文 UI 展示

### 10.3 第一版候选池

无代价池：

- 获得 `100` 金币
- 升级 `1` 张牌
- 移除 `1` 张牌
- 获得 `1` 瓶随机药水

带代价池：

- 获得 `250` 金币，加入 `1` 张随机诅咒
- 获得 `1` 个随机非 Boss 遗物，失去 `10%` 最大生命
- 获得 `1` 张随机稀有牌，失去 `10%` 当前生命
- 移除 `1` 张牌，失去起始遗物

本轮刻意不加入需要额外底层支持的复杂效果，例如：

- 变换牌
- 全部换牌
- 换起始遗物后从更大专属池补发
- 多阶段条件奖励

### 10.4 可复用能力

现有代码已经具备或接近具备以下效果基础：

- `gold`
- `relic`
- `card`
- `upgrade_card`
- `remove_card`
- `heal`
- `increase_max_hp`
- `lose_hp`

因此第一版候选池优先围绕这些能力展开，避免为了 `Neow` 单独做一批一次性特殊逻辑。

## 11. Neow 随机来源

### 11.1 药水

随机药水从当前角色可用药水池中抽取。现阶段项目只有 `starter_potions`，因此第一版可直接从：

- `registry.potion_ids_for_pool("starter_potions")`

中确定性抽样。

### 11.2 稀有牌

随机稀有牌从当前角色所属卡池中、且满足以下条件的牌里抽取：

- `rarity == "rare"`
- 非起始基础牌
- 可被玩家获得

当前铁甲战士卡池已经包含若干 `rare` 牌，足以支撑第一版。

### 11.3 随机诅咒

随机诅咒从 `content/cards/curses.json` 中满足：

- `card_type == "curse"`

的候选中抽取，排除状态牌如 `burn`。

### 11.4 随机非 Boss 遗物

随机非 Boss 遗物从当前已加载遗物中抽取，满足：

- 不属于 `boss_relics`
- 不在当前 `run_blueprint.relics` 中
- 不是仅作为占位回退的 `circlet`

对当前项目来说，这会自然落到已实现的普通遗物集合上。

## 12. Neow 交互与状态流转

### 12.1 Neow 主页面

Neow 主页面直接展示四个候选，菜单动作为：

- `choose_neow_offer:<offer_id>`
- `quit`

页面正文需要展示：

- 角色名
- 当前起始状态预览
- 候选摘要
- 代价说明

### 12.2 需要目标卡的候选

当玩家选择以下候选时，不立即结算：

- 升级 `1` 张牌
- 移除 `1` 张牌

而是：

1. 把 `pending_neow_offer_id` 设为当前候选
2. 切换到对应子菜单
3. 等玩家选定目标卡后再一次性结算

### 12.3 子菜单动作

升级牌页：

- `upgrade_card:<instance_id>`
- `back`

删牌页：

- `remove_card:<instance_id>`
- `back`

`back` 返回 `Neow` 主页面，并清空 `pending_neow_offer_id`。

### 12.4 结算顺序

统一采用：

1. 应用代价
2. 应用奖励
3. 清空 opening 状态
4. 生成正式地图和第一层房间

这样规则最稳定，测试也最直接。

## 13. 正式开局生成

当 `Neow` 选项结算完成后：

1. 取得更新后的 `run_blueprint`
2. 把它作为正式 `run_state`
3. 基于 `run_state.current_act_id` 生成 `act_state`
4. 调用 `enter_room()` 进入当前 Act 的起始节点
5. 返回 `run_phase == "active"` 的正式 `SessionState`

这一刻起：

- `opening_state` 置空
- `menu_state` 回到正式房间对应模式
- 之后全部逻辑复用现有正常流程

## 14. 结算逻辑

### 14.1 建议新增的 helper

建议新增一个专门的 opening 模块，例如：

- `src/slay_the_spire/use_cases/opening_flow.py`

职责包括：

- 构建 opening session 所需的 `run_blueprint`
- 生成 `Neow` 候选
- 结算 `Neow` 候选
- 升级牌/删牌等需要目标卡的辅助操作

### 14.2 与现有 use case 的复用

应尽量复用现有逻辑：

- 加金币/加遗物/加卡：复用 `apply_reward()`
- 升级牌、删牌：抽取轻量 helper，避免复制事件逻辑
- 扣血/加最大生命：沿用现有 `RunState` 直接 `replace()` 模式

如果事件中的“删牌/升级牌”逻辑已经足够集中，可以在本轮顺手把它们抽成共享函数，供事件和 opening 共用。

## 15. 渲染设计

### 15.1 Opening Renderer

新增独立 opening renderer，不把 opening 页面硬塞进现有 `non_combat` 渲染逻辑。

建议文件：

- `src/slay_the_spire/adapters/presentation/opening_renderer.py`

负责渲染：

- 角色选择页
- `Neow` 候选页
- `Neow` 升级牌页
- `Neow` 删牌页

### 15.2 render_session_renderable 分流

`render_session_renderable()` 先判断：

- 若 `run_phase == "opening"`，走 opening renderer
- 否则维持当前 `combat / non_combat` 逻辑

这能避免：

- 在 opening 阶段渲染地图房间标题
- 在 opening 阶段出现“当前可达地图”等错误语义

## 16. Textual 集成

### 16.1 布局原则

不重做 Textual 总体布局，继续保留：

- 左侧面板
- 右侧日志、操作摘要、预览、菜单

### 16.2 左侧面板在 opening 阶段的行为

opening 阶段不显示真实地图。

建议行为：

- 左侧主区域显示 opening 摘要面板
- 角色页显示角色信息
- `Neow` 页显示起始状态和候选说明
- 一旦进入正式 run，再恢复现有地图组件行为

### 16.3 右侧菜单

`_current_action_menu()` 新增 opening mode 支持，让现有：

- `OptionList`
- 鼠标悬停
- 编号选择

保持统一。

### 16.4 悬停预览

第一版可为 opening 阶段提供轻量预览：

- 角色页：悬停角色显示角色摘要
- `Neow` 页：悬停候选显示完整说明
- 升级牌/删牌页：复用已有卡牌详情预览

不是本轮核心目标，但应至少保证 opening 阶段不会触发地图预览和 Boss 宝箱类错误提示。

## 17. 菜单路由

新增路由函数：

- `_route_opening_character_select_menu()`
- `_route_opening_neow_offer_menu()`
- `_route_opening_neow_upgrade_card_menu()`
- `_route_opening_neow_remove_card_menu()`

在 `route_menu_choice()` 中优先按 opening mode 分发。

同时需要调整以下根规则：

- opening 阶段只允许开局相关动作和 `quit`
- opening 阶段禁止 `save`
- opening 阶段禁止 `load`

若用户试图在 opening 阶段保存或读取，应返回明确中文提示，而不是静默失败。

## 18. 错误处理

### 18.1 参数与内容校验

- 传入未知 `character_id` 时，`new --character <id>` 直接报错
- `Neow` 候选池为空、角色池为空、遗物/药水/牌池无法抽样时，应抛出清晰异常

### 18.2 目标卡失效

理论上 opening 阶段没有战斗并发状态，目标卡失效概率很低，但仍需防御：

- 若 `pending_neow_offer_id` 指向的候选不存在
- 若待升级/移除的牌不在 `run_blueprint.deck`

则回到 `Neow` 主页面并给出提示，而不是让 session 坏掉。

### 18.3 空值防御

因为 `SessionState` 会允许 `act_state` / `room_state` 为空，所有依赖这些字段的渲染和 Textual 代码都必须先判断当前是否为 opening 阶段，避免直接访问空对象。

## 19. 测试策略

### 19.1 Session / 路由测试

补充或新增测试覆盖：

- `new` 默认进入角色选择页
- `new --character ironclad` 直接进入 `Neow`
- opening session 初始字段符合约束
- 同一 `seed + character` 的 `Neow` 候选完全一致
- 不同 `seed` 会产生不同候选
- 选择无目标候选后进入正式 Act1 第一层
- 选择升级/删牌候选时会进入子菜单
- 从升级/删牌子菜单返回时能回到 `Neow`
- 目标卡确认后才真正进入正式 run
- opening 阶段禁止 `save/load`

### 19.2 渲染测试

补充 opening renderer 测试：

- 角色页可渲染
- `Neow` 页可渲染
- 升级牌页可渲染
- 删牌页可渲染
- opening 阶段不会渲染真实地图文案

### 19.3 Textual 测试

补充 `tests/adapters/textual/test_slay_app.py`：

- opening mode 下 `_current_action_menu()` 正常工作
- opening 阶段左侧不展示真实地图行为
- 从 opening 进入正式 run 后恢复地图与原有菜单逻辑

### 19.4 E2E 冒烟

补充：

- `new -> 角色选择 -> Neow -> 第一层`
- `new --character ironclad -> Neow -> 第一层`

并验证：

- 进入正式 run 后 `room_state.room_type == "combat"`
- `run_phase == "active"`

## 20. 风险与控制

主要风险：

- `SessionState` 改为允许空的 `act_state / room_state` 后，现有代码可能有空值访问
- `Neow` 与事件/奖励逻辑有部分重叠，若重复实现容易出现规则漂移
- CLI 若不改 `--character` 默认值，角色页是否跳过会失真

控制方式：

- 先补 opening 测试，再改 `SessionState`
- 抽共享 helper 复用升级牌/删牌逻辑
- 让 `render_session_renderable()` 和 `_current_action_menu()` 先做 opening 分流，减少空值访问面
- 最终跑针对性测试和全量测试

## 21. 验收标准

- `new` 默认先进入真正的角色选择页
- `new --character ironclad` 跳过角色选择页，直接进入 `Neow`
- `Neow` 候选按 `seed` 确定性生成
- `Neow` 可正确处理：
  - 直接结算型候选
  - 升级牌型候选
  - 删牌型候选
- 只有 `Neow` 结算完成后，才进入 Act1 第一层
- opening 阶段不显示真实地图，不允许 `save/load`
- `load` 流程保持不变
- 相关测试通过，玩家可从新游戏稳定进入正式跑图
