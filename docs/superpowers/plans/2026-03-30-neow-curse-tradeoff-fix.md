# Neow Curse Tradeoff Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修正 opening 阶段的 Neow 诅咒 tradeoff，使诅咒只作为代价出现，并总是配套高价值奖励。

**Architecture:** 保留现有 `2 free + 2 tradeoff` 的 opening 结构，只替换 `opening_flow.py` 中错误的 `curse_card` 语义。用新的 `curse_bonus` 奖励类型承载“真实高价值奖励 + curse cost”，并同步修正文案渲染与测试，不引入新的 opening 交互模式。

**Tech Stack:** Python 3.12、pytest、textual、rich、uv

---

## File Map

- Modify: `src/slay_the_spire/use_cases/opening_flow.py`
  - 负责 Neow offer 生成、奖励/代价 payload、奖励应用、描述文案。
- Modify: `src/slay_the_spire/adapters/presentation/opening_renderer.py`
  - 负责 opening 面板内联文案，确保诅咒只显示为代价。
- Modify: `src/slay_the_spire/adapters/textual/slay_app.py`
  - 负责 hover preview，确保展示真实奖励和 curse 代价。
- Modify: `tests/use_cases/test_opening_flow.py`
  - 负责生成与结算层 TDD。
- Modify: `tests/adapters/textual/test_slay_app.py`
  - 负责 hover preview TDD。
- Modify: `tests/adapters/presentation/test_presentation_renderer.py`
  - 负责 opening 面板文本 TDD。
- Modify: `README.md`
  - 记录 Neow curse tradeoff 的最新行为。
- Modify: `AGENTS.md`
  - 同步项目行为事实。

### Task 1: 锁定 use case 层的失败测试

**Files:**
- Modify: `tests/use_cases/test_opening_flow.py`
- Test: `tests/use_cases/test_opening_flow.py`

- [ ] **Step 1: 写失败测试，明确 `curse_bonus` 的结构和结算结果**

```python
def test_build_offer_curse_bonus_uses_curse_as_cost_and_non_curse_reward() -> None:
    provider = _provider()

    offer = opening_flow._build_offer("curse", "tradeoff", "curse_bonus", provider, Random(0))

    assert offer.cost_kind == "curse"
    assert offer.cost_payload["card_id"] == "doubt"
    assert offer.reward_kind == "curse_bonus"
    assert offer.reward_payload["reward_type"] in {"gold", "relic", "card"}
    assert offer.summary != "获得诅咒牌"
    assert offer.reward_payload.get("card_id") != "doubt"


def test_apply_neow_offer_curse_bonus_adds_curse_and_applies_premium_reward() -> None:
    provider = _provider()
    opening = build_opening_state(seed=11, preferred_character_id="ironclad", registry=provider)
    offer = opening_flow._build_offer("curse", "tradeoff", "curse_bonus", provider, Random(0))
    opening = replace(opening, neow_offers=[offer])
    before = opening.run_blueprint

    updated = apply_neow_offer(opening, offer.offer_id, registry=provider)

    assert before is not None
    assert updated.run_blueprint is not None
    assert "doubt#11" in updated.run_blueprint.deck
    if offer.reward_payload["reward_type"] == "gold":
        assert updated.run_blueprint.gold == before.gold + 250
```

- [ ] **Step 2: 运行测试，确认按预期失败**

Run: `uv run pytest tests/use_cases/test_opening_flow.py -k "curse_bonus" -v`

Expected: FAIL，失败原因应是 `curse_bonus` 尚未被 `opening_flow.py` 支持，或者 summary / payload 仍沿用旧 `curse_card` 语义。

- [ ] **Step 3: 以最小实现支持 `curse_bonus`**

在 `src/slay_the_spire/use_cases/opening_flow.py` 中做这些改动：

