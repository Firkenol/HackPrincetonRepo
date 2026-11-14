"""Unit tests for the arithmetic helpers and each check's edge cases."""

from __future__ import annotations

import math

import pytest

from claimcheck import arithmetic as ar
from claimcheck import evaluate
from claimcheck.checks import (
    check_chemistry_mismatch,
    check_dimension_bound,
    check_form_factor_bound,
    check_label_consistency,
    check_label_contradiction,
    check_weight_bound,
    parse_iec_code,
    series_cells,
)
from claimcheck.models import (
    Chemistry,
    ChemistryClaim,
    CheckStatus,
    Claims,
    DimensionsClaim,
    MeasurementKind,
    NumberClaim,
    Routing,
    TextClaim,
    Verdict,
    WeightClaim,
)

PRODUCT, PACKAGE = MeasurementKind.PRODUCT, MeasurementKind.PACKAGE


def num(value, confidence=1.0):
    return NumberClaim(value=value, confidence=confidence)


def chem(value):
    return ChemistryClaim(value=value)


def sizes(*codes):
    return [TextClaim(value=c) for c in codes]


# ------------------------------------------------------------------------ arithmetic


def test_energy_and_volume_helpers():
    assert ar.energy_wh(7.4, 6200) == pytest.approx(45.88)
    assert ar.cylinder_volume_mm3(18.5, 65.3) == pytest.approx(math.pi * 9.25**2 * 65.3)
    assert ar.mm3_to_litres(ar.box_volume_mm3(139.5, 47.5, 26)) == pytest.approx(0.1722825)
    assert ar.g_to_kg(315) == pytest.approx(0.315)
    assert ar.relative_difference(45.88, 45.88) == 0


@pytest.mark.parametrize(
    "value, text",
    [(45.88, "45.88"), (7.4, "7.4"), (12000, "12,000"), (0.0175526, "0.01755"), (23.187, "23.19"), (266.31, "266.3"), (1321.0, "1,321"), (12.0, "12"),
     (1.847e-14, "0"), (0.00012345, "0.0001234"), (0.84, "0.84")],
)
def test_fmt(value, text):
    assert ar.fmt(value) == text


# ------------------------------------------------------------------- voltage sanity


@pytest.mark.parametrize(
    "volts, chemistry, cells",
    [(3.7, "li-ion", 1), (3.2, "li-ion", 1), (3.85, "li-ion", 1), (7.4, "li-ion", 2), (11.1, "li-ion", 3), (22.2, "li-ion", 6),
     (5.0, "li-ion", 0), (9.0, "li-ion", 0), (1.2, "nimh", 1), (1.5, "alkaline", 1), (9.0, "alkaline", 6), (3.7, None, None)],
)
def test_series_cells(volts, chemistry, cells):
    assert series_cells(volts, chemistry) == cells


# ---------------------------------------------------------------- label consistency


def test_label_mismatch_is_a_flag_not_a_hard_violation():
    claims = Claims(chemistry=chem(Chemistry.LI_ION), nominal_voltage_v=num(3.7), capacity_mah=num(50000), energy_wh=num(37))
    result = check_label_consistency(claims)
    assert result.status is CheckStatus.FLAG
    assert result.steps[1].result == pytest.approx(185.0)


def test_label_rounding_and_nominal_convention_pass():
    # 3.7 V x 20 Ah = 74 Wh, labeled 72 Wh by a maker using 3.6 V: 2.7% apart
    claims = Claims(chemistry=chem(Chemistry.LI_ION), nominal_voltage_v=num(3.7), capacity_mah=num(20000), energy_wh=num(72))
    assert check_label_consistency(claims).status is CheckStatus.PASS


def test_label_consistency_skips_output_voltage():
    # 5 V is a USB output, not a nominal lithium-ion voltage: must not be flagged
    claims = Claims(chemistry=chem(Chemistry.LI_ION), nominal_voltage_v=num(5), capacity_mah=num(20000), energy_wh=num(74))
    result = check_label_consistency(claims)
    assert result.status is CheckStatus.NOT_ASSESSED
    assert "not a nominal battery voltage" in result.not_assessed_reason


def test_power_bank_usable_output_below_cell_capacity_is_not_flagged():
    claims = Claims(
        chemistry=chem(Chemistry.LI_ION),
        nominal_voltage_v=num(3.7),
        capacity_mah=num(20000),
        energy_wh=num(74),
        output_capacity_mah=num(12000),
        weight=WeightClaim(value_g=420, kind=PRODUCT),
    )
    report = evaluate(claims)
    assert report.verdict is Verdict.NO_RED_FLAGS
    label = report.checks[0]
    assert any("conversion loss" in note for note in label.notes)


