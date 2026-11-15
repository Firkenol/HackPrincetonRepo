"""Check-pack fixtures as hand-entered claims, with expected verdicts.

power_budget has two: one honest listing and one impossible one. The projector,
magnifier and monocular packs have three each: one that trips the rule, one honest
listing and one with missing data. The listing text is written for these tests and
names no seller, store or brand. Keep ids stable: the expected report for each fixture
is fixtures/expected/pack_<id>.json and its listing text is fixtures/pack_<id>.txt.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from claimcheck.models import DimensionsClaim, MeasurementKind, NumberClaim, Routing, Verdict
from packs import magnifier_lens as mg
from packs import monocular_optics as mo
from packs import power_budget as pb
from packs import projector_resolution as pr
from packs.common import PackReport


@dataclass(frozen=True)
class PackFixture:
    id: str
    pack: str
    listing_text: str
    claims: BaseModel
    evaluate: Callable[[BaseModel], PackReport]
    verdict: Verdict
    routing: Routing


def _heater(watts: float) -> pb.PowerBudgetClaims:
    return pb.PowerBudgetClaims(
        output_power_w=pb.PowerClaim(value=watts, found_in="title", quote=f"{watts:g}W"),
        input_source=pb.InputSourceClaim(
            value=pb.InputSource.US_HOUSEHOLD_OUTLET, found_in="bullet points", quote="standard 120V wall outlet"
        ),
        energy_storage=pb.EnergyStorageClaim(value=pb.EnergyStorage.NONE, found_in="description", quote="corded"),
    )


def _projector(headline: str, native: tuple[float, float] | None) -> pr.ProjectorClaims:
    return pr.ProjectorClaims(
        claimed_resolution=pr.ResolutionNameClaim(value=headline, found_in="title", quote=headline.upper()),
        native_pixels=(
            pr.PixelResolutionClaim(
                width_px=native[0], height_px=native[1], found_in="spec table", quote=f"{native[0]:g} x {native[1]:g}"
            )
            if native
            else None
        ),
    )


def _magnifier(power: float, diameter_mm: float | None) -> mg.MagnifierClaims:
    return mg.MagnifierClaims(
        magnification=NumberClaim(value=power, found_in="title", quote=f"{power:g}X"),
        lens_diameter_mm=(
            NumberClaim(value=diameter_mm, found_in="spec table", quote=f"{diameter_mm:g} mm")
            if diameter_mm
            else None
        ),
    )


def _monocular(
    power: float, objective_mm: float, body: tuple[float, float, float] | None, fine_print_power: float | None = None
) -> mo.MonocularClaims:
    return mo.MonocularClaims(
        magnification=NumberClaim(value=power, found_in="title", quote=f"{power:g}x{objective_mm:g}"),
        objective_mm=NumberClaim(value=objective_mm, found_in="title", quote=f"{power:g}x{objective_mm:g}"),
        body_dimensions=(
            DimensionsClaim(
                length_mm=body[0],
                width_mm=body[1],
                height_mm=body[2],
                kind=MeasurementKind.PRODUCT,
                found_in="spec table",
                quote=f"{body[0]:g} x {body[1]:g} x {body[2]:g} mm",
            )
            if body
            else None
        ),
        fine_print_magnification=(
            NumberClaim(value=fine_print_power, found_in="spec table", quote=f"{fine_print_power:g}x")
            if fine_print_power
            else None
        ),
    )


FIXTURES: list[PackFixture] = [
    PackFixture(
        "power_budget_honest",
        pb.PACK_ID,
        "Portable Ceramic Space Heater, 1500W. Corded, plugs into any standard 120V wall outlet.",
        _heater(1500),
        pb.evaluate,
        Verdict.NO_RED_FLAGS,
        Routing.NO_ACTION_NEEDED,
    ),
    PackFixture(
        "power_budget_impossible",
        pb.PACK_ID,
        "Portable Ceramic Space Heater, 5000W. Corded, plugs into any standard 120V wall outlet.",
        _heater(5000),
        pb.evaluate,
        Verdict.IMPOSSIBLE,
        Routing.AUTO_RESOLVABLE,
    ),
    PackFixture(
        "projector_resolution_flag",
        pr.PACK_ID,
        "4K Home Theater Projector, Portable Movie Projector.\nSpecifications: Native resolution 1280 x 720. Supports 4K input.",
        _projector("4k", (1280, 720)),
        pr.evaluate,
        Verdict.FLAG,
        Routing.NEEDS_HUMAN_REVIEW,
    ),
    PackFixture(
        "projector_resolution_honest",
        pr.PACK_ID,
        "1080p Home Theater Projector.\nSpecifications: Native resolution 1920 x 1080.",
        _projector("1080p", (1920, 1080)),
        pr.evaluate,
        Verdict.NO_RED_FLAGS,
        Routing.NO_ACTION_NEEDED,
    ),
    PackFixture(
        "projector_resolution_missing",
        pr.PACK_ID,
        "4K Home Theater Projector, Portable Movie Projector. Bright picture, built-in speaker.",
        _projector("4k", None),
        pr.evaluate,
        Verdict.NO_CHECKABLE_CLAIM,
        Routing.NEEDS_HUMAN_REVIEW,
    ),
    PackFixture(
        "magnifier_lens_impossible",
        mg.PACK_ID,
        "30X Handheld Magnifying Glass for Reading.\nSpecifications: Lens diameter 75 mm. Glass lens.",
        _magnifier(30, 75),
        mg.evaluate,
        Verdict.IMPOSSIBLE,
        Routing.AUTO_RESOLVABLE,
    ),
    PackFixture(
        "magnifier_lens_honest",
        mg.PACK_ID,
        "3X Handheld Magnifying Glass for Reading.\nSpecifications: Lens diameter 75 mm. Glass lens.",
        _magnifier(3, 75),
        mg.evaluate,
        Verdict.NO_RED_FLAGS,
        Routing.NO_ACTION_NEEDED,
    ),
    PackFixture(
        "magnifier_lens_missing",
        mg.PACK_ID,
        "30X Handheld Magnifying Glass for Reading. Lightweight handle.",
        _magnifier(30, None),
        mg.evaluate,
        Verdict.NO_CHECKABLE_CLAIM,
        Routing.NEEDS_HUMAN_REVIEW,
    ),
    PackFixture(
        "monocular_optics_flag",
        mo.PACK_ID,
        "80x100 High Power Monocular Telescope.\nSpecifications: Product dimensions 180 x 75 x 75 mm. Actual magnification 12x.",
        _monocular(80, 100, (180, 75, 75), fine_print_power=12),
        mo.evaluate,
        Verdict.FLAG,
        Routing.NEEDS_HUMAN_REVIEW,
    ),
    PackFixture(
        "monocular_optics_honest",
        mo.PACK_ID,
        "12x50 Monocular Telescope.\nSpecifications: Product dimensions 150 x 60 x 55 mm.",
        _monocular(12, 50, (150, 60, 55)),
        mo.evaluate,
        Verdict.NO_RED_FLAGS,
        Routing.NO_ACTION_NEEDED,
    ),
    PackFixture(
        "monocular_optics_missing",
        mo.PACK_ID,
        "80x100 High Power Monocular Telescope. Waterproof, with phone holder.",
        _monocular(80, 100, None),
        mo.evaluate,
        Verdict.NO_CHECKABLE_CLAIM,
        Routing.NEEDS_HUMAN_REVIEW,
    ),
]

BY_ID = {f.id: f for f in FIXTURES}
