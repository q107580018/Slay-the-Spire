# Neow Hover Preview Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich Textual Neow option hover previews so card, relic, and potion rewards reuse the same detailed formatter output as other hover-preview surfaces, while preserving the existing compact inline Neow panel.

**Architecture:** Keep the change isolated to the Textual adapter. Add one private formatter in `src/slay_the_spire/adapters/textual/slay_app.py` for Neow hover content, switch the Neow hover branch to that formatter, and cover each reward kind with focused adapter tests in `tests/adapters/textual/test_slay_app.py`.

**Tech Stack:** Python 3.12, Textual, Rich, pytest, uv

---

## File Structure

- Modify: `src/slay_the_spire/adapters/textual/slay_app.py`
  Responsibility: Textual hover-preview rendering for opening/Neow menus. Add a Neow-specific hover formatter and route Neow hover preview through it.
- Modify: `tests/adapters/textual/test_slay_app.py`
  Responsibility: Regression coverage for Textual hover preview behavior in the opening flow.
- Modify: `README.md`
  Responsibility: Document that Neow option hover preview now shows detailed reward effects in Textual.
- Modify: `AGENTS.md`
  Responsibility: Keep the repo-specific behavior notes aligned with the new Neow hover-preview capability.

---

### Task 1: Add Failing Tests For Richer Neow Hover Preview

**Files:**
- Modify: `tests/adapters/textual/test_slay_app.py:140-190`
- Test: `tests/adapters/textual/test_slay_app.py`

- [ ] **Step 1: Write the failing tests**

Insert or update the Neow hover-preview tests so they assert detailed formatter output instead of only localized names:

```python
def test_hover_preview_shows_localized_neow_offer_details() -> None:
    session = start_new_game_session(seed=5, preferred_character_id="ironclad")
    provider = StarterContentProvider(session.content_root)
    offer = opening_flow._build_offer("rare-card", "free", "rare_card", provider, Random(0))
    localized_name = provider.cards().get(str(offer.reward_payload["card_id"])).name
    session = replace(session, opening_state=replace(session.opening_state, neow_offers=[offer]))

    preview = _hover_preview_renderable(session, f"choose_neow_offer:{offer.offer_id}")

    assert preview is not None
    assert localized_name in preview.plain
    assert "效果" in preview.plain
    assert str(offer.reward_payload["card_id"]) not in preview.plain


def test_hover_preview_neow_relic_offer_shows_relic_detail() -> None:
    session = start_new_game_session(seed=5, preferred_character_id="ironclad")
    provider = StarterContentProvider(session.content_root)
    offer = opening_flow._build_offer("relic-offer", "free", "relic", provider, Random(0))
    relic_name = provider.relics().get(str(offer.reward_payload["relic_id"])).name
    session = replace(session, opening_state=replace(session.opening_state, neow_offers=[offer]))

    preview = _hover_preview_renderable(session, f"choose_neow_offer:{offer.offer_id}")

    assert preview is not None
    assert relic_name in preview.plain
    assert "效果" in preview.plain


def test_hover_preview_neow_potion_offer_shows_potion_detail() -> None:
    session = start_new_game_session(seed=5, preferred_character_id="ironclad")
    provider = StarterContentProvider(session.content_root)
    offer = opening_flow._build_offer("potion-offer", "free", "potion", provider, Random(0))
    potion_name = provider.potions().get(str(offer.reward_payload["potion_id"])).name
    session = replace(session, opening_state=replace(session.opening_state, neow_offers=[offer]))

    preview = _hover_preview_renderable(session, f"choose_neow_offer:{offer.offer_id}")

    assert preview is not None
    assert potion_name in preview.plain
    assert "效果" in preview.plain


def test_hover_preview_neow_gold_offer_shows_amount_without_cost() -> None:
    session = start_new_game_session(seed=5, preferred_character_id="ironclad")
    provider = StarterContentProvider(session.content_root)
    offer = opening_flow._build_offer("gold-offer", "free", "gold", provider, Random(0))
    session = replace(session, opening_state=replace(session.opening_state, neow_offers=[offer]))

    preview = _hover_preview_renderable(session, f"choose_neow_offer:{offer.offer_id}")

    assert preview is not None
    assert "100" in preview.plain
    assert "金币" in preview.plain
    assert "代价" not in preview.plain


def test_hover_preview_neow_upgrade_offer_shows_cost() -> None:
    session = start_new_game_session(seed=5, preferred_character_id="ironclad")
    provider = StarterContentProvider(session.content_root)
    offer = opening_flow._build_offer("upgrade-offer", "tradeoff", "upgrade_card", provider, Random(0))
    session = replace(session, opening_state=replace(session.opening_state, neow_offers=[offer]))

    preview = _hover_preview_renderable(session, f"choose_neow_offer:{offer.offer_id}")

    assert preview is not None
    assert "升级" in preview.plain
    assert "代价" in preview.plain


def test_hover_preview_neow_remove_offer_shows_cost() -> None:
    session = start_new_game_session(seed=5, preferred_character_id="ironclad")
    provider = StarterContentProvider(session.content_root)
    offer = opening_flow._build_offer("remove-offer", "tradeoff", "remove_card", provider, Random(0))
    session = replace(session, opening_state=replace(session.opening_state, neow_offers=[offer]))

    preview = _hover_preview_renderable(session, f"choose_neow_offer:{offer.offer_id}")

    assert preview is not None
    assert "移除" in preview.plain
    assert "代价" in preview.plain
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -k "neow and hover_preview" -v`

