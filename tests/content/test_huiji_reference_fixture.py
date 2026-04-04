from __future__ import annotations

import json
from pathlib import Path


def test_card_relic_expectation_fixture_exists_and_is_non_empty() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "reference"
        / "sts_huijiwiki"
        / "card_relic_expectations.json"
    )

    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert payload["cards"]
    assert payload["relics"]
    assert "strike" in payload["cards"]
    assert "burning_blood" in payload["relics"]
