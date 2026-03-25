from __future__ import annotations

from slay_the_spire.domain.effects.effect_types import copy_effect
from slay_the_spire.domain.hooks.hook_types import HookRegistration
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort
from slay_the_spire.shared.types import JsonDict


def build_runtime_hook_registrations(
    run_state: RunState,
    registry: ContentProviderPort,
) -> list[HookRegistration]:
    registrations: list[HookRegistration] = []
    player_instance_id = f"player-{run_state.character_id}"

    for registration_index, relic_id in enumerate(run_state.relics):
        relic = registry.relics().get(relic_id)
        effects: list[JsonDict] = []
        for raw_effect in relic.passive_effects:
            effect = copy_effect(raw_effect)
            if effect.get("type") == "heal" and "target_instance_id" not in effect:
                effect["target_instance_id"] = player_instance_id
            effects.append(effect)
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
