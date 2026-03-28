from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable

from rich.console import RenderableType

from slay_the_spire.adapters.rich_ui.renderer import render_room, render_room_renderable
from slay_the_spire.adapters.persistence.save_files import JsonFileSaveRepository
from slay_the_spire.app.map_labels import format_next_room_labels
from slay_the_spire.app.menu_definitions import (
    build_boss_relic_menu,
    build_boss_reward_menu,
    build_card_detail_menu,
    build_enemy_detail_menu,
    build_event_choice_menu,
    build_event_remove_menu,
    build_event_upgrade_menu,
    build_inspect_root_menu,
    build_leaf_menu,
    build_next_room_menu,
    build_relic_detail_menu,
    build_reward_menu,
    build_rest_root_menu,
    build_rest_upgrade_menu,
    build_root_menu,
    build_select_card_menu,
    build_shop_remove_menu,
    build_shop_root_menu,
    build_target_menu,
    build_terminal_phase_menu,
    resolve_menu_action,
)
from slay_the_spire.app.inspect_registry import (
    COMBAT_INSPECT_CARD_LIST_MODES,
    COMBAT_INSPECT_ROOT_ACTIONS,
    SHARED_INSPECT_ROOT_ACTIONS,
    inspect_leaf_title,
)
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.map.map_generator import generate_act_state
from slay_the_spire.domain.hooks.runtime import build_runtime_hook_registrations
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.act_state import ActState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.domain.rewards.reward_generator import generate_boss_rewards, generate_combat_rewards
from slay_the_spire.ports.input_port import InputPort
from slay_the_spire.use_cases.load_game import load_game
from slay_the_spire.use_cases.apply_reward import apply_reward
from slay_the_spire.use_cases.event_action import event_action
from slay_the_spire.use_cases.resolve_event_choice import resolve_event_choice
from slay_the_spire.use_cases.end_turn import end_turn
from slay_the_spire.use_cases.enter_room import enter_room
from slay_the_spire.use_cases.play_card import play_card
from slay_the_spire.use_cases.rest_action import rest_action
from slay_the_spire.use_cases.save_game import save_game
from slay_the_spire.use_cases.shop_action import shop_action
from slay_the_spire.use_cases.start_run import start_new_run


def default_content_root() -> Path:
    packaged_content_root = Path(__file__).resolve().parents[1] / "data" / "content"
    if _is_content_root(packaged_content_root):
        return packaged_content_root
    for candidate in _candidate_content_roots():
        if _is_content_root(candidate):
            return candidate
    raise FileNotFoundError("could not locate content root; pass --content-root explicitly")


def _candidate_content_roots() -> tuple[Path, ...]:
    module_path = Path(__file__).resolve()
    candidates = [module_path.parents[i] / "content" for i in range(1, min(5, len(module_path.parents)))]
    candidates.append(Path.cwd() / "content")
    return tuple(dict.fromkeys(candidates))


def _is_content_root(path: Path) -> bool:
    return path.is_dir() and (path / "characters" / "ironclad.json").exists()


@dataclass(slots=True)
class MenuState:
    mode: str = "root"
    selected_card_instance_id: str | None = None
    inspect_item_id: str | None = None
    inspect_parent_mode: str | None = None


@dataclass(slots=True)
class SessionState:
    run_state: RunState
    act_state: ActState
    room_state: RoomState
    content_root: Path
    save_path: Path
    run_phase: str = "active"
    menu_state: MenuState = field(default_factory=MenuState)
    command_history: list[str] | None = None


@dataclass(slots=True)
class SessionRouteResult:
    running: bool
    session: SessionState
    render_message: str | None = None
    status_message: str | None = None

    @property
    def message(self) -> str:
        if self.status_message and self.render_message:
            return f"{self.status_message}\n\n{self.render_message}"
        if self.status_message is not None:
            return self.status_message
        return self.render_message or ""

    def __iter__(self):
        yield self.running
        yield self.session
        yield self.message


@dataclass(slots=True)
class SessionLoopResult:
    outputs: list[str]
    final_session: SessionState


_MENU_PROMPT = "请输入编号: "


def _with_command_history(session: SessionState, command: str) -> SessionState:
    history = list(session.command_history or [])
    history.append(command)
    return replace(session, command_history=history)


def _with_menu_choice_history(session: SessionState, choice: str) -> SessionState:
    history = list(session.command_history or [])
    history.append(choice)
    return replace(session, command_history=history)


def _preserve_menu_history(updated_session: SessionState, *, history_session: SessionState) -> SessionState:
    return replace(updated_session, command_history=list(history_session.command_history or []))


def _content_provider(session: SessionState) -> StarterContentProvider:
    return StarterContentProvider(session.content_root)


def default_save_path() -> Path:
    return Path.cwd() / "saves" / "latest.json"


def _combat_state_from_room(room_state: RoomState) -> CombatState | None:
    combat_state = room_state.payload.get("combat_state")
    if not isinstance(combat_state, dict):
        return None
    return CombatState.from_dict(combat_state)


def _derive_run_phase(
    run_state: RunState,
    act_state: ActState,
    room_state: RoomState,
    *,
    registry: StarterContentProvider,
) -> str:
    if run_state.current_hp <= 0:
        return "game_over"
    if room_state.stage == "defeated":
        return "game_over"
    if room_state.room_type == "boss" and _boss_rewards_complete(room_state):
        if registry.acts().get(act_state.act_id).next_act_id is None:
            return "victory"
    return "active"


def _menu_state_for_room(room_state: RoomState) -> MenuState:
    if room_state.room_type == "shop" and not room_state.is_resolved:
        if room_state.stage == "select_remove_card":
            return MenuState(mode="shop_remove_card")
        return MenuState(mode="shop_root")
    if room_state.room_type == "rest" and not room_state.is_resolved:
        if room_state.stage == "select_upgrade_card":
            return MenuState(mode="rest_upgrade_card")
        return MenuState(mode="rest_root")
    if room_state.room_type == "event" and not room_state.is_resolved:
        if room_state.stage == "select_event_upgrade_card":
            return MenuState(mode="event_upgrade_card")
        if room_state.stage == "select_event_remove_card":
            return MenuState(mode="event_remove_card")
    return MenuState()


def _room_with_rewards_claimed(room_state: RoomState, reward_id: str) -> RoomState:
    if reward_id not in room_state.rewards:
        raise ValueError("reward_id not found in room rewards")
    payload = dict(room_state.payload)
    claimed_reward_ids = list(payload.get("claimed_reward_ids", []))
    claimed_reward_ids.append(reward_id)
    payload["claimed_reward_ids"] = claimed_reward_ids
    if reward_id.startswith("card_offer:"):
        remaining_rewards = [reward for reward in room_state.rewards if not reward.startswith("card_offer:")]
    else:
        remaining_rewards = [reward for reward in room_state.rewards if reward != reward_id]
    return RoomState(
        schema_version=room_state.schema_version,
        room_id=room_state.room_id,
        room_type=room_state.room_type,
        stage=room_state.stage,
        payload=payload,
        is_resolved=room_state.is_resolved,
        rewards=remaining_rewards,
    )


def _room_with_all_rewards_claimed(room_state: RoomState) -> RoomState:
    claimed_room = room_state
    for reward_id in list(room_state.rewards):
        claimed_room = _room_with_rewards_claimed(claimed_room, reward_id)
    return claimed_room


def _boss_rewards(room_state: RoomState) -> dict[str, object] | None:
    boss_rewards = room_state.payload.get("boss_rewards")
    if not isinstance(boss_rewards, dict):
        return None
    return boss_rewards


