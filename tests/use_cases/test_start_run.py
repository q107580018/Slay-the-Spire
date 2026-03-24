from slay_the_spire.app.cli import main


def test_main_returns_zero_for_help():
    assert main(["--help"]) == 0
