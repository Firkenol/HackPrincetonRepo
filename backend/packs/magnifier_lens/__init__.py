"""Magnifier-lens pack: claimed magnifying power against the diameter of the lens."""

from packs.magnifier_lens.checks import CHECKS, HARD_RESULT_MARGIN, PACK_ID, check_lens_diameter, evaluate
from packs.magnifier_lens.models import LensType, LensTypeClaim, MagnifierClaims

__all__ = [
    "CHECKS",
    "HARD_RESULT_MARGIN",
    "PACK_ID",
    "LensType",
    "LensTypeClaim",
    "MagnifierClaims",
    "check_lens_diameter",
    "evaluate",
]
