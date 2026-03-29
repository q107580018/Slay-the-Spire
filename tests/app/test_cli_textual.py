from __future__ import annotations

from slay_the_spire.app import cli


def test_main_new_without_character_enters_character_select(monkeypatch) -> None:
    recorded: dict[str, object] = {}

    def fake_run_textual_session(*, session) -> None:
        recorded["run_phase"] = session.run_phase
        recorded["menu_mode"] = session.menu_state.mode

    monkeypatch.setattr(cli, "run_textual_session", fake_run_textual_session)

    exit_code = cli.main(["new", "--seed", "5"])

    assert exit_code == 0
    assert recorded == {"run_phase": "opening", "menu_mode": "opening_character_select"}


def test_main_new_with_character_skips_to_neow(monkeypatch) -> None:
    recorded: dict[str, object] = {}

    def fake_run_textual_session(*, session) -> None:
        recorded["menu_mode"] = session.menu_state.mode
        recorded["character_id"] = session.opening_state.selected_character_id

    monkeypatch.setattr(cli, "run_textual_session", fake_run_textual_session)

    exit_code = cli.main(["new", "--seed", "5", "--character", "ironclad"])

    assert exit_code == 0
    assert recorded == {"menu_mode": "opening_neow_offer", "character_id": "ironclad"}


def test_main_dispatches_new_game_with_generated_seed_when_seed_missing(monkeypatch) -> None:
    recorded: dict[str, object] = {}

    def fake_run_textual_session(*, session) -> None:
        recorded["seed"] = session.opening_state.seed

    monkeypatch.setattr(cli, "run_textual_session", fake_run_textual_session)
    monkeypatch.setattr(cli, "_generate_seed", lambda: 11)

    exit_code = cli.main(["new"])

    assert exit_code == 0
    assert recorded == {"seed": 11}


def test_main_rejects_removed_ui_flag(monkeypatch) -> None:
    monkeypatch.setattr(cli, "run_textual_session", lambda *, session: None)

    exit_code = cli.main(["--ui", "textual", "new", "--seed", "5"])

    assert exit_code == 2
