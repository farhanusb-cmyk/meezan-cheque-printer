"""Pakistani rupee amount parsing and South Asian number words."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


_ONES = (
    "Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven",
    "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen",
    "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen",
)
_TENS = (
    "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy",
    "Eighty", "Ninety",
)
_MAX_AMOUNT = Decimal("999999999999.99")


class AmountError(ValueError):
    """Raised for invalid or unsupported cheque amounts."""


def parse_amount(value: str | int | float | Decimal) -> Decimal:
    """Parse a non-negative rupee amount, rounded to paisa precision."""
    try:
        amount = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        raise AmountError("Enter a valid numeric amount.") from None
    if not amount.is_finite():
        raise AmountError("Enter a finite numeric amount.")
    if amount < 0:
        raise AmountError("The amount cannot be negative.")
    rounded = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if amount != rounded:
        raise AmountError("Enter no more than two decimal places (paisa precision).")
    amount = rounded
    if amount > _MAX_AMOUNT:
        raise AmountError("The amount is too large to print safely.")
    return amount


def _under_thousand(number: int) -> str:
    parts: list[str] = []
    hundreds, remainder = divmod(number, 100)
    if hundreds:
        parts.extend((_ONES[hundreds], "Hundred"))
    if remainder >= 20:
        parts.append(_TENS[remainder // 10])
        if remainder % 10:
            parts.append(_ONES[remainder % 10])
    elif remainder:
        parts.append(_ONES[remainder])
    return " ".join(parts)


def _integer_words(number: int) -> str:
    if number == 0:
        return _ONES[0]

    groups = (
        (1_000_000_000, "Arab"),
        (10_000_000, "Crore"),
        (100_000, "Lakh"),
        (1_000, "Thousand"),
    )
    parts: list[str] = []
    remaining = number
    for divisor, label in groups:
        count, remaining = divmod(remaining, divisor)
        if count:
            parts.extend((_under_thousand(count), label))
    if remaining:
        parts.append(_under_thousand(remaining))
    return " ".join(parts)


def amount_to_words(value: str | int | float | Decimal) -> str:
    """Return a cheque-ready amount in words, including paisa when present."""
    amount = parse_amount(value)
    rupees = int(amount)
    paisa = int((amount - rupees) * 100)
    result = f"{_integer_words(rupees)} Rupees"
    if paisa:
        result += f" and {_integer_words(paisa)} Paisa"
    return result + " Only"
