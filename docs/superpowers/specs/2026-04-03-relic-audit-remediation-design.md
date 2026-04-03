# 设计规格：原版遗物审计修复

**日期**：2026-04-03  
**范围**：基于本次仓库审计结果，分三阶段修复原版遗物的掉落接线、统一领奖路径、运行时效果缺口、静态资料偏差与缺失条目。  
**策略**：先止血“未实现遗物仍会掉落”的运行时问题，再补真实效果，最后统一修正 `content/relics/` 与 README，保证每个阶段都可独立验证。

---

## 一、目标

- 禁止 `placeholder` 遗物继续进入实际可获得池，避免玩家拿到无效果 relic。
- 统一 relic 获得入口，避免商店、事件、Boss、宝箱绕过 `apply_reward` 导致替换和获得时效果失效。
- 修复当前已接线但实现时机错误的 relic，优先覆盖已经能掉落或已被标记为 `implemented` 的条目。
- 修正 `content/relics/*.json` 中与本地原版资料明显不一致的名称、描述、稀有度、池子、角色归属和替换关系。
- 补齐审计中缺失的原版遗物条目，并同步更新 README 对当前遗物状态的表述。

---

## 二、现状

本次审计确认了以下事实：

- 仓库当前 `content/relics/*.json` 共 177 条遗物，但本地资料里还有 `怀表`、`扭曲漏斗`、`忍术卷轴` 未录入。
- 运行时生成遗物序列时，只按 `pool` 和 `owner_character_ids` 过滤，不看 `implementation_status`：`src/slay_the_spire/use_cases/start_run.py`。
- 商店购买和事件发 relic 直接追加 `run_state.relics`，没有走统一领奖路径：
  - `src/slay_the_spire/use_cases/shop_action.py`
  - `src/slay_the_spire/use_cases/event_action.py`
- `replaces_relic_id` 当前只有 `black_blood` 被硬编码支持，其它替换型遗物只是元数据。
- Boss 能量 relic 目前通过 `on_combat_start` 获得能量，只影响进入战斗后的首回合，和“每回合 +1 能量”不一致。
- README 当前声称“原版 1 代基础遗物目录已完整录入到内容层”，与审计事实不一致：`README.md:23`。

---

## 三、方案比较

### 方案 A：先修静态资料，再修运行时

- 优点：内容层会先变整齐。
- 缺点：短期内仍会掉落未实现 relic，玩家面问题不减。

### 方案 B：先修运行时实现，再最后回收接线和资料

- 优点：部分 relic 可以更快开始生效。
- 缺点：未实现 relic 继续进奖励池，测试基线最脆弱。

### 方案 C：分阶段收敛（推荐）

- 第一阶段：修掉落池过滤、统一领奖路径、关键回归测试。
- 第二阶段：修当前已经接线但实现不完整的 relic 运行时逻辑。
- 第三阶段：修静态资料偏差、补缺失遗物、更新 README 和内容校验。
- 优点：先止血，再扩功能，测试面最清晰。
- 缺点：中间阶段会暂时保留少量已知资料偏差，直到第三阶段完成。

**结论**：采用方案 C。

---

## 四、分阶段设计

### 4.1 第一阶段：止血可获得性与统一领奖路径

目标：让“是否可掉落/售卖/发放”与“当前是否真的实现”重新一致。

需要完成：

- 为 relic 序列构建增加“当前允许进入奖励池”的统一过滤规则。
- 默认只让 `implementation_status in {"implemented", "partial"}` 的 relic 进入 `common`、`uncommon`、`rare`、`shop`、`boss`、`neow` 等可获得池。
- 明确保留 `circlet` 的兜底逻辑，不受过滤影响。
- 保留 starter relic、事件专属 relic、特殊 relic 的注册，但不自动把它们塞进通用可获得池。
- 商店、事件、Boss、宝箱获得 relic 一律走统一领取逻辑，而不是直接改 `run_state.relics`。

这一阶段不追求补齐所有 relic 效果，只处理“未实现却会拿到”的核心风险。

### 4.2 第二阶段：修运行时效果与生命周期时机

目标：把当前已经半接线的 relic 修成真实生效，而不是靠元数据或一次性 hook 冒充。

