from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable

from rich.console import RenderableType

from slay_the_spire.adapters.terminal.prompts import prompt_for_session
from slay_the_spire.adapters.terminal.renderer import render_room, render_room_renderable
from slay_the_spire.adapters.persistence.save_files import JsonFileSaveRepository
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.map.map_generator import generate_act_state
from slay_the_spire.domain.hooks.runtime import build_runtime_hook_registrations
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.act_state import ActState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.domain.rewards.reward_generator import generate_combat_rewards
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
class SessionLoopResult:
    outputs: list[str]
    final_session: SessionState


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


def _derive_run_phase(run_state: RunState, room_state: RoomState) -> str:
    if run_state.current_hp <= 0:
        return "game_over"
    if room_state.stage == "defeated":
        return "game_over"
    if room_state.room_type == "boss" and room_state.is_resolved and not room_state.rewards:
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


def _claim_session_reward(session: SessionState, reward_id: str) -> SessionState:
    updated_run_state = apply_reward(
        run_state=session.run_state,
        reward_id=reward_id,
        registry=_content_provider(session),
    )
    updated_room_state = _room_with_rewards_claimed(session.room_state, reward_id)
    run_phase = session.run_phase
    if session.room_state.room_type == "boss" and not updated_room_state.rewards:
        run_phase = "victory"
    return replace(
        session,
        run_state=updated_run_state,
        room_state=updated_room_state,
        run_phase=run_phase,
        menu_state=MenuState(),
    )


def _claim_all_session_rewards(session: SessionState) -> SessionState:
    updated_session = session
    for reward_id in list(session.room_state.rewards):
        updated_session = _claim_session_reward(updated_session, reward_id)
    return updated_session


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
        room_state = _room_with_combat_state(
            session.room_state,
            combat_state,
            stage="completed",
            is_resolved=True,
            rewards=generate_combat_rewards(room_id=session.room_state.room_id, seed=session.run_state.seed),
        )
        return replace(session, run_state=updated_run_state, room_state=room_state)
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
    try:
        index = int(target_index)
    except ValueError as exc:
        raise ValueError("target index must be an integer") from exc
    if index <= 0 or index > len(living_targets):
        raise ValueError("target index is out of range")
    return living_targets[index - 1]


def _card_requires_target(card_instance_id: str, session: SessionState) -> bool:
    card_def = _content_provider(session).cards().get(card_id_from_instance_id(card_instance_id))
    return any(effect.get("type") in {"damage", "vulnerable"} for effect in card_def.effects)


def _hand_index_for_card(combat_state: CombatState, card_instance_id: str) -> int:
    for index, current in enumerate(combat_state.hand, start=1):
        if current == card_instance_id:
            return index
    raise ValueError("selected card is no longer in hand")


def _advance_to_next_room(session: SessionState) -> SessionState:
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
    return SessionState(
        run_state=loaded["run_state"],
        act_state=loaded["act_state"],
        room_state=loaded["room_state"],
        content_root=resolved_content_root,
        save_path=resolved_save_path,
        run_phase=_derive_run_phase(loaded["run_state"], loaded["room_state"]),
        menu_state=_menu_state_for_room(loaded["room_state"]),
    )


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


def route_command(command: str, *, session: SessionState) -> tuple[bool, SessionState, str]:
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
            target_id = _resolve_target_id(combat_state, parts[2] if len(parts) == 3 else None)
            if any(effect.get("type") in {"damage", "vulnerable"} for effect in card_def.effects) and target_id is None:
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
    if choice == "1":
        return True, replace(session, menu_state=MenuState()), render_session(replace(session, menu_state=MenuState()))
    if choice == "2":
        return _save_current_session(session)
    if choice == "3":
        return _load_current_session(session)
    if choice == "4":
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
    if session.room_state.is_resolved and session.room_state.rewards:
        return "查看奖励"
    if session.room_state.room_type in {"combat", "elite", "boss"}:
        return "战斗"
    if session.room_state.room_type == "event":
        return "查看事件"
    if session.menu_state.mode == "shop_root" or session.room_state.room_type == "shop":
        return "商店操作"
    if session.menu_state.mode == "rest_root" or session.room_state.room_type == "rest":
        return "休息点操作"
    return "查看当前状态"


