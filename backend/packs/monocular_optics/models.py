"""What a listing can state for the monocular-optics pack.

Built from the claim types in claimcheck.models, so every claim carries found_in,
quote and confidence. There is no field for a seller, store or brand name.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from claimcheck.models import DimensionsClaim, NumberClaim


class MonocularClaims(BaseModel):
    """Everything the listing states that this pack uses. Absent means not stated."""

    model_config = ConfigDict(extra="forbid")

    magnification: NumberClaim | None = Field(
        default=None,
        description="Headline magnification: the first number of an 'AxB' figure, such as 80 in '80x100'.",
    )
    objective_mm: NumberClaim | None = Field(
        default=None,
        description="Headline objective lens diameter in mm: the second number of an 'AxB' figure, such as 100 in '80x100'.",
    )
    body_dimensions: DimensionsClaim | None = Field(
        default=None,
        description="Listed outer dimensions of the monocular. kind is 'package' when they describe the box.",
    )
    fine_print_magnification: NumberClaim | None = Field(
        default=None,
        description="A different 'actual', 'real' or 'true' magnification stated in the spec table or fine print.",
    )
    fine_print_objective_mm: NumberClaim | None = Field(
        default=None,
        description="A different 'actual' objective lens diameter in mm stated in the spec table or fine print.",
    )
