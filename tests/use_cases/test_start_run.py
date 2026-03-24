from slay_the_spire.app.cli import main


def test_main_returns_zero_for_stub_argv():
    assert main(["--help"]) == 0