```python
def _pick_tradeoff_reward_kind(rng: Random) -> str:
    kinds = ["upgrade_card", "remove_card", "curse_bonus"]
    return rng.choice(kinds)


def _build_reward_payload(*, reward_kind: str, registry, rng: Random) -> dict[str, object]:
    ...
    if reward_kind == "curse_bonus":
        premium_kind = rng.choice(["gold", "relic", "rare_card"])
        if premium_kind == "gold":
            return {"reward_type": "gold", "reward_id": "gold:250", "amount": 250}
        if premium_kind == "relic":
            relic_id = _choose_relic_id(registry=registry, rng=rng)
            return {
                "reward_type": "relic",
                "reward_id": f"relic:{relic_id}",
                "relic_id": relic_id,
            }
        card_id = _choose_rare_card_id(registry=registry, rng=rng)
        return {
            "reward_type": "card",
            "reward_id": f"card:{card_id}",
            "card_id": card_id,
        }


def _build_cost_payload(*, reward_kind: str, rng: Random) -> tuple[str | None, dict[str, object]]:
    ...
    if reward_kind == "curse_bonus":
        return "curse", {"card_id": "doubt"}


def _build_description(...):
    summary_map = {
        ...
        "curse_bonus": "诅咒换取高价值奖励",
    }
    ...
    elif reward_kind == "curse_bonus":
        reward_type = str(reward_payload["reward_type"])
        if reward_type == "gold":
            summary = "获得 250 金币"
            details = [summary]
        elif reward_type == "relic":
            summary = "获得稀有遗物"
            details = [summary, f"获得遗物：{reward_payload['relic_id']}"]
        else:
            summary = "获得稀有牌"
            details = [summary, f"获得稀有牌：{reward_payload['card_id']}"]


def _apply_reward(...):
    ...
    if reward_kind == "curse_bonus":
        return apply_reward(
            run_state=run_blueprint,
            reward_id=str(reward_payload["reward_id"]),
            registry=registry,
        )
```

同时删除或替换旧的 `curse_card` 分支，避免同义分支并存。

- [ ] **Step 4: 运行测试，确认通过**

Run: `uv run pytest tests/use_cases/test_opening_flow.py -k "curse_bonus" -v`

Expected: PASS

- [ ] **Step 5: 提交 use case 层改动**

```bash
git add tests/use_cases/test_opening_flow.py src/slay_the_spire/use_cases/opening_flow.py
git commit -m "fix: correct Neow curse tradeoff rewards"
```

### Task 2: 修正 opening 面板与 hover preview 的失败测试

**Files:**
- Modify: `tests/adapters/presentation/test_presentation_renderer.py`
- Modify: `tests/adapters/textual/test_slay_app.py`
- Test: `tests/adapters/presentation/test_presentation_renderer.py`
- Test: `tests/adapters/textual/test_slay_app.py`

- [ ] **Step 1: 先补失败测试，锁定展示语义**

在 `tests/adapters/presentation/test_presentation_renderer.py` 增加：

```python
def test_render_session_renderable_shows_curse_bonus_reward_and_cost_separately() -> None:
    session = start_new_game_session(seed=5, preferred_character_id="ironclad")
    provider = StarterContentProvider(session.content_root)
    offer = opening_flow._build_offer("curse", "tradeoff", "curse_bonus", provider, Random(0))
    session = replace(
        session,
        opening_state=replace(session.opening_state, neow_offers=[offer]),
        menu_state=MenuState(mode="opening_neow_offer"),
    )
    ...
    assert "牌组中加入诅咒牌" in rendered
    assert "获得诅咒牌" not in rendered
```

在 `tests/adapters/textual/test_slay_app.py` 增加：

```python
def test_hover_preview_shows_neow_curse_bonus_reward_details_and_curse_cost() -> None:
    session = start_new_game_session(seed=5, preferred_character_id="ironclad")
    provider = StarterContentProvider(session.content_root)
    offer = opening_flow._build_offer("curse-offer", "tradeoff", "curse_bonus", provider, Random(0))
    session = replace(
        session, opening_state=replace(session.opening_state, neow_offers=[offer])
    )

    preview = _hover_preview_renderable(session, f"choose_neow_offer:{offer.offer_id}")

    assert preview is not None
    assert "代价" in preview.plain
    assert "疑虑" in preview.plain
    assert "获得诅咒牌" not in preview.plain
```

- [ ] **Step 2: 运行展示测试，确认先红**

