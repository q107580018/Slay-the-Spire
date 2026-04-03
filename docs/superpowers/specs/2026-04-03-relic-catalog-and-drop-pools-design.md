# 设计规格：原版 1 代遗物词条补全与掉落池复刻

**日期**：2026-04-03  
**范围**：将原版《Slay the Spire》1 代遗物完整录入仓库 `content/`，补全中文名、效果描述、原版分类与掉落池信息，并把当前遗物掉落入口改为读取原版导向的遗物池与遗物序列。  
**策略**：先完成内容真源与掉落框架复刻，再分批实现具体遗物效果。

---

## 一、目标

- 把原版 1 代全部遗物录入 `content/`，不再只有当前少量已实现遗物。
- 中文术语、效果说明优先对齐灰机 wiki；必要时用英文 wiki 校对英文 ID、分类和原版掉落规则。
- 保持 `content/` 作为唯一真源，不引入旁路图鉴文件。
- 让遗物掉落逻辑从当前的硬编码列表和 `can_appear_in_shop` 布尔判断，切换到原版分类池与 run 内遗物序列。
- 即使很多遗物暂时还没有行为实现，也先允许它们按原版进入实际掉落；运行时先展示词条，后续再逐批补效果。

---

## 二、现状

当前仓库的遗物内容和逻辑存在这些限制：

- `content/relics/` 里只有 `starter_relics.json`、`shop_relics.json`、`boss_relics.json` 三个文件，总量只有 10 个遗物。
- `RelicDef` 只有 `summary`、`description`、`trigger_hooks`、`passive_effects`、`replaces_relic_id`、`disabled_actions`、`blocks_gold_gain`、`can_appear_in_shop` 等少量字段，适合少数已实现遗物，不够承载“原版全量资料 + 后续实现占位”。
- 商店遗物来自 `relic.can_appear_in_shop`。
- 宝箱遗物来自“所有非商店遗物”的集合，没有区分普通/罕见/稀有。
- Boss 三选一和精英遗物都还是硬编码 ID 列表。
- Opening/Neow 随机遗物逻辑也不是按原版分类池筛选。

这意味着：仅靠补几份 JSON 不能完成“原版全部遗物 + 原版掉落池”。内容 schema、运行时取池和存档状态都要一起扩。

---

## 三、方案比较

### 方案 A：扩展遗物 schema，直接把全量原版内容录入 `content/`，并让运行时改读新分类池（推荐）

- 优点：
  - `content/` 继续是唯一真源。
  - 录入一次后，后续实现遗物效果时不用再迁移文案、分类和来源。
  - 可以同步去掉当前的硬编码遗物池。
- 缺点：
  - 需要同时改内容 schema、取池逻辑、存档和测试。

### 方案 B：只把原版信息塞进现有字段

- 优点：
  - 初始代码改动小。
- 缺点：
  - 无法干净表达原版分类、角色专属限制、实现状态和结构化效果占位。
  - 后续实现效果时会发生二次 schema 迁移。

### 方案 C：先做独立遗物图鉴，再晚点回填运行时 content

- 优点：
  - 录入速度最快。
- 缺点：
  - 会形成两套真源，违反仓库约束。
  - 后续容易出现图鉴与运行时数据不一致。

**结论**：采用方案 A。

---

## 四、内容模型设计

### 4.1 文件组织

- 保留 `content/relics/` 作为唯一真源目录。
- 不再只依赖当前三份文件表达全部遗物。
- 新增按原版分类拆分的 relic 内容文件，建议至少包含：
  - `starter_relics.json`
  - `common_relics.json`
  - `uncommon_relics.json`
  - `rare_relics.json`
  - `shop_relics.json`
  - `boss_relics.json`
  - `event_relics.json`
  - `special_relics.json`
- `special_relics.json` 用于 `circlet`、钥匙相关或不适合归到普通掉落池但需要注册的特殊遗物。

文件名用于维护和阅读；运行时不应继续依赖“某个文件名等于某个逻辑池”的隐含规则，而应读取遗物自身字段。

