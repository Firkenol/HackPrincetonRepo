"""The test fixtures as hand-entered claims, with expected verdicts.

Fixtures 1 to 9 are the nine from SPEC.md. Fixtures 10 to 20 were added on
2026-11-14 from real listing screenshots stored in fixtures/ (see fixtures/README.md
for which screenshot belongs to which fixture). Later phases reuse this list: Phase 2
adds the text version of each listing, and Phase 3 the screenshots. Keep ids stable.
"""

from __future__ import annotations

from dataclasses import dataclass

from claimcheck.models import (
    Chemistry,
    ChemistryClaim,
    Claims,
    DimensionsClaim,
    MeasurementKind,
    NumberClaim,
    ProductType,
    Routing,
    TextClaim,
    Verdict,
    WeightClaim,
)

PRODUCT = MeasurementKind.PRODUCT
PACKAGE = MeasurementKind.PACKAGE


@dataclass(frozen=True)
class Fixture:
    id: int
    name: str
    claims: Claims
    verdict: Verdict
    routing: Routing


def _num(value: float, found_in: str = "title") -> NumberClaim:
    return NumberClaim(value=value, found_in=found_in)


def _chem(value: Chemistry) -> ChemistryClaim:
    return ChemistryClaim(value=value, found_in="title")


def _sizes(*codes: str) -> list[TextClaim]:
    return [TextClaim(value=code, found_in="title") for code in codes]


def _printed(*values: str) -> list[TextClaim]:
    return [TextClaim(value=value, found_in="product photo") for value in values]


def _pouch(volts: float, mah: float, wh: float, dims: tuple[float, float, float], grams: float, cells: int | None = None) -> Claims:
    """A single-cell or multi-cell lithium pouch pack as listed in bullet points, label values from the photo."""
    return Claims(
        product_type=ProductType.BATTERY_PACK,
        chemistry=_chem(Chemistry.LI_ION),
        cell_count=_num(cells) if cells else None,
        nominal_voltage_v=_num(volts),
        capacity_mah=_num(mah),
        energy_wh=_num(wh, "product photo"),
        dimensions=DimensionsClaim(length_mm=dims[0], width_mm=dims[1], height_mm=dims[2], kind=PRODUCT, found_in="bullet points"),
        weight=WeightClaim(value_g=grams, kind=PRODUCT, found_in="bullet points"),
    )


def _lipo(cells: int, volts: float, mah: float, wh: float, dims: tuple[float, float, float] | None, grams: float | None) -> Claims:
    return Claims(
        chemistry=_chem(Chemistry.LI_ION),
        cell_count=_num(cells),
        nominal_voltage_v=_num(volts, "label"),
        capacity_mah=_num(mah, "label"),
        energy_wh=_num(wh, "label"),
        dimensions=DimensionsClaim(length_mm=dims[0], width_mm=dims[1], height_mm=dims[2], kind=PRODUCT, found_in="spec table") if dims else None,
        weight=WeightClaim(value_g=grams, kind=PRODUCT, found_in="spec table") if grams else None,
    )