def _boss_rewards_complete(room_state: RoomState) -> bool:
    boss_rewards = _boss_rewards(room_state)
    if boss_rewards is None:
        return False
    claimed_relic_id = boss_rewards.get("claimed_relic_id")
    return boss_rewards.get("claimed_gold") is True and isinstance(claimed_relic_id, str) and bool(claimed_relic_id)


def _has_pending_boss_rewards(room_state: RoomState) -> bool:
    return room_state.room_type == "boss" and room_state.is_resolved and _boss_rewards(room_state) is not None and not _boss_rewards_complete(room_state)


def _claim_session_reward(session: SessionState, reward_id: str) -> SessionState:
    provider = _content_provider(session)
    updated_run_state = apply_reward(
        run_state=session.run_state,
        reward_id=reward_id,
        registry=provider,
    )
    updated_room_state = _room_with_rewards_claimed(session.room_state, reward_id)
    next_menu_state = MenuState(mode="select_reward") if updated_room_state.rewards else MenuState()
    return replace(
        session,
        run_state=updated_run_state,
        room_state=updated_room_state,
        run_phase=_derive_run_phase(updated_run_state, session.act_state, updated_room_state, registry=provider),
        menu_state=next_menu_state,
    )


def _claim_all_session_rewards(session: SessionState) -> SessionState:
    updated_session = session
    for reward_id in [reward for reward in session.room_state.rewards if not reward.startswith("card_offer:")]:
        updated_session = _claim_session_reward(updated_session, reward_id)
    return updated_session


def _skip_card_offer_rewards(session: SessionState) -> SessionState:
    remaining_rewards = [reward for reward in session.room_state.rewards if not reward.startswith("card_offer:")]
    updated_room_state = replace(session.room_state, rewards=remaining_rewards)
    next_menu_state = MenuState(mode="select_reward") if updated_room_state.rewards else MenuState()
    return replace(session, room_state=updated_room_state, menu_state=next_menu_state)


def _open_treasure(session: SessionState) -> SessionState:
    if session.room_state.is_resolved:
        return session
    claimed_relic_id = session.room_state.payload.get("claimed_treasure_relic_id")
    if isinstance(claimed_relic_id, str) and claimed_relic_id:
        updated_room_state = replace(
            session.room_state,
            stage="completed",
            is_resolved=True,
        )
        return replace(
            session,
            room_state=updated_room_state,
            run_phase=_derive_run_phase(session.run_state, session.act_state, updated_room_state, registry=_content_provider(session)),
            menu_state=MenuState(),
        )
    relic_id = session.room_state.payload.get("treasure_relic_id")
    if not isinstance(relic_id, str) or not relic_id:
        return session
    provider = _content_provider(session)
    updated_run_state = apply_reward(
        run_state=session.run_state,
        reward_id=f"relic:{relic_id}",
        registry=provider,
    )
    updated_room_state = replace(
        session.room_state,
        stage="completed",
        is_resolved=True,
        payload={**session.room_state.payload, "claimed_treasure_relic_id": relic_id},
    )
    return replace(
        session,
        run_state=updated_run_state,
        room_state=updated_room_state,
        run_phase=_derive_run_phase(updated_run_state, session.act_state, updated_room_state, registry=provider),
        menu_state=MenuState(),
    )


def _claim_boss_gold(session: SessionState) -> SessionState:
    boss_rewards = _boss_rewards(session.room_state)
    if boss_rewards is None:
        return replace(session, menu_state=MenuState(mode="select_boss_reward"))
    if boss_rewards.get("claimed_gold") is True:
        return replace(session, menu_state=MenuState(mode="select_boss_reward"))
    gold_reward = boss_rewards.get("gold_reward")
    if not isinstance(gold_reward, int) or isinstance(gold_reward, bool):
        return replace(session, menu_state=MenuState(mode="select_boss_reward"))
    provider = _content_provider(session)
    updated_run_state = apply_reward(
        run_state=session.run_state,
        reward_id=f"gold:{gold_reward}",
        registry=provider,
    )
    updated_boss_rewards = dict(boss_rewards)
    updated_boss_rewards["claimed_gold"] = True
    updated_room_state = replace(
        session.room_state,
        payload={**session.room_state.payload, "boss_rewards": updated_boss_rewards},
    )
    updated_session = replace(
        session,
        run_state=updated_run_state,
        room_state=updated_room_state,
        run_phase=_derive_run_phase(updated_run_state, session.act_state, updated_room_state, registry=provider),
        menu_state=MenuState(mode="select_boss_reward"),
    )
    return _resolve_boss_reward_completion(updated_session, registry=provider)


def _claim_boss_relic(session: SessionState, relic_id: str) -> SessionState:
    boss_rewards = _boss_rewards(session.room_state)
    if boss_rewards is None:
        return replace(session, menu_state=MenuState(mode="select_boss_reward"))
    offers = boss_rewards.get("boss_relic_offers")
    if not isinstance(offers, list) or relic_id not in offers:
        return session
    claimed_relic_id = boss_rewards.get("claimed_relic_id")
    if isinstance(claimed_relic_id, str) and claimed_relic_id:
        return replace(session, menu_state=MenuState(mode="select_boss_reward"))
    provider = _content_provider(session)
    updated_run_state = apply_reward(
        run_state=session.run_state,
        reward_id=f"relic:{relic_id}",
        registry=provider,
    )
    updated_boss_rewards = dict(boss_rewards)
    updated_boss_rewards["claimed_relic_id"] = relic_id
    updated_room_state = replace(
        session.room_state,
        payload={**session.room_state.payload, "boss_rewards": updated_boss_rewards},
    )
    updated_session = replace(
        session,
        run_state=updated_run_state,
        room_state=updated_room_state,
        run_phase=_derive_run_phase(updated_run_state, session.act_state, updated_room_state, registry=provider),
        menu_state=MenuState(mode="select_boss_reward"),
    )
    return _resolve_boss_reward_completion(updated_session, registry=provider)


def _resolve_boss_reward_completion(
    session: SessionState,
    *,
    registry: StarterContentProvider,
) -> SessionState:
    if session.room_state.room_type == "boss_chest":
        return replace(session, run_phase="active", menu_state=_menu_state_for_room(session.room_state))
    if not _boss_rewards_complete(session.room_state):
        return session
    current_act = registry.acts().get(session.act_state.act_id)
    boss_chest_payload = {
        "act_id": session.act_state.act_id,
        "node_id": "boss_chest",
        "next_node_ids": [],
    }
    boss_rewards = _boss_rewards(session.room_state)
    if boss_rewards is not None:
        boss_chest_payload["boss_rewards"] = boss_rewards
    if current_act.next_act_id is not None:
        boss_chest_payload["next_act_id"] = current_act.next_act_id
    next_room_state = RoomState(
        room_id=f"{session.act_state.act_id}:boss_chest",
        room_type="boss_chest",
        stage="completed",
        payload=boss_chest_payload,
        is_resolved=True,
        rewards=[],
    )
    return replace(
        session,
        room_state=next_room_state,
        run_phase="active",
        menu_state=_menu_state_for_room(next_room_state),
    )


def _advance_boss_chest(session: SessionState) -> SessionState:
    provider = _content_provider(session)
    next_act_id = session.room_state.payload.get("next_act_id")
    if not isinstance(next_act_id, str) or not next_act_id:
        return replace(session, run_phase="victory", menu_state=MenuState())
    updated_run_state = replace(session.run_state, current_act_id=next_act_id)
    next_act_state = generate_act_state(next_act_id, seed=updated_run_state.seed, registry=provider)
    next_room_state = enter_room(
        updated_run_state,
        next_act_state,
        node_id=next_act_state.current_node_id,
        registry=provider,
    )
    return replace(
        session,
        run_state=updated_run_state,
        act_state=next_act_state,
        room_state=next_room_state,
        run_phase="active",
        menu_state=_menu_state_for_room(next_room_state),
    )