### 4.2 `RelicDef` 新字段

在保留现有字段的基础上，新增以下字段：

```python
rarity: str
pools: list[str] = field(default_factory=list)
source_tags: list[str] = field(default_factory=list)
owner_character_ids: list[str] = field(default_factory=list)
implementation_status: str = "placeholder"
effect_blueprint: list[JsonDict] = field(default_factory=list)
flavor_text: str | None = None
```

字段语义：

- `rarity`
  - 表达原版遗物分类。
  - 建议允许值：`starter`、`common`、`uncommon`、`rare`、`shop`、`boss`、`event`、`special`。
- `pools`
  - 表达运行时掉落池成员资格。
  - 建议允许值：`common`、`uncommon`、`rare`、`shop`、`boss`、`event`、`starter`、`neow`、`non_boss_chest`、`elite_reward`、`treasure`、`special_fallback`。
  - 一个遗物可以同时属于多个池；例如 `common` 和 `treasure`。
- `source_tags`
  - 记录原版获取来源说明，例如 `elite`、`chest`、`merchant`、`event`、`boss_reward`、`starting_relic`、`neow_bonus`。
  - 偏文档和校验用途，不直接承担运行时逻辑判断。
- `owner_character_ids`
  - 角色专属遗物限制；空列表表示通用遗物。
  - 例如铁甲战士专属遗物只允许 `ironclad`。
- `implementation_status`
  - 标记当前项目里的实现状态。
  - 允许值：`implemented`、`partial`、`placeholder`。
- `effect_blueprint`
  - 结构化记录原版效果，不要求当前运行时立刻消费。
  - 例如“战斗开始时获得格挡”“第一次攻击增加伤害”“洗牌计数触发”等，都先以统一 JSON 结构存放。
- `flavor_text`
  - 可选的原版风味文本；不参与逻辑，但便于未来图鉴展示。

### 4.3 现有字段的保留原则

- `summary` 和 `description` 继续保留，并作为当前 UI 的主要展示来源。
- `trigger_hooks`、`passive_effects`、`replaces_relic_id`、`disabled_actions`、`blocks_gold_gain` 保留给已经实现或部分实现的遗物。
- `can_appear_in_shop` 不再作为权威来源；如果代码迁移时暂时保留该字段，也只能由 `pools` 是否包含 `shop` 推导，不能再由内容维护者单独手填。
- 对尚未实现的遗物：
  - 可以没有 `trigger_hooks` / `passive_effects`。
  - 但必须有完整的 `summary`、`description`、`rarity`、`pools`、`implementation_status`、`effect_blueprint`。

这样可以保证“内容录全”和“运行时逐步实现”并行推进。

---

## 五、原版掉落模型设计

### 5.1 总原则

- run 开始时，为不同遗物池创建独立遗物序列。
- 每个序列只包含当前角色可获取的遗物。
- 每次需要从某个池拿遗物时，从该池序列中按顺序取下一个尚未拥有的遗物。
- 某个序列耗尽时，回退到 `circlet`。

### 5.2 需要持久化的遗物序列

`RunState` 新增一个结构，例如：

```python
relic_sequences: dict[str, list[str]]
relic_sequence_positions: dict[str, int]
```

至少覆盖这些逻辑池：

- `common`
- `uncommon`
- `rare`
- `shop`
- `boss`

可选地再加一个更高层辅助字段，例如：

```python
seen_relic_ids_by_pool: dict[str, list[str]]
```

但首选还是“序列 + 指针”模型，和原版“每局开局洗好序列”的思路更接近。

### 5.3 角色专属过滤

- 生成每条序列时，只纳入：
  - `owner_character_ids` 为空的通用遗物，或
  - `owner_character_ids` 包含当前角色 ID 的角色专属遗物。
- 这一步必须在开局时做，否则把静默/机器人/观者专属遗物放进铁甲战士的普通池会直接偏离原版。

### 5.4 商店遗物

- 商店遗物不再依赖 `can_appear_in_shop`。
- 商店入口改为从 `pools` 含 `shop` 的序列取值。
- 若未来要复刻“商店内多个遗物与价格修正”，再在此基础上扩展；本次先解决“来源正确”和“去硬编码”。