Expected: At least the updated `rare_card` test fails because current hover preview still uses `format_neow_offer_detail_lines(...)` and does not include `"效果"` for card/relic/potion offers.

- [ ] **Step 3: Commit the failing test changes**

```bash
git add tests/adapters/textual/test_slay_app.py
git commit -m "test: cover richer Neow hover previews"
```

---

### Task 2: Implement Neow-Specific Hover Preview Formatting

**Files:**
- Modify: `src/slay_the_spire/adapters/textual/slay_app.py:15-17`
- Modify: `src/slay_the_spire/adapters/textual/slay_app.py:330-355`
- Test: `tests/adapters/textual/test_slay_app.py`

- [ ] **Step 1: Add the minimal implementation helper**

In `src/slay_the_spire/adapters/textual/slay_app.py`, remove the unused `format_neow_offer_detail_lines` import and add a private helper before `_opening_hover_preview_renderable`:

```python
from slay_the_spire.adapters.presentation.opening_renderer import render_opening_summary_panel


def _format_neow_offer_hover_lines(offer, *, registry) -> list[Text | str]:
    reward_payload = offer.reward_payload
    if offer.reward_kind == "gold":
        return [f"获得 {reward_payload['amount']} 金币"]
    if offer.reward_kind == "relic":
        relic_id = str(reward_payload["relic_id"])
        return format_relic_detail_lines(relic_id, registry)
    if offer.reward_kind == "potion":
        potion_id = str(reward_payload["potion_id"])
        return format_potion_detail_lines(potion_id, registry)
    if offer.reward_kind in {"rare_card", "curse_card"}:
        card_id = str(reward_payload["card_id"])
        lines: list[Text | str] = format_card_detail_lines(f"{card_id}#neow", registry)
        if offer.cost_kind == "curse":
            cost_card_id = str(offer.cost_payload["card_id"])
            cost_name = registry.cards().get(cost_card_id).name
            return [*lines, f"代价：牌组中加入诅咒牌 {cost_name}"]
        return lines
    if offer.reward_kind == "upgrade_card":
        return [
            "升级牌组中任意一张可升级的牌",
            f"代价：失去 {offer.cost_payload['amount']} 点生命",
        ]
    if offer.reward_kind == "remove_card":
        return [
            "移除牌组中任意一张牌",
            f"代价：失去 {offer.cost_payload['amount']} 金币",
        ]
    return [offer.summary]
```

- [ ] **Step 2: Route Neow hover preview through the new helper**

Replace the current Neow hover branch in `_opening_hover_preview_renderable`:

```python
if session.menu_state.mode == "opening_neow_offer" and action_id.startswith("choose_neow_offer:"):
    offer_id = action_id.split(":", 1)[1]
    offer = next((item for item in opening_state.neow_offers if item.offer_id == offer_id), None)
    if offer is None:
        return None
    return _text_from_lines(_format_neow_offer_hover_lines(offer, registry=registry))
```

- [ ] **Step 3: Run the targeted tests to verify they pass**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -k "neow and hover_preview" -v`

Expected: PASS for the new/updated Neow hover-preview tests.

- [ ] **Step 4: Commit the implementation**

```bash
git add src/slay_the_spire/adapters/textual/slay_app.py tests/adapters/textual/test_slay_app.py
git commit -m "feat: enrich Neow hover previews"
```

---

### Task 3: Verify Broader Textual Behavior And Refresh Docs

**Files:**
- Modify: `README.md:7-19`
- Modify: `AGENTS.md:69-74`
- Test: `tests/adapters/textual/test_slay_app.py`

- [ ] **Step 1: Update README behavior summary**

Add one bullet under `## 当前实现` describing the new behavior:

```md
- 当前 opening 的 Neow 菜单支持悬浮预览完整奖励信息：卡牌、遗物、药水会显示与其他 hover preview 一致的详细效果说明
```

- [ ] **Step 2: Update AGENTS behavior facts**

Add one bullet in the opening-related facts section:

```md
- opening 的 `Neow` 选项悬浮预览会显示完整奖励说明；卡牌、遗物、药水复用与其他查看页一致的详细 hover preview 文案
```

- [ ] **Step 3: Run the focused Textual test slice**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -k "opening or hover_preview" -v`

Expected: PASS for the affected opening and hover-preview tests, with no regression in opening target-card preview behavior.

- [ ] **Step 4: Run the full Textual app test file**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -v`

Expected: PASS for the complete Textual adapter suite.

- [ ] **Step 5: Commit docs and verification-ready changes**

```bash
git add README.md AGENTS.md tests/adapters/textual/test_slay_app.py src/slay_the_spire/adapters/textual/slay_app.py
git commit -m "docs: describe detailed Neow hover previews"
```

---

## Self-Review

- Spec coverage: covered helper addition, hover routing change, reward-kind behavior, tests, and README/AGENTS sync.
- Placeholder scan: no TODO/TBD placeholders remain; every step has exact files and commands.
- Type consistency: plan uses existing `_hover_preview_renderable`, `format_card_detail_lines`, `format_relic_detail_lines`, and `format_potion_detail_lines` names consistently.
