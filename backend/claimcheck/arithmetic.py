"""Plain numeric helpers. All math in OffSpec happens here, never in the model."""

from __future__ import annotations

import math

MM3_PER_LITRE = 1_000_000.0
G_PER_KG = 1000.0
MAH_PER_AH = 1000.0


def mah_to_ah(capacity_mah: float) -> float:
    return capacity_mah / MAH_PER_AH


def energy_wh(voltage_v: float, capacity_mah: float) -> float:
    """E = V x Q, with Q converted from mAh to Ah."""
    return voltage_v * mah_to_ah(capacity_mah)


def cylinder_volume_mm3(diameter_mm: float, height_mm: float) -> float:
    return math.pi * (diameter_mm / 2.0) ** 2 * height_mm


def box_volume_mm3(length_mm: float, width_mm: float, height_mm: float) -> float:
    return length_mm * width_mm * height_mm


def mm3_to_litres(volume_mm3: float) -> float:
    return volume_mm3 / MM3_PER_LITRE


def g_to_kg(mass_g: float) -> float:
    return mass_g / G_PER_KG


def relative_difference(stated: float, computed: float) -> float:
    """|stated - computed| as a fraction of computed."""
    return abs(stated - computed) / computed


def fmt(x: float) -> str:
    """Format a number for display with about four significant figures."""
    ax = abs(x)
    if ax < 1e-9:  # zero, or floating-point noise such as 45.88 - 7.4 * 6.2
        return "0"
    if ax >= 1000:
        return f"{x:,.0f}"
    if ax >= 100:
        s = f"{x:.1f}"
    elif ax >= 10:
        s = f"{x:.2f}"
    elif ax >= 1:
        s = f"{x:.3f}"
    else:
        decimals = 3 - math.floor(math.log10(ax))  # four significant figures, no exponent
        s = f"{x:.{decimals}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s
