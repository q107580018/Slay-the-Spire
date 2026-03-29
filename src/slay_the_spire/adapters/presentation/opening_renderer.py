from __future__ import annotations

from io import StringIO

from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.text import Text

from slay_the_spire.adapters.presentation.theme import PANEL_BOX, TERMINAL_THEME
from slay_the_spire.adapters.presentation.widgets import render_card_name, render_hp_bar, render_menu
from slay_the_spire.app.menu_definitions import MenuDefinition, format_menu_entries
from slay_the_spire.app.opening_state import OpeningState
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.ports.content_provider import ContentProviderPort
from slay_the_spire.use_cases.start_run import start_new_run


def _render_to_text(renderable: RenderableType) -> str:
    buffer = StringIO()
    console = Console(
        file=buffer,
        width=100,
        record=True,
        force_terminal=False,
        color_system=None,
        theme=TERMINAL_THEME,
    )
    console.print(renderable)
    return console.export_text(clear=False).rstrip()


def _selected_character_name(opening_state: OpeningState, registry: ContentProviderPort) -> str:
    character_id = opening_state.selected_character_id
    if character_id is None:
        return "未选择角色"
    return registry.characters().get(character_id).name


def _localized_card_name(card_id: str, registry: ContentProviderPort) -> str:
    resolved_card_id = card_id_from_instance_id(card_id) if "#" in card_id else card_id
    return render_card_name(registry.cards().get(resolved_card_id)).plain


def format_neow_offer_detail_lines(offer, *, registry: ContentProviderPort) -> list[str]:
    details = [offer.summary]
    reward_payload = offer.reward_payload
    if offer.reward_kind == "gold":
        details.append(f"获得 {reward_payload['amount']} 金币")
    elif offer.reward_kind == "relic":
        relic_id = str(reward_payload["relic_id"])
        details.append(f"获得遗物：{registry.relics().get(relic_id).name}")
    elif offer.reward_kind == "potion":
        potion_id = str(reward_payload["potion_id"])
        details.append(f"获得药水：{registry.potions().get(potion_id).name}")
    elif offer.reward_kind == "rare_card":
        details.append(f"获得稀有牌：{_localized_card_name(str(reward_payload['card_id']), registry)}")
    elif offer.reward_kind == "curse_card":
        details.append(f"获得诅咒牌：{_localized_card_name(str(reward_payload['card_id']), registry)}")
    if offer.cost_kind == "hp_loss":
        details.append(f"失去 {offer.cost_payload['amount']} 点生命")
    elif offer.cost_kind == "gold_loss":
        details.append(f"失去 {offer.cost_payload['amount']} 金币")
    elif offer.cost_kind == "curse":
        details.append(f"牌组中加入诅咒牌：{_localized_card_name(str(offer.cost_payload['card_id']), registry)}")
    return details


def _opening_summary_lines(opening_state: OpeningState, registry: ContentProviderPort) -> list[Text]:
    lines: list[Text] = [Text.assemble("角色：", _selected_character_name(opening_state, registry))]
    if opening_state.run_blueprint is None:
        lines.append(Text("状态：等待选择角色"))
        return lines

    run_state = opening_state.run_blueprint
    starting_relic = run_state.relics[0] if run_state.relics else "无"
    lines.extend(
        [
            Text.assemble("生命：", render_hp_bar(run_state.current_hp, run_state.max_hp)),
            Text(f"起始遗物：{registry.relics().get(starting_relic).name if starting_relic != '无' else starting_relic}"),
            Text(f"起始牌组：{len(run_state.deck)} 张"),
            Text(f"当前幕：{run_state.current_act_id or 'act1'}"),
        ]
    )
    if opening_state.pending_neow_offer_id is not None:
        lines.append(Text("状态：等待选择目标卡牌"))
    return lines


