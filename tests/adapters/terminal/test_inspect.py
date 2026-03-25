from slay_the_spire.adapters.terminal.inspect import (
    format_card_detail_lines,
    format_relic_detail_lines,
)
from slay_the_spire.app.session import start_session
from slay_the_spire.content.provider import StarterContentProvider


def test_format_card_detail_lines_include_cost_effects_and_upgrade() -> None:
    session = start_session(seed=5)
    registry = StarterContentProvider(session.content_root)

    lines = format_card_detail_lines("bash#1", registry)

    assert any("费用" in line.plain for line in lines)
    assert any("造成 8 伤害" in line.plain for line in lines)
    assert any("施加 2 易伤" in line.plain for line in lines)


def test_format_relic_detail_lines_include_passive_effect_description() -> None:
    session = start_session(seed=5)
    registry = StarterContentProvider(session.content_root)

    lines = format_relic_detail_lines("burning_blood", registry)

    assert any("燃烧之血" in line.plain for line in lines)
    assert any("回复 6 点生命" in line.plain for line in lines)
