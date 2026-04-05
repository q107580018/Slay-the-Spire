# 遗物描述字段合并 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 删除 `RelicDef.summary` 字段及 JSON 中所有 `"summary"` 键，统一使用 `description` 作为遗物唯一描述字段。

**Architecture:** 自下而上逐层改动：先清理 JSON 内容文件，再收紧 `RelicDef` 数据类及其解析，再删除渲染层对 `summary` 的引用，最后同步测试。每个任务单独提交，全程保持测试绿色。

**Tech Stack:** Python 3.12, pytest, Rich/Textual

---

### Task 1：从 JSON 内容文件删除 `"summary"` 字段

**Files:**
- Modify: `content/relics/starter_relics.json`
- Modify: `content/relics/common_relics.json`
- Modify: `content/relics/uncommon_relics.json`
- Modify: `content/relics/rare_relics.json`
- Modify: `content/relics/boss_relics.json`
- Modify: `content/relics/shop_relics.json`
- Modify: `content/relics/event_relics.json`
- Modify: `content/relics/special_relics.json`

- [ ] **Step 1：用脚本批量删除所有 JSON 文件中的 `"summary"` 行**

```bash
cd /path/to/repo   # 替换为实际仓库根目录
python3 - <<'EOF'
import json, pathlib

relic_dir = pathlib.Path("content/relics")
for json_file in sorted(relic_dir.glob("*.json")):
    data = json.loads(json_file.read_text(encoding="utf-8"))
    for relic in data["relics"]:
        relic.pop("summary", None)
    json_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"cleaned: {json_file}")
EOF
```

预期输出（8 行）：
```
cleaned: content/relics/boss_relics.json
cleaned: content/relics/common_relics.json
cleaned: content/relics/event_relics.json
cleaned: content/relics/rare_relics.json
cleaned: content/relics/shop_relics.json
cleaned: content/relics/special_relics.json
cleaned: content/relics/starter_relics.json
cleaned: content/relics/uncommon_relics.json
```

- [ ] **Step 2：抽查确认 `"summary"` 已不存在**

```bash
grep -r '"summary"' content/relics/
```

预期：无输出（exit code 1）。

- [ ] **Step 3：抽查 `"description"` 仍保留**

```bash
python3 -c "
import json, pathlib
count = sum(
    1 for f in pathlib.Path('content/relics').glob('*.json')
    for r in json.loads(f.read_text())['relics']
    if 'description' in r
)
print('relics with description:', count)
"
```

预期：`relics with description: 180`（或实际遗物总数）。

- [ ] **Step 4：提交**

```bash
git add content/relics/
git commit -m "content: remove redundant summary field from all relic JSON files"
```

---

### Task 2：收紧 `RelicDef` 数据类及解析函数

**Files:**
- Modify: `src/slay_the_spire/content/registries.py:145-162, 372-420`

- [ ] **Step 1：先跑现有测试，确认基线绿色**

```bash
uv run pytest tests/content/test_registry_validation.py -v --tb=short 2>&1 | tail -20
```

预期：全部 PASS（此时 JSON 已无 `summary`，但 `RelicDef` 仍接受 `None`，所以不会报错）。

- [ ] **Step 2：修改 `RelicDef` 数据类**

在 `src/slay_the_spire/content/registries.py` 中，找到：

```python
@dataclass(slots=True, frozen=True)
class RelicDef:
    id: str
    name: str
    trigger_hooks: list[str]
    passive_effects: list[JsonDict]
    summary: str | None = None
    description: str | None = None
    replaces_relic_id: str | None = None
```

改为：

```python
@dataclass(slots=True, frozen=True)
class RelicDef:
    id: str
    name: str
    trigger_hooks: list[str]
    passive_effects: list[JsonDict]
    description: str = ""
    replaces_relic_id: str | None = None
```

（删除 `summary` 行；`description` 从 `str | None = None` 改为必填 `str = ""`，后续解析会覆盖默认值。）

- [ ] **Step 3：修改 `_build` 解析函数**

找到：

```python
        summary=_require_optional_str(data.get("summary"), "summary"),
        description=_require_optional_str(data.get("description"), "description"),
```

改为（删掉 `summary` 行，`description` 改用 `_require_str`）：

```python
        description=_require_str(data.get("description"), "description"),
```

- [ ] **Step 4：跑测试，预期此时部分测试会失败（因为测试还引用 `relic.summary`）**

```bash
uv run pytest tests/content/test_registry_validation.py -v --tb=short 2>&1 | tail -30
```

预期：与 `relic.summary` 相关的测试报 `AttributeError: 'RelicDef' object has no attribute 'summary'`。

- [ ] **Step 5：提交（红色测试状态，下一个 Task 修复）**

