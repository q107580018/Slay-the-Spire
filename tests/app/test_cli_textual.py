from __future__ import annotations

from slay_the_spire.app import cli


def test_main_dispatches_new_game_to_textual_runner(monkeypatch) -> None:
    recorded: dict[str, object] = {}

    def fake_run_textual_session(*, session) -> None:
        recorded["seed"] = session.run_state.seed

    def fail_terminal_session(*, session) -> None:  # pragma: no cover
        raise AssertionError("terminal runner should not be called")

    monkeypatch.setattr(cli, "run_textual_session", fake_run_textual_session)
    monkeypatch.setattr(cli, "run_terminal_session", fail_terminal_session)

    exit_code = cli.main(["--ui", "textual", "new", "--seed", "5"])

    assert exit_code == 0
    assert recorded == {"seed": 5}