def _route_inspect_root_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    parent_mode = session.menu_state.inspect_parent_mode or "root"
    reward_room_inspect = session.room_state.is_resolved and bool(session.room_state.rewards)
    combat_inspect_enabled = session.room_state.room_type in {"combat", "elite", "boss"} and not reward_room_inspect
    if combat_inspect_enabled:
        if choice == "1":
            next_session = replace(
                session,
                menu_state=MenuState(
                    mode="inspect_stats",
                    inspect_parent_mode=parent_mode,
                    inspect_item_id="stats",
                ),
            )
            return True, next_session, _inspect_transition_message(next_session, "角色状态")
        if choice == "2":
            next_session = replace(
                session,
                menu_state=MenuState(
                    mode="inspect_deck",
                    inspect_parent_mode=parent_mode,
                    inspect_item_id="deck",
                ),
            )
            return True, next_session, _inspect_transition_message(next_session, "牌组列表")
        if choice == "3":
            next_session = replace(
                session,
                menu_state=MenuState(
                    mode="inspect_relics",
                    inspect_parent_mode=parent_mode,
                    inspect_item_id="relics",
                ),
            )
            return True, next_session, _inspect_transition_message(next_session, "遗物列表")
        if choice == "4":
            next_session = replace(
                session,
                menu_state=MenuState(
                    mode="inspect_potions",
                    inspect_parent_mode=parent_mode,
                    inspect_item_id="potions",
                ),
            )
            return True, next_session, _inspect_transition_message(next_session, "药水列表")
        combat_inspect_modes = {
            "5": ("inspect_hand", "hand", "手牌列表"),
            "6": ("inspect_draw_pile", "draw_pile", "抽牌堆列表"),
            "7": ("inspect_discard_pile", "discard_pile", "弃牌堆列表"),
            "8": ("inspect_exhaust_pile", "exhaust_pile", "消耗堆列表"),
            "9": ("inspect_enemy_list", "enemies", "敌人列表"),
        }
        if choice in combat_inspect_modes:
            mode, item_id, title = combat_inspect_modes[choice]
            next_session = replace(
                session,
                menu_state=MenuState(
                    mode=mode,
                    inspect_parent_mode="inspect_root",
                    inspect_item_id=item_id,
                ),
            )
            return True, next_session, _inspect_transition_message(next_session, title)
        if choice == "10":
            next_session = _return_from_inspect(session)
            return True, next_session, _inspect_transition_message(next_session, _root_view_title(next_session))
        return _invalid_menu_choice(session)
    if choice == "1":
        next_session = replace(
            session,
            menu_state=MenuState(
                mode="inspect_stats",
                inspect_parent_mode=parent_mode,
                inspect_item_id="stats",
            ),
        )
        return True, next_session, _inspect_transition_message(next_session, "角色状态")
    if choice == "2":
        next_session = replace(
            session,
            menu_state=MenuState(
                mode="inspect_deck",
                inspect_parent_mode=parent_mode,
                inspect_item_id="deck",
            ),
        )
        return True, next_session, _inspect_transition_message(next_session, "牌组列表")
    if choice == "3":
        next_session = replace(
            session,
            menu_state=MenuState(
                mode="inspect_relics",
                inspect_parent_mode=parent_mode,
                inspect_item_id="relics",
            ),
        )
        return True, next_session, _inspect_transition_message(next_session, "遗物列表")
    if choice == "4":
        if session.room_state.room_type in {"combat", "elite", "boss"} and not reward_room_inspect:
            next_session = _return_from_inspect(session)
            return True, next_session, _inspect_transition_message(next_session, "战斗")
        next_session = replace(
            session,
            menu_state=MenuState(
                mode="inspect_potions",
                inspect_parent_mode=parent_mode,
                inspect_item_id="potions",
            ),
        )
        return True, next_session, _inspect_transition_message(next_session, "药水列表")
    if choice == "5":
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
 
 
def _inspect_root_parent_mode_for_room(session: SessionState) -> str:
    return _menu_state_for_room(session.room_state).mode or "root"


def _route_inspect_leaf_menu(choice: str, session: SessionState, title: str) -> tuple[bool, SessionState, str]:
    if choice == "1":
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
    if choice == "1":
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
    if choice == "2":
        next_session = _enter_inspect_root(
            session,
            parent_mode="root" if parent_mode != "inspect_deck" else _inspect_root_parent_mode_for_room(session),
        )
        return True, next_session, _inspect_transition_message(next_session, "资料总览")
    return _invalid_menu_choice(session)