def _combat_target_ids(combat_state: CombatState) -> list[str]:
    return [enemy.instance_id for enemy in combat_state.enemies if enemy.hp > 0]


def _combat_is_won(combat_state: CombatState) -> bool:
    return bool(combat_state.enemies) and all(enemy.hp == 0 for enemy in combat_state.enemies)


def _combat_hook_registrations(session: SessionState):
    return build_runtime_hook_registrations(session.run_state, _content_provider(session))


def _room_with_combat_state(
    room_state: RoomState,
    combat_state: CombatState,
    *,
    stage: str,
    is_resolved: bool,
    rewards: list[str] | None = None,
) -> RoomState:
    payload = dict(room_state.payload)
    payload["combat_state"] = combat_state.to_dict()
    return RoomState(
        schema_version=room_state.schema_version,
        room_id=room_state.room_id,
        room_type=room_state.room_type,
        stage=stage,
        payload=payload,
        is_resolved=is_resolved,
        rewards=list(room_state.rewards if rewards is None else rewards),
    )


def _session_with_combat_state(session: SessionState, combat_state: CombatState) -> SessionState:
    updated_run_state = replace(
        session.run_state,
        current_hp=combat_state.player.hp,
        max_hp=combat_state.player.max_hp,
    )
    if combat_state.player.hp <= 0:
        room_state = _room_with_combat_state(
            session.room_state,
            combat_state,
            stage="defeated",
            is_resolved=False,
        )
        return replace(session, run_state=updated_run_state, room_state=room_state, run_phase="game_over")
    if _combat_is_won(combat_state):
        reward_run_state = updated_run_state
        room_rewards: list[str] = []
        if session.room_state.room_type != "boss":
            room_rewards, next_rare_offset = generate_combat_rewards(
                room_id=session.room_state.room_id,
                run_state=updated_run_state,
                registry=_content_provider(session),
            )
            reward_run_state = replace(updated_run_state, rare_card_reward_offset=next_rare_offset)
        room_state = _room_with_combat_state(
            session.room_state,
            combat_state,
            stage="completed",
            is_resolved=True,
            rewards=room_rewards,
        )
        if session.room_state.room_type == "boss":
            room_state = replace(
                room_state,
                payload={
                    **room_state.payload,
                    "boss_rewards": generate_boss_rewards(
                        room_id=session.room_state.room_id,
                        seed=session.run_state.seed,
                        run_state=reward_run_state,
                        registry=_content_provider(session),
                    ),
                },
            )
        return replace(
            session,
            run_state=reward_run_state,
            room_state=room_state,
            run_phase=_derive_run_phase(reward_run_state, session.act_state, room_state, registry=_content_provider(session)),
        )
    room_state = _room_with_combat_state(
        session.room_state,
        combat_state,
        stage="waiting_input",
        is_resolved=False,
    )
    return replace(session, run_state=updated_run_state, room_state=room_state)


def _resolve_hand_card(combat_state: CombatState, hand_index: str) -> str:
    try:
        index = int(hand_index)
    except ValueError as exc:
        raise ValueError("hand index must be an integer") from exc
    if index <= 0 or index > len(combat_state.hand):
        raise ValueError("hand index is out of range")
    return combat_state.hand[index - 1]


def _resolve_target_id(combat_state: CombatState, target_index: str | None) -> str | None:
    living_targets = _combat_target_ids(combat_state)
    if target_index is None:
        if len(living_targets) == 1:
            return living_targets[0]
        return None
    if target_index.startswith("enemy:"):
        target_index = target_index.split(":", 1)[1]
    try:
        index = int(target_index)
    except ValueError as exc:
        raise ValueError("target index must be an integer") from exc
    if index <= 0 or index > len(living_targets):
        raise ValueError("target index is out of range")
    return living_targets[index - 1]


def _resolve_hand_target_id(combat_state: CombatState, selected_card_instance_id: str, target_index: str) -> str:
    if target_index.startswith("hand:"):
        target_index = target_index.split(":", 1)[1]
    try:
        index = int(target_index)
    except ValueError as exc:
        raise ValueError("target index must be an integer") from exc
    selectable_hand_cards = [card for card in combat_state.hand if card != selected_card_instance_id]
    if index <= 0 or index > len(selectable_hand_cards):
        raise ValueError("target index is out of range")
    return selectable_hand_cards[index - 1]


def _card_requires_target(card_instance_id: str, session: SessionState) -> bool:
    card_def = _content_provider(session).cards().get(card_id_from_instance_id(card_instance_id))
    return any(effect.get("type") in {"damage", "vulnerable", "exhaust_target_card", "upgrade_target_card"} for effect in card_def.effects)


def _card_requires_hand_target(card_instance_id: str, session: SessionState) -> bool:
    card_def = _content_provider(session).cards().get(card_id_from_instance_id(card_instance_id))
    return any(effect.get("type") in {"exhaust_target_card", "upgrade_target_card"} for effect in card_def.effects)


def _card_requires_enemy_target(card_instance_id: str, session: SessionState) -> bool:
    card_def = _content_provider(session).cards().get(card_id_from_instance_id(card_instance_id))
    return any(effect.get("type") in {"damage", "vulnerable"} for effect in card_def.effects)


def _hand_index_for_card(combat_state: CombatState, card_instance_id: str) -> int:
    for index, current in enumerate(combat_state.hand, start=1):
        if current == card_instance_id:
            return index
    raise ValueError("selected card is no longer in hand")


def _advance_to_next_room(session: SessionState) -> SessionState:
    if session.room_state.room_type == "boss_chest":
        return _advance_boss_chest(session)
    return _advance_to_node(session, None)


def _advance_to_node(session: SessionState, node_id: str | None) -> SessionState:
    next_node_ids = session.room_state.payload.get("next_node_ids", [])
    if not isinstance(next_node_ids, list) or not next_node_ids:
        return session
    next_node_id = next_node_ids[0] if node_id is None else node_id
    if not isinstance(next_node_id, str):
        return session
    provider = StarterContentProvider(session.content_root)
    room_state = enter_room(session.run_state, session.act_state, node_id=next_node_id, registry=provider)
    return replace(session, room_state=room_state, menu_state=_menu_state_for_room(room_state))


def start_session(
    *,
    seed: int,
    character_id: str = "ironclad",
    content_root: str | Path | None = None,
    save_path: str | Path | None = None,
) -> SessionState:
    resolved_content_root = default_content_root() if content_root is None else Path(content_root)
    resolved_save_path = default_save_path() if save_path is None else Path(save_path)
    provider = StarterContentProvider(resolved_content_root)
    run_state = start_new_run(character_id, seed=seed, registry=provider)
    act_state = generate_act_state(run_state.current_act_id or "act1", seed=seed, registry=provider)
    room_state = enter_room(run_state, act_state, node_id=act_state.current_node_id, registry=provider)
    return SessionState(
        run_state=run_state,
        act_state=act_state,
        room_state=room_state,
        content_root=resolved_content_root,
        save_path=resolved_save_path,
        run_phase="active",
        menu_state=_menu_state_for_room(room_state),
    )