### 5.5 Boss 遗物

- Boss 三选一不再使用 `_BOSS_RELIC_OFFERS` 硬编码。
- 从 `boss` 序列中按顺序读取三个尚未拥有且不重复的候选。
- 如果某些 Boss 遗物存在角色限制或替换关系，直接依赖内容字段过滤。

### 5.6 宝箱与精英遗物

- 常规遗物池按 `common / uncommon / rare` 三条序列建模。
- 宝箱和精英奖励都从这三类里按原版导向选择稀有度，再到对应序列取遗物。
- 当前项目没有“小/中/大宝箱”尺寸区分；第一阶段可先统一复用同一套常规宝箱稀有度规则，但底层已经使用序列模型。
- 参考英文 wiki，常规遗物稀有度整体可按 `3:2:1` 近似为 `50% / 33% / 17%` 建模；如果后续查到灰机或代码级更精细规则，再细化而不改 schema。
- 精英奖励不再使用 `_ELITE_RELIC_OFFERS` 硬编码，而是复用常规遗物池抽法。

### 5.7 `circlet` 兜底

- `circlet` 归入 `special` / `special_fallback`。
- 当目标逻辑池无可用候选时，统一回落到 `circlet`。
- 保留当前“重复或耗尽时出现圆环”的项目内约定。

### 5.8 Placeholder 遗物是否进入实际掉落

本次按已确认方向处理：

- `placeholder` 遗物也进入实际掉落池。
- 运行时先依赖 `summary`、`description` 和 `effect_blueprint` 展示它们。
- 这会暂时带来“部分遗物只显示文本，不产生完整原版效果”的玩法偏差，但这是用户明确接受的取舍，优先满足“先复刻原版掉落池和全部词条”。

---

## 六、运行时改造点

### 6.1 内容注册与校验

文件：

- `src/slay_the_spire/content/registries.py`
- `src/slay_the_spire/content/catalog.py`

需要完成：

- 扩展 `RelicDef` 数据类和注册器字段校验。
- 为新字段补充枚举值和列表值校验。
- 继续允许旧字段为空，以兼容未实现遗物。

### 6.2 开局初始化

文件：

- `src/slay_the_spire/use_cases/start_run.py`
- `src/slay_the_spire/domain/models/run_state.py`
- `src/slay_the_spire/use_cases/save_game.py`
- `src/slay_the_spire/use_cases/load_game.py`

需要完成：

- 在创建新 run 时生成遗物序列并持久化到 `RunState`。
- 保存/读档时同步持久化序列和指针。
- 因为当前 `schema_version` 是 `2`，这次如果改了存档结构，要同步更新版本与相关测试。

### 6.3 商店、宝箱、Boss、Opening 入口

文件：

- `src/slay_the_spire/use_cases/enter_room.py`
- `src/slay_the_spire/domain/rewards/reward_generator.py`
- `src/slay_the_spire/use_cases/opening_flow.py`

需要完成：

- 商店遗物候选改为按 `shop` 序列读取。
- 宝箱遗物改为先选常规遗物稀有度，再从对应序列取下一个候选。
- 精英奖励遗物改为复用常规遗物序列，不再硬编码列表。
- Boss 三选一改为读 `boss` 序列。
- Opening/Neow 的“随机遗物”奖励改为读取允许的原版池，而不是用“没有副作用字段就可选”的临时逻辑。

### 6.4 展示层

文件：

- `src/slay_the_spire/adapters/presentation/inspect.py`
- `src/slay_the_spire/adapters/textual/slay_app.py`
- `scripts/generate_local_wiki.py`

需要完成：

- Hover preview 和 inspect 保持优先显示 `summary`、`description`。
- 在遗物详情展示里追加新字段摘要，例如分类、来源、实现状态。
- 本地 wiki 的遗物页按原版分类展示，并标出 `implementation_status`。

---

## 七、数据录入规范

### 7.1 资料来源顺序