def _route_combat_inspect_enemy_detail_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    if choice == "1":
        next_session = replace(
            session,
            menu_state=MenuState(
                mode="inspect_enemy_list",
                inspect_parent_mode="inspect_root",
                inspect_item_id="enemies",
            ),
        )
        return True, next_session, _inspect_transition_message(next_session, "敌人列表")
    if choice == "2":
        next_session = _enter_inspect_root(session, parent_mode="root")
        return True, next_session, _inspect_transition_message(next_session, "资料总览")
    return _invalid_menu_choice(session)


def _route_root_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    if session.run_phase in {"victory", "game_over"}:
        return _route_terminal_phase_menu(choice, session)

    if session.room_state.is_resolved:
        if session.room_state.rewards:
            if choice == "1":
                return True, replace(session, menu_state=MenuState()), render_session(replace(session, menu_state=MenuState()))
            if choice == "2":
                if not session.room_state.rewards:
                    return True, replace(session, menu_state=MenuState()), "当前没有可领取的奖励。"
                next_session = replace(session, menu_state=MenuState(mode="select_reward"))
                return True, next_session, render_session(next_session)
            if choice == "3":
                next_node_ids = session.room_state.payload.get("next_node_ids", [])
                if isinstance(next_node_ids, list) and len(next_node_ids) > 1:
                    next_session = replace(session, menu_state=MenuState(mode="select_next_room"))
                    return True, next_session, render_session(next_session)
                running, next_session, message = route_command("next", session=replace(session, menu_state=MenuState()))
                next_session = _preserve_menu_history(next_session, history_session=session)
                return running, replace(next_session, menu_state=_menu_state_for_room(next_session.room_state)), message
            if choice == "4":
                next_session = _enter_inspect_root(session, parent_mode="root")
                return True, next_session, _menu_view_message(next_session, "资料总览")
            if choice == "5":
                return _save_current_session(session)
            if choice == "6":
                return _load_current_session(session)
            if choice == "7":
                return False, replace(session, menu_state=MenuState()), "已退出游戏。"
            return _invalid_menu_choice(session)
        if choice == "1":
            next_node_ids = session.room_state.payload.get("next_node_ids", [])
            if isinstance(next_node_ids, list) and len(next_node_ids) > 1:
                next_session = replace(session, menu_state=MenuState(mode="select_next_room"))
                return True, next_session, render_session(next_session)
            running, next_session, message = route_command("next", session=replace(session, menu_state=MenuState()))
            next_session = _preserve_menu_history(next_session, history_session=session)
            return running, replace(next_session, menu_state=_menu_state_for_room(next_session.room_state)), message
        if choice == "2":
            next_session = _enter_inspect_root(session, parent_mode="root")
            return True, next_session, _menu_view_message(next_session, "资料总览")
        if choice == "3":
            return _save_current_session(session)
        if choice == "4":
            return _load_current_session(session)
        if choice == "5":
            return False, replace(session, menu_state=MenuState()), "已退出游戏。"
        return _invalid_menu_choice(session)

    if session.room_state.room_type in {"combat", "elite", "boss"}:
        if choice == "1":
            return True, replace(session, menu_state=MenuState()), render_session(replace(session, menu_state=MenuState()))
        if choice == "2":
            combat_state = _combat_state_from_room(session.room_state)
            if combat_state is None or not combat_state.hand:
                return True, replace(session, menu_state=MenuState()), "当前没有可打出的手牌。"
            next_session = replace(session, menu_state=MenuState(mode="select_card"))
            return True, next_session, render_session(next_session)
        if choice == "3":
            running, next_session, message = route_command("end", session=replace(session, menu_state=MenuState()))
            next_session = _preserve_menu_history(next_session, history_session=session)
            return running, replace(next_session, menu_state=MenuState()), message
        if choice == "4":
            next_session = _enter_inspect_root(session, parent_mode="root")
            return True, next_session, _menu_view_message(next_session, "资料总览")
        if choice == "5":
            return _save_current_session(session)
        if choice == "6":
            return _load_current_session(session)
        if choice == "7":
            return False, replace(session, menu_state=MenuState()), "已退出游戏。"
        return _invalid_menu_choice(session)

    if session.room_state.room_type == "event":
        if choice == "1":
            return True, replace(session, menu_state=MenuState()), render_session(replace(session, menu_state=MenuState()))
        if choice == "2":
            next_session = replace(session, menu_state=MenuState(mode="select_event_choice"))
            return True, next_session, render_session(next_session)
        if choice == "3":
            next_session = _enter_inspect_root(session, parent_mode="root")
            return True, next_session, _menu_view_message(next_session, "资料总览")
        if choice == "4":
            return _save_current_session(session)
        if choice == "5":
            return _load_current_session(session)
        if choice == "6":
            return False, replace(session, menu_state=MenuState()), "已退出游戏。"
        return _invalid_menu_choice(session)

    if choice == "1":
        return True, replace(session, menu_state=MenuState()), render_session(replace(session, menu_state=MenuState()))
    if choice == "2":
        running, next_session, message = route_command("next", session=replace(session, menu_state=MenuState()))
        next_session = _preserve_menu_history(next_session, history_session=session)
        return running, replace(next_session, menu_state=MenuState()), message
    if choice == "3":
        next_session = _enter_inspect_root(session, parent_mode="root")
        return True, next_session, _menu_view_message(next_session, "资料总览")
    if choice == "4":
        return _save_current_session(session)
    if choice == "5":
        return _load_current_session(session)
    if choice == "6":
        return False, replace(session, menu_state=MenuState()), "已退出游戏。"
    return _invalid_menu_choice(session)