```bash
git add src/slay_the_spire/content/registries.py
git commit -m "refactor: remove RelicDef.summary, make description required str"
```

---

### Task 3：修复测试层——删除所有对 `summary` 的引用

**Files:**
- Modify: `tests/content/test_registry_validation.py:383-410, 583-799, 848-857, 1126-1154`

- [ ] **Step 1：修复 `test_boss_relic_fields` 中的 `black_blood.summary` 断言**

找到（约第 394-395 行）：

```python
    assert black_blood.name == "黑色之血"
    assert black_blood.summary == "战斗结束后回复 12 点生命"
    assert black_blood.description == "取代燃烧之血，战斗结束后回复 12 点生命。"
```

改为（删掉 `summary` 那行）：

```python
    assert black_blood.name == "黑色之血"
    assert black_blood.description == "取代燃烧之血，战斗结束后回复 12 点生命。"
```

- [ ] **Step 2：修复 `test_all_relics_have_localized_summary_and_description`**

找到（约第 848-857 行）：

```python
@pytest.mark.parametrize("content_root", _content_roots())
def test_all_relics_have_localized_summary_and_description(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    for relic in provider.relics().all():
        assert relic.name
        assert relic.summary
        assert relic.description
        assert relic.pools
        assert relic.effect_blueprint is not None
```

改为：

```python
@pytest.mark.parametrize("content_root", _content_roots())
def test_all_relics_have_description(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    for relic in provider.relics().all():
        assert relic.name
        assert relic.description
        assert relic.pools
        assert relic.effect_blueprint is not None
```

- [ ] **Step 3：修复参数化测试 `test_audited_relic_metadata_matches_local_reference`**

找到（约第 583-799 行）整个 `@pytest.mark.parametrize` 块的参数元组头部：

```python
@pytest.mark.parametrize(
    (
        "relic_id",
        "expected_name",
        "expected_summary",
        "expected_description",
        "expected_rarity",
        "expected_pools",
        "expected_source_tags",
        "expected_owner_ids",
    ),
    [
        (
            "face_of_cleric",
            "牧师的脸",
            "每场战斗后你的最大生命值增加 1",
            "每场战斗后，你的最大生命值增加 1。",
            ...
        ),
        ...
    ],
)
```

将参数名元组改为（删掉 `"expected_summary"`）：

```python
@pytest.mark.parametrize(
    (
        "relic_id",
        "expected_name",
        "expected_description",
        "expected_rarity",
        "expected_pools",
        "expected_source_tags",
        "expected_owner_ids",
    ),
    [
```

然后对每个参数元组，删掉 `expected_summary` 对应的那个字符串值（每个元组的第三个元素，即"短句无句号"的那个值）。

完整更新后的参数列表（共 18 条）：

