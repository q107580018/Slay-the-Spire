from pathlib import Path


def test_readme_mentions_batch_five_relic_coverage_without_claiming_full_completion() -> (
    None
):
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text(
        encoding="utf-8"
    )

    assert "the_courier" in readme
    assert "matryoshka" in readme
    assert "wing_boots" in readme
    assert "高复杂度遗物" in readme
    assert "遗物已全部完成" not in readme
