from __future__ import annotations

from slay_the_spire.app.cli import main


def test_main_new_run_renders_first_room(capsys) -> None:
    exit_code = main(["new", "--seed", "5"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Run seed: 5" in captured.out
    assert "Act: act1" in captured.out
    assert "Room: start" in captured.out
