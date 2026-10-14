from decimal import Decimal

import pytest

from app.amount_words import AmountError, amount_to_words, parse_amount


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        ("1000", "One Thousand Rupees Only"),
        ("25000", "Twenty Five Thousand Rupees Only"),
        ("150000", "One Lakh Fifty Thousand Rupees Only"),
        ("1250000", "Twelve Lakh Fifty Thousand Rupees Only"),
        ("10000000", "One Crore Rupees Only"),
        ("1000000000", "One Arab Rupees Only"),
        ("125.50", "One Hundred Twenty Five Rupees and Fifty Paisa Only"),
        ("0.01", "Zero Rupees and One Paisa Only"),
    ],
)
def test_amount_to_words(amount, expected):
    assert amount_to_words(amount) == expected


@pytest.mark.parametrize("value", ["", "abc", "-1", "NaN", "Infinity", "0.001"])
def test_invalid_amounts_are_rejected(value):
    with pytest.raises(AmountError):
        parse_amount(value)


def test_amount_precision_and_upper_bound():
    assert parse_amount("1.20") == Decimal("1.20")
    with pytest.raises(AmountError):
        parse_amount("1000000000000")
