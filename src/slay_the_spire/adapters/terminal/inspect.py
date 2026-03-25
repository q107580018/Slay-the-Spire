from __future__ import annotations

from rich.text import Text

from slay_the_spire.adapters.terminal.widgets import (
    format_card_cost,
    summarize_card_effects,
    summarize_relic_effects,
    summarize_trigger_hooks,
)
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.ports.content_provider import ContentProviderPort


def format_card_detail_lines(card_instance_id: str, registry: ContentProviderPort) -> list[Text]:
    card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
    lines = [
        Text.assemble(("名称 ", "summary.label"), card_def.name),
        Text.assemble(("实例 ", "summary.label"), card_instance_id),
        Text.assemble(("费用 ", "summary.label"), format_card_cost(card_def.cost)),
        Text.assemble(("效果 ", "summary.label"), summarize_card_effects(card_def.effects)),
    ]
    if card_def.upgrades_to is not None:
        upgraded = registry.cards().get(card_def.upgrades_to)
        lines.append(Text.assemble(("升级为 ", "summary.label"), upgraded.name))
    return lines


def format_relic_detail_lines(relic_id: str, registry: ContentProviderPort) -> list[Text]:
    relic_def = registry.relics().get(relic_id)
    lines = [
        Text.assemble(("名称 ", "summary.label"), relic_def.name),
        Text.assemble(("遗物 ", "summary.label"), relic_id),
        Text.assemble(("效果 ", "summary.label"), summarize_relic_effects(relic_def.passive_effects)),
    ]
    if relic_def.trigger_hooks:
        lines.append(Text.assemble(("触发 ", "summary.label"), summarize_trigger_hooks(relic_def.trigger_hooks)))
    return lines
