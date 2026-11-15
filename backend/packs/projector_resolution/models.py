"""What a listing can state for the projector-resolution pack.

Built from the claim types in claimcheck.models, so every claim carries found_in,
quote and confidence. There is no field for a seller, store or brand name.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from claimcheck.models import TextClaim, _Claim


class NamedResolution(str, Enum):
    HD_720P = "720p"  # also written HD, HD Ready
    FHD_1080P = "1080p"  # also written Full HD, FHD
    UHD_4K = "4k"  # also written 4K UHD, UHD, 2160p
    UHD_8K = "8k"  # also written 8K UHD, 4320p


class ResolutionNameClaim(TextClaim):
    """A resolution given by name, such as "4K" or "1080p"."""

    value: NamedResolution


class PixelResolutionClaim(_Claim):
    """A resolution given in pixels, such as 1280 x 720."""

    width_px: float = Field(gt=0)
    height_px: float = Field(gt=0)


class ProjectorClaims(BaseModel):
    """Everything the listing states that this pack uses. Absent means not stated."""

    model_config = ConfigDict(extra="forbid")

    claimed_resolution: ResolutionNameClaim | None = Field(
        default=None,
        description="The resolution named in the title or headline, such as 4K or 1080p.",
    )
    native_pixels: PixelResolutionClaim | None = Field(
        default=None,
        description=(
            "The native (physical) resolution in pixels, as stated in the spec table or description. "
            "Not a 'supported', 'compatible' or 'maximum input' resolution."
        ),
    )
    native_name: ResolutionNameClaim | None = Field(
        default=None,
        description="The native resolution when the listing gives it only by name, such as 'Native 720p'.",
    )
