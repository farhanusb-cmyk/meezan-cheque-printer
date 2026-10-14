"""Input validation helpers used by the form and persistence layer."""

from datetime import date

from .amount_words import AmountError, parse_amount

MAX_PAYEE_LENGTH = 120
MAX_MEMO_LENGTH = 120
MAX_REMARKS_LENGTH = 1000


class ValidationError(ValueError):
    """Raised when cheque form data is invalid."""


def validate_cheque_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError):
        raise ValidationError("Enter a valid cheque date.") from None


def validate_cheque(
    cheque_date: str,
    payee: str,
    amount: str,
    memo: str = "",
    remarks: str = "",
) -> tuple[str, str, str, str, str]:
    normalized_date = validate_cheque_date(cheque_date)
    normalized_payee = (payee or "").strip()
    if not normalized_payee:
        raise ValidationError("Enter a payee name.")
    if len(normalized_payee) > MAX_PAYEE_LENGTH:
        raise ValidationError(f"Payee name must be {MAX_PAYEE_LENGTH} characters or fewer.")
    normalized_memo = (memo or "").strip()
    if len(normalized_memo) > MAX_MEMO_LENGTH:
        raise ValidationError(f"Memo must be {MAX_MEMO_LENGTH} characters or fewer.")
    normalized_remarks = (remarks or "").strip()
    if len(normalized_remarks) > MAX_REMARKS_LENGTH:
        raise ValidationError(f"Internal remarks must be {MAX_REMARKS_LENGTH} characters or fewer.")
    try:
        normalized_amount = str(parse_amount(amount))
    except AmountError as error:
        raise ValidationError(str(error)) from None
    return normalized_date, normalized_payee, normalized_amount, normalized_memo, normalized_remarks
