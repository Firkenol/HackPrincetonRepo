"""What the model hands to a pack's record tool, and its conversion to the pack's claims.

The same rules as agent/extraction.py: the model reports each value in the unit the
listing shows and Python converts it; there is no field for a seller, store or brand
name; no text field may carry the word "verified".

One extraction model per pack in packs.registry. EXTRACTIONS maps each pack id to the
record tool the listing reader calls for it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agent import units
from agent.extraction import StatedCount, StatedDimensions, _Stated
from claimcheck.models import NumberClaim
from packs import magnifier_lens, monocular_optics, projector_resolution
from packs.magnifier_lens import LensType, LensTypeClaim, MagnifierClaims
from packs.monocular_optics import MonocularClaims
from packs.projector_resolution import NamedResolution, PixelResolutionClaim, ProjectorClaims, ResolutionNameClaim


def _one(stated):
    return stated.to_claim() if stated is not None else None


class StatedLength(_Stated):
    value: float = Field(gt=0)
    unit: Literal["mm", "cm", "in"] = Field(description="The unit as shown.")

    def to_claim(self) -> NumberClaim:
        return NumberClaim(value=units.convert(self.value, self.unit, units.TO_MM), **self._provenance())


class StatedResolutionName(_Stated):
    value: NamedResolution = Field(
        description="'4k' for 4K, UHD or 2160p; '1080p' for Full HD or FHD; '720p' for HD; '8k' for 8K or 4320p."
    )

    def to_claim(self) -> ResolutionNameClaim:
        return ResolutionNameClaim(value=self.value, **self._provenance())


class StatedPixels(_Stated):
    width: float = Field(gt=0, description="Pixels across, the first number of '1280 x 720'.")
    height: float = Field(gt=0, description="Pixels down, the second number of '1280 x 720'.")

    def to_claim(self) -> PixelResolutionClaim:
        return PixelResolutionClaim(width_px=self.width, height_px=self.height, **self._provenance())


class StatedLensType(_Stated):
    value: LensType

    def to_claim(self) -> LensTypeClaim:
        return LensTypeClaim(value=self.value, **self._provenance())


class ProjectorExtraction(BaseModel):
    """What a projector listing states about resolution. Leave out what it does not state."""

    model_config = ConfigDict(extra="forbid")

    claimed_resolution: StatedResolutionName | None = Field(
        default=None, description="The resolution named in the title or headline, such as 4K or 1080p."
    )
    native_pixels: StatedPixels | None = Field(
        default=None,
        description=(
            "The native or physical resolution in pixels, from the spec table or description. Never a "
            "'supported', 'compatible' or 'maximum input' resolution."
        ),
    )
    native_name: StatedResolutionName | None = Field(
        default=None,
        description="The native resolution when it is given only by name, such as 'Native 720p'. Leave out when pixels are given.",
    )

    def to_claims(self) -> ProjectorClaims:
        return ProjectorClaims(
            claimed_resolution=_one(self.claimed_resolution),
            native_pixels=_one(self.native_pixels),
            native_name=_one(self.native_name),
        )


class MagnifierExtraction(BaseModel):
    """What a magnifying glass listing states. Leave out what it does not state."""

    model_config = ConfigDict(extra="forbid")

    magnification: StatedCount | None = Field(
        default=None,
        description=(
            "The magnifying power, such as 30 for '30X'. When a large lens and a small inset lens have "
            "different powers, give the power of the lens whose diameter you record."
        ),
    )
    lens_diameter: StatedLength | None = Field(
        default=None, description="Diameter of the lens itself. Not the frame, the handle or the package."
    )
    lens_type: StatedLensType | None = Field(
        default=None,
        description="'fresnel' when the listing says Fresnel, flat sheet or card lens; 'simple' when it says glass or optical lens. Leave out otherwise.",
    )

    def to_claims(self) -> MagnifierClaims:
        return MagnifierClaims(
            magnification=_one(self.magnification),
            lens_diameter_mm=_one(self.lens_diameter),
            lens_type=_one(self.lens_type),
        )


class MonocularExtraction(BaseModel):
    """What a monocular listing states. Leave out what it does not state."""

    model_config = ConfigDict(extra="forbid")

    magnification: StatedCount | None = Field(
        default=None, description="Headline magnification: the first number of an 'AxB' figure, 80 in '80x100'."
    )
    objective: StatedLength | None = Field(
        default=None,
        description="Headline objective lens diameter: the second number of an 'AxB' figure, 100 in '80x100', in mm.",
    )
    body_dimensions: StatedDimensions | None = Field(
        default=None,
        description="Listed dimensions of the monocular, only when all three sides are stated (or a diameter and a length).",
    )
    fine_print_magnification: StatedCount | None = Field(
        default=None,
        description="An 'actual', 'real' or 'true' magnification stated elsewhere in the listing. Never a copy of the headline.",
    )
    fine_print_objective: StatedLength | None = Field(
        default=None,
        description="An 'actual' objective lens diameter stated elsewhere in the listing. Never a copy of the headline.",
    )

    def to_claims(self) -> MonocularClaims:
        return MonocularClaims(
            magnification=_one(self.magnification),
            objective_mm=_one(self.objective),
            body_dimensions=_one(self.body_dimensions),
            fine_print_magnification=_one(self.fine_print_magnification),
            fine_print_objective_mm=_one(self.fine_print_objective),
        )


@dataclass(frozen=True)
class PackExtraction:
    pack: str
    tool: str  # the record tool the listing reader calls for this category
    model: type[BaseModel]
    description: str


_RECORD_SUFFIX = (
    " Call it once, instead of record_claims. Give each value in the unit shown; conversion happens "
    "inside the tool. Leave out every field the listing does not state. Never include a seller, store "
    "or brand name. Returns the claims as stored."
)

EXTRACTIONS: dict[str, PackExtraction] = {
    e.pack: e
    for e in (
        PackExtraction(
            projector_resolution.PACK_ID,
            "record_projector_claims",
            ProjectorExtraction,
            "Save what a projector listing states about its resolution." + _RECORD_SUFFIX,
        ),
        PackExtraction(
            magnifier_lens.PACK_ID,
            "record_magnifier_claims",
            MagnifierExtraction,
            "Save what a magnifying glass or loupe listing states." + _RECORD_SUFFIX,
        ),
        PackExtraction(
            monocular_optics.PACK_ID,
            "record_monocular_claims",
            MonocularExtraction,
            "Save what a monocular or spotting scope listing states." + _RECORD_SUFFIX,
        ),
    )
}