def load_session(
    *,
    save_path: str | Path | None = None,
    content_root: str | Path | None = None,
) -> SessionState:
    resolved_content_root = default_content_root() if content_root is None else Path(content_root)
    resolved_save_path = default_save_path() if save_path is None else Path(save_path)
    repository = JsonFileSaveRepository(resolved_save_path)
    loaded = load_game(repository=repository)
    if loaded["run_state"] is None or loaded["act_state"] is None or loaded["room_state"] is None:
        raise FileNotFoundError(f"save file is empty or incomplete: {resolved_save_path}")
    session = SessionState(
        run_state=loaded["run_state"],
        act_state=loaded["act_state"],
        room_state=loaded["room_state"],
        content_root=resolved_content_root,
        save_path=resolved_save_path,
        run_phase=_derive_run_phase(
            loaded["run_state"],
            loaded["act_state"],
            loaded["room_state"],
            registry=StarterContentProvider(resolved_content_root),
        ),
        menu_state=_menu_state_for_room(loaded["room_state"]),
    )
    return _resolve_boss_reward_completion(session, registry=StarterContentProvider(resolved_content_root))


def render_session(session: SessionState) -> str:
    return render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_content_provider(session),
        menu_state=session.menu_state,
        run_phase=session.run_phase,
    )


def render_session_renderable(session: SessionState) -> RenderableType:
    return render_room_renderable(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_content_provider(session),
        menu_state=session.menu_state,
        run_phase=session.run_phase,
    )


def _coerce_route_result(result: SessionRouteResult | tuple[bool, SessionState, str]) -> SessionRouteResult:
    if isinstance(result, SessionRouteResult):
        return result
    running, session, message = result
    rendered = render_session(session)
    if message == rendered:
        return SessionRouteResult(running=running, session=session, render_message=rendered)
    render_suffix = f"\n\n{rendered}"
    if rendered and message.endswith(render_suffix):
        return SessionRouteResult(
            running=running,
            session=session,
            status_message=message[: -len(render_suffix)],
            render_message=rendered,
        )
    return SessionRouteResult(running=running, session=session, status_message=message)


def _route_command_legacy(command: str, *, session: SessionState) -> tuple[bool, SessionState, str]:
    raw_command = command.strip()
    normalized = raw_command.lower()
    next_session = _with_command_history(session, normalized or "look")
    if normalized in {"", "look"}:
        return True, next_session, render_session(next_session)
    if next_session.run_phase != "active":
        if normalized in {"help", "?"}:
            return True, next_session, "Commands: look, help, quit"
        if normalized in {"quit", "exit"}:
            return False, next_session, "Goodbye."
        return True, next_session, "本局已结束，无法继续操作。"
    if normalized == "hand":
        return True, next_session, render_session(next_session)
    if normalized.startswith("play"):
        if next_session.room_state.room_type not in {"combat", "elite", "boss"}:
            return True, next_session, "Play is only available in combat rooms."
        if next_session.room_state.is_resolved:
            return True, next_session, "Combat is already resolved."
        combat_state = _combat_state_from_room(next_session.room_state)
        if combat_state is None:
            return True, next_session, "Combat state is unavailable."
        parts = normalized.split()
        if len(parts) not in {2, 3}:
            return True, next_session, "Usage: play <hand-index> [target-index]"
        try:
            card_instance_id = _resolve_hand_card(combat_state, parts[1])
            card_def = _content_provider(next_session).cards().get(card_id_from_instance_id(card_instance_id))
            target_token = parts[2] if len(parts) == 3 else None
            if _card_requires_hand_target(card_instance_id, next_session):
                target_id = _resolve_hand_target_id(combat_state, card_instance_id, target_token) if target_token is not None else None
            else:
                target_id = _resolve_target_id(combat_state, target_token)
            if _card_requires_target(card_instance_id, next_session) and target_id is None:
                return True, next_session, "Target is required."
            result = play_card(
                combat_state,
                card_instance_id,
                target_id,
                _content_provider(next_session),
                hook_registrations=_combat_hook_registrations(next_session),
            )
        except (KeyError, TypeError, ValueError) as exc:
            return True, next_session, str(exc)
        resolved_session = _session_with_combat_state(next_session, result.combat_state)
        return True, resolved_session, render_session(resolved_session)
    if normalized == "end":
        if next_session.room_state.room_type not in {"combat", "elite", "boss"}:
            return True, next_session, "End is only available in combat rooms."
        if next_session.room_state.is_resolved:
            return True, next_session, "Combat is already resolved."
        combat_state = _combat_state_from_room(next_session.room_state)
        if combat_state is None:
            return True, next_session, "Combat state is unavailable."
        try:
            result = end_turn(
                combat_state,
                _content_provider(next_session),
                hook_registrations=_combat_hook_registrations(next_session),
            )
        except (KeyError, TypeError, ValueError) as exc:
            return True, next_session, str(exc)
        resolved_session = _session_with_combat_state(next_session, result.combat_state)
        return True, resolved_session, render_session(resolved_session)
    if normalized in {"next", "advance"}:
        if not next_session.room_state.is_resolved:
            return True, next_session, "Room is not resolved."
        advanced_session = _advance_to_next_room(next_session)
        return True, advanced_session, render_session(advanced_session)
    if normalized in {"help", "?"}:
        return (
            True,
            next_session,
            "Commands: look, hand, play <hand-index> [target-index], end, next, help, quit",
        )
    if normalized in {"quit", "exit"}:
        return False, next_session, "Goodbye."
    return True, next_session, f"Unknown command: {raw_command or '<empty>'}"


def route_command(command: str, *, session: SessionState) -> SessionRouteResult:
    return _coerce_route_result(_route_command_legacy(command, session=session))


def _invalid_menu_choice(session: SessionState) -> tuple[bool, SessionState, str]:
    return True, session, "无效选项，请输入菜单编号。"


def _menu_view_message(session: SessionState, title: str) -> str:
    return f"{title}\n\n{render_session(session)}"


def _inspect_transition_message(session: SessionState, title: str) -> str:
    return _menu_view_message(session, title)


def _message_with_render(session: SessionState, message: str | None) -> str:
    rendered = render_session(session)
    if not message:
        return rendered
    return f"{message}\n\n{rendered}"


def _retarget_route_result(result: SessionRouteResult, session: SessionState) -> tuple[bool, SessionState, str]:
    if result.render_message is None:
        return result.running, session, result.status_message or ""
    if result.status_message is None:
        return result.running, session, render_session(session)
    return result.running, session, _message_with_render(session, result.status_message)


def _save_current_session(session: SessionState) -> tuple[bool, SessionState, str]:
    repository = JsonFileSaveRepository(session.save_path)
    combat_state = _combat_state_from_room(session.room_state)
    save_game(
        repository=repository,
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        combat_state=combat_state,
    )
    return True, replace(session, menu_state=MenuState()), f"已保存到 {session.save_path}"


def _load_current_session(session: SessionState) -> tuple[bool, SessionState, str]:
    restored = load_session(save_path=session.save_path, content_root=session.content_root)
    restored = replace(restored, command_history=list(session.command_history or []))
    return True, restored, f"已从存档恢复。当前存档: {session.save_path}"


def _route_terminal_phase_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    action_id = resolve_menu_action(choice, build_terminal_phase_menu(run_phase=session.run_phase))
    if action_id == "view_terminal":
        return True, replace(session, menu_state=MenuState()), render_session(replace(session, menu_state=MenuState()))
    if action_id == "save":
        return _save_current_session(session)
    if action_id == "load":
        return _load_current_session(session)
    if action_id == "quit":
        return False, replace(session, menu_state=MenuState()), "已退出游戏。"
    return _invalid_menu_choice(session)