FIXTURES: list[Fixture] = [
    Fixture(
        1,
        "18650 Li-ion, 12,000 mAh at 3.7 V, package 0.600 kg in a 15 cm cube",
        Claims(
            chemistry=_chem(Chemistry.LI_ION),
            form_factors=_sizes("18650"),
            nominal_voltage_v=_num(3.7),
            capacity_mah=_num(12000),
            weight=WeightClaim(value_g=600, kind=PACKAGE, found_in="spec table"),
            dimensions=DimensionsClaim(length_mm=150, width_mm=150, height_mm=150, kind=PACKAGE, found_in="spec table"),
        ),
        Verdict.IMPOSSIBLE,
        Routing.AUTO_RESOLVABLE,
    ),
    Fixture(
        2,
        "AA Ni-MH, 700 mAh, 1.2 V",
        Claims(chemistry=_chem(Chemistry.NIMH), form_factors=_sizes("AA"), nominal_voltage_v=_num(1.2), capacity_mah=_num(700)),
        Verdict.NO_RED_FLAGS,
        Routing.NO_ACTION_NEEDED,
    ),
    Fixture(
        3,
        "Pack titled Alkaline; cells in photo read R6/R03 and Heavy Duty",
        Claims(
            chemistry=_chem(Chemistry.ALKALINE),
            form_factors=_sizes("AA", "AAA"),
            printed_codes=_printed("R6", "R03"),
            printed_terms=_printed("Heavy Duty"),
        ),
        Verdict.FLAG,
        Routing.NEEDS_HUMAN_REVIEW,
    ),
    Fixture(
        4,
        "Carbon AA/AAA pack claiming 10-year shelf life, no capacity",
        Claims(chemistry=_chem(Chemistry.ZINC_CARBON), form_factors=_sizes("AA", "AAA"), shelf_life_years=_num(10)),
        Verdict.FLAG,
        Routing.NEEDS_HUMAN_REVIEW,
    ),
    Fixture(
        5,
        "Carbon AA/AAA heavy duty multipack, no numeric claims",
        Claims(
            chemistry=_chem(Chemistry.ZINC_CARBON),
            form_factors=_sizes("AA", "AAA"),
            printed_codes=_printed("R6", "R03"),
            printed_terms=_printed("Heavy Duty"),
        ),
        Verdict.NO_CHECKABLE_CLAIM,
        Routing.NO_ACTION_NEEDED,
    ),
    Fixture(
        6,
        "2S LiPo, 7.4 V, 6200 mAh, 45.88 Wh, 139.5 x 47.5 x 26 mm, 315 g",
        _lipo(2, 7.4, 6200, 45.88, (139.5, 47.5, 26), 315),
        Verdict.NO_RED_FLAGS,
        Routing.NO_ACTION_NEEDED,
    ),
    Fixture(
        7,
        "3S LiPo, 11.1 V, 2200 mAh, 24.42 Wh, 106 x 33 x 23 mm, 179 g",
        _lipo(3, 11.1, 2200, 24.42, (106, 33, 23), 179),
        Verdict.NO_RED_FLAGS,
        Routing.NO_ACTION_NEEDED,
    ),
    Fixture(
        8,
        "2S LiPo, 7.4 V, 5200 mAh, 38.48 Wh, 25 x 47 x 139 mm, 307 g",
        _lipo(2, 7.4, 5200, 38.48, (25, 47, 139), 307),
        Verdict.NO_RED_FLAGS,
        Routing.NO_ACTION_NEEDED,
    ),
    Fixture(
        9,
        "2S LiPo, 7.4 V, 5200 mAh, 38.48 Wh, weight and dimensions not visible",
        _lipo(2, 7.4, 5200, 38.48, None, None),
        Verdict.NO_RED_FLAGS,
        Routing.NO_ACTION_NEEDED,
    ),
    # ---- added 2026-11-14 from screenshots of real listings (fixtures/README.md)
    Fixture(
        10,
        "AAA alkaline 4-pack, 1.5 V, cells printed LR03, no capacity",
        Claims(
            chemistry=_chem(Chemistry.ALKALINE),
            form_factors=_sizes("AAA"),
            nominal_voltage_v=_num(1.5),
            printed_codes=_printed("LR03"),
        ),
        Verdict.NO_CHECKABLE_CLAIM,
        Routing.NO_ACTION_NEEDED,
    ),
    Fixture(
        11,
        "9 V alkaline 4-pack, 6LR61, 7-year shelf life",
        Claims(
            chemistry=_chem(Chemistry.ALKALINE),
            form_factors=_sizes("9V"),
            nominal_voltage_v=_num(9),
            shelf_life_years=_num(7, "bullet points"),
            printed_codes=_printed("6LR61"),
        ),
        Verdict.NO_CHECKABLE_CLAIM,
        Routing.NEEDS_HUMAN_REVIEW,
    ),
    Fixture(
        12,
        "AAA alkaline 4-pack, 12-year shelf life",
        Claims(chemistry=_chem(Chemistry.ALKALINE), form_factors=_sizes("AAA"), shelf_life_years=_num(12, "product photo")),
        Verdict.NO_CHECKABLE_CLAIM,
        Routing.NEEDS_HUMAN_REVIEW,
    ),
    Fixture(
        13,
        "AAA alkaline 8-pack, 1.5 V, 10-year shelf life, cells printed LR03",
        Claims(
            chemistry=_chem(Chemistry.ALKALINE),
            form_factors=_sizes("AAA"),
            nominal_voltage_v=_num(1.5),
            shelf_life_years=_num(10),
            printed_codes=_printed("LR03"),
        ),
        Verdict.NO_CHECKABLE_CLAIM,
        Routing.NEEDS_HUMAN_REVIEW,
    ),
    Fixture(
        14,
        "6 V spring-terminal lantern battery, Super Heavy Duty, no chemistry or capacity stated",
        Claims(nominal_voltage_v=_num(6), printed_terms=_printed("Super Heavy Duty")),
        Verdict.NO_CHECKABLE_CLAIM,
        Routing.NO_ACTION_NEEDED,
    ),
    Fixture(
        15,
        "AAA carbon-zinc 4-pack, 1.5 V, packaging printed Super Heavy Duty",
        Claims(
            chemistry=ChemistryClaim(value=Chemistry.ZINC_CARBON, found_in="product photo"),
            form_factors=_sizes("AAA"),
            nominal_voltage_v=_num(1.5, "spec table"),
            printed_terms=_printed("Super Heavy Duty"),
        ),
        Verdict.NO_CHECKABLE_CLAIM,
        Routing.NO_ACTION_NEEDED,
    ),
    Fixture(
        16,
        "1S LiPo pouch, 3.7 V, 2000 mAh, 7.4 Wh, 34 x 10 x 50 mm, 35 g",
        _pouch(3.7, 2000, 7.4, (34, 10, 50), 35, cells=1),
        Verdict.NO_RED_FLAGS,
        Routing.NO_ACTION_NEEDED,
    ),
    Fixture(
        17,
        "3S LiPo, 11.1 V, 1300 mAh, 14.4 Wh, 72 x 36 x 23 mm, 119 g",
        _pouch(11.1, 1300, 14.4, (72, 36, 23), 119, cells=3),
        Verdict.NO_RED_FLAGS,
        Routing.NO_ACTION_NEEDED,
    ),
    Fixture(
        18,
        "LiPo pouch, 3.7 V, 3000 mAh, 11.1 Wh, 36 x 10 x 65 mm, 49 g",
        _pouch(3.7, 3000, 11.1, (36, 10, 65), 49),
        Verdict.NO_RED_FLAGS,
        Routing.NO_ACTION_NEEDED,
    ),
    Fixture(
        19,
        "LiPo pouch 4-pack, 3.7 V, 1000 mAh, 3.7 Wh, 30 x 8 x 42 mm, 18 g each",
        _pouch(3.7, 1000, 3.7, (30, 8, 42), 18),
        Verdict.NO_RED_FLAGS,
        Routing.NO_ACTION_NEEDED,
    ),
    Fixture(
        20,
        "LiPo pouch, 3.7 V, 1100 mAh typical, 4.1 Wh, 34.5 x 51 x 6.3 mm, 22 g",
        _pouch(3.7, 1100, 4.1, (34.5, 51, 6.3), 22),
        Verdict.NO_RED_FLAGS,
        Routing.NO_ACTION_NEEDED,
    ),
]

BY_ID = {f.id: f for f in FIXTURES}
