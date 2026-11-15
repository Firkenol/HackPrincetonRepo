"""What a listing can state for the magnifier-lens pack.

Built from the claim types in claimcheck.models, so every claim carries found_in,
quote and confidence. There is no field for a seller, store or brand name.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from claimcheck.models import NumberClaim, TextClaim


class LensType(str, Enum):
    SIMPLE = "simple"  # one ordinary curved lens of glass or plastic
    FRESNEL = "fresnel"  # a Fresnel lens, a flat sheet or a card magnifier


class LensTypeClaim(TextClaim):
    value: LensType


class MagnifierClaims(BaseModel):
    """Everything the listing states that this pack uses. Absent means not stated."""

    model_config = ConfigDict(extra="forbid")

    magnification: NumberClaim | None = Field(
        default=None,
        description=(
            "The magnifying power claimed for the lens that the diameter belongs to, such as 30 for '30X'. "
            "When a handle holds a large lens and a small inset lens, this is the power of the large lens."
        ),
    )
    lens_diameter_mm: NumberClaim | None = Field(
        default=None, description="Diameter of that lens itself. Not the frame, the handle or the package."
    )
    lens_type: LensTypeClaim | None = Field(
        default=None,
        description="'fresnel' when the listing describes a Fresnel, flat sheet or card lens. Absent when it does not say.",
    )
