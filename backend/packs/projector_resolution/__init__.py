"""Projector-resolution pack: the headline resolution against the native pixel count."""

from packs.projector_resolution.checks import CHECKS, PACK_ID, check_native_resolution, evaluate
from packs.projector_resolution.models import (
    NamedResolution,
    PixelResolutionClaim,
    ProjectorClaims,
    ResolutionNameClaim,
)

__all__ = [
    "CHECKS",
    "PACK_ID",
    "NamedResolution",
    "PixelResolutionClaim",
    "ProjectorClaims",
    "ResolutionNameClaim",
    "check_native_resolution",
    "evaluate",
]
