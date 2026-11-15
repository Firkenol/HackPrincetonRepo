"""Every pack fixture gives its expected verdict, and the stored reports match the code."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claimcheck.models import CheckResult, CheckStatus
from packs.common import PackReport
from packs.fixtures_data import FIXTURES

EXPECTED_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "expected"
IDS = [f.id for f in FIXTURES]


def test_every_pack_has_an_honest_fixture_and_one_that_trips_the_rule():
    by_pack: dict[str, list[str]] = {}
    for f in FIXTURES:
        by_pack.setdefault(f.pack, []).append(f.verdict.value)
    assert sorted(by_pack.pop("power_budget")) == ["Impossible", "No red flags"]
    assert set(by_pack) == {"projector_resolution", "magnifier_lens", "monocular_optics"}
    for pack, verdicts in by_pack.items():
        # one that trips the rule, one honest listing, one with missing data
        assert len(verdicts) == 3, pack
        assert "No red flags" in verdicts and "No checkable claim" in verdicts, pack
        assert {"Impossible", "Flag"} & set(verdicts), pack


@pytest.mark.parametrize("fixture", FIXTURES, ids=IDS)
def test_listing_text_file_matches_the_fixture(fixture):
    path = EXPECTED_DIR.parent / f"pack_{fixture.id}.txt"
    assert path.exists(), "run: python packs/write_expected_reports.py"
    assert path.read_text(encoding="utf-8").strip() == fixture.listing_text.strip()


@pytest.mark.parametrize("fixture", FIXTURES, ids=IDS)
def test_fixture_verdict_and_routing(fixture):
    report = fixture.evaluate(fixture.claims)
    assert report.pack == fixture.pack
    assert report.verdict is fixture.verdict
    assert report.routing is fixture.routing


@pytest.mark.parametrize("fixture", FIXTURES, ids=IDS)
def test_expected_report_matches_the_code(fixture):
    path = EXPECTED_DIR / f"pack_{fixture.id}.json"
    assert path.exists(), "run: python packs/write_expected_reports.py"
    expected = json.loads(path.read_text(encoding="utf-8"))
    report = fixture.evaluate(fixture.claims)
    assert expected == json.loads(report.model_dump_json())
    # the stored file is itself a valid report for this pack's claims model
    assert PackReport[type(fixture.claims)].model_validate(expected).verdict is fixture.verdict


@pytest.mark.parametrize("fixture", FIXTURES, ids=IDS)
def test_report_wording_and_shape(fixture):
    report = fixture.evaluate(fixture.claims)
    data = json.loads(report.model_dump_json())
    assert data["schema_version"] == "1.0"
    assert data["verdict"] in {"Impossible", "Flag", "No red flags", "No checkable claim"}
    assert data["routing"] in {"auto-resolvable", "needs human review", "no action needed"}
    text = json.dumps(data).lower()
    for banned in ("verified", "seller", "fake", "counterfeit", "scam", "implausible"):
        assert banned not in text, banned
    for check in report.checks:
        assert isinstance(check, CheckResult)
        if check.status in (CheckStatus.PASS, CheckStatus.VIOLATED):
            # reproducible by hand: inputs, formula and arithmetic. A check that only compares
            # two values the listing states (the monocular pack) uses no constant.
            assert check.inputs and check.formula and check.steps, check.check_id
            assert check.constants or fixture.pack == "monocular_optics", check.check_id
            for citation in check.constants:
                assert citation.source_url.startswith("https://") and citation.quote