Run: `uv run pytest tests/adapters/presentation/test_presentation_renderer.py tests/adapters/textual/test_slay_app.py -k "curse_bonus" -v`

Expected: FAIL，失败原因应是渲染代码仍只识别 `curse_card`。

- [ ] **Step 3: 最小修正渲染代码**

在 `src/slay_the_spire/adapters/presentation/opening_renderer.py` 中，把原本 `curse_card` 的展示分支改为 `curse_bonus`，并按底层 `reward_type` 输出真实奖励：

```python
elif offer.reward_kind == "curse_bonus":
    reward_type = str(reward_payload["reward_type"])
    if reward_type == "gold":
        details.append(f"获得 {reward_payload['amount']} 金币")
    elif reward_type == "relic":
        relic_id = str(reward_payload["relic_id"])
        details.append(f"获得遗物：{registry.relics().get(relic_id).name}")
    elif reward_type == "card":
        details.append(
            f"获得稀有牌：{_localized_card_name(str(reward_payload['card_id']), registry)}"
        )
```

在 `src/slay_the_spire/adapters/textual/slay_app.py` 中，把 `_format_neow_offer_hover_lines()` 的卡牌分支从：

```python
if offer.reward_kind in {"rare_card", "curse_card"}:
```

改成区分 `rare_card` 和 `curse_bonus`，其中 `curse_bonus` 根据 `reward_type` 分别复用 gold / relic / card 的详情渲染，并始终追加：

```python
f"代价：牌组中加入诅咒牌：{localized_cost_name}"
```
```

- [ ] **Step 4: 运行展示测试，确认转绿**

Run: `uv run pytest tests/adapters/presentation/test_presentation_renderer.py tests/adapters/textual/test_slay_app.py -k "curse_bonus" -v`

Expected: PASS

- [ ] **Step 5: 提交渲染层改动**

```bash
git add \
  tests/adapters/presentation/test_presentation_renderer.py \
  tests/adapters/textual/test_slay_app.py \
  src/slay_the_spire/adapters/presentation/opening_renderer.py \
  src/slay_the_spire/adapters/textual/slay_app.py
git commit -m "fix: clarify Neow curse tradeoff previews"
```

### Task 3: 全量回归与文档同步

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Test: `tests/use_cases/test_opening_flow.py`
- Test: `tests/adapters/presentation/test_presentation_renderer.py`
- Test: `tests/adapters/textual/test_slay_app.py`

- [ ] **Step 1: 更新 README 行为描述**

在 `README.md` 的 opening / Neow 说明中加入类似表述：

```md
- 当前 Neow 的 tradeoff 诅咒选项会以“加入诅咒牌”作为代价，并发放配套高价值奖励；不会再出现“奖励本身就是诅咒牌”的选项。
```

- [ ] **Step 2: 更新 AGENTS.md 行为事实**

在 `AGENTS.md` 的 opening / Neow 相关条目中加入类似表述：

```md
- 当前 opening 的 Neow tradeoff 中，诅咒只作为代价出现；若选项要求加入诅咒牌，会同时提供配套高价值奖励，不会把诅咒牌当成奖励本体。
```

- [ ] **Step 3: 运行目标测试集**

Run:

```bash
uv run pytest \
  tests/use_cases/test_opening_flow.py \
  tests/adapters/presentation/test_presentation_renderer.py \
  tests/adapters/textual/test_slay_app.py -v
```

Expected: PASS

- [ ] **Step 4: 运行完整测试集**

Run: `uv run pytest`

Expected: PASS

- [ ] **Step 5: 提交文档与验证收尾**

```bash
git add README.md AGENTS.md
git commit -m "docs: document Neow curse tradeoff behavior"
```

## Self-Review

- Spec coverage:
  - `curse` 只作为代价：Task 1
  - 必须配套高价值奖励：Task 1
  - 面板与 hover preview 区分奖励/代价：Task 2
  - README / AGENTS 同步：Task 3
- Placeholder scan:
  - 已给出具体文件、测试名、命令和代码片段，没有 `TODO` / `TBD` 占位。
- Type consistency:
  - 全计划统一使用 `curse_bonus`、`reward_type`、`cost_kind == "curse"`，没有混用旧命名作为新行为。