- 第一优先：灰机 wiki
  - `遗物收藏`
  - `遗物`
  - `遗物序列`
  - 各分类页
  - 单遗物页面
- 第二优先：英文 wiki
  - 用于校对英文 ID、稀有度、掉落分类和原版措辞。

### 7.2 每个遗物至少要有的信息

- `id`
- `name`
- `summary`
- `description`
- `rarity`
- `pools`
- `source_tags`
- `owner_character_ids`
- `implementation_status`
- `effect_blueprint`

### 7.3 已实现与未实现遗物的差异

- 已实现/部分实现遗物：
  - 继续维护 `trigger_hooks`、`passive_effects` 等可执行字段。
- 未实现遗物：
  - 至少把原版效果写入 `description` 和 `effect_blueprint`。
  - 不要求立刻补运行时逻辑。

---

## 八、测试策略

### 8.1 内容校验

优先检查：`tests/content/test_registry_validation.py`

新增或扩展测试：

- 遗物总数覆盖原版 1 代全量。
- 关键遗物在正确分类中存在。
- 所有遗物都具备必填字段。
- `rarity`、`pools`、`source_tags`、`implementation_status` 枚举值合法。
- 角色专属遗物只在允许角色的池中出现。

### 8.2 运行时逻辑

优先检查：

- `tests/use_cases/test_start_run.py`
- `tests/use_cases/test_enter_room.py`
- `tests/use_cases/test_apply_reward.py`
- `tests/use_cases/test_save_load.py`

新增或扩展测试：

- 新 run 会生成稳定且可持久化的遗物序列。
- 商店遗物来自 `shop` 序列，不再依赖 `can_appear_in_shop`。
- 宝箱遗物来自常规遗物池，而不是“所有非商店遗物”。
- 精英奖励遗物来自常规遗物序列，不再依赖硬编码列表。
- Boss 三选一来自 `boss` 序列。
- 当某个池耗尽时回退到 `circlet`。
- 读档后遗物序列和指针不重复发放、不跳序。

### 8.3 展示与文档

优先检查：

- `tests/adapters/presentation/test_inspect.py`
- `tests/adapters/textual/test_slay_app.py`

新增或扩展测试：

- 未实现遗物的 hover preview 仍能展示完整摘要和描述。
- wiki 生成结果能按原版分类输出遗物，并标记实现状态。

---

## 九、风险与取舍

### 9.1 Placeholder 遗物直接掉落

风险：

- 玩家可能拿到只有文案、未完整生效的遗物。

取舍：

- 这是本次明确接受的阶段性偏差，优先完成“原版词条 + 原版掉落池”。
- 需要在遗物详情中显示实现状态，减少误解。

### 9.2 存档结构变更

风险：

- 遗物序列状态加入后，读档兼容和回档恢复更容易出错。

处理：

- 同步更新 save/load 和恢复测试。
- 当前阶段默认不兼容旧存档，可以按仓库约束直接迁移。

### 9.3 原版掉落规则细节不全

风险：

- 宝箱尺寸、精英和宝箱的精细概率、事件特殊规则未必一次查全。

处理：

- 本次先把 schema 和主流程搭成“原版导向”。
- 对缺失概率细节，先用可验证的保守近似，并在内容/测试里把规则写死，后续再精修。

---

## 十、实施边界

这份设计覆盖的工作：

- 全量原版遗物内容录入。
- 遗物 schema 扩展。
- 商店 / 宝箱 / 精英 / Boss / Opening 的遗物取池改造。
- run 内遗物序列状态与存档支持。
- 相关测试和文档更新。

这份设计不要求本次完成的工作：

- 全部遗物效果的真实运行时实现。
- 小/中/大宝箱 UI 或地图层面的完整复刻。
- 全角色开局流程与全部角色内容实现。

---

## 十一、下一步

- 先依据本 spec 写实现计划，拆成可执行的小任务。
- 按任务顺序先做 schema、测试和掉落骨架，再批量录入遗物数据。
- 之后再分批把 `placeholder` 遗物从“文案占位”推进到“部分实现”与“完整实现”。
