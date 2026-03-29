# Neow Opening Rule Alignment Design

## Goal

Align the opening `Neow` offer generation with the original Slay the Spire rule structure while preserving this project's existing Textual opening flow, numbered menus, targeted submenus, and hover preview model.

This design intentionally does not implement the original game's separate branch where failing to reach the Act 1 boss in the previous run reduces Neow to two options. The scope here is the four-offer opening structure only.

## Context

The current implementation in `src/slay_the_spire/use_cases/opening_flow.py` generates `2` free offers and `2` tradeoff offers. That differs from the original game's opening rules in two important ways:

1. The original game uses four fixed slots with distinct purposes, not two free plus two tradeoff draws from mixed pools.
2. The current project models `curse_card` as a reward kind and can pair it with a curse cost, producing a nonsensical option where the player effectively takes curses as both the reward and the drawback.

The new design corrects the slot structure, reward pools, and tradeoff constraints, but keeps the current opening session architecture intact.

## Non-Goals

- Do not implement the original "previous run failed before Act 1 boss" two-option branch.
- Do not implement `Neow's Lament` in this change. It is allowed to remain absent until there is a concrete implementation for its runtime behavior.
- Do not build the full original three-card choice UI for class cards or colorless cards in this change.
- Do not refactor the entire opening flow into content JSON or a fully generic reward engine.

## Recommended Approach

Use a fixed four-slot generator in `opening_flow.py` and keep `NeowOffer` as the existing data carrier.

This is the smallest change that restores the original opening rule structure without forcing a large UI rewrite or premature data-driven refactor. The project already has working menu routing, target selection, reward application, and hover rendering. Reusing those pieces keeps the change focused on opening rule correctness.

Alternative approaches considered:

1. Minimal hotfix only
   Fix the curse reward bug and add a boss relic swap option, but keep the existing `2 free + 2 tradeoff` structure. Rejected because it still leaves the core opening structure unlike the original game.
2. Full data-driven Neow framework
   Move slot definitions, pools, and constraints into content files. Rejected for now because it is a larger architectural change than this rule-alignment task needs.

## Offer Model

Keep the existing `NeowOffer` shape and continue using these fields:

- `offer_id`
- `category`
- `reward_kind`
- `cost_kind`
- `reward_payload`
- `cost_payload`
- `requires_target`
- `summary`
- `detail_lines`

The main change is semantic: `category`, `reward_kind`, and `cost_kind` will now represent the original game's slot structure instead of the current free/tradeoff simplification.

## Fixed Four Slots

Every opening with a preselected character will generate exactly four offers in this fixed order:

1. `card_bonus`
2. `non_card_bonus`
3. `tradeoff_bonus`
4. `boss_relic_swap`

This order should be stable for rendering and tests.

### Slot 1: `card_bonus`

This slot chooses one reward from a card-focused pool. It has no cost.

Supported rewards in this project:

- Remove `1` card
- Transform `1` card
- Upgrade `1` card
- Obtain `1` random rare card

Notes:

- The original game also includes class-card choice and uncommon colorless-card choice. Those are intentionally omitted here because the project does not yet have the matching three-choice UI and content support to present them faithfully.
- `remove_card`, `transform_card`, and `upgrade_card` continue to use targeted submenu flow.

### Slot 2: `non_card_bonus`

This slot chooses one reward from a non-card pool. It has no cost.

Supported rewards in this project:

- Increase max HP by the original Ironclad amount
- Obtain `1` random common relic
- Gain `100` gold
- Obtain `3` random potions

Notes:

- `Neow's Lament` is excluded from the pool until it has a proper implementation.
- The common relic draw must exclude starter relic replacement targets and relics that are not appropriate as a general opening reward, following the same filtering principles already used by the current implementation.

### Slot 3: `tradeoff_bonus`

This slot combines one drawback and one strong reward.

Supported drawbacks:

- Lose max HP by the original Ironclad amount
- Take HP damage based on current HP
- Add `1` curse to the deck
- Lose all gold

Supported rewards:

- Remove `2` cards
- Transform `2` cards
- Gain `250` gold
- Obtain `1` random rare card
- Obtain `1` random rare relic
- Increase max HP by the original large Ironclad amount

Required pairing constraints:

- `curse` must not pair with `remove_2_cards`
- `gold_loss_all` must not pair with `gain_250_gold`
- `max_hp_loss` must not pair with `max_hp_gain_large`

Additional rule:

- `curse_card` is no longer a reward kind. Curses appear only as a drawback.

### Slot 4: `boss_relic_swap`

This slot is always present.

Effect:

- Replace the starter relic with `1` random boss relic

Behavior requirements:

- Remove `burning_blood` from the player's relic list
- Add the chosen boss relic
- Preserve any existing relic runtime constraints already supported in the project
- Exclude boss relics that the project cannot support correctly at game start