def _enter_inspect_root(session: SessionState, *, parent_mode: str | None = None) -> SessionState:
    resolved_parent_mode = parent_mode
    if resolved_parent_mode is None:
        resolved_parent_mode = session.menu_state.inspect_parent_mode or "root"
    return replace(
        session,
        menu_state=MenuState(
            mode="inspect_root",
            inspect_parent_mode=resolved_parent_mode,
            inspect_item_id=None,
        ),
    )


def _return_from_inspect(session: SessionState) -> SessionState:
    parent_mode = session.menu_state.inspect_parent_mode or "root"
    return replace(
        session,
        menu_state=MenuState(
            mode=parent_mode,
            inspect_parent_mode=None,
            inspect_item_id=None,
        ),
    )


def _root_view_title(session: SessionState) -> str:
    if session.room_state.is_resolved and (session.room_state.rewards or _has_pending_boss_rewards(session.room_state)):
        return "领取奖励"
    if session.room_state.room_type == "boss_chest":
        return "Boss宝箱"
    if session.room_state.room_type in {"combat", "elite", "boss"}:
        return "战斗"
    if session.room_state.room_type == "event":
        return "事件操作"
    if session.menu_state.mode == "shop_root" or session.room_state.room_type == "shop":
        return "商店操作"
    if session.menu_state.mode == "rest_root" or session.room_state.room_type == "rest":
        return "休息点操作"
    return "查看当前状态"


def _normalize_legacy_reward_inspect_mode(session: SessionState) -> SessionState:
    if session.menu_state.mode not in {"inspect_reward_root", "inspect_reward_list", "inspect_reward_detail"}:
        return session
    return replace(session, menu_state=MenuState())


def _route_inspect_root_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    parent_mode = session.menu_state.inspect_parent_mode or "root"
    action_id = resolve_menu_action(choice, build_inspect_root_menu(room_state=session.room_state))
    if action_id is None:
        return _invalid_menu_choice(session)
    shared_target = SHARED_INSPECT_ROOT_ACTIONS.get(action_id)
    if shared_target is not None:
        mode, item_id, title = shared_target
        next_session = replace(
            session,
            menu_state=MenuState(
                mode=mode,
                inspect_parent_mode=parent_mode,
                inspect_item_id=item_id,
            ),
        )
        return True, next_session, _inspect_transition_message(next_session, title)
    combat_target = COMBAT_INSPECT_ROOT_ACTIONS.get(action_id)
    if combat_target is not None:
        mode, item_id, title = combat_target
        next_session = replace(
            session,
            menu_state=MenuState(
                mode=mode,
                inspect_parent_mode="inspect_root",
                inspect_item_id=item_id,
            ),
        )
        return True, next_session, _inspect_transition_message(next_session, title)
    if action_id == "back":
        next_session = _return_from_inspect(session)
        return True, next_session, _inspect_transition_message(next_session, _root_view_title(next_session))
    return _invalid_menu_choice(session)


def _route_inspect_deck_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    deck = session.run_state.deck
    back_choice = str(len(session.run_state.deck) + 1)
    if choice == back_choice:
        next_session = _enter_inspect_root(session, parent_mode=session.menu_state.inspect_parent_mode or "root")
        return True, next_session, _inspect_transition_message(next_session, "资料总览")
    try:
        index = int(choice)
    except ValueError:
        return _invalid_menu_choice(session)
    if index <= 0 or index > len(deck):
        return _invalid_menu_choice(session)
    next_session = replace(
        session,
        menu_state=MenuState(
            mode="inspect_card_detail",
            inspect_parent_mode="inspect_deck",
            inspect_item_id=deck[index - 1],
        ),
    )
    return True, next_session, _inspect_transition_message(next_session, "卡牌详情")


def _route_inspect_relics_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    relics = session.run_state.relics
    back_choice = str(len(relics) + 1)
    if choice == back_choice:
        next_session = _enter_inspect_root(session, parent_mode=session.menu_state.inspect_parent_mode or "root")
        return True, next_session, _inspect_transition_message(next_session, "资料总览")
    try:
        index = int(choice)
    except ValueError:
        return _invalid_menu_choice(session)
    if index <= 0 or index > len(relics):
        return _invalid_menu_choice(session)
    next_session = replace(
        session,
        menu_state=MenuState(
            mode="inspect_relic_detail",
            inspect_parent_mode="inspect_relics",
            inspect_item_id=relics[index - 1],
        ),
    )
    return True, next_session, _inspect_transition_message(next_session, "遗物详情")


def _inspect_root_parent_mode_for_room(session: SessionState) -> str:
    return _menu_state_for_room(session.room_state).mode or "root"


def _route_inspect_leaf_menu(choice: str, session: SessionState, title: str) -> tuple[bool, SessionState, str]:
    action_id = resolve_menu_action(choice, build_leaf_menu(title=title))
    if action_id == "back":
        next_session = _enter_inspect_root(session, parent_mode=session.menu_state.inspect_parent_mode or "root")
        return True, next_session, _inspect_transition_message(next_session, "资料总览")
    return _invalid_menu_choice(session)


def _inspect_card_items(session: SessionState, mode: str) -> list[str]:
    combat_state = _combat_state_from_room(session.room_state)
    if combat_state is None:
        return []
    if mode == "inspect_hand":
        return combat_state.hand
    if mode == "inspect_draw_pile":
        return combat_state.draw_pile
    if mode == "inspect_discard_pile":
        return combat_state.discard_pile
    if mode == "inspect_exhaust_pile":
        return combat_state.exhaust_pile
    return []


def _route_combat_inspect_card_list_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    card_instance_ids = _inspect_card_items(session, session.menu_state.mode)
    back_choice = str(len(card_instance_ids) + 1)
    if choice == back_choice:
        next_session = _enter_inspect_root(session, parent_mode="root")
        return True, next_session, _inspect_transition_message(next_session, "资料总览")
    try:
        index = int(choice)
    except ValueError:
        return _invalid_menu_choice(session)
    if index <= 0 or index > len(card_instance_ids):
        return _invalid_menu_choice(session)
    next_session = replace(
        session,
        menu_state=MenuState(
            mode="inspect_card_detail",
            inspect_parent_mode=session.menu_state.mode,
            inspect_item_id=card_instance_ids[index - 1],
        ),
    )
    return True, next_session, _inspect_transition_message(next_session, "卡牌详情")


def _route_combat_inspect_enemy_list_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    combat_state = _combat_state_from_room(session.room_state)
    if combat_state is None:
        return True, replace(session, menu_state=MenuState()), "战斗状态不可用。"
    back_choice = str(len(combat_state.enemies) + 1)
    if choice == back_choice:
        next_session = _enter_inspect_root(session, parent_mode="root")
        return True, next_session, _inspect_transition_message(next_session, "资料总览")
    try:
        index = int(choice)
    except ValueError:
        return _invalid_menu_choice(session)
    if index <= 0 or index > len(combat_state.enemies):
        return _invalid_menu_choice(session)
    next_session = replace(
        session,
        menu_state=MenuState(
            mode="inspect_enemy_detail",
            inspect_parent_mode="inspect_enemy_list",
            inspect_item_id=combat_state.enemies[index - 1].instance_id,
        ),
    )
    return True, next_session, _inspect_transition_message(next_session, "敌人详情")


