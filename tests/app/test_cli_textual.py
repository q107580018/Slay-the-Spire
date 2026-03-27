from __future__ import annotations

from slay_the_spire.app import cli


def test_main_dispatches_new_game_to_textual_runner_by_default(monkeypatch) -> None:
    recorded: dict[str, object] = {}

    def fake_run_textual_session(*, session) -> None:
        recorded["seed"] = session.run_state.seed

    monkeypatch.setattr(cli, "run_textual_session", fake_run_textual_session)

    exit_code = cli.main(["new", "--seed", "5"])

    assert exit_code == 0
    assert recorded == {"seed": 5}


def test_main_dispatches_new_game_with_generated_seed_when_seed_missing(monkeypatch) -> None:
    recorded: dict[str, object] = {}

    def fake_run_textual_session(*, session) -> None:
        recorded["seed"] = session.run_state.seed

    monkeypatch.setattr(cli, "run_textual_session", fake_run_textual_session)
    monkeypatch.setattr(cli, "_generate_seed", lambda: 11)

    exit_code = cli.main(["new"])

    assert exit_code == 0
    assert recorded == {"seed": 11}


def test_main_rejects_removed_ui_flag(monkeypatch) -> None:
    monkeypatch.setattr(cli, "run_textual_session", lambda *, session: None)

    exit_code = cli.main(["--ui", "textual", "new", "--seed", "5"])

    assert exit_code == 2
