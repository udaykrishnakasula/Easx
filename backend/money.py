"""Exact-decimal money helpers. All monetary values use Decimal / Decimal128.
Never use float for money."""
from decimal import Decimal, ROUND_HALF_UP

from bson.decimal128 import Decimal128

TWO = Decimal("0.01")


def to_dec(value) -> Decimal:
    """Coerce Decimal128 / str / int to Decimal."""
    if isinstance(value, Decimal128):
        return value.to_decimal()
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def d128(value) -> Decimal128:
    if isinstance(value, Decimal128):
        return value
    return Decimal128(to_dec(value))


def quantize(value) -> Decimal:
    return to_dec(value).quantize(TWO, rounding=ROUND_HALF_UP)


def fmt(value) -> str:
    """Human/API string, 2dp, plain (no exponent)."""
    return format(quantize(value), "f")