def _route_combat_inspect_card_detail_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    parent_mode = session.menu_state.inspect_parent_mode or "inspect_hand"
    action_id = resolve_menu_action(choice, build_card_detail_menu())
    if action_id == "back_to_list":
        if parent_mode == "inspect_deck":
            next_session = replace(
                session,
                menu_state=MenuState(
                    mode="inspect_deck",
                    inspect_parent_mode=_inspect_root_parent_mode_for_room(session),
                    inspect_item_id="deck",
                ),
            )
            return True, next_session, _inspect_transition_message(next_session, "牌组列表")
        next_session = replace(
            session,
            menu_state=MenuState(
                mode=parent_mode,
                inspect_parent_mode="inspect_root",
                inspect_item_id=None,
            ),
        )
        return True, next_session, _inspect_transition_message(next_session, "卡牌列表")
    if action_id == "back_to_root":
        next_session = _enter_inspect_root(
            session,
            parent_mode="root" if parent_mode != "inspect_deck" else _inspect_root_parent_mode_for_room(session),
        )
        return True, next_session, _inspect_transition_message(next_session, "资料总览")
    return _invalid_menu_choice(session)


def _route_inspect_relic_detail_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    action_id = resolve_menu_action(choice, build_relic_detail_menu())
    parent_mode = _inspect_root_parent_mode_for_room(session)
    if action_id == "back_to_list":
        next_session = replace(
            session,
            menu_state=MenuState(
                mode="inspect_relics",
                inspect_parent_mode=parent_mode,
                inspect_item_id="relics",
            ),
        )
        return True, next_session, _inspect_transition_message(next_session, "遗物列表")
    if action_id == "back_to_root":
        next_session = _enter_inspect_root(session, parent_mode=parent_mode)
        return True, next_session, _inspect_transition_message(next_session, "资料总览")
    return _invalid_menu_choice(session)


def _route_combat_inspect_enemy_detail_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    action_id = resolve_menu_action(choice, build_enemy_detail_menu())
    if action_id == "back_to_list":
        next_session = replace(
            session,
            menu_state=MenuState(
                mode="inspect_enemy_list",
                inspect_parent_mode="inspect_root",
                inspect_item_id="enemies",
            ),
        )
        return True, next_session, _inspect_transition_message(next_session, "敌人列表")
    if action_id == "back_to_root":
        next_session = _enter_inspect_root(session, parent_mode="root")
        return True, next_session, _inspect_transition_message(next_session, "资料总览")
    return _invalid_menu_choice(session)


def _route_root_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    if session.run_phase in {"victory", "game_over"}:
        return _route_terminal_phase_menu(choice, session)
    action_id = resolve_menu_action(choice, build_root_menu(room_state=session.room_state))
    if action_id is None:
        return _invalid_menu_choice(session)
    if action_id == "view_current":
        next_session = replace(session, menu_state=MenuState())
        return True, next_session, render_session(next_session)
    if action_id == "claim_rewards":
        if _has_pending_boss_rewards(session.room_state):
            next_session = replace(session, menu_state=MenuState(mode="select_boss_reward"))
            return True, next_session, render_session(next_session)
        if not session.room_state.rewards:
            return True, replace(session, menu_state=MenuState()), "当前没有可领取的奖励。"
        next_session = replace(session, menu_state=MenuState(mode="select_reward"))
        return True, next_session, render_session(next_session)
    if action_id == "next_room":
        next_node_ids = session.room_state.payload.get("next_node_ids", [])
        if isinstance(next_node_ids, list) and len(next_node_ids) > 1:
            next_session = replace(session, menu_state=MenuState(mode="select_next_room"))
            return True, next_session, render_session(next_session)
        result = route_command("next", session=replace(session, menu_state=MenuState()))
        next_session = _preserve_menu_history(result.session, history_session=session)
        adjusted_session = replace(next_session, menu_state=_menu_state_for_room(next_session.room_state))
        return _retarget_route_result(result, adjusted_session)
    if action_id == "advance_boss_chest":
        next_session = _advance_boss_chest(replace(session, menu_state=MenuState()))
        return True, next_session, render_session(next_session)
    if action_id == "inspect":
        next_session = _enter_inspect_root(session, parent_mode="root")
        return True, next_session, _menu_view_message(next_session, "资料总览")
    if action_id == "save":
        return _save_current_session(session)
    if action_id == "load":
        return _load_current_session(session)
    if action_id == "quit":
        return False, replace(session, menu_state=MenuState()), "已退出游戏。"
    if action_id == "play_card":
        combat_state = _combat_state_from_room(session.room_state)
        if combat_state is None or not combat_state.hand:
            return True, replace(session, menu_state=MenuState()), "当前没有可打出的手牌。"
        next_session = replace(session, menu_state=MenuState(mode="select_card"))
        return True, next_session, render_session(next_session)
    if action_id == "end_turn":
        result = route_command("end", session=replace(session, menu_state=MenuState()))
        next_session = _preserve_menu_history(result.session, history_session=session)
        adjusted_session = replace(next_session, menu_state=MenuState())
        return _retarget_route_result(result, adjusted_session)
    if action_id == "event_choice":
        next_session = replace(session, menu_state=MenuState(mode="select_event_choice"))
        return True, next_session, render_session(next_session)
    if action_id == "open_treasure":
        next_session = _open_treasure(session)
        return True, next_session, render_session(next_session)
    return _invalid_menu_choice(session)


def _menu_state_for_post_play_session(session: SessionState) -> MenuState:
    default_menu_state = _menu_state_for_room(session.room_state)
    if session.run_phase != "active":
        return default_menu_state
    if session.room_state.room_type not in {"combat", "elite", "boss"} or session.room_state.is_resolved:
        return default_menu_state
    combat_state = _combat_state_from_room(session.room_state)
    if combat_state is None or not combat_state.hand:
        return default_menu_state
    return MenuState(mode="select_card")


def _route_card_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    combat_state = _combat_state_from_room(session.room_state)
    if combat_state is None:
        return True, replace(session, menu_state=MenuState()), "战斗状态不可用。"
    action_id = resolve_menu_action(choice, build_select_card_menu(combat_state=combat_state, registry=_content_provider(session)))
    if action_id == "back":
        next_session = replace(session, menu_state=MenuState())
        return True, next_session, render_session(next_session)
    if action_id == "end_turn":
        result = route_command("end", session=replace(session, menu_state=MenuState()))
        next_session = _preserve_menu_history(result.session, history_session=session)
        adjusted_session = replace(next_session, menu_state=_menu_state_for_post_play_session(next_session))
        return _retarget_route_result(result, adjusted_session)
    if action_id is None or not action_id.startswith("play_card:"):
        return _invalid_menu_choice(session)
    choice_index = action_id.split(":", 1)[1]
    try:
        card_instance_id = _resolve_hand_card(combat_state, choice_index)
    except ValueError:
        return _invalid_menu_choice(session)
    requires_hand_target = _card_requires_hand_target(card_instance_id, session)
    requires_enemy_target = _card_requires_enemy_target(card_instance_id, session)
    should_select_target = requires_hand_target or (requires_enemy_target and len(_combat_target_ids(combat_state)) > 1)
    if should_select_target:
        next_session = replace(
            session,
            menu_state=MenuState(mode="select_target", selected_card_instance_id=card_instance_id),
        )
        return True, next_session, render_session(next_session)
    result = route_command(
        f"play {choice_index}",
        session=replace(session, menu_state=MenuState()),
    )
    next_session = _preserve_menu_history(result.session, history_session=session)
    adjusted_session = replace(next_session, menu_state=_menu_state_for_post_play_session(next_session))
    return _retarget_route_result(result, adjusted_session)


