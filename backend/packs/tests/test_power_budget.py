"""Unit tests for the power-budget pack."""

from __future__ import annotations

import pytest

from claimcheck.models import CheckStatus, Routing, Verdict
from packs.power_budget import (
    EnergyStorage,
    EnergyStorageClaim,
    InputSource,
    InputSourceClaim,
    PowerBudgetClaims,
    PowerClaim,
    PowerKind,
    check_power_budget,
    evaluate,
)
from packs.power_budget import constants as K

NO_BATTERY = EnergyStorageClaim(value=EnergyStorage.NONE)
BATTERY = EnergyStorageClaim(value=EnergyStorage.BUILT_IN)
OUTLET = InputSource.US_HOUSEHOLD_OUTLET


def claims(watts, source, storage=NO_BATTERY, kind=PowerKind.RATED, confidence=1.0) -> PowerBudgetClaims:
    return PowerBudgetClaims(
        output_power_w=PowerClaim(value=watts, kind=kind, confidence=confidence) if watts else None,
        input_source=InputSourceClaim(value=source) if source else None,
        energy_storage=storage,
    )


# ------------------------------------------------------------------------- constants


def test_every_constant_has_a_citation():
    constants = K.all_constants()
    assert len(constants) == 6
    for c in constants:
        assert c.value > 0 and c.unit and c.description
        assert c.source.url.startswith("https://")
        assert c.source.title and c.source.publisher and c.source.locator
        assert len(c.source.quote) >= 20
        assert c.source.accessed == "2026-11-14"


def test_every_usb_source_has_a_limit_and_only_some_are_hard():
    usb = {s.value for s in InputSource} - {"us_household_outlet", "other"}
    assert set(K.USB_MAX_W) == usb
    hard = {key for key, c in K.USB_MAX_W.items() if c.hard_bound}
    assert hard == {"usb_pd", "usb_c"}
    assert K.US_OUTLET_VOLTAGE_V.hard_bound and K.US_OUTLET_CURRENT_A.hard_bound


# ------------------------------------------------------------------ household outlet


def test_outlet_limit_is_rated_voltage_times_rated_current():
    result = check_power_budget(claims(1500, OUTLET))
    assert result.status is CheckStatus.PASS
    assert result.steps[0].result == pytest.approx(125 * 20)
    assert result.steps[0].text == "Most power the outlet can supply: 125 V × 20 A = 2,500 W"
    assert [c.key for c in result.constants] == ["us_outlet_rated_voltage_v", "us_outlet_max_rated_current_a"]
    assert any("20 A rating is used" in a for a in result.assumptions)


@pytest.mark.parametrize("watts", [600, 1500, 1800, 1875, 2400, 2500])
def test_honest_outlet_products_pass(watts):
    # 1875 W is 15 A x 125 V (hair dryers); 2400 W is a full 20 A at 120 V
    assert check_power_budget(claims(watts, OUTLET)).status is CheckStatus.PASS


def test_outlet_claim_above_the_limit_is_a_hard_result_with_arithmetic():
    result = check_power_budget(claims(5000, OUTLET))
    assert result.status is CheckStatus.VIOLATED
    assert result.steps[-1].result == pytest.approx(2.0)
    assert "5,000 W > 2,500 W" in result.steps[-1].text
    assert "2× that limit" in result.summary
    report = evaluate(claims(5000, OUTLET))
    assert report.verdict is Verdict.IMPOSSIBLE and report.routing is Routing.AUTO_RESOLVABLE


def test_low_confidence_routes_an_impossible_verdict_to_a_person():
    report = evaluate(claims(5000, OUTLET, confidence=0.5))
    assert report.verdict is Verdict.IMPOSSIBLE
    assert report.routing is Routing.NEEDS_HUMAN_REVIEW


# ------------------------------------------------------------------------------- USB


