"""Shared data contract.

Claims is what the listing reader produces. CheckResult is what each check returns.
EvidenceReport is the main output. There is deliberately no field for a seller,
store or brand name anywhere in these models.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Verdict(str, Enum):
    IMPOSSIBLE = "Impossible"
    FLAG = "Flag"
    NO_RED_FLAGS = "No red flags"
    NO_CHECKABLE_CLAIM = "No checkable claim"


class Routing(str, Enum):
    AUTO_RESOLVABLE = "auto-resolvable"
    NEEDS_HUMAN_REVIEW = "needs human review"


class CheckStatus(str, Enum):
    PASS = "pass"
    VIOLATED = "violated"  # hard physical bound exceeded
    FLAG = "flag"  # contradiction or unusual claim
    NOT_ASSESSED = "not_assessed"


class Chemistry(str, Enum):
    LI_ION = "li-ion"  # all rechargeable lithium: Li-ion, LiPo, LiFePO4
    NIMH = "nimh"
    ALKALINE = "alkaline"
    ZINC_CARBON = "zinc-carbon"  # also sold as carbon zinc, zinc chloride, heavy duty
    NICD = "nicd"
    LITHIUM_PRIMARY = "lithium-primary"
    OTHER = "other"


CHEMISTRY_LABELS: dict[str, str] = {
    "li-ion": "lithium-ion",
    "nimh": "NiMH",
    "alkaline": "alkaline",
    "zinc-carbon": "zinc-carbon",
    "nicd": "NiCd",
    "lithium-primary": "primary lithium",
    "other": "another chemistry",
}


class MeasurementKind(str, Enum):
    PRODUCT = "product"  # the cell or pack itself
    PACKAGE = "package"  # shipping box or retail packaging; treated as unreliable


# ----------------------------------------------------------------------------- claims


class _Claim(BaseModel):
    """One extracted claim: where it was found and how sure the extractor is."""

    model_config = ConfigDict(extra="forbid")

    found_in: str = Field(
        default="manual entry",
        description="Where the claim appears: title, bullet points, spec table, product photo, description.",
    )
    quote: str | None = Field(
        default=None,
        description="The claim as shown, e.g. '12000mAh'. Never a seller, store or brand name.",
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class NumberClaim(_Claim):
    value: float = Field(gt=0)


class TextClaim(_Claim):
    value: str = Field(min_length=1)


class ChemistryClaim(_Claim):
    value: Chemistry


class WeightClaim(_Claim):
    value_g: float = Field(gt=0)
    kind: MeasurementKind


class DimensionsClaim(_Claim):
    """Outer dimensions. For a cylinder given as diameter x length, repeat the diameter."""

    length_mm: float = Field(gt=0)
    width_mm: float = Field(gt=0)
    height_mm: float = Field(gt=0)
    kind: MeasurementKind


class Claims(BaseModel):
    """Everything the listing itself states. Absent means not stated."""

    model_config = ConfigDict(extra="forbid")

    chemistry: ChemistryClaim | None = Field(default=None, description="Chemistry as stated in the title or description.")
    form_factors: list[TextClaim] = Field(default_factory=list, description="Size codes such as 18650, 21700, AA, AAA.")
    cell_count: NumberClaim | None = Field(
        default=None,
        description="Number of cells the stated capacity or energy covers: 1 for loose cells rated individually, N for an assembled pack.",
    )
    nominal_voltage_v: NumberClaim | None = Field(
        default=None, description="Nominal voltage of the cell or pack. Not a USB or output voltage."
    )
    capacity_mah: NumberClaim | None = Field(default=None, description="Labeled cell or pack capacity.")
    energy_wh: NumberClaim | None = Field(default=None, description="Energy as printed on the label.")
    output_capacity_mah: NumberClaim | None = Field(
        default=None,
        description="Rated or usable output capacity of a power bank. Recorded but never compared: conversion loss is normal.",
    )
    weight: WeightClaim | None = None
    dimensions: DimensionsClaim | None = None
    shelf_life_years: NumberClaim | None = None
    printed_codes: list[TextClaim] = Field(
        default_factory=list, description="Designation codes read off the product itself, e.g. R6, LR03."
    )
    printed_terms: list[TextClaim] = Field(
        default_factory=list, description="Grade wording read off the product itself, e.g. Heavy Duty."
    )


# ---------------------------------------------------------------------------- results


class Quantity(BaseModel):
    """One input to a check."""

    name: str
    value: float | str
    unit: str = ""
    origin: Literal["claim", "constant", "derived", "assumption"]
    found_in: str | None = None
    confidence: float | None = None


class Step(BaseModel):
    """One line of arithmetic, reproducible with a calculator."""

    label: str
    formula: str
    substitution: str
    result: float | None = None
    unit: str = ""
    text: str  # the whole line, ready to display


class Citation(BaseModel):
    """A constant used by a check, with its source."""

    key: str
    value: float
    unit: str
    description: str
    source_title: str
    source_publisher: str
    source_url: str
    locator: str
    quote: str
    accessed: str
    note: str = ""


class CheckResult(BaseModel):
    check_id: str
    title: str
    status: CheckStatus
    summary: str
    inputs: list[Quantity] = Field(default_factory=list)
    formula: str | None = None
    steps: list[Step] = Field(default_factory=list)
    constants: list[Citation] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    not_assessed_reason: str | None = None


class EvidenceReport(BaseModel):
    """The main output. A person with a calculator can reproduce every number in it."""

    claims: Claims
    checks: list[CheckResult]
    verdict: Verdict
    verdict_reason: str
    routing: Routing
    routing_reason: str
    assumptions: list[str] = Field(default_factory=list)
    not_assessed: list[str] = Field(default_factory=list)