# ---------------------------------------------------------------- form-factor bound


def test_form_factor_uses_nominal_voltage_when_none_is_stated():
    claims = Claims(form_factors=sizes("18650"), capacity_mah=num(9900))
    result = check_form_factor_bound(claims)
    assert result.status is CheckStatus.VIOLATED  # 3.6 V x 9.9 Ah = 35.64 Wh > 23.19 Wh
    assert any("3.6 V is assumed" in a for a in result.assumptions)
    assert any("lithium-ion is assumed" in a for a in result.assumptions)


def test_honest_18650_and_21700_pass():
    best_18650 = Claims(chemistry=chem(Chemistry.LI_ION), form_factors=sizes("18650"), nominal_voltage_v=num(3.6), capacity_mah=num(3600))
    best_21700 = Claims(chemistry=chem(Chemistry.LI_ION), form_factors=sizes("21700"), nominal_voltage_v=num(3.6), capacity_mah=num(5800))
    assert check_form_factor_bound(best_18650).status is CheckStatus.PASS
    assert check_form_factor_bound(best_21700).status is CheckStatus.PASS


@pytest.mark.parametrize("mah, status", [(2850, CheckStatus.PASS), (1100, CheckStatus.PASS), (4700, CheckStatus.VIOLATED)])
def test_nimh_aa_ceiling(mah, status):
    claims = Claims(chemistry=chem(Chemistry.NIMH), form_factors=sizes("AA"), nominal_voltage_v=num(1.2), capacity_mah=num(mah))
    assert check_form_factor_bound(claims).status is status


def test_pack_built_from_cells_is_not_judged_as_one_cell():
    # 11.1 V means three cells in series; without a cell count the single-cell bound does not apply
    pack = Claims(chemistry=chem(Chemistry.LI_ION), form_factors=sizes("18650"), nominal_voltage_v=num(11.1), capacity_mah=num(5200))
    assert check_form_factor_bound(pack).status is CheckStatus.NOT_ASSESSED
    with_count = pack.model_copy(update={"cell_count": num(6)})
    assert check_form_factor_bound(with_count).status is CheckStatus.PASS  # 57.72 Wh against 6 cells


def test_form_factor_not_assessed_without_a_ceiling_for_the_chemistry():
    claims = Claims(chemistry=chem(Chemistry.ALKALINE), form_factors=sizes("AA"), nominal_voltage_v=num(1.5), capacity_mah=num(2800))
    result = check_form_factor_bound(claims)
    assert result.status is CheckStatus.NOT_ASSESSED
    assert "No vetted best-case ceiling" in result.not_assessed_reason


def test_unknown_size_code_is_not_assessed():
    claims = Claims(chemistry=chem(Chemistry.LI_ION), form_factors=sizes("26650"), capacity_mah=num(5000))
    assert check_form_factor_bound(claims).status is CheckStatus.NOT_ASSESSED


# ------------------------------------------------------- dimension and weight bounds


def test_weight_bound_violation_on_product_weight():
    # 3.6 V x 50 Ah = 180 Wh at 0.25 kg = 720 Wh/kg, above 504 Wh/kg
    claims = Claims(chemistry=chem(Chemistry.LI_ION), capacity_mah=num(50000), weight=WeightClaim(value_g=250, kind=PRODUCT))
    result = check_weight_bound(claims)
    assert result.status is CheckStatus.VIOLATED
    assert result.steps[-2].result == pytest.approx(720.0)
    assert evaluate(claims).routing is Routing.AUTO_RESOLVABLE


def test_package_weight_never_produces_a_hard_result():
    claims = Claims(chemistry=chem(Chemistry.LI_ION), capacity_mah=num(50000), weight=WeightClaim(value_g=10, kind=PACKAGE))
    assert check_weight_bound(claims).status is CheckStatus.NOT_ASSESSED
    assert evaluate(claims).verdict is Verdict.NO_CHECKABLE_CLAIM


def test_dimension_bound_violation_on_product_dimensions():
    # 3.6 V x 30 Ah = 108 Wh in 100 x 50 x 10 mm = 0.05 L is 2160 Wh/L, above 1321 Wh/L
    claims = Claims(
        chemistry=chem(Chemistry.LI_ION),
        capacity_mah=num(30000),
        dimensions=DimensionsClaim(length_mm=100, width_mm=50, height_mm=10, kind=PRODUCT),
    )
    result = check_dimension_bound(claims)
    assert result.status is CheckStatus.VIOLATED
    assert result.steps[-2].result == pytest.approx(2160.0)


