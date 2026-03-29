# 设计规范：Neow 悬浮预览丰富化

**日期：** 2026-03-29  
**状态：** 已确认，待实现

---

## 背景

当前 Neow 阶段的悬浮预览（`#hover-preview`）已存在基础实现：
- 当玩家悬停在 `choose_neow_offer:*` 菜单项上时，调用 `format_neow_offer_detail_lines(offer, registry)` 展示选项内容。
- 该函数输出：summary 首行（与菜单标签重复）+ 简短的奖励行（仅名称）+ 代价行。

问题：对于 `rare_card`、`relic`、`potion` 类奖励，悬浮预览只显示名称，不显示效果描述，体验弱于商店/奖励页的悬浮预览（后者已使用 `format_card_detail_lines` 等完整 formatter）。

---

## 目标

让 Neow 菜单的每个选项在悬浮时，以与商店/奖励页一致的风格展示完整效果信息。

---

## 范围约束

- **仅修改** `src/slay_the_spire/adapters/textual/slay_app.py`
- **不修改** `opening_renderer.py`（游戏日志内联面板保持简洁格式不变）
- **不修改** session、use_case、content JSON、domain 逻辑
- 测试文件 `tests/adapters/textual/test_slay_app.py` 需同步更新

---

## 设计

### 新增私有函数

在 `slay_app.py` 中新增：

```python
def _format_neow_offer_hover_lines(offer: NeowOffer, *, registry) -> list[Text | str]:
    ...
```

此函数根据 `offer.reward_kind` 分支处理：

| `reward_kind` | 主体内容来源 | 代价行 |
|---|---|---|
| `gold` | `f"获得 {offer.reward_payload['amount']} 金币"` | 不追加 |
| `rare_card` | `format_card_detail_lines(f"{card_id}#neow", registry)` | 不追加 |
| `relic` | `format_relic_detail_lines(relic_id, registry)` | 不追加 |
| `potion` | `format_potion_detail_lines(potion_id, registry)` | 不追加 |
| `upgrade_card` | `"升级牌组中任意一张可升级的牌"` | `"代价：失去 {amount} 点生命"` |
| `remove_card` | `"移除牌组中任意一张牌"` | `f"代价：失去 {offer.cost_payload['amount']} 金币"` |
| `curse_card` | `format_card_detail_lines(f"{card_id}#neow", registry)` | `f"代价：牌组中加入诅咒牌 {registry.cards().get(cost_card_id).name}"` |

- 免费奖励（`gold`、`rare_card`、`relic`、`potion`）不追加代价行（无代价）。
- 有代价的奖励（`upgrade_card`、`remove_card`、`curse_card`）在主体内容末尾追加代价行。
- 不再以 `offer.summary` 作为首行（去除与菜单标签的重复）。

### 修改调用处

在 `_opening_hover_preview_renderable()` 中，将：

```python
return _text_from_lines(format_neow_offer_detail_lines(offer, registry=registry))
```

改为：

```python
return _text_from_lines(_format_neow_offer_hover_lines(offer, registry=registry))
```

---

## 数据流

```
OptionList.OptionHighlighted / MouseMove
  → _refresh_hover_preview(action_id)
    → _hover_preview_renderable(session, action_id)
      → run_phase == "opening"
        → _opening_hover_preview_renderable(session, action_id)
          → menu_mode == "opening_neow_offer" and action_id.startswith("choose_neow_offer:")
            → offer = neow_offers[offer_id]
            → _format_neow_offer_hover_lines(offer, registry=registry)  ← 新逻辑
              → format_card/relic/potion_detail_lines(...)              ← 复用现有 formatter
```

---

## 测试变更

文件：`tests/adapters/textual/test_slay_app.py`

### 修改现有测试

`test_hover_preview_shows_localized_neow_offer_details`（当前测试 `rare_card` offer）：
- 保留对本地化卡牌名的断言
- **新增**对 `"效果"` 字段的断言（因为 `format_card_detail_lines` 包含 `效果` 字段）

### 新增测试

1. **`test_hover_preview_neow_relic_offer_shows_relic_detail`**  
   构造 `relic` offer，断言预览包含遗物名和 `"效果"` 字段。

2. **`test_hover_preview_neow_potion_offer_shows_potion_detail`**  
   构造 `potion` offer，断言预览包含药水名和 `"效果"` 字段。

3. **`test_hover_preview_neow_gold_offer_shows_amount`**  
   构造 `gold` offer，断言预览包含 `"100"` 和 `"金币"`，不包含 `"代价"`。

4. **`test_hover_preview_neow_upgrade_card_offer_shows_cost`**  
   构造 `upgrade_card` offer，断言预览包含 `"升级"` 和 `"代价"`。

5. **`test_hover_preview_neow_remove_card_offer_shows_cost`**  
   构造 `remove_card` offer，断言预览包含 `"移除"` 和 `"代价"`。

---

## 不在范围内

- 修改游戏日志内联 Neow 面板格式（`_neow_offer_panel`）
- 修改 `format_neow_offer_detail_lines`（其他调用方不受影响）
- 删除无用的 `_supports_hover_preview` 函数（可单独清理，本次不纳入）
- 修改 `opening_neow_upgrade_card` / `opening_neow_remove_card` 模式下的悬浮预览（卡牌选择页已有 `format_card_detail_lines`，无需改动）
