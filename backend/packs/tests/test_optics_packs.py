"""Unit tests for the projector, magnifier and monocular packs."""

from __future__ import annotations

import pytest

from claimcheck.models import CheckStatus, DimensionsClaim, MeasurementKind, NumberClaim, Routing, Verdict
from packs import magnifier_lens as mg
from packs import monocular_optics as mo
from packs import projector_resolution as pr
from packs.magnifier_lens import constants as MK
from packs.monocular_optics import constants as OK
from packs.projector_resolution import constants as PK
from packs.registry import PACKS

# ------------------------------------------------------------------------- constants


@pytest.mark.parametrize("module", [PK, MK, OK], ids=["projector", "magnifier", "monocular"])
def test_every_constant_has_a_citation(module):
    for c in module.all_constants():
        assert c.value > 0 and c.unit and c.description
        assert c.source.url.startswith("https://")
        assert c.source.title and c.source.publisher and c.source.locator
        assert len(c.source.quote) >= 20
        assert c.source.accessed == "2026-11-14"


def test_constant_counts():
    assert len(PK.all_constants()) == 8  # width and height of four named resolutions
    assert [c.key for c in MK.all_constants()] == ["near_point_distance_mm"]
    assert OK.all_constants() == []


def test_resolution_definitions_are_soft_and_cover_every_name():
    assert set(PK.RESOLUTIONS) == {r.value for r in pr.NamedResolution}
    assert not any(c.hard_bound for c in PK.all_constants())
    uhd = PK.RESOLUTIONS["4k"]
    assert (uhd.width_px.value, uhd.height_px.value) == (3840, 2160)


def test_the_registry_lists_the_three_packs():
    assert list(PACKS) == ["projector_resolution", "magnifier_lens", "monocular_optics"]
    for pack in PACKS.values():
        report = pack.evaluate(pack.claims_model())
        assert report.pack == pack.id and len(report.checks) == len(pack.checks)
        assert report.verdict is Verdict.NO_CHECKABLE_CLAIM and report.routing is Routing.NO_ACTION_NEEDED


# ------------------------------------------------------------------------- projector


def projector(headline=None, native=None, native_name=None, confidence=1.0) -> pr.ProjectorClaims:
    return pr.ProjectorClaims(
        claimed_resolution=pr.ResolutionNameClaim(value=headline, confidence=confidence) if headline else None,
        native_pixels=pr.PixelResolutionClaim(width_px=native[0], height_px=native[1]) if native else None,
        native_name=pr.ResolutionNameClaim(value=native_name) if native_name else None,
    )


def test_4k_headline_over_720p_native_is_a_flag_with_the_arithmetic():
    result = pr.check_native_resolution(projector("4k", (1280, 720)))
    assert result.status is CheckStatus.FLAG
    assert [s.text for s in result.steps] == [
        "Pixels in the headline resolution: 3,840 × 2,160 = 8,294,400 pixels",
        "Pixels in the native resolution: 1,280 × 720 = 921,600 pixels",
        "Headline pixels divided by native pixels: 8,294,400 ÷ 921,600 = 9 (> 1)",
    ]
    assert result.steps[-1].result == pytest.approx(9.0)
    assert "9× the native pixel count" in result.summary and "flag rather than a hard result" in result.summary
    report = pr.evaluate(projector("4k", (1280, 720)))
    assert (report.verdict, report.routing) == (Verdict.FLAG, Routing.NEEDS_HUMAN_REVIEW)


def test_projector_never_gives_a_hard_result():
    result = pr.check_native_resolution(projector("8k", (320, 240)))
    assert result.status is CheckStatus.FLAG


@pytest.mark.parametrize(
    "headline, native",
    [("1080p", (1920, 1080)), ("4k", (3840, 2160)), ("4k", (4096, 2160)), ("720p", (1920, 1080))],
)
def test_headline_at_or_below_native_passes(headline, native):
    assert pr.check_native_resolution(projector(headline, native)).status is CheckStatus.PASS


def test_native_given_by_name_uses_the_same_table():
    result = pr.check_native_resolution(projector("4k", native_name="1080p"))
    assert result.status is CheckStatus.FLAG
    assert result.steps[-1].result == pytest.approx(4.0)
    assert pr.check_native_resolution(projector("1080p", native_name="1080p")).status is CheckStatus.PASS


