# 遗物描述字段合并设计

**日期**：2026-04-05
**状态**：已批准

## 背景

当前每条遗物在 JSON 中有两个高度重复的文本字段：
- `"summary"`：短句，无句号（如 `"战斗结束后回复 6 点生命"`）
- `"description"`：完整句，有句号（如 `"战斗结束后，回复 6 点生命。"`）

两者内容几乎完全相同，仅差一个逗号和句号。UI 有多处同时展示两个字段，造成冗余显示。目标是合并为单一字段 `description`（完整句式，有句号），与原版游戏 tooltip 概念对齐。

## 方案

**删除 `summary`，保留 `description` 为唯一描述字段。**

## 改动范围

### 1. 数据层

**`content/relics/*.json`（8 个文件，180 条遗物）：**
- 删除每条遗物的 `"summary"` 字段。
- 保留 `"description"` 字段，内容不变（完整句式，有句号）。

**`src/slay_the_spire/content/registries.py`（`RelicDef`）：**
- 删除 `summary: str | None = None` 字段。
- `description: str | None = None` 改为必填 `description: str`。
- 解析函数删掉 `summary=` 赋值行，`description=` 改为必填读取（`_require_str`）。

### 2. 渲染层

**`src/slay_the_spire/adapters/presentation/inspect.py`：**
- `format_relic_detail_lines`（详细面板）：删掉"摘要"行；fallback 逻辑 `summary or description` 简化为直接用 `description`。
- hover 预览处：删掉"摘要:"行，只保留"描述:"行。

**`src/slay_the_spire/adapters/textual/slay_app.py`：**
- 遗物列表预览：`summary = relic_def.summary or relic_def.description` 改为直接用 `relic_def.description`。

### 3. 测试层

**`tests/content/test_registry_validation.py`：**
- `test_all_relics_have_localized_summary_and_description` 改名为 `test_all_relics_have_description`，删掉 `assert relic.summary` 行。
- 参数化测试组：删掉 `expected_summary` 参数列及所有入参值，删掉 `assert relic.summary == expected_summary`。
- 语料库回归测试（对比 `card_relic_expectations.json`）：删掉 `relic.summary` 对比逻辑，只保留 `name` 和 `description`。

## 不在范围内

- 卡牌、药水、敌人等其他内容类型的描述字段不受影响。
- `docs/reference/sts_huijiwiki/card_relic_expectations.json` 当前不在仓库中，无需处理。
- 不修改遗物描述文本内容本身，只做字段结构调整。
