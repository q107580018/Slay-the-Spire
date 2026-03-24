from slay_the_spire.shared.rng import SeededRng


def test_seeded_rng_is_deterministic():
    left = SeededRng(42)
    right = SeededRng(42)
    assert [left.randint(1, 9) for _ in range(5)] == [
        right.randint(1, 9) for _ in range(5)
    ]
