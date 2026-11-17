"""Ops units: money is whole minor units (1 AMD = 100, a decimal string), quantities are whole
base units (g, ml, pcs) — ops/packages/contracts/src/quantity.ts. Never floats.

A stock unit is `pack` (counted in pcs) or `loose` (kg / g or l / ml); `count`, `mass` and
`volume` are accepted for a caller that knows the measure. A `loose` quantity is shown in g / kg.
"""
import re
from decimal import Decimal

from siruk.payload import PayloadError

MINOR_PER_AMD = 100
FACTOR = {"kg": 1000, "g": 1, "l": 1000, "ml": 1, "pcs": 1, "pc": 1}
SUFFIXES = {"pack": ("pcs", "pc"), "count": ("pcs", "pc"), "loose": ("kg", "g", "l", "ml"),
            "mass": ("kg", "g"), "volume": ("l", "ml")}
BASE = {"pack": "pcs", "count": "pcs", "loose": "g", "mass": "g", "volume": "ml"}


def amd_to_minor(x):
    """"1300" → "130000", "1300.5" → "130050". Refuses negatives and more than 2 decimals."""
    if isinstance(x, bool) or not isinstance(x, (int, str, float, Decimal)):
        raise PayloadError(f"not an amount: {x!r}")
    s = (repr(x) if isinstance(x, float) else str(x)).strip()
    if s.startswith("-"):
        raise PayloadError(f"an amount cannot be negative: {s}")
    m = re.fullmatch(r"(\d+)(?:\.(\d+))?", s)
    if not m:
        raise PayloadError(f"not an amount in AMD: {s!r}")
    whole, frac = m.group(1), m.group(2) or ""
    if len(frac) > 2:
        raise PayloadError(f"{s} AMD has more than 2 decimals (the smallest unit is 0.01)")
    return str(int(whole) * MINOR_PER_AMD + int(frac.ljust(2, "0") or "0"))


def minor_to_amd(s):
    """"130000" → "1300", "130050" → "1300.50"."""
    t = str(s).strip()
    if not re.fullmatch(r"-?\d+", t):
        raise PayloadError(f"not a minor-unit amount: {s!r}")
    n = int(t)
    whole, cents = divmod(abs(n), MINOR_PER_AMD)
    out = f"{whole}.{cents:02d}" if cents else str(whole)
    return "-" + out if n < 0 else out


def _unit(stock_unit):
    if stock_unit not in SUFFIXES:
        raise PayloadError(f"unknown stock unit {stock_unit!r}; one of {', '.join(SUFFIXES)}")
    return stock_unit


def _nonneg(n, x):
    if n < 0:
        raise PayloadError(f"a quantity cannot be negative: {x!r}")
    return n


def parse_quantity(x, stock_unit):
    """An int is base units as is; "2.5kg" "500g" "1.5l" "250ml" "3pcs" are converted. A suffix the unit
    does not use (kg on a pack) is refused, and so is a negative or anything that is not a whole number of
    base units. Zero is allowed."""
    unit = _unit(stock_unit)
    if isinstance(x, bool) or not isinstance(x, (int, str)):
        raise PayloadError(f"not a quantity: {x!r}")
    if isinstance(x, int):
        return _nonneg(x, x)
    s = x.strip().lower()
    if re.fullmatch(r"-?\d+", s):
        return _nonneg(int(s), x)
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*([a-z]+)", s)
    if not m or m.group(2) not in FACTOR:
        raise PayloadError(f"not a quantity: {x!r} (a whole number of {BASE[unit]}, or with a unit: "
                           f"{', '.join(SUFFIXES[unit])})")
    if m.group(2) not in SUFFIXES[unit]:
        raise PayloadError(f"{x!r}: a {stock_unit} good is counted in {' / '.join(SUFFIXES[unit])}, "
                           f"not {m.group(2)}")
    base = Decimal(m.group(1)) * FACTOR[m.group(2)]
    _nonneg(base, x)
    if base != base.to_integral_value():
        raise PayloadError(f"{x!r} is not a whole number of {BASE[unit]}")
    return int(base)


def _trim(d):
    return format(d.quantize(Decimal("0.001")).normalize(), "f")


def format_quantity(n, stock_unit):
    """745 loose → "745 g", 2500 loose → "2.5 kg", 3 pack → "3 pcs"."""
    unit, n = _unit(stock_unit), int(n)
    if unit in ("loose", "mass") and abs(n) >= 1000:
        return f"{_trim(Decimal(n) / 1000)} kg"
    if unit == "volume" and abs(n) >= 1000:
        return f"{_trim(Decimal(n) / 1000)} l"
    return f"{n} {BASE[unit]}"
