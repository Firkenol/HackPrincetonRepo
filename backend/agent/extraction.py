"""What the model hands to record_claims, and its conversion to the contract's Claims.

The model reports each value in the unit the listing or photo shows. to_claims()
converts to the fixed units of claimcheck.models.Claims in Python, so the model never
converts a unit. There is no field for a seller, store or brand name, and no text
field may carry the word "verified", which the tool never says about a listing.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agent import units
from claimcheck.models import (
    Chemistry,
    ChemistryClaim,
    Claims,
    DimensionsClaim,
    MeasurementKind,
    NumberClaim,
    ProductType,
    TextClaim,
    WeightClaim,
)


# The tool never describes a listing with this word, so it is kept out of the text a
# report quotes as well.
NOT_SAID = "verified"


class _Stated(BaseModel):
    """Provenance every extracted claim carries."""

    model_config = ConfigDict(extra="forbid")

    found_in: str = Field(
        min_length=1,
        description=(
            "Where the claim appears: title, bullet points, spec table, description, or, for something "
            "printed on the product itself in an image, product photo."
        ),
    )
    quote: str | None = Field(
        default=None,
        description="The few characters that state the claim, e.g. '12000mAh'. Never a seller, store or brand name.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "How sure you are that you read this correctly. 1.0 for plain, sharp text. Below 0.8 when it is "
            "small, blurred, partly hidden or ambiguous."
        ),
    )

    @model_validator(mode="after")
    def _no_verified_wording(self):
        for name in ("found_in", "quote", "value"):
            text = getattr(self, name, None)
            if isinstance(text, str) and NOT_SAID in text.lower():
                raise ValueError(f"Leave the word '{NOT_SAID}' out of {name}. Give only the characters that state the claim.")
        return self

    def _provenance(self) -> dict:
        return {"found_in": self.found_in, "quote": self.quote, "confidence": self.confidence}


class StatedText(_Stated):
    value: str = Field(min_length=1)

    def to_claim(self) -> TextClaim:
        return TextClaim(value=self.value, **self._provenance())


class StatedChemistry(_Stated):
    value: Chemistry

    def to_claim(self) -> ChemistryClaim:
        return ChemistryClaim(value=self.value, **self._provenance())


class StatedCount(_Stated):
    value: float = Field(gt=0)

    def to_claim(self) -> NumberClaim:
        return NumberClaim(value=self.value, **self._provenance())


class StatedVoltage(_Stated):
    value: float = Field(gt=0)
    unit: Literal["V", "mV"] = Field(description="The unit as shown.")

    def to_claim(self) -> NumberClaim:
        return NumberClaim(value=units.convert(self.value, self.unit, units.TO_V), **self._provenance())


class StatedCapacity(_Stated):
    value: float = Field(gt=0)
    unit: Literal["mAh", "Ah"] = Field(description="The unit as shown.")

    def to_claim(self) -> NumberClaim:
        return NumberClaim(value=units.convert(self.value, self.unit, units.TO_MAH), **self._provenance())


class StatedEnergy(_Stated):
    value: float = Field(gt=0)
    unit: Literal["Wh", "mWh"] = Field(description="The unit as shown.")

    def to_claim(self) -> NumberClaim:
        return NumberClaim(value=units.convert(self.value, self.unit, units.TO_WH), **self._provenance())


class StatedShelfLife(_Stated):
    value: float = Field(gt=0)
    unit: Literal["years", "months"] = Field(description="The unit as shown.")

    def to_claim(self) -> NumberClaim:
        return NumberClaim(value=units.convert(self.value, self.unit, units.TO_YEARS), **self._provenance())


class StatedWeight(_Stated):
    value: float = Field(gt=0)
    unit: Literal["g", "kg", "mg", "oz", "lb"] = Field(description="The unit as shown.")
    kind: MeasurementKind = Field(description="package when described as package, shipping or box; otherwise product.")

    def to_claim(self) -> WeightClaim:
        return WeightClaim(
            value_g=units.convert(self.value, self.unit, units.TO_G), kind=self.kind, **self._provenance()
        )


class StatedDimensions(_Stated):
    """Outer dimensions. For a cylinder given as diameter x length, repeat the diameter."""

    length: float = Field(gt=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    unit: Literal["mm", "cm", "m", "in"] = Field(description="The unit as shown; one unit for all three.")
    kind: MeasurementKind = Field(description="package when described as package, shipping or box; otherwise product.")

    def to_claim(self) -> DimensionsClaim:
        return DimensionsClaim(
            length_mm=units.convert(self.length, self.unit, units.TO_MM),
            width_mm=units.convert(self.width, self.unit, units.TO_MM),
            height_mm=units.convert(self.height, self.unit, units.TO_MM),
            kind=self.kind,
            **self._provenance(),
        )


class ListingExtraction(BaseModel):
    """Everything the listing text or image itself states. Leave out what it does not state."""

    model_config = ConfigDict(extra="forbid")

    product_type: ProductType = Field(default=ProductType.UNKNOWN, description="What kind of product the listing is for.")
    chemistry: StatedChemistry | None = Field(default=None, description="Chemistry as stated in the title or description.")
    form_factors: list[StatedText] = Field(default_factory=list, description="Size codes such as 18650, 21700, AA, AAA.")
    cell_count: StatedCount | None = Field(
        default=None,
        description="Number of cells the stated capacity or energy covers: 1 for loose cells rated individually, N for an assembled pack.",
    )
    nominal_voltage: StatedVoltage | None = Field(
        default=None, description="Nominal voltage of the cell or pack. Not a USB, output or charging voltage."
    )
    capacity: StatedCapacity | None = Field(default=None, description="Labeled cell or pack capacity.")
    energy: StatedEnergy | None = Field(default=None, description="Energy as printed. Only if a Wh figure is shown.")
    output_capacity: StatedCapacity | None = Field(
        default=None, description="Rated or usable output capacity of a power bank."
    )
    weight: StatedWeight | None = None
    dimensions: StatedDimensions | None = None
    shelf_life: StatedShelfLife | None = None
    printed_codes: list[StatedText] = Field(
        default_factory=list,
        description="Designation codes printed on the product itself, e.g. R6, LR6, R03, LR03, FR6, HR6. One entry per code.",
    )
    printed_terms: list[StatedText] = Field(
        default_factory=list, description="Grade wording printed on the product itself, e.g. Heavy Duty, Super Heavy Duty."
    )

    def to_claims(self) -> Claims:
        def one(stated):
            return stated.to_claim() if stated is not None else None

        return Claims(
            product_type=self.product_type,
            chemistry=one(self.chemistry),
            form_factors=[s.to_claim() for s in self.form_factors],
            cell_count=one(self.cell_count),
            nominal_voltage_v=one(self.nominal_voltage),
            capacity_mah=one(self.capacity),
            energy_wh=one(self.energy),
            output_capacity_mah=one(self.output_capacity),
            weight=one(self.weight),
            dimensions=one(self.dimensions),
            shelf_life_years=one(self.shelf_life),
            printed_codes=[s.to_claim() for s in self.printed_codes],
            printed_terms=[s.to_claim() for s in self.printed_terms],
        )
