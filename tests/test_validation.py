import pytest

from app.validation import ValidationError, validate_cheque, validate_cheque_date


def test_valid_cheque_data_is_normalized():
    assert validate_cheque("2026-10-14", "  A. Person  ", "25,000.00", " ref ") == (
        "2026-10-14", "A. Person", "25000.00", "ref", ""
    )


@pytest.mark.parametrize("value", ["14/10/2026", "2026-02-30", ""])
def test_invalid_dates_are_rejected(value):
    with pytest.raises(ValidationError):
        validate_cheque_date(value)


def test_empty_payee_and_long_fields_are_rejected():
    with pytest.raises(ValidationError, match="payee"):
        validate_cheque("2026-10-14", " ", "1")
    with pytest.raises(ValidationError, match="Payee"):
        validate_cheque("2026-10-14", "x" * 121, "1")
    with pytest.raises(ValidationError, match="Memo"):
        validate_cheque("2026-10-14", "Payee", "1", "x" * 121)