优先范围：

- `burning_blood` / `black_blood`：补战斗结束回血的显式集成测试。
- `ectoplasm` / `coffee_dripper` / `fusion_hammer` / `busted_crown`：把“额外能量”从 `on_combat_start` 修为每回合生效的运行时规则。
- `guarding_totem`：若保留，则必须补明确来源；若不保留在本轮范围内，至少不能把它当作“原版已实现遗物”在文档里表述。
- `replaces_relic_id`：从 `black_blood` 的单点特判推广为统一规则，至少覆盖已经存在于 `content/relics` 的替换型 relic。

这一阶段的原则是：

- 只修当前已接线或马上要接线的 relic。
- 不在本轮尝试把全部 177 条 relic 一次性做完。

### 4.3 第三阶段：修静态资料与补齐缺失条目

目标：让内容真源与本地原版资料重新一致，并更新项目说明。

需要完成：

- 修复审计中确认的静态资料偏差：
  - 关键效果错配
  - 稀有度/池子不一致
  - 角色归属不一致
  - 命名/ID 异常
- 补录 `怀表`、`扭曲漏斗`、`忍术卷轴`。
- 对仍未实现效果的 relic，保留 `implementation_status` 标记，但让静态资料准确。
- 更新 `README.md` 中关于“已完整录入”“运行时逐步补齐”的描述，使之与代码事实一致。

---

## 五、组件与文件边界

### 5.1 运行时可获得性与序列构建

文件：

- `src/slay_the_spire/use_cases/start_run.py`
- `src/slay_the_spire/domain/rewards/reward_generator.py`
- `src/slay_the_spire/use_cases/opening_flow.py`
- `src/slay_the_spire/use_cases/enter_room.py`

职责：

- 用统一规则构建 relic sequences。
- 保证普通/精英/商店/Boss/Neow 的 relic 来源都依赖相同的可获得性约束。
- 不在各处复制“implementation_status 过滤”逻辑，避免再次分叉。

### 5.2 统一 relic 领取路径

文件：

- `src/slay_the_spire/use_cases/apply_reward.py`
- `src/slay_the_spire/use_cases/shop_action.py`
- `src/slay_the_spire/use_cases/event_action.py`
- `src/slay_the_spire/app/session.py`

职责：

- `apply_reward` 成为唯一的 relic 领取真源。
- 统一处理：
  - 重复 relic
  - `circlet`
  - `replaces_relic_id`
  - 获得时副作用
- 其余入口只负责把用户动作转成 reward id，再调用统一入口。

### 5.3 运行时 lifecycle 与 Hook

文件：

- `src/slay_the_spire/domain/hooks/runtime.py`
- `src/slay_the_spire/domain/combat/turn_flow.py`
- `src/slay_the_spire/use_cases/enter_room.py`

职责：

- 区分：
  - 进入战斗时一次性触发
  - 每回合开始触发
  - 战斗结束触发
- 不再把“每回合 +1 能量”建模成“战斗开始时给 1 能量”。
- 如果现有 Hook 名称不够表达生命周期，可以最小化扩展新的 hook 名称，但不引入和仓库风格不一致的大型框架。

### 5.4 内容真源与文档

文件：

- `content/relics/*.json`
- `tests/content/test_registry_validation.py`
- `README.md`

职责：

- 让 `content/` 成为原版遗物静态事实的唯一真源。
- 把本地资料比对结果沉淀为内容校验测试，避免同类偏差再次回归。
- README 只陈述当前事实，不提前声称“已完整”或“已实现”。

---

## 六、运行时规则设计

### 6.1 哪些 relic 可以进入实际奖励池

统一规则：

- 通用可获得池：`common`、`uncommon`、`rare`、`shop`、`boss`、`neow`
- 进入这些池的条件：
  - 属于该 pool
  - 角色归属允许
  - `implementation_status` 为 `implemented` 或 `partial`
- 永不由该规则直接发放的条目：
  - `starter`
  - `event`
  - `special`

这样可以保留内容录入进度，又不再让 placeholder 进入真实游戏。

### 6.2 统一 relic 获得规则

