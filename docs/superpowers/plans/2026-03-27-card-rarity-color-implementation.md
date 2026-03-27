# Card Rarity Color Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为终端版与 Textual 预览中的卡牌建立稳定的稀有度属性与颜色展示规则，并用统一强调区分升级前后。

**Architecture:** 先通过测试锁定内容与展示规则，再抽出统一的卡牌展示语义 helper，分别接到 `rich` 终端 widgets 和 `textual` hover preview 上。升级态独立于稀有度判断，升级牌继承基础牌稀有度。

**Tech Stack:** Python 3.12, pytest, rich, uv

---

### Task 1: 锁定卡牌稀有度内容规则

**Files:**
- Modify: `tests/content/test_registry_validation.py`
- Modify: `content/cards/ironclad_starter.json`
- Modify: `content/cards/curses.json`
- Modify: `src/slay_the_spire/data/content/cards/ironclad_starter.json`
- Modify: `src/slay_the_spire/data/content/cards/curses.json`

- [ ] **Step 1: 写失败测试**

在 `tests/content/test_registry_validation.py` 添加测试，验证：
- `strike` 与 `strike_plus` 都是 `basic`
- `anger` 与 `anger_plus` 都是 `common`
- `burn` / `doubt` / `injury` 都是 `curse`

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/content/test_registry_validation.py -v`
Expected: FAIL，因现有升级牌仍为 `special` 且诅咒牌缺少 `rarity`

- [ ] **Step 3: 最小实现**

同步修改两套卡牌 JSON：
- 升级牌继承原稀有度
- 诅咒牌补 `rarity: "curse"`

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/content/test_registry_validation.py -v`
Expected: PASS

### Task 2: 为卡牌样式写终端组件测试

**Files:**
- Modify: `tests/adapters/terminal/test_renderer.py`
- Modify: `src/slay_the_spire/adapters/terminal/widgets.py`
- Modify: `src/slay_the_spire/adapters/terminal/theme.py`

- [ ] **Step 1: 写失败测试**

新增测试覆盖：
- 普通 `common` 牌名称使用 `card.rarity.common`
- 升级牌在原主色基础上附加 `card.upgraded`
- `curse` 牌使用 `card.rarity.curse`

优先直接断言 `Text` 样式或 `spans`，不要只断言导出文本。

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/adapters/terminal/test_renderer.py -v`
Expected: FAIL，因 helper 与样式尚不存在

- [ ] **Step 3: 最小实现**

在 `src/slay_the_spire/adapters/terminal/theme.py` 增加卡牌稀有度与升级态样式。

在 `src/slay_the_spire/adapters/terminal/widgets.py` 增加：
- 稀有度样式映射
- 升级态判断
- 返回 `Text` 的卡牌名称 helper
- 稀有度中文标签 helper（若详情页需要）

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/adapters/terminal/test_renderer.py -v`
Expected: PASS

### Task 3: 接入主要终端入口

**Files:**
- Modify: `src/slay_the_spire/adapters/terminal/screens/combat.py`
- Modify: `src/slay_the_spire/adapters/terminal/screens/non_combat.py`
- Modify: `src/slay_the_spire/adapters/terminal/inspect.py`
- Test: `tests/adapters/terminal/test_renderer.py`

- [ ] **Step 1: 写失败测试**

补测试锁定：
- 战斗选牌列表可正常渲染带样式的卡牌名
- inspect 卡牌详情包含“稀有度”和“状态”
- 非战斗场景的可升级/商店/奖励列表仍可正常显示卡牌名

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/adapters/terminal/test_renderer.py -v`
Expected: FAIL，因这些入口仍使用旧的字符串拼接

- [ ] **Step 3: 最小实现**

把主要入口改为调用统一 helper，保持现有菜单编号和摘要结构不变。

在卡牌详情面板中新增：
- `稀有度`
- `状态`

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/adapters/terminal/test_renderer.py -v`
Expected: PASS

### Task 4: 接入 Textual 卡牌悬浮预览

**Files:**
- Modify: `src/slay_the_spire/adapters/textual/slay_app.py`
- Modify: `tests/adapters/textual/test_slay_app.py`
- Modify: helper file(s) introduced in Task 2 if needed

- [ ] **Step 1: 写失败测试**

补测试锁定：
- 卡牌 hover preview 显示稀有度与状态
- 普通牌和升级牌走同一稀有度主色规则
- 升级牌有统一强调

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -v`
Expected: FAIL，因现有 textual hover preview 尚未使用该规则

- [ ] **Step 3: 最小实现**

把 textual 卡牌预览接到统一卡牌展示语义：
- 名称按稀有度着色
- 升级牌附加统一强调
- 文本包含 `稀有度` 与 `状态`

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -v`
Expected: PASS

### Task 5: 全量回归

**Files:**
- Modify: only if regressions appear during verification

- [ ] **Step 1: 运行针对性测试集**

Run: `uv run pytest tests/content/test_registry_validation.py tests/adapters/terminal/test_renderer.py tests/adapters/terminal/test_app.py tests/adapters/textual/test_slay_app.py -v`
Expected: PASS

- [ ] **Step 2: 运行全量测试**

Run: `uv run pytest`
Expected: PASS

- [ ] **Step 3: 手动 smoke**

Run: `uv run python -m slay_the_spire.app.cli new --seed 5`
Expected: 终端中手牌、牌堆或详情页可看到按稀有度的卡牌颜色，升级牌有统一强调