def test_product_dimensions_that_do_not_match_the_size_code_are_set_aside():
    claims = Claims(
        chemistry=chem(Chemistry.LI_ION),
        form_factors=sizes("18650"),
        nominal_voltage_v=num(3.7),
        capacity_mah=num(3000),
        dimensions=DimensionsClaim(length_mm=1, width_mm=1, height_mm=1, kind=PRODUCT),
    )
    result = check_dimension_bound(claims)
    assert result.status is CheckStatus.NOT_ASSESSED
    assert "placeholder" in result.not_assessed_reason
    assert evaluate(claims).verdict is Verdict.NO_RED_FLAGS


def test_unknown_chemistry_uses_the_most_lenient_ceiling():
    claims = Claims(energy_wh=num(45.88), weight=WeightClaim(value_g=315, kind=PRODUCT))
    result = check_weight_bound(claims)
    assert result.status is CheckStatus.PASS
    assert any("most lenient" in a for a in result.assumptions)


def test_larger_of_label_energy_and_capacity_energy_is_tested():
    claims = Claims(
        chemistry=chem(Chemistry.LI_ION),
        nominal_voltage_v=num(3.7),
        capacity_mah=num(50000),
        energy_wh=num(37),
        weight=WeightClaim(value_g=250, kind=PRODUCT),
    )
    result = check_weight_bound(claims)
    assert result.status is CheckStatus.VIOLATED  # 185 Wh at 0.25 kg = 740 Wh/kg
    assert any("larger figure is tested" in note for note in result.notes)


# ---------------------------------------------------------------------- IEC parsing


@pytest.mark.parametrize(
    "text, expected",
    [("R6", ("R6", "zinc-carbon")), ("R03", ("R03", "zinc-carbon")), ("LR6", ("LR6", "alkaline")), ("lr03", ("LR03", "alkaline")),
     ("IEC-LR6", ("LR6", "alkaline")), ("HR6", ("HR6", "nimh")), ("FR6", ("FR6", "lithium-primary")), ("6F22", ("6F22", "zinc-carbon")),
     ("6LR61", ("6LR61", "alkaline")), ("AA", None), ("18650", None), ("ICR18650", None), ("Heavy Duty", None)],
)
def test_parse_iec_code(text, expected):
    assert parse_iec_code(text) == expected


def test_matching_markings_pass_the_contradiction_check():
    claims = Claims(chemistry=chem(Chemistry.ALKALINE), printed_codes=[TextClaim(value="LR6")])
    assert check_label_contradiction(claims).status is CheckStatus.PASS


def test_contradiction_check_needs_both_sides():
    assert check_label_contradiction(Claims(printed_codes=[TextClaim(value="R6")])).status is CheckStatus.NOT_ASSESSED
    assert check_label_contradiction(Claims(chemistry=chem(Chemistry.ALKALINE))).status is CheckStatus.NOT_ASSESSED


# ---------------------------------------------------------------------- shelf life


def test_shelf_life_within_published_data_passes():
    claims = Claims(chemistry=chem(Chemistry.ZINC_CARBON), shelf_life_years=num(3))
    assert check_chemistry_mismatch(claims).status is CheckStatus.PASS
    assert evaluate(claims).verdict is Verdict.NO_RED_FLAGS


def test_alkaline_ten_year_claim_is_not_flagged():
    claims = Claims(chemistry=chem(Chemistry.ALKALINE), shelf_life_years=num(10))
    assert check_chemistry_mismatch(claims).status is CheckStatus.NOT_ASSESSED


# ------------------------------------------------------------------------- routing


def test_low_extraction_confidence_routes_an_impossible_verdict_to_a_person():
    claims = Claims(
        chemistry=chem(Chemistry.LI_ION),
        form_factors=sizes("18650"),
        nominal_voltage_v=num(3.7),
        capacity_mah=num(12000, confidence=0.4),
    )
    report = evaluate(claims)
    assert report.verdict is Verdict.IMPOSSIBLE
    assert report.routing is Routing.NEEDS_HUMAN_REVIEW
    assert "low confidence" in report.routing_reason


def test_empty_listing_has_no_checkable_claim():
    report = evaluate(Claims())
    assert report.verdict is Verdict.NO_CHECKABLE_CLAIM
    assert len(report.not_assessed) == 6