所有 `relic:<id>` 奖励统一经过 `apply_reward`。

统一行为：

- `circlet`：允许重复。
- 普通 relic：默认去重。
- `replaces_relic_id`：若存在被替换 relic，则替换旧 relic，而不是简单 append。
- 获得时副作用：集中放在 `apply_reward` 处理，避免商店/事件/Boss 各写一份。

### 6.3 每回合能量 relic 的实现边界

本轮至少覆盖：

- `ectoplasm`
- `coffee_dripper`
- `fusion_hammer`
- `busted_crown`

目标行为：

- 玩家每回合开始时，基础能量结算后获得额外能量。
- 不能只在进入战斗时给一次。
- 现有首回合测试要保留，并新增第二回合验证。

### 6.4 替换型 relic 的实现边界

本轮不做“所有替换型 relic 的完整运行时功能”，但至少建立统一替换契约：

- `black_blood` 替换 `burning_blood`
- `frozen_core` 替换 `cracked_core`
- `holy_water` 替换 `pure_water`
- `ring_of_the_serpent` 替换 `ring_of_the_snake`

如果后 3 个 relic 仍然属于未实现内容，则它们至少要在统一领取入口中具备正确替换行为，避免未来再次硬编码。

---

## 七、测试设计

### 7.1 第一阶段测试

- `tests/use_cases/test_start_run.py`
  - 断言 relic sequences 不再包含 placeholder relic。
- `tests/use_cases/test_apply_reward.py`
  - 断言 `replaces_relic_id` 通用生效。
  - 断言 `circlet` 仍允许重复。
- `tests/use_cases/test_enter_room.py`
  - 断言宝箱/精英掉落不会再落到 placeholder relic。
- `tests/use_cases/test_shop_and_rest_actions.py`
  - 断言商店买 relic 走统一入口而不是直接 append。
- `tests/use_cases/test_event_actions.py`
  - 断言事件加 relic 走统一入口。

### 7.2 第二阶段测试

- `tests/domain/test_combat_flow.py` 或 `tests/use_cases/test_start_run.py`
  - 新增第二回合能量 relic 验证。
- `tests/use_cases/test_enter_room.py` 或新增更合适文件
  - 覆盖 `burning_blood` / `black_blood` 战斗结束回血。
- `tests/use_cases/test_apply_reward.py`
  - 覆盖替换 relic 的统一契约。

### 7.3 第三阶段测试

- `tests/content/test_registry_validation.py`
  - 校验缺失 relic 已录入。
  - 校验关键偏差项的 rarity / pools / owner / implementation_status。
- 如 README 的事实陈述发生变化，不单独加测试，但必须在最终 diff 中可见。

---

## 八、文档与事实更新

需要同步更新 `README.md`：

- 删除“原版 1 代基础遗物目录已完整录入到内容层”的不实表述。
- 改为准确描述：
  - 内容层是否已补齐
  - 运行时效果当前覆盖到哪一批
  - placeholder relic 是否仍会进入实际掉落池

如果第三阶段完成后缺失遗物已补齐，可以把 README 改成“已补齐原版遗物目录，运行时效果按批次实现”。

---

## 九、非目标

本轮不做：

- 一次性实现全部原版遗物的完整运行时效果。
- 扩展到新角色可玩、补齐静默/机器人/观者完整开局流程。
- 为本地资料与代码的每一处细微冲突引入复杂的双来源兼容逻辑。
- 为旧存档提供兼容迁移；若确需改存档结构，按仓库现状直接同步更新 schema 和测试。

---

## 十、验收标准

- placeholder relic 不再进入普通/商店/Boss/Neow 实际可获得池。
- 商店、事件、Boss、宝箱 relic 获得路径统一，不再直接 append relic。
- `ectoplasm`、`coffee_dripper`、`fusion_hammer`、`busted_crown` 的额外能量行为不再只生效首回合。
- `black_blood` 以外的替换型 relic 不再依赖未来的硬编码补丁。
- `content/relics` 中审计点名的高优先级资料偏差已修正。
- `怀表`、`扭曲漏斗`、`忍术卷轴` 已录入。
- README 对遗物状态的表述与代码事实一致。
