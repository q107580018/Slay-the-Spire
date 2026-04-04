from __future__ import annotations

from collections.abc import Sequence

from slay_the_spire.domain.effects.effect_types import copy_effect
from slay_the_spire.domain.hooks.hook_types import HookRegistration
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort
from slay_the_spire.shared.types import JsonDict


def _player_instance_id(run_state: RunState) -> str:
    return f"player-{run_state.character_id}"


def _materialize_relic_effects(
    effects: Sequence[JsonDict],
    *,
    target_instance_id: str,
) -> list[JsonDict]:
    materialized: list[JsonDict] = []
    for raw_effect in effects:
        effect = copy_effect(raw_effect)
        if (
            effect.get("type") in {"heal", "block"}
            and "target_instance_id" not in effect
        ):
            effect["target_instance_id"] = target_instance_id
        materialized.append(effect)
    return materialized


def build_runtime_hook_registrations(
    run_state: RunState,
    registry: ContentProviderPort,
) -> list[HookRegistration]:
    registrations: list[HookRegistration] = []
    player_instance_id = _player_instance_id(run_state)
    opening_combat_relic_ids = {
        "anchor",
        "bag_of_marbles",
        "bag_of_preparation",
        "lantern",
        "clockwork_souvenir",
        "thread_and_needle",
        "twisted_funnel",
        "ninja_scroll",
    }

    for registration_index, relic_id in enumerate(run_state.relics):
        relic = registry.relics().get(relic_id)
        effects = _materialize_relic_effects(
            relic.passive_effects, target_instance_id=player_instance_id
        )
        registrations.append(
            HookRegistration(
                hook_name="__runtime__",
                category="relic",
                priority=0,
                source_type="relic",
                source_instance_id=relic_id,
                registration_index=registration_index,
                effects=[],
            )
        )
        if relic_id in opening_combat_relic_ids:
            registrations.append(
                HookRegistration(
                    hook_name="on_opening_combat_turn",
                    category="relic",
                    priority=0,
                    source_type="relic",
                    source_instance_id=relic_id,
                    registration_index=registration_index,
                    effects=[],
                )
            )
        for hook_name in relic.trigger_hooks:
            registrations.append(
                HookRegistration(
                    hook_name=hook_name,
                    category="relic",
                    priority=0,
                    source_type="relic",
                    source_instance_id=relic_id,
                    registration_index=registration_index,
                    effects=effects,
                )
            )
    return registrations


def registered_relic_ids(
    registrations: Sequence[HookRegistration],
    *,
    hook_names: Sequence[str] | None = None,
) -> set[str]:
    allowed_hooks = set(hook_names) if hook_names is not None else None
    return {
        registration.source_instance_id
        for registration in registrations
        if registration.source_type == "relic"
        and (allowed_hooks is None or registration.hook_name in allowed_hooks)
    }
