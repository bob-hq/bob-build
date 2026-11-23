import pytest

from bob.pretty import truncate_middle


@pytest.mark.parametrize(
    ("width", "expected"),
    [
        (10, " build/out"),
        (9, " bu...out"),
        (4, "...t"),
        (3, " bu"),
        (0, ""),
        (-5, ""),
    ],
)
def test_truncate_middle(width: int, expected: str) -> None:
    assert truncate_middle(" build/out", width) == expected
