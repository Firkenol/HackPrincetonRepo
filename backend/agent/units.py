"""Unit conversion, in Python. The model reports a value in the unit the listing uses.

These factors are definitions, not measurements, so they are exact:

- SI prefixes (milli, centi, kilo): BIPM, The International System of Units (SI),
  9th edition, table 7.
- inch = 25.4 mm, pound = 0.45359237 kg, ounce = pound / 16: international yard and
  pound agreement of 1959, as listed in NIST Special Publication 811 (2008),
  Appendix B.8, where each is marked exact.
- 12 months in a year.

Measured physical reference data does not belong here; it lives in
claimcheck/constants.py with a citation per value.
"""

from __future__ import annotations

_POUND_G = 453.59237

TO_MAH = {"mAh": 1.0, "Ah": 1000.0}
TO_WH = {"Wh": 1.0, "mWh": 0.001}
TO_V = {"V": 1.0, "mV": 0.001}
TO_G = {"g": 1.0, "mg": 0.001, "kg": 1000.0, "oz": _POUND_G / 16, "lb": _POUND_G}
TO_MM = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4}
TO_YEARS = {"years": 1.0, "months": 1 / 12}


def convert(value: float, unit: str, table: dict[str, float]) -> float:
    """value in `unit`, expressed in the table's base unit.

    A value already in the base unit is returned untouched. The result is rounded to
    nine significant figures so that binary floating point does not leave digits such
    as 139.70000000000002 in a report.
    """
    factor = table[unit]
    if factor == 1.0:
        return value
    return float(f"{value * factor:.9g}")