def test_projector_missing_data_is_not_assessed():
    assert pr.check_native_resolution(projector()).status is CheckStatus.NOT_ASSESSED
    result = pr.check_native_resolution(projector("4k"))
    assert result.status is CheckStatus.NOT_ASSESSED
    assert "native resolution" in result.not_assessed_reason
    # a headline claim that could not be tested goes to a person
    report = pr.evaluate(projector("4k"))
    assert (report.verdict, report.routing) == (Verdict.NO_CHECKABLE_CLAIM, Routing.NEEDS_HUMAN_REVIEW)


def test_projector_low_confidence_goes_to_a_person():
    report = pr.evaluate(projector("1080p", (1920, 1080), confidence=0.5))
    assert (report.verdict, report.routing) == (Verdict.NO_RED_FLAGS, Routing.NEEDS_HUMAN_REVIEW)


# ------------------------------------------------------------------------- magnifier


def magnifier(power=None, diameter=None, lens_type=None, confidence=1.0) -> mg.MagnifierClaims:
    return mg.MagnifierClaims(
        magnification=NumberClaim(value=power, confidence=confidence) if power else None,
        lens_diameter_mm=NumberClaim(value=diameter) if diameter else None,
        lens_type=mg.LensTypeClaim(value=lens_type) if lens_type else None,
    )


def test_30x_with_a_75_mm_lens_is_a_hard_result_with_the_arithmetic():
    result = mg.check_lens_diameter(magnifier(30, 75))
    assert result.status is CheckStatus.VIOLATED
    assert [s.text for s in result.steps] == [
        "Focal length implied by the claimed magnification: 250 mm ÷ 30 = 8.333 mm",
        "Widest lens with that focal length: 2 × 8.333 mm = 16.67 mm",
        "Comparison: 75 mm > 16.67 mm (4.5× the limit)",
        "Diameter above which the result is hard: 2 × 16.67 mm = 33.33 mm",
    ]
    assert result.steps[2].result == pytest.approx(4.5)
    assert [c.key for c in result.constants] == ["near_point_distance_mm"]
    # the uncited index and the margin are shown as assumptions, not as constants
    assert {q.name for q in result.inputs if q.origin == "assumption"} == {
        "Refractive index of the lens material",
        "Margin before a hard result",
    }
    assert any("no cited source" in a for a in result.assumptions)
    report = mg.evaluate(magnifier(30, 75))
    assert (report.verdict, report.routing) == (Verdict.IMPOSSIBLE, Routing.AUTO_RESOLVABLE)


@pytest.mark.parametrize("power, diameter", [(3, 75), (2, 100), (5, 50), (10, 21), (20, 12), (30, 16)])
def test_honest_magnifiers_pass(power, diameter):
    assert mg.check_lens_diameter(magnifier(power, diameter)).status is CheckStatus.PASS


def test_between_the_limit_and_the_margin_is_a_flag_not_a_hard_result():
    # 10x: limit 50 mm, hard above 100 mm
    assert mg.check_lens_diameter(magnifier(10, 50)).status is CheckStatus.PASS
    assert mg.check_lens_diameter(magnifier(10, 60)).status is CheckStatus.FLAG
    assert mg.check_lens_diameter(magnifier(10, 100)).status is CheckStatus.FLAG
    assert mg.check_lens_diameter(magnifier(10, 101)).status is CheckStatus.VIOLATED
    assert mg.HARD_RESULT_MARGIN == 2.0


def test_fresnel_and_missing_diameter_are_not_assessed():
    fresnel = mg.check_lens_diameter(magnifier(30, 75, lens_type="fresnel"))
    assert fresnel.status is CheckStatus.NOT_ASSESSED and "Fresnel" in fresnel.not_assessed_reason
    missing = mg.check_lens_diameter(magnifier(30))
    assert missing.status is CheckStatus.NOT_ASSESSED and "diameter" in missing.not_assessed_reason
    assert mg.check_lens_diameter(magnifier(diameter=75)).status is CheckStatus.NOT_ASSESSED
    report = mg.evaluate(magnifier(30))
    assert (report.verdict, report.routing) == (Verdict.NO_CHECKABLE_CLAIM, Routing.NEEDS_HUMAN_REVIEW)


def test_magnifier_low_confidence_hard_result_goes_to_a_person():
    report = mg.evaluate(magnifier(30, 75, confidence=0.5))
    assert (report.verdict, report.routing) == (Verdict.IMPOSSIBLE, Routing.NEEDS_HUMAN_REVIEW)


# ------------------------------------------------------------------------- monocular