@pytest.mark.parametrize(
    "source, watts, status",
    [
        (InputSource.USB_PD, 100, CheckStatus.PASS),
        (InputSource.USB_PD, 240, CheckStatus.PASS),
        (InputSource.USB_PD, 300, CheckStatus.VIOLATED),
        (InputSource.USB_C, 65, CheckStatus.PASS),
        (InputSource.USB_C, 1000, CheckStatus.VIOLATED),
        (InputSource.USB_BC_1_2, 7.5, CheckStatus.PASS),
        (InputSource.USB_BC_1_2, 12, CheckStatus.FLAG),
        (InputSource.USB_3, 4.5, CheckStatus.PASS),
        (InputSource.USB_3, 7.5, CheckStatus.PASS),
        (InputSource.USB_3, 10, CheckStatus.FLAG),
        (InputSource.USB_2, 2.5, CheckStatus.PASS),
        (InputSource.USB_2, 10, CheckStatus.FLAG),
    ],
)
def test_usb_limits(source, watts, status):
    assert check_power_budget(claims(watts, source)).status is status


def test_usb_pd_limit_is_cited_not_computed():
    result = check_power_budget(claims(300, InputSource.USB_PD))
    assert result.steps[0].result == 240
    assert result.constants[0].source_url == "https://www.usb.org/usb-charger-pd"
    assert "240W" in result.constants[0].quote
    assert result.steps[-1].result == pytest.approx(1.25)


def test_soft_usb_limit_never_gives_a_hard_result():
    # a 10 W warmer on a "USB 2.0" plug may simply expect a 2 A charger
    result = check_power_budget(claims(10, InputSource.USB_2))
    assert result.status is CheckStatus.FLAG
    assert "flag rather than a hard result" in result.summary
    assert result.constants[0].hard_bound is False
    report = evaluate(claims(10, InputSource.USB_2))
    assert report.verdict is Verdict.FLAG and report.routing is Routing.NEEDS_HUMAN_REVIEW


def test_lenient_assumptions_are_recorded():
    assert any("USB Power Delivery" in a for a in check_power_budget(claims(65, InputSource.USB_C)).assumptions)
    assert any("dual-lane" in a for a in check_power_budget(claims(4, InputSource.USB_3)).assumptions)
    assert check_power_budget(claims(100, InputSource.USB_PD)).assumptions == []


# ---------------------------------------------------------------------- not assessed


def test_battery_products_are_never_judged():
    # a power bank charging at 10 W can deliver 65 W
    result = check_power_budget(claims(65, InputSource.USB_2, storage=BATTERY))
    assert result.status is CheckStatus.NOT_ASSESSED
    assert "battery" in result.not_assessed_reason


def test_unknown_energy_storage_is_not_assessed():
    result = check_power_budget(claims(5000, OUTLET, storage=None))
    assert result.status is CheckStatus.NOT_ASSESSED
    assert "whether the product has a battery" in result.not_assessed_reason


def test_peak_power_is_not_assessed():
    # motor start-up and "peak horsepower" figures are momentary
    result = check_power_budget(claims(4800, OUTLET, kind=PowerKind.PEAK))
    assert result.status is CheckStatus.NOT_ASSESSED
    assert "peak" in result.not_assessed_reason
    assert result.inputs[0].name == "Output power (peak)"


def test_missing_or_unknown_input_is_not_assessed():
    assert check_power_budget(claims(5000, None)).status is CheckStatus.NOT_ASSESSED
    assert check_power_budget(claims(5000, InputSource.OTHER)).status is CheckStatus.NOT_ASSESSED
    assert check_power_budget(claims(None, OUTLET)).status is CheckStatus.NOT_ASSESSED


def test_untestable_power_claim_goes_to_a_person():
    report = evaluate(claims(5000, None))
    assert report.verdict is Verdict.NO_CHECKABLE_CLAIM
    assert report.routing is Routing.NEEDS_HUMAN_REVIEW
    assert len(report.not_assessed) == 1


def test_empty_listing_needs_no_action():
    report = evaluate(PowerBudgetClaims())
    assert report.verdict is Verdict.NO_CHECKABLE_CLAIM
    assert report.routing is Routing.NO_ACTION_NEEDED


def test_low_confidence_on_a_passing_listing_goes_to_a_person():
    report = evaluate(claims(1500, OUTLET, confidence=0.5))
    assert report.verdict is Verdict.NO_RED_FLAGS
    assert report.routing is Routing.NEEDS_HUMAN_REVIEW


def test_claims_model_rejects_unknown_fields():
    with pytest.raises(ValueError):
        PowerBudgetClaims(seller="x")
