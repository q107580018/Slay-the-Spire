from __future__ import annotations

from collections.abc import Iterable, Sequence

from slay_the_spire.domain.effects.effect_types import copy_effect
from slay_the_spire.domain.hooks.hook_types import HookRegistration, hook_sort_key
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.shared.types import JsonDict


def iter_hook_registrations(
    hook_name: str,
    registrations: Iterable[HookRegistration],
) -> list[HookRegistration]:
    return sorted(
        (registration for registration in registrations if registration.hook_name == hook_name),
        key=hook_sort_key,
    )


def dispatch_hook(
    state: CombatState,
    hook_name: str,
    registrations: Sequence[HookRegistration],
    payload: JsonDict | None = None,
) -> None:
    for registration in iter_hook_registrations(hook_name, registrations):
        for effect in registration.effects:
            derived_effect = copy_effect(effect)
            derived_effect["hook_context"] = {
                "hook_name": hook_name,
                "payload": copy_effect(payload or {}),
            }
            state.effect_queue.append(derived_effect)


def serialize_hook_registrations(registrations: Sequence[HookRegistration]) -> list[JsonDict]:
    return [registration.to_dict() for registration in sorted(registrations, key=hook_sort_key)]