def monocular(power=None, objective=None, body=None, kind="product", fine_power=None, fine_objective=None):
    return mo.MonocularClaims(
        magnification=NumberClaim(value=power) if power else None,
        objective_mm=NumberClaim(value=objective) if objective else None,
        body_dimensions=(
            DimensionsClaim(length_mm=body[0], width_mm=body[1], height_mm=body[2], kind=MeasurementKind(kind))
            if body
            else None
        ),
        fine_print_magnification=NumberClaim(value=fine_power) if fine_power else None,
        fine_print_objective_mm=NumberClaim(value=fine_objective) if fine_objective else None,
    )


def test_100_mm_objective_in_a_75_mm_body_is_a_flag_with_the_arithmetic():
    # the geometry is hard, but listed dimensions can be wrong, so the owner chose a flag
    result = mo.check_objective_fits_body(monocular(80, 100, (180, 75, 75)))
    assert result.status is CheckStatus.FLAG
    assert [s.text for s in result.steps] == [
        "Body width available to the lens: 75 mm (the second-longest listed side)",
        "Body width with the rounding tolerance: 75 mm × 1.03 = 77.25 mm",
        "Comparison: 100 mm > 77.25 mm (1.294× the limit)",
    ]
    assert "1.333× that width" in result.summary and "flag" in result.summary
    assert result.constants == []
    report = mo.evaluate(monocular(80, 100, (180, 75, 75)))
    assert (report.verdict, report.routing) == (Verdict.FLAG, Routing.NEEDS_HUMAN_REVIEW)


def test_the_second_longest_side_is_the_width_whatever_the_order():
    for body in [(180, 75, 60), (60, 180, 75), (75, 60, 180)]:
        result = mo.check_objective_fits_body(monocular(10, 70, body))
        assert result.status is CheckStatus.PASS and result.steps[0].result == 75


def test_objective_within_the_rounding_tolerance_passes():
    assert mo.check_objective_fits_body(monocular(12, 50, (150, 50, 50))).status is CheckStatus.PASS
    assert mo.check_objective_fits_body(monocular(12, 51, (150, 50, 50))).status is CheckStatus.PASS
    assert mo.check_objective_fits_body(monocular(12, 52, (150, 50, 50))).status is CheckStatus.FLAG


def test_package_dimensions_are_set_aside():
    result = mo.check_objective_fits_body(monocular(80, 100, (180, 75, 75), kind="package"))
    assert result.status is CheckStatus.NOT_ASSESSED and "package" in result.not_assessed_reason.lower()
    assert result.notes


def test_fine_print_contradiction_is_a_flag_with_the_ratio():
    result = mo.check_fine_print_consistency(monocular(80, 100, fine_power=12))
    assert result.status is CheckStatus.FLAG
    assert result.steps[0].text == "Headline magnification divided by the fine-print value: 80 ÷ 12 = 6.667 ×"
    assert "contradicts itself" in result.summary
    report = mo.evaluate(monocular(80, 100, fine_power=12))
    assert (report.verdict, report.routing) == (Verdict.FLAG, Routing.NEEDS_HUMAN_REVIEW)


def test_fine_print_objective_is_compared_too_and_agreement_passes():
    both = mo.check_fine_print_consistency(monocular(80, 100, fine_power=12, fine_objective=50))
    assert both.status is CheckStatus.FLAG and len(both.steps) == 2
    assert mo.check_fine_print_consistency(monocular(12, 50, fine_power=12, fine_objective=50)).status is CheckStatus.PASS


def test_both_monocular_checks_flag_and_the_report_names_both():
    report = mo.evaluate(monocular(80, 100, (180, 75, 75), fine_power=12))
    assert [c.status for c in report.checks] == [CheckStatus.FLAG, CheckStatus.FLAG]
    assert (report.verdict, report.routing) == (Verdict.FLAG, Routing.NEEDS_HUMAN_REVIEW)
    assert "cannot both be right" in report.verdict_reason and "contradicts itself" in report.verdict_reason


def test_the_monocular_pack_never_gives_a_hard_result():
    for check in mo.CHECKS:
        result = check(monocular(80, 100, (180, 75, 75), fine_power=12, fine_objective=50))
        assert result.status is CheckStatus.FLAG


def test_monocular_with_no_body_and_no_fine_print_is_not_assessed():
    report = mo.evaluate(monocular(80, 100))
    assert [c.status for c in report.checks] == [CheckStatus.NOT_ASSESSED, CheckStatus.NOT_ASSESSED]
    assert (report.verdict, report.routing) == (Verdict.NO_CHECKABLE_CLAIM, Routing.NEEDS_HUMAN_REVIEW)
    assert len(report.not_assessed) == 2