def _route_card_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    combat_state = _combat_state_from_room(session.room_state)
    if combat_state is None:
        return True, replace(session, menu_state=MenuState()), "战斗状态不可用。"
    back_choice = str(len(combat_state.hand) + 1)
    if choice == back_choice:
        next_session = replace(session, menu_state=MenuState())
        return True, next_session, render_session(next_session)
    try:
        card_instance_id = _resolve_hand_card(combat_state, choice)
    except ValueError:
        return _invalid_menu_choice(session)
    if _card_requires_target(card_instance_id, session) and len(_combat_target_ids(combat_state)) > 1:
        next_session = replace(
            session,
            menu_state=MenuState(mode="select_target", selected_card_instance_id=card_instance_id),
        )
        return True, next_session, render_session(next_session)
    running, next_session, message = route_command(
        f"play {choice}",
        session=replace(session, menu_state=MenuState()),
    )
    next_session = _preserve_menu_history(next_session, history_session=session)
    return running, replace(next_session, menu_state=MenuState()), message


def _route_target_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    combat_state = _combat_state_from_room(session.room_state)
    if combat_state is None:
        return True, replace(session, menu_state=MenuState()), "战斗状态不可用。"
    selected_card_instance_id = session.menu_state.selected_card_instance_id
    if selected_card_instance_id is None:
        next_session = replace(session, menu_state=MenuState(mode="select_card"))
        return True, next_session, render_session(next_session)
    targets = _combat_target_ids(combat_state)
    back_choice = str(len(targets) + 1)
    if choice == back_choice:
        next_session = replace(session, menu_state=MenuState(mode="select_card"))
        return True, next_session, render_session(next_session)
    try:
        target_index = int(choice)
    except ValueError:
        return _invalid_menu_choice(session)
    if target_index <= 0 or target_index > len(targets):
        return _invalid_menu_choice(session)
    try:
        hand_index = _hand_index_for_card(combat_state, selected_card_instance_id)
    except ValueError:
        next_session = replace(session, menu_state=MenuState())
        return True, next_session, "所选手牌已发生变化，请重新选择。"
    running, next_session, message = route_command(
        f"play {hand_index} {target_index}",
        session=replace(session, menu_state=MenuState()),
    )
    next_session = _preserve_menu_history(next_session, history_session=session)
    return running, replace(next_session, menu_state=MenuState()), message


def _route_next_room_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    next_node_ids = session.room_state.payload.get("next_node_ids", [])
    if not isinstance(next_node_ids, list):
        return _invalid_menu_choice(session)
    back_choice = str(len(next_node_ids) + 1)
    if choice == back_choice:
        next_session = replace(session, menu_state=MenuState())
        return True, next_session, render_session(next_session)
    try:
        index = int(choice)
    except ValueError:
        return _invalid_menu_choice(session)
    if index <= 0 or index > len(next_node_ids):
        return _invalid_menu_choice(session)
    next_node_id = next_node_ids[index - 1]
    if not isinstance(next_node_id, str):
        return _invalid_menu_choice(session)
    next_session = _advance_to_node(replace(session, menu_state=MenuState()), next_node_id)
    return True, _preserve_menu_history(next_session, history_session=session), render_session(next_session)