def _route_target_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    combat_state = _combat_state_from_room(session.room_state)
    if combat_state is None:
        return True, replace(session, menu_state=MenuState()), "战斗状态不可用。"
    selected_card_instance_id = session.menu_state.selected_card_instance_id
    if selected_card_instance_id is None:
        next_session = replace(session, menu_state=MenuState(mode="select_card"))
        return True, next_session, render_session(next_session)
    enemy_targets = _combat_target_ids(combat_state) if _card_requires_enemy_target(selected_card_instance_id, session) else []
    hand_targets = [card for card in combat_state.hand if card != selected_card_instance_id] if _card_requires_hand_target(selected_card_instance_id, session) else []
    target_options = [
        *( (f"target_enemy:{index}", target_id) for index, target_id in enumerate(enemy_targets, start=1) ),
        *( (f"target_hand:{index}", card_id) for index, card_id in enumerate(hand_targets, start=1) ),
    ]
    action_id = resolve_menu_action(
        choice,
        build_target_menu(
            target_options=target_options,
            current_card_name=None,
        ),
    )
    if action_id == "back":
        next_session = replace(session, menu_state=MenuState(mode="select_card"))
        return True, next_session, render_session(next_session)
    if action_id is None:
        return _invalid_menu_choice(session)
    try:
        hand_index = _hand_index_for_card(combat_state, selected_card_instance_id)
    except ValueError:
        next_session = replace(session, menu_state=MenuState())
        return True, next_session, "所选手牌已发生变化，请重新选择。"
    if action_id.startswith("target_enemy:"):
        target_token = f"enemy:{action_id.split(':', 1)[1]}"
    elif action_id.startswith("target_hand:"):
        target_token = f"hand:{action_id.split(':', 1)[1]}"
    else:
        return _invalid_menu_choice(session)
    result = route_command(
        f"play {hand_index} {target_token}",
        session=replace(session, menu_state=MenuState()),
    )
    next_session = _preserve_menu_history(result.session, history_session=session)
    adjusted_session = replace(next_session, menu_state=_menu_state_for_post_play_session(next_session))
    return _retarget_route_result(result, adjusted_session)


def _route_next_room_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    next_node_ids = session.room_state.payload.get("next_node_ids", [])
    if not isinstance(next_node_ids, list):
        return _invalid_menu_choice(session)
    labels = format_next_room_labels(session.act_state, next_node_ids)
    action_id = resolve_menu_action(
        choice,
        build_next_room_menu(
            options=[(f"next_node:{node_id}", label) for node_id, label in zip(next_node_ids, labels, strict=False)]
        ),
    )
    if action_id == "back":
        next_session = replace(session, menu_state=MenuState())
        return True, next_session, render_session(next_session)
    if action_id is None or not action_id.startswith("next_node:"):
        return _invalid_menu_choice(session)
    next_node_id = action_id.split(":", 1)[1]
    if not isinstance(next_node_id, str):
        return _invalid_menu_choice(session)
    next_session = _advance_to_node(replace(session, menu_state=MenuState()), next_node_id)
    return True, _preserve_menu_history(next_session, history_session=session), render_session(next_session)


def _route_event_choice_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    event_id = session.room_state.payload.get("event_id")
    if not isinstance(event_id, str):
        return True, replace(session, menu_state=MenuState()), "当前事件不可用。"
    event_def = _content_provider(session).events().get(event_id)
    action_id = resolve_menu_action(
        choice,
        build_event_choice_menu(
            options=[(f"choice:{choice_def.get('id')}", str(choice_def.get("label"))) for choice_def in event_def.choices]
        ),
    )
    if action_id == "back":
        next_session = replace(session, menu_state=MenuState())
        return True, next_session, render_session(next_session)
    if action_id is None or not action_id.startswith("choice:"):
        return _invalid_menu_choice(session)
    choice_id = action_id.split(":", 1)[1]
    if not isinstance(choice_id, str):
        return True, replace(session, menu_state=MenuState()), "事件选项无效。"
    result = event_action(
        run_state=session.run_state,
        room_state=session.room_state,
        action_id=f"choice:{choice_id}",
        registry=_content_provider(session),
    )
    next_session = replace(
        session,
        run_state=result.run_state,
        room_state=result.room_state,
        run_phase=_derive_run_phase(result.run_state, session.act_state, result.room_state, registry=_content_provider(session)),
        menu_state=_menu_state_for_room(result.room_state),
    )
    return True, next_session, _message_with_render(next_session, result.message)


def _route_event_upgrade_card_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    options = session.room_state.payload.get("upgrade_options", [])
    if not isinstance(options, list):
        return _invalid_menu_choice(session)
    action_id = resolve_menu_action(
        choice,
        build_event_upgrade_menu(options=[(f"upgrade_card:{card_instance_id}", str(card_instance_id)) for card_instance_id in options]),
    )
    if action_id == "cancel":
        result = event_action(
            run_state=session.run_state,
            room_state=session.room_state,
            action_id="cancel",
            registry=_content_provider(session),
        )
    else:
        if action_id is None or not action_id.startswith("upgrade_card:"):
            return _invalid_menu_choice(session)
        result = event_action(
            run_state=session.run_state,
            room_state=session.room_state,
            action_id=action_id,
            registry=_content_provider(session),
        )
    next_session = replace(
        session,
        run_state=result.run_state,
        room_state=result.room_state,
        run_phase=_derive_run_phase(result.run_state, session.act_state, result.room_state, registry=_content_provider(session)),
        menu_state=_menu_state_for_room(result.room_state),
    )
    return True, next_session, _message_with_render(next_session, result.message)


def _route_event_remove_card_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    candidates = session.room_state.payload.get("remove_candidates", [])
    if not isinstance(candidates, list):
        return _invalid_menu_choice(session)
    action_id = resolve_menu_action(
        choice,
        build_event_remove_menu(options=[(f"remove_card:{card_instance_id}", str(card_instance_id)) for card_instance_id in candidates]),
    )
    if action_id == "cancel":
        result = event_action(
            run_state=session.run_state,
            room_state=session.room_state,
            action_id="cancel",
            registry=_content_provider(session),
        )
    else:
        if action_id is None or not action_id.startswith("remove_card:"):
            return _invalid_menu_choice(session)
        result = event_action(
            run_state=session.run_state,
            room_state=session.room_state,
            action_id=action_id,
            registry=_content_provider(session),
        )
    next_session = replace(
        session,
        run_state=result.run_state,
        room_state=result.room_state,
        run_phase=_derive_run_phase(result.run_state, session.act_state, result.room_state, registry=_content_provider(session)),
        menu_state=_menu_state_for_room(result.room_state),
    )
    return True, next_session, _message_with_render(next_session, result.message)


def _route_reward_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    action_id = resolve_menu_action(choice, build_reward_menu(room_state=session.room_state, registry=_content_provider(session)))
    if action_id is None:
        return _invalid_menu_choice(session)
    if action_id == "back":
        next_session = replace(session, menu_state=MenuState())
        return True, next_session, render_session(next_session)
    if action_id == "claim_all":
        next_session = _claim_all_session_rewards(session)
        return True, next_session, render_session(next_session)
    if action_id == "skip_card_rewards":
        next_session = _skip_card_offer_rewards(session)
        return True, next_session, render_session(next_session)
    if action_id.startswith("claim_reward:"):
        next_session = _claim_session_reward(session, action_id.split(":", 1)[1])
        return True, next_session, render_session(next_session)
    return _invalid_menu_choice(session)


