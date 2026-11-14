"""Phase 1 acceptance: all nine fixtures give the expected verdict from hand-entered claims."""

from __future__ import annotations

import json

import pytest

from claimcheck import evaluate
from claimcheck.checks import (
    DIMENSION_BOUND,
    FORM_FACTOR_BOUND,
    LABEL_CONSISTENCY,
    LABEL_CONTRADICTION,
    CHEMISTRY_MISMATCH,
    WEIGHT_BOUND,
)
from claimcheck.models import CheckStatus, Routing, Verdict
from tests.fixtures_data import BY_ID, FIXTURES


def _status(report, check_id):
    return next(c for c in report.checks if c.check_id == check_id)


@pytest.mark.parametrize("fixture", FIXTURES, ids=[f"fixture_{f.id}" for f in FIXTURES])
def test_fixture_verdict_and_routing(fixture):
    report = evaluate(fixture.claims)
    assert report.verdict is fixture.verdict, report.verdict_reason
    assert report.routing is fixture.routing, report.routing_reason


def test_fixture_1_fails_on_form_factor_and_notes_package_weight():
    report = evaluate(BY_ID[1].claims)
    form = _status(report, FORM_FACTOR_BOUND)
    assert form.status is CheckStatus.VIOLATED
    # 3.7 V x 12 Ah = 44.4 Wh against 1321 Wh/L x 0.017553 L = 23.19 Wh
    assert form.steps[1].result == pytest.approx(44.4)
    assert form.steps[-2].result == pytest.approx(23.19, abs=0.01)

    weight = _status(report, WEIGHT_BOUND)
    assert weight.status is CheckStatus.NOT_ASSESSED
    assert any("placeholder" in note for note in weight.notes)
    dims = _status(report, DIMENSION_BOUND)
    assert dims.status is CheckStatus.NOT_ASSESSED
    assert any("placeholder" in note for note in dims.notes)


def test_fixture_2_passes_on_form_factor():
    report = evaluate(BY_ID[2].claims)
    assert _status(report, FORM_FACTOR_BOUND).status is CheckStatus.PASS


def test_fixture_3_is_caught_by_label_contradiction():
    report = evaluate(BY_ID[3].claims)
    check = _status(report, LABEL_CONTRADICTION)
    assert check.status is CheckStatus.FLAG
    assert "R6" in check.summary and "R03" in check.summary and "Heavy Duty" in check.summary


def test_fixture_4_is_a_soft_flag_from_shelf_life():
    report = evaluate(BY_ID[4].claims)
    assert _status(report, CHEMISTRY_MISMATCH).status is CheckStatus.FLAG
    assert not any(c.status is CheckStatus.VIOLATED for c in report.checks)


def test_fixture_5_consistent_markings_do_not_count_as_a_checked_claim():
    report = evaluate(BY_ID[5].claims)
    assert _status(report, LABEL_CONTRADICTION).status is CheckStatus.PASS
    assert report.verdict is Verdict.NO_CHECKABLE_CLAIM


@pytest.mark.parametrize(
    "fixture_id, wh_per_l, wh_per_kg",
    [(6, 266.3, 145.65), (7, 303.5, 136.4), (8, 235.6, 125.3)],
)
def test_lipo_fixtures_pass_all_three_numeric_checks(fixture_id, wh_per_l, wh_per_kg):
    report = evaluate(BY_ID[fixture_id].claims)
    assert _status(report, LABEL_CONSISTENCY).status is CheckStatus.PASS
    dims, weight = _status(report, DIMENSION_BOUND), _status(report, WEIGHT_BOUND)
    assert dims.status is CheckStatus.PASS and weight.status is CheckStatus.PASS
    assert dims.steps[-2].result == pytest.approx(wh_per_l, abs=0.1)
    assert weight.steps[-2].result == pytest.approx(wh_per_kg, abs=0.1)


def test_fixture_9_reports_weight_and_dimensions_as_not_assessed():
    report = evaluate(BY_ID[9].claims)
    assert _status(report, LABEL_CONSISTENCY).status is CheckStatus.PASS
    assert _status(report, DIMENSION_BOUND).status is CheckStatus.NOT_ASSESSED
    assert _status(report, WEIGHT_BOUND).status is CheckStatus.NOT_ASSESSED
    assert any("Dimensions are not stated" in line for line in report.not_assessed)
    assert any("Weight is not stated" in line for line in report.not_assessed)


@pytest.mark.parametrize("fixture", FIXTURES, ids=[f"fixture_{f.id}" for f in FIXTURES])
def test_report_wording_and_shape(fixture):
    report = evaluate(fixture.claims)
    data = json.loads(report.model_dump_json())
    assert data["verdict"] in {"Impossible", "Flag", "No red flags", "No checkable claim"}
    assert data["routing"] in {"auto-resolvable", "needs human review"}
    assert len(data["checks"]) == 6
    text = json.dumps(data).lower()
    for banned in ("verified", "seller", "fake", "counterfeit", "scam"):
        assert banned not in text
    # every assessed arithmetic check shows its working
    for check in report.checks:
        if check.status in (CheckStatus.PASS, CheckStatus.VIOLATED) and check.check_id != LABEL_CONTRADICTION:
            assert check.steps, check.check_id
    assert report.routing is Routing.AUTO_RESOLVABLE or report.routing is Routing.NEEDS_HUMAN_REVIEW
