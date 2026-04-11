from pathlib import Path

import pytest


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


@pytest.mark.guardrail
def test_readme_documents_guardrail_command_and_content_batch_checklist() -> None:
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text(
        encoding="utf-8"
    )

    required_fragments = [
        "uv run pytest -m guardrail",
        "session 菜单模式",
        "跨幕推进",
        "reward generate/apply",
        "effect queue/hook 时序",
        "save/load round-trip",
        "内容已录入 vs 可触达校验",
        "`content/`",
        "registry/content validation",
        "domain/use case",
        "session route",
        "presentation/Textual",
        "`implementation_status`",
        "不进入随机投放池",
    ]

    for fragment in required_fragments:
        assert fragment in readme, f"README is missing required fragment: {fragment}"