def _route_event_choice_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    event_id = session.room_state.payload.get("event_id")
    if not isinstance(event_id, str):
        return True, replace(session, menu_state=MenuState()), "当前事件不可用。"
    event_def = _content_provider(session).events().get(event_id)
    back_choice = str(len(event_def.choices) + 1)
    if choice == back_choice:
        next_session = replace(session, menu_state=MenuState())
        return True, next_session, render_session(next_session)
    try:
        index = int(choice)
    except ValueError:
        return _invalid_menu_choice(session)
    if index <= 0 or index > len(event_def.choices):
        return _invalid_menu_choice(session)
    choice_id = event_def.choices[index - 1].get("id")
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
        run_phase=_derive_run_phase(result.run_state, result.room_state),
        menu_state=_menu_state_for_room(result.room_state),
    )
    return True, next_session, _message_with_render(next_session, result.message)


def _route_event_upgrade_card_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    options = session.room_state.payload.get("upgrade_options", [])
    if not isinstance(options, list):
        return _invalid_menu_choice(session)
    back_choice = str(len(options) + 1)
    if choice == back_choice:
        result = event_action(
            run_state=session.run_state,
            room_state=session.room_state,
            action_id="cancel",
            registry=_content_provider(session),
        )
    else:
        try:
            index = int(choice)
        except ValueError:
            return _invalid_menu_choice(session)
        if index <= 0 or index > len(options):
            return _invalid_menu_choice(session)
        result = event_action(
            run_state=session.run_state,
            room_state=session.room_state,
            action_id=f"upgrade_card:{options[index - 1]}",
            registry=_content_provider(session),
        )
    next_session = replace(
        session,
        run_state=result.run_state,
        room_state=result.room_state,
        run_phase=_derive_run_phase(result.run_state, result.room_state),
        menu_state=_menu_state_for_room(result.room_state),
    )
    return True, next_session, _message_with_render(next_session, result.message)


def _route_event_remove_card_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    candidates = session.room_state.payload.get("remove_candidates", [])
    if not isinstance(candidates, list):
        return _invalid_menu_choice(session)
    back_choice = str(len(candidates) + 1)
    if choice == back_choice:
        result = event_action(
            run_state=session.run_state,
            room_state=session.room_state,
            action_id="cancel",
            registry=_content_provider(session),
        )
    else:
        try:
            index = int(choice)
        except ValueError:
            return _invalid_menu_choice(session)
        if index <= 0 or index > len(candidates):
            return _invalid_menu_choice(session)
        result = event_action(
            run_state=session.run_state,
            room_state=session.room_state,
            action_id=f"remove_card:{candidates[index - 1]}",
            registry=_content_provider(session),
        )
    next_session = replace(
        session,
        run_state=result.run_state,
        room_state=result.room_state,
        run_phase=_derive_run_phase(result.run_state, result.room_state),
        menu_state=_menu_state_for_room(result.room_state),
    )
    return True, next_session, _message_with_render(next_session, result.message)


def _route_reward_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    rewards = list(session.room_state.rewards)
    claim_all_choice = str(len(rewards) + 1)
    back_choice = str(len(rewards) + 2)
    if choice == back_choice:
        next_session = replace(session, menu_state=MenuState())
        return True, next_session, render_session(next_session)
    if choice == claim_all_choice:
        next_session = _claim_all_session_rewards(session)
    else:
        try:
            index = int(choice)
        except ValueError:
            return _invalid_menu_choice(session)
        if index <= 0 or index > len(rewards):
            return _invalid_menu_choice(session)
        next_session = _claim_session_reward(session, rewards[index - 1])
    return True, next_session, render_session(next_session)


def _shop_root_actions(room_state: RoomState) -> list[str]:
    actions: list[str] = []
    for offer in room_state.payload.get("cards", []):
        if isinstance(offer, dict) and isinstance(offer.get("offer_id"), str):
            actions.append(f"buy_card:{offer['offer_id']}")
    for offer in room_state.payload.get("relics", []):
        if isinstance(offer, dict) and isinstance(offer.get("offer_id"), str):
            actions.append(f"buy_relic:{offer['offer_id']}")
    for offer in room_state.payload.get("potions", []):
        if isinstance(offer, dict) and isinstance(offer.get("offer_id"), str):
            actions.append(f"buy_potion:{offer['offer_id']}")
    actions.append("remove")
    actions.extend(["leave", "__inspect__", "__save__", "__load__", "__quit__"])
    return actions