def render_opening_summary_panel(opening_state: OpeningState, *, registry: ContentProviderPort) -> Panel:
    return Panel(
        Group(*_opening_summary_lines(opening_state, registry)),
        title="开场摘要",
        box=PANEL_BOX,
        expand=False,
    )


def _character_select_panel(opening_state: OpeningState, registry: ContentProviderPort) -> Panel:
    body: list[Text] = [Text("请选择角色后进入 Neow。")]
    for character_id in opening_state.available_character_ids:
        character = registry.characters().get(character_id)
        preview_run = start_new_run(character_id, seed=opening_state.seed, registry=registry)
        relic_id = character.starter_relic_ids[0] if character.starter_relic_ids else None
        relic_name = registry.relics().get(relic_id).name if relic_id is not None else "无"
        body.extend(
            [
                Text.assemble("角色：", character.name),
                Text(f"生命：{preview_run.current_hp}/{preview_run.max_hp}"),
                Text(f"起始遗物：{relic_name}"),
                Text(f"起始套牌：{len(character.starter_deck)} 张"),
                Text(""),
            ]
        )
    if body and body[-1].plain == "":
        body.pop()
    return Panel(Group(*body), title="角色信息", box=PANEL_BOX, expand=False)


def _neow_offer_panel(opening_state: OpeningState, registry: ContentProviderPort) -> Panel:
    body: list[Text] = [
        Text.assemble("已选择角色：", _selected_character_name(opening_state, registry)),
        Text("Neow 提供以下开局选项："),
    ]
    for index, offer in enumerate(opening_state.neow_offers, start=1):
        body.append(Text(f"{index}. {offer.summary}"))
        for line in format_neow_offer_detail_lines(offer, registry=registry):
            body.append(Text(f"   - {line}"))
    return Panel(Group(*body), title="Neow 赐福", box=PANEL_BOX, expand=False)


def _target_card_panel(
    opening_state: OpeningState,
    *,
    registry: ContentProviderPort,
    title: str,
    target_kind: str,
) -> Panel:
    run_state = opening_state.run_blueprint
    body: list[RenderableType] = [Text("从右侧菜单确认目标卡牌，或选择返回上一步。")]
    if run_state is None:
        body.append(Text("当前没有可用牌组。"))
    else:
        for card_instance_id in run_state.deck:
            card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
            if target_kind == "upgrade_card" and card_def.upgrades_to is None:
                continue
            body.append(Text.assemble(render_card_name(card_def), f" ({card_instance_id})"))
    return Panel(Group(*body), title=title, box=PANEL_BOX, expand=False)


def render_opening_screen(
    *,
    opening_state: OpeningState,
    menu: MenuDefinition,
    menu_mode: str,
    registry: ContentProviderPort,
) -> RenderableType:
    summary = render_opening_summary_panel(opening_state, registry=registry)
    if menu_mode == "opening_character_select":
        body = _character_select_panel(opening_state, registry)
    elif menu_mode == "opening_neow_offer":
        body = _neow_offer_panel(opening_state, registry)
    elif menu_mode == "opening_neow_upgrade_card":
        body = _target_card_panel(opening_state, registry=registry, title="选择要升级的卡牌", target_kind="upgrade_card")
    elif menu_mode == "opening_neow_remove_card":
        body = _target_card_panel(opening_state, registry=registry, title="选择要移除的卡牌", target_kind="remove_card")
    else:
        body = Panel(Group(Text("当前 opening 页面不可用。")), title="开场", box=PANEL_BOX, expand=False)
    footer = render_menu(format_menu_entries(menu), title="可选操作")
    return Group(summary, body, footer)


def render_opening_text(
    *,
    opening_state: OpeningState,
    menu: MenuDefinition,
    menu_mode: str,
    registry: ContentProviderPort,
) -> str:
    return _render_to_text(
        render_opening_screen(
            opening_state=opening_state,
            menu=menu,
            menu_mode=menu_mode,
            registry=registry,
        )
    )
