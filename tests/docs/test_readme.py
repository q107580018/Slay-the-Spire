from pathlib import Path


def test_readme_mentions_batch_five_relic_coverage_without_claiming_full_completion() -> (
    None
):
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text(
        encoding="utf-8"
    )

    assert "question_card" in readme
    assert "prayer_wheel" in readme
    assert "busted_crown" in readme
    assert "white_beast_statue" in readme
    assert "sozu" in readme
    assert "the_courier" in readme
    assert "matryoshka" in readme
    assert "wing_boots" in readme
    assert "高复杂度遗物" in readme
    assert "implementation_status" in readme
    assert "占位遗物不进入随机投放池" in readme
    assert "遗物已全部完成" not in readme