def _route_shop_root_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    actions = _shop_root_actions(session.room_state)
    try:
        index = int(choice)
    except ValueError:
        return _invalid_menu_choice(session)
    if index <= 0 or index > len(actions):
        return _invalid_menu_choice(session)
    action_id = actions[index - 1]
    if action_id == "__inspect__":
        next_session = _enter_inspect_root(session, parent_mode="shop_root")
        return True, next_session, _menu_view_message(next_session, "资料总览")
    if action_id == "__save__":
        return _save_current_session(session)
    if action_id == "__load__":
        return _load_current_session(session)
    if action_id == "__quit__":
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
    candidates = session.room_state.payload.get("remove_candidates", [])
    if not isinstance(candidates, list):
        return _invalid_menu_choice(session)
    extra_actions = ["cancel", "__save__", "__load__", "__quit__"]
    actions = [f"remove_card:{candidate}" for candidate in candidates if isinstance(candidate, str)] + extra_actions
    try:
        index = int(choice)
    except ValueError:
        return _invalid_menu_choice(session)
    if index <= 0 or index > len(actions):
        return _invalid_menu_choice(session)
    action_id = actions[index - 1]
    if action_id == "__save__":
        return _save_current_session(session)
    if action_id == "__load__":
        return _load_current_session(session)
    if action_id == "__quit__":
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
    actions = [action for action in session.room_state.payload.get("actions", []) if isinstance(action, str)]
    actions.extend(["__inspect__", "__save__", "__load__", "__quit__"])
    try:
        index = int(choice)
    except ValueError:
        return _invalid_menu_choice(session)
    if index <= 0 or index > len(actions):
        return _invalid_menu_choice(session)
    action_id = actions[index - 1]
    if action_id == "__inspect__":
        next_session = _enter_inspect_root(session, parent_mode="rest_root")
        return True, next_session, _menu_view_message(next_session, "资料总览")
    if action_id == "__save__":
        return _save_current_session(session)
    if action_id == "__load__":
        return _load_current_session(session)
    if action_id == "__quit__":
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
    return True, next_session, render_session(next_session)


def _route_rest_upgrade_card_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    options = session.room_state.payload.get("upgrade_options", [])
    if not isinstance(options, list):
        return _invalid_menu_choice(session)
    actions = [f"upgrade_card:{card_instance_id}" for card_instance_id in options if isinstance(card_instance_id, str)]
    actions.extend(["cancel", "__save__", "__load__", "__quit__"])
    try:
        index = int(choice)
    except ValueError:
        return _invalid_menu_choice(session)
    if index <= 0 or index > len(actions):
        return _invalid_menu_choice(session)
    action_id = actions[index - 1]
    if action_id == "__save__":
        return _save_current_session(session)
    if action_id == "__load__":
        return _load_current_session(session)
    if action_id == "__quit__":
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
    return True, next_session, render_session(next_session)


def route_menu_choice(choice: str, *, session: SessionState) -> tuple[bool, SessionState, str]:
    next_session = _with_menu_choice_history(session, choice.strip())
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
    if next_session.menu_state.mode == "inspect_stats":
        return _route_inspect_leaf_menu(choice.strip(), next_session, "角色状态")
    if next_session.menu_state.mode == "inspect_relics":
        return _route_inspect_leaf_menu(choice.strip(), next_session, "遗物列表")
    if next_session.menu_state.mode == "inspect_potions":
        return _route_inspect_leaf_menu(choice.strip(), next_session, "药水列表")
    if next_session.menu_state.mode in {"inspect_hand", "inspect_draw_pile", "inspect_discard_pile", "inspect_exhaust_pile"}:
        return _route_combat_inspect_card_list_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "inspect_card_detail":
        return _route_combat_inspect_card_detail_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "inspect_enemy_list":
        return _route_combat_inspect_enemy_list_menu(choice.strip(), next_session)
    if next_session.menu_state.mode == "inspect_enemy_detail":
        return _route_combat_inspect_enemy_detail_menu(choice.strip(), next_session)
    return _invalid_menu_choice(replace(next_session, menu_state=MenuState()))


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
        command = input_port.read(prompt_for_session(session))
        running, session, message = route_menu_choice(command, session=session)
        outputs.append(message)
        if output_writer is not None:
            output_writer(message)
    return SessionLoopResult(outputs=outputs, final_session=session)