## Reward and Cost Semantics

### Max HP amounts

Use the original Ironclad values because the project currently only supports Ironclad:

- Small max HP gain: `+8`
- Large max HP gain: `+16`
- Max HP loss: `-8`

Current HP should be clamped consistently with the project's existing state semantics when max HP changes.

### Damage drawback

Use the original formula described by the wiki entry:

- Damage = `(current_hp // 10) * 3`

Apply the same floor and lower-bound safety semantics already used elsewhere in the project so the run state remains valid.

### Gold amounts

- Free gold reward: `100`
- Tradeoff gold reward: `250`
- Gold loss drawback: lose all current gold

### Potion reward

The free non-card potion reward becomes `3` random potions instead of `1`.

The project may allow duplicate potion IDs unless there is already an established uniqueness rule elsewhere. This change should follow existing potion storage semantics rather than inventing a new uniqueness system.

## Targeted Offer Flow

The current opening flow already supports one-target card operations through `pending_neow_offer_id` and submenu routing. The redesign extends that model instead of replacing it.

Requirements:

- `upgrade_card` continues selecting exactly `1` target card
- `remove_card` continues selecting exactly `1` target card
- `transform_card` selects exactly `1` target card
- `remove_2_cards` selects `2` cards sequentially using the existing submenu pattern
- `transform_2_cards` selects `2` cards sequentially using the existing submenu pattern

Sequential multi-target selection is preferred over designing a new multi-select UI. It is simpler, fits the current numbered menu model, and keeps the change small.

## Transform Behavior

This change introduces the minimal transform behavior needed for Neow.

Rules:

- Remove the selected card instance from the deck
- Replace it with a new card instance from a valid transform pool
- The transform result should be deterministic for the run seed and slot seed inputs
- The replacement should not be a curse or status card
- The replacement should not be the same base card ID as the removed card unless no valid alternative exists

Pool policy for this change:

- Use a practical project-local transform pool rather than trying to fully replicate original transform rarity logic if that logic does not already exist elsewhere
- Document the exact pool and deterministic selection method in code comments or tests if it is not obvious from the implementation

This keeps the behavior consistent and testable without expanding scope into a full transform system overhaul.

## Rendering and Copy

The existing opening renderer and Textual hover preview should continue to work through `summary` and `detail_lines`, but the text must reflect the new semantics.

Requirements:

- All player-facing copy remains Chinese
- No option should present curse as the reward when the curse is actually the drawback
- Boss relic swap should clearly say that the starter relic is replaced
- Potion rewards should clearly show that the reward grants `3` potions
- Tradeoff offers should clearly show both the benefit and the drawback

## Testing Strategy

Follow TDD. Write failing tests first, verify the failures, then implement the smallest changes needed.

At minimum, add or update tests for these behaviors:

1. Opening state generates exactly four offers with stable fixed slot IDs and categories
2. The fourth offer is always the boss relic swap
3. Tradeoff offers never use curse as a reward kind
4. Tradeoff offer pairings respect all three forbidden combinations
5. Free non-card gold reward uses `100`
6. Tradeoff gold reward uses `250`
7. Free non-card potion reward grants `3` potions
8. Max HP gain and loss amounts match Ironclad values
9. Boss relic swap removes `burning_blood` and adds a supported boss relic
10. Transform `1` card updates the deck deterministically and preserves replayability
11. Remove/transform `2` cards can complete through the existing opening submenu flow
12. Opening summaries and hover details describe the new reward semantics correctly

Relevant test files:

- `tests/use_cases/test_opening_flow.py`
- `tests/app/test_opening_session.py`
- `tests/adapters/textual/test_slay_app.py`
- additional focused tests if transform or relic replacement logic needs isolated coverage

## Documentation Updates

After implementation, update:

- `README.md`
- `AGENTS.md`

The docs should describe the new four-slot Neow structure, the current omission of `Neow's Lament`, and the fact that choice-based card rewards are still simplified relative to the original game.

## Risks and Mitigations

### Risk: multi-target card flow complicates opening state

Mitigation:

- Keep the existing submenu approach and extend it incrementally for `2` targets
- Avoid introducing a new generic multi-select menu system in this change

### Risk: transform pool behavior becomes surprising

Mitigation:

- Keep the transform selection deterministic
- Test the exact resulting deck updates
- Prefer a simple and explicit pool rule over a partially guessed imitation of the original rarity algorithm

### Risk: boss relic replacement creates unsupported start-of-run effects

Mitigation:

- Reuse the current boss relic filtering approach where possible
- Add tests for supported relic insertion and basic run-state correctness

## Implementation Boundaries

This design is complete enough for one implementation plan. It does not need to be decomposed further before planning.