```python
    [
        (
            "face_of_cleric",
            "牧师的脸",
            "每场战斗后，你的最大生命值增加 1。",
            "event",
            ["event"],
            ["event_reward"],
            [],
        ),
        (
            "gremlin_visage",
            "地精容貌",
            "每场战斗开始时，你拥有 1 层虚弱。",
            "event",
            ["event"],
            ["event_reward"],
            [],
        ),
        (
            "nloths_gift",
            "恩洛斯的礼物",
            "使你在怪物奖励中遇见稀有牌的几率变为 3 倍。",
            "event",
            ["event"],
            ["event_reward"],
            [],
        ),
        (
            "ssserpent_head",
            "蛇的头",
            "每次进入？房间时，获得 50 金币。",
            "event",
            ["event"],
            ["event_reward"],
            [],
        ),
        (
            "warped_tongs",
            "弯曲铁钳",
            "在你的每个回合开始时，随机升级一张你的手牌（只影响本场战斗）。",
            "event",
            ["event"],
            ["event_reward"],
            [],
        ),
        (
            "cloak_clasp",
            "斗篷扣",
            "在你的回合结束时，每有一张手牌获得 1 点格挡。",
            "rare",
            ["rare", "neow"],
            ["standard_pool"],
            ["watcher"],
        ),
        (
            "damaru",
            "手摇鼓",
            "在你的回合开始时，获得 1 层真言。",
            "common",
            ["common", "neow"],
            ["standard_pool"],
            ["watcher"],
        ),
        (
            "melange",
            "美琅脂",
            "你每次将抽牌堆洗牌时，预见 3。",
            "shop",
            ["shop"],
            ["shop"],
            ["watcher"],
        ),
        (
            "thread_and_needle",
            "针线",
            "在每场战斗开始时，获得 4 层多层护甲。",
            "rare",
            ["rare", "neow"],
            ["standard_pool"],
            [],
        ),
        (
            "abacus",
            "算盘",
            "你每次将抽牌堆洗牌时，获得 6 点格挡。",
            "shop",
            ["shop"],
            ["shop"],
            [],
        ),
        (
            "gambling_chip",
            "赌博筹码",
            "在每场战斗开始时，丢弃任意张牌，然后抽相同数量张牌。",
            "rare",
            ["rare", "neow"],
            ["standard_pool"],
            [],
        ),
        (
            "shuriken",
            "手里剑",
            "你每在同一回合内打出 3 张攻击牌，获得 1 点力量。",
            "uncommon",
            ["uncommon", "neow"],
            ["standard_pool"],
            [],
        ),
        (
            "runic_capacitor",
            "符文电容器",
            "每场战斗开始时，获得 3 个额外充能球栏位。",
            "shop",
            ["shop"],
            ["shop"],
            [],
        ),
        (
            "the_courier",
            "送货员",
            "商人的卡牌、遗物和药水不再会卖光，并且所有商品打折 20%。",
            "uncommon",
            ["uncommon", "neow"],
            ["standard_pool"],
            [],
        ),
        (
            "neows_lament",
            "涅奥的悲恸",
            "接下来 3 场战斗中的敌人将只有 1 点生命。",
            "event",
            ["event"],
            ["event_reward"],
            [],
        ),
        (
            "pocketwatch",
            "怀表",
            "若你在某个回合打出的牌少于等于 3 张，则在你的下个回合开始时额外抽 3 张牌。",
            "rare",
            ["rare", "neow"],
            ["standard_pool"],
            [],
        ),
        (
            "twisted_funnel",
            "扭曲漏斗",
            "在每场战斗开始时，给予所有敌人 4 层中毒。",
            "shop",
            ["shop"],
            ["shop"],
            ["silent"],
        ),
        (
            "ninja_scroll",
            "忍术卷轴",
            "每场战斗开始时，手牌中增加 3 张小刀。",
            "uncommon",
            ["uncommon", "neow"],
            ["standard_pool"],
            ["silent"],
        ),
    ],
```

- [ ] **Step 4：更新函数签名和函数体，删掉 `expected_summary`**

找到（约第 778-799 行）：

```python
def test_audited_relic_metadata_matches_local_reference(
    content_root: Path,
    relic_id: str,
    expected_name: str,
    expected_summary: str,
    expected_description: str,
    expected_rarity: str,
    expected_pools: list[str],
    expected_source_tags: list[str],
    expected_owner_ids: list[str],
) -> None:
    provider = StarterContentProvider(content_root)

    relic = provider.relics().get(relic_id)

    assert relic.name == expected_name
    assert relic.summary == expected_summary
    assert relic.description == expected_description
    assert relic.rarity == expected_rarity
    assert relic.pools == expected_pools
    assert relic.source_tags == expected_source_tags
    assert relic.owner_character_ids == expected_owner_ids
```

改为：

```python
def test_audited_relic_metadata_matches_local_reference(
    content_root: Path,
    relic_id: str,
    expected_name: str,
    expected_description: str,
    expected_rarity: str,
    expected_pools: list[str],
    expected_source_tags: list[str],
    expected_owner_ids: list[str],
) -> None:
    provider = StarterContentProvider(content_root)

    relic = provider.relics().get(relic_id)

    assert relic.name == expected_name
    assert relic.description == expected_description
    assert relic.rarity == expected_rarity
    assert relic.pools == expected_pools
    assert relic.source_tags == expected_source_tags
    assert relic.owner_character_ids == expected_owner_ids
```

- [ ] **Step 5：修复 `test_all_relic_names_and_summaries_match_huiji_reference`**

找到（约第 1125-1154 行）：

```python
@pytest.mark.parametrize("content_root", _content_roots())
def test_all_relic_names_and_summaries_match_huiji_reference(
    content_root: Path,
) -> None:
    fixture_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "reference"
        / "sts_huijiwiki"
        / "card_relic_expectations.json"
    )
    expectations = json.loads(fixture_path.read_text(encoding="utf-8"))["relics"]
    provider = StarterContentProvider(content_root)

    mismatches: list[str] = []
    for relic in provider.relics().all():
        expected = expectations.get(relic.id)
        if expected is None:
            mismatches.append(f"{relic.id}: missing expectation")
            continue
        if relic.name != expected["name"]:
            mismatches.append(
                f"{relic.id}: name mismatch (content={relic.name!r}, fixture={expected['name']!r})"
            )
        if relic.summary != expected["summary"]:
            mismatches.append(
                f"{relic.id}: summary mismatch (content={relic.summary!r}, fixture={expected['summary']!r})"
            )

    assert not mismatches, "\n".join(mismatches[:20])
```

