"""Monocular-optics pack: an "80x100"-style figure against body size and fine print."""

from packs.monocular_optics.checks import (
    CHECKS,
    PACK_ID,
    ROUNDING_TOLERANCE,
    check_fine_print_consistency,
    check_objective_fits_body,
    evaluate,
)
from packs.monocular_optics.models import MonocularClaims

__all__ = [
    "CHECKS",
    "PACK_ID",
    "ROUNDING_TOLERANCE",
    "MonocularClaims",
    "check_fine_print_consistency",
    "check_objective_fits_body",
    "evaluate",
]
