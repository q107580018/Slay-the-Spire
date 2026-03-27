# Card Rarity Color Design

Date: 2026-03-27
Status: Draft for review

## 1. 背景

当前项目的 `CardDef` 已支持 `rarity` 字段，但终端展示尚未围绕稀有度建立统一视觉规则：

- 手牌、牌堆、目标选择、商店、奖励和详情页大多直接输出普通字符串
- 升级牌目前在内容里大量使用 `rarity: "special"`，这会把“是否升级”与“基础稀有度”混在一起
- 诅咒牌内容没有显式 `rarity`

这导致两个问题：

- 玩家无法在终端里快速通过颜色识别卡牌稀有度
- 升级前后没有稳定一致的视觉区分规则

## 2. 目标

- 给所有卡牌建立稳定的 `rarity` 内容语义
- 在终端 UI 中按稀有度着色卡牌名称
- 升级前后保留相同主色，升级后只增加统一强调样式
- 让战斗、非战斗、inspect、奖励与商店等入口复用同一套卡牌格式化逻辑

## 3. 非目标

- 不修改卡牌数值、效果或战斗规则
- 不为 Textual UI 单独设计另一套卡牌稀有度语义
- 不引入复杂的多属性标签系统

## 4. 最终规则

### 4.1 稀有度语义

卡牌 `rarity` 表达“这张牌的基础稀有度”，而不是“它是否已经升级”。

因此：

- `strike` / `strike_plus` 都是 `basic`
- `anger` / `anger_plus` 都是 `common`
- 如果后续有 `uncommon` / `rare` 卡，同理升级后仍保持原稀有度
- 诅咒牌统一标记为 `curse`

`special` 不再作为升级牌的常规稀有度使用。

### 4.2 升级态语义

升级态单独判断，不由 `rarity` 决定。

当前实现可基于以下任一稳定事实判断：

- 卡牌 ID 是某张基础牌的 `upgrades_to` 目标
- 或卡牌名称以 `+` 结尾

展示层只消费统一的“是否升级”布尔值，不直接依赖某个硬编码稀有度。

### 4.3 颜色规则

采用“稀有度决定主色，升级后只增加统一强调”的方案：

- `basic`：中性基础色
- `common`：绿色系
- `uncommon`：蓝色系
- `rare`：金色系
- `curse`：红色系
- 升级态：在原主色基础上统一加粗

如果某张卡缺失稀有度，则回退到默认卡牌颜色，避免渲染报错。

## 5. 架构设计

### 5.1 内容层

维护所有卡牌 JSON，使每张牌都有明确 `rarity`：

- 根目录 `content/cards/*.json`
- 打包副本 `src/slay_the_spire/data/content/cards/*.json`

升级牌改为继承原始稀有度，不再写成 `special`。

### 5.2 注册表层

`CardRegistry` 继续承载 `rarity`，但要把它视为正式内容字段而不是可有可无的注释字段。

首轮不强制把 `rarity` 提升为注册时必填，避免一次性打断所有内容；但会通过内容测试确保仓库内实际卡牌都带有合法稀有度。

### 5.3 展示层

在展示层新增统一卡牌展示语义，负责：

- 根据 `rarity` 选择样式
- 根据升级态叠加统一强调
- 向不同 UI 适配层提供一致的“颜色 + 升级态”规则

`rich` 终端层输出 `Text`，`textual` 悬浮预览沿用相同语义，但按 `textual` 组件可接受的样式方式渲染。

所有需要显示卡牌名称的主要入口都优先复用该 helper：

- 战斗手牌列表
- 目标选择中的手牌目标
- 牌堆列表
- inspect 牌组列表与卡牌详情
- 商店卡牌列表
- 奖励列表和奖励详情
- 休息点/事件的升级与删牌候选列表
- Textual 悬浮卡牌预览

## 6. 具体改动边界

### 6.1 主题样式

在 `src/slay_the_spire/adapters/terminal/theme.py` 新增：

- `card.name`
- `card.rarity.basic`
- `card.rarity.common`
- `card.rarity.uncommon`
- `card.rarity.rare`
- `card.rarity.curse`
- `card.upgraded`

升级样式只做统一强调，不覆盖主色。

### 6.2 卡牌格式化 helper

在 `src/slay_the_spire/adapters/terminal/widgets.py` 增加：

- 稀有度到样式名的映射
- 升级态判断 helper
- 生成卡牌显示名 `Text` 的 helper
- 必要时补充“稀有度中文标签” helper 供详情页使用

### 6.3 详情页信息

在 `src/slay_the_spire/adapters/terminal/inspect.py` 的卡牌详情中新增：

- `稀有度`
- `状态`（普通 / 已升级）

这样即便终端不显示颜色，导出的纯文本仍保留关键信息。

### 6.4 Textual 预览

在 `src/slay_the_spire/adapters/textual/slay_app.py` 中，卡牌 hover preview 也要沿用相同规则：

- 名称按基础稀有度着色
- 升级牌保留主色并加统一强调
- 详情文本中补充稀有度与状态，避免纯文本场景丢失信息

## 7. 测试策略

### 7.1 内容测试

验证：

- 根目录与打包目录的卡牌内容都包含稀有度
- 升级牌与基础牌保持相同稀有度
- 诅咒牌显式标记为 `curse`

### 7.2 终端组件/渲染测试

验证：

- 卡牌格式化 helper 为普通牌和升级牌返回正确样式
- 纯文本导出仍包含名称与详情字段
- 关键列表页和详情页继续可读

### 7.3 Textual 测试

验证：

- 卡牌 hover preview 展示基础稀有度对应的颜色语义
- 升级牌在预览中带统一强调
- 预览文本包含 `稀有度` 与 `状态`

### 7.4 回归范围

确保不破坏：

- 战斗页主菜单
- inspect 牌组查看
- 商店和奖励页
- Textual hover preview

## 8. 风险与约束

- 终端 `export_text()` 不保留颜色，因此测试不能只看导出文本判断配色，需要直接检查 `Text.spans` 或 `Text` 的样式结构
- 现有很多菜单 helper 返回 `list[str]`，要局部引入 `Text` 而不打断现有菜单编号逻辑
- 需要同步维护 `content/` 与 `src/slay_the_spire/data/content/`，否则默认运行和打包结果会不一致

## 9. 验收标准

- 玩家在终端中能通过颜色区分卡牌基础稀有度
- 升级牌保持原稀有度主色，并统一显示为强调样式
- inspect 卡牌详情能明确看到稀有度和是否升级
- 根目录内容与打包内容保持一致
- 相关测试通过