def _route_boss_reward_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    boss_rewards = _boss_rewards(session.room_state)
    if boss_rewards is None:
        return _invalid_menu_choice(session)
    action_id = resolve_menu_action(choice, build_boss_reward_menu(boss_rewards))
    if action_id is None:
        return _invalid_menu_choice(session)
    if action_id == "back":
        next_session = replace(session, menu_state=MenuState())
        return True, next_session, render_session(next_session)
    if action_id == "claimed_boss_gold":
        return True, session, _message_with_render(session, "Boss金币已领取。")
    if action_id == "claimed_boss_relic":
        return True, session, _message_with_render(session, "Boss遗物已选择。")
    if action_id == "choose_boss_relic":
        next_session = replace(session, menu_state=MenuState(mode="select_boss_relic"))
        return True, next_session, render_session(next_session)
    next_session = _claim_boss_gold(session)
    return True, next_session, render_session(next_session)


def _route_boss_relic_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    boss_rewards = _boss_rewards(session.room_state)
    if boss_rewards is None:
        next_session = replace(session, menu_state=MenuState())
        return True, next_session, render_session(next_session)
    offers = boss_rewards.get("boss_relic_offers")
    if not isinstance(offers, list):
        return _invalid_menu_choice(session)
    action_id = resolve_menu_action(choice, build_boss_relic_menu(offers, registry=_content_provider(session)))
    if action_id is None:
        return _invalid_menu_choice(session)
    if action_id == "back":
        next_session = replace(session, menu_state=MenuState(mode="select_boss_reward"))
        return True, next_session, render_session(next_session)
    if not action_id.startswith("claim_boss_relic:"):
        return _invalid_menu_choice(session)
    relic_id = action_id.split(":", 1)[1]
    next_session = _claim_boss_relic(session, relic_id)
    return True, next_session, render_session(next_session)


def _route_shop_root_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    action_id = resolve_menu_action(
        choice,
        build_shop_root_menu(run_state=session.run_state, room_state=session.room_state, registry=_content_provider(session)),
    )
    if action_id is None:
        return _invalid_menu_choice(session)
    if action_id == "inspect":
        next_session = _enter_inspect_root(session, parent_mode="shop_root")
        return True, next_session, _menu_view_message(next_session, "资料总览")
    if action_id == "save":
        return _save_current_session(session)
    if action_id == "load":
        return _load_current_session(session)
    if action_id == "quit":
        return False, replace(session, menu_state=MenuState()), "已退出游戏。"
    result = shop_action(run_state=session.run_state, room_state=session.room_state, action_id=action_id)
    next_session = replace(
        session,
        run_state=result.run_state,
        room_state=result.room_state,
        menu_state=_menu_state_for_room(result.room_state),
    )
    return True, next_session, _message_with_render(next_session, result.message)


def _route_shop_remove_card_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    action_id = resolve_menu_action(
        choice,
        build_shop_remove_menu(room_state=session.room_state, registry=_content_provider(session)),
    )
    if action_id is None:
        return _invalid_menu_choice(session)
    if action_id == "save":
        return _save_current_session(session)
    if action_id == "load":
        return _load_current_session(session)
    if action_id == "quit":
        return False, replace(session, menu_state=MenuState()), "已退出游戏。"
    result = shop_action(run_state=session.run_state, room_state=session.room_state, action_id=action_id)
    next_session = replace(
        session,
        run_state=result.run_state,
        room_state=result.room_state,
        menu_state=_menu_state_for_room(result.room_state),
    )
    return True, next_session, _message_with_render(next_session, result.message)


def _route_rest_root_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    action_id = resolve_menu_action(
        choice,
        build_rest_root_menu(room_state=session.room_state, run_state=session.run_state),
    )
    if action_id is None:
        return _invalid_menu_choice(session)
    if action_id == "inspect":
        next_session = _enter_inspect_root(session, parent_mode="rest_root")
        return True, next_session, _menu_view_message(next_session, "资料总览")
    if action_id == "save":
        return _save_current_session(session)
    if action_id == "load":
        return _load_current_session(session)
    if action_id == "quit":
        return False, replace(session, menu_state=MenuState()), "已退出游戏。"
    result = rest_action(
        run_state=session.run_state,
        room_state=session.room_state,
        action_id=action_id,
        registry=_content_provider(session),
    )
    next_session = replace(
        session,
        run_state=result.run_state,
        room_state=result.room_state,
        menu_state=_menu_state_for_room(result.room_state),
    )
    return True, next_session, _message_with_render(next_session, result.message)


def _route_rest_upgrade_card_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    action_id = resolve_menu_action(
        choice,
        build_rest_upgrade_menu(room_state=session.room_state, registry=_content_provider(session)),
    )
    if action_id is None:
        return _invalid_menu_choice(session)
    if action_id == "save":
        return _save_current_session(session)
    if action_id == "load":
        return _load_current_session(session)
    if action_id == "quit":
        return False, replace(session, menu_state=MenuState()), "已退出游戏。"
    result = rest_action(
        run_state=session.run_state,
        room_state=session.room_state,
        action_id=action_id,
        registry=_content_provider(session),
    )
    next_session = replace(
        session,
        run_state=result.run_state,
        room_state=result.room_state,
        menu_state=_menu_state_for_room(result.room_state),
    )
    return True, next_session, _message_with_render(next_session, result.message)


def _route_menu_choice_legacy(choice: str, *, session: SessionState) -> tuple[bool, SessionState, str]:
    next_session = _normalize_legacy_reward_inspect_mode(_with_menu_choice_history(session, choice.strip()))
    if next_session.menu_state.mode == "root":
        return _route_root_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "select_card":
        return _route_card_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "select_target":
        return _route_target_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "select_next_room":
        return _route_next_room_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "select_event_choice":
        return _route_event_choice_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "event_upgrade_card":
        return _route_event_upgrade_card_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "event_remove_card":
        return _route_event_remove_card_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "select_reward":
        return _route_reward_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "select_boss_reward":
        return _route_boss_reward_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "select_boss_relic":
        return _route_boss_relic_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "shop_root":
        return _route_shop_root_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "shop_remove_card":
        return _route_shop_remove_card_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "rest_root":
        return _route_rest_root_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "rest_upgrade_card":
        return _route_rest_upgrade_card_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "inspect_root":
        return _route_inspect_root_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "inspect_deck":
        return _route_inspect_deck_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "inspect_relics":
        return _route_inspect_relics_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "inspect_relic_detail":
        return _route_inspect_relic_detail_menu(choice.strip(), next_session)
    leaf_title = inspect_leaf_title(next_session.menu_state.mode)
    if leaf_title is not None:
        return _route_inspect_leaf_menu(choice.strip(), next_session, leaf_title)
    if next_session.menu_state.mode in COMBAT_INSPECT_CARD_LIST_MODES:
        return _route_combat_inspect_card_list_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "inspect_card_detail":
        return _route_combat_inspect_card_detail_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "inspect_enemy_list":
        return _route_combat_inspect_enemy_list_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "inspect_enemy_detail":
        return _route_combat_inspect_enemy_detail_menu(choice.strip(), next_session)
    return _invalid_menu_choice(replace(next_session, menu_state=MenuState()))


def route_menu_choice(choice: str, *, session: SessionState) -> SessionRouteResult:
    return _coerce_route_result(_route_menu_choice_legacy(choice, session=session))


def interactive_loop(
    *,
    session: SessionState,
    input_port: InputPort,
    output_writer: Callable[[str], None] | None = None,
) -> SessionLoopResult:
    initial_output = render_session(session)
    outputs = [initial_output]
    if output_writer is not None:
        output_writer(initial_output)
    running = True
    while running:
        command = input_port.read(_MENU_PROMPT)
        result = route_menu_choice(command, session=session)
        running = result.running
        session = result.session
        outputs.append(result.message)
        if output_writer is not None:
            output_writer(result.message)
    return SessionLoopResult(outputs=outputs, final_session=session)
