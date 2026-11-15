"""Parseo de salarios a EUR brutos/año."""

from __future__ import annotations

import re

from jobmatch.config import FX_TO_EUR

_CURRENCY = [("USD", r"\$|usd|us\$"), ("GBP", r"£|gbp"), ("CHF", r"chf"), ("EUR", r"€|eur|euros?")]
_NUMBER = re.compile(r"(\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s*(k|mil)?", re.I)
_HOURLY = re.compile(r"/\s*h(ou)?r|per hour|por hora|hourly", re.I)
_MONTHLY = re.compile(r"/\s*mo(nth)?|per month|al mes|mensual|monthly", re.I)


def _currency(text: str) -> str:
    low = text.lower()
    for code, pattern in _CURRENCY:
        if re.search(pattern, low):
            return code
    return "EUR"


def _to_number(raw: str, suffix: str | None) -> float:
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", raw):
        value = float(re.sub(r"[.,]", "", raw))
    else:
        value = float(raw.replace(",", "."))
    if suffix:
        value *= 1000
    return value


def to_eur(amount: float | None, currency: str = "EUR") -> float | None:
    if amount is None:
        return None
    return round(amount * FX_TO_EUR.get(currency.upper(), 1.0), 0)


def parse_salary(text: str | None) -> tuple[float | None, float | None]:
    """'40k-50k', '35.000 € brutos/año', '$120k' → (min, max) en EUR/año."""
    if not text:
        return None, None
    values = [_to_number(n, k) for n, k in _NUMBER.findall(text)]
    values = [v for v in values if v >= 10]
    if not values:
        return None, None
    if _HOURLY.search(text):
        values = [v * 1700 for v in values]
    elif _MONTHLY.search(text):
        values = [v * 12 for v in values]
    values = [v for v in values if 8_000 <= v <= 600_000]
    if not values:
        return None, None
    currency = _currency(text)
    return to_eur(min(values), currency), to_eur(max(values), currency)