改为（函数改名，删掉 `summary` 对比，只保留 `name` 和 `description`）：

```python
@pytest.mark.parametrize("content_root", _content_roots())
def test_all_relic_names_and_descriptions_match_huiji_reference(
    content_root: Path,
) -> None:
    fixture_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "reference"
        / "sts_huijiwiki"
        / "card_relic_expectations.json"
    )
    expectations = json.loads(fixture_path.read_text(encoding="utf-8"))["relics"]
    provider = StarterContentProvider(content_root)

    mismatches: list[str] = []
    for relic in provider.relics().all():
        expected = expectations.get(relic.id)
        if expected is None:
            mismatches.append(f"{relic.id}: missing expectation")
            continue
        if relic.name != expected["name"]:
            mismatches.append(
                f"{relic.id}: name mismatch (content={relic.name!r}, fixture={expected['name']!r})"
            )
        if relic.description != expected["description"]:
            mismatches.append(
                f"{relic.id}: description mismatch (content={relic.description!r}, fixture={expected['description']!r})"
            )

    assert not mismatches, "\n".join(mismatches[:20])
```

- [ ] **Step 6：跑测试，确认全部通过**

```bash
uv run pytest tests/content/test_registry_validation.py -v --tb=short 2>&1 | tail -30
```

预期：所有测试 PASS，无 `AttributeError`，无 `FAILED`。

- [ ] **Step 7：提交**

```bash
git add tests/content/test_registry_validation.py
git commit -m "test: remove expected_summary from relic tests, rename description test"
```

---

### Task 4：修复渲染层——`inspect.py` 删除 `summary` 引用

**Files:**
- Modify: `src/slay_the_spire/adapters/presentation/inspect.py:235-291, 362-404`

- [ ] **Step 1：修复 `format_relic_detail_lines`（约第 235-291 行）**

找到：

```python
    effect_summary = summarize_relic_effects(relic_def.passive_effects)
    if effect_summary == "-":
        fallback = relic_def.summary or relic_def.description
        if isinstance(fallback, str) and fallback:
            effect_summary = fallback
    lines = [
        Text.assemble(("名称 ", "summary.label"), relic_def.name),
        Text.assemble(("遗物 ", "summary.label"), relic_id),
        Text.assemble(
            ("效果 ", "summary.label"),
            effect_summary,
        ),
    ]
    lines.extend(_format_relic_metadata_lines(relic_def))
    if relic_def.summary is not None:
        lines.append(Text.assemble(("摘要 ", "summary.label"), relic_def.summary))
    if relic_def.description is not None:
        lines.append(Text.assemble(("描述 ", "summary.label"), relic_def.description))
```

改为：

```python
    effect_summary = summarize_relic_effects(relic_def.passive_effects)
    if effect_summary == "-" and relic_def.description:
        effect_summary = relic_def.description
    lines = [
        Text.assemble(("名称 ", "summary.label"), relic_def.name),
        Text.assemble(("遗物 ", "summary.label"), relic_id),
        Text.assemble(
            ("效果 ", "summary.label"),
            effect_summary,
        ),
    ]
    lines.extend(_format_relic_metadata_lines(relic_def))
    lines.append(Text.assemble(("描述 ", "summary.label"), relic_def.description))
```

- [ ] **Step 2：修复 hover 预览处（约第 362-404 行）**

找到：

```python
        if relic_def.summary is not None:
            lines.append(Text.assemble(("摘要: ", "summary.label"), relic_def.summary))
        if relic_def.description is not None:
            lines.append(
                Text.assemble(("描述: ", "summary.label"), relic_def.description)
            )
```

改为：

```python
        lines.append(Text.assemble(("描述: ", "summary.label"), relic_def.description))
```

- [ ] **Step 3：修复 `slay_app.py` 遗物列表预览**

在 `src/slay_the_spire/adapters/textual/slay_app.py`（约第 403-408 行），找到：

```python
            summary = relic_def.summary or relic_def.description
            if not isinstance(summary, str) or not summary:
                summary = summarize_relic_effects(relic_def.passive_effects)
            lines.append(Text.assemble(f"{index}. ", relic_def.name, f" - {summary}"))
```

改为：

```python
            description = relic_def.description or summarize_relic_effects(relic_def.passive_effects)
            lines.append(Text.assemble(f"{index}. ", relic_def.name, f" - {description}"))
```

- [ ] **Step 4：跑全量测试**

```bash
uv run pytest --tb=short 2>&1 | tail -20
```

预期：全部 PASS。

- [ ] **Step 5：提交**

```bash
git add src/slay_the_spire/adapters/presentation/inspect.py \
        src/slay_the_spire/adapters/textual/slay_app.py
git commit -m "refactor: remove summary references from relic render layer"
```
