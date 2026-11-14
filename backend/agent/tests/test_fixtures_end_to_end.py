"""All fixtures through run_listing, from text and from an image. Scripted model, no network.

The scripted model stands in for the four agents: it makes the tool calls a real
model is asked to make, with the claims a correct reading of the fixture gives. What
is tested is everything after the reading: delegation to the three subagents, unit
conversion, the checks, the verdict, the routing, and the shape of the report.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import claimcheck
from agent import run_listing
from agent.prompts import SUBAGENT_NAMES
from agent.tests.fake_model import TASK, ScriptedChatModel, full_script
from agent.tests.listings import LISTING_TEXT
from agent.tools import ASSEMBLE_REPORT, CHECK_TOOL_NAMES, RECORD_CLAIMS
from claimcheck.checks import ALL_CHECKS
from claimcheck.events import STREAM_EVENT_ADAPTER, FinalReportEvent
from claimcheck.models import CheckResult, Claims, EvidenceReport, Routing, Verdict
from tests.fixtures_data import BY_ID, FIXTURES

EXPECTED_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "expected"
FIXTURE_IDS = [fixture.id for fixture in FIXTURES]

# Only the leading bytes matter: the scripted model never decodes the picture.
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32

CHECK_IDS = [
    "label_consistency",
    "form_factor_bound",
    "dimension_bound",
    "weight_bound",
    "label_contradiction",
    "chemistry_mismatch",
]

# The verdict and routing each fixture must give, from SPEC.md and its amendments.
# Written out here so a change to tests/fixtures_data.py cannot quietly move them.
EXPECTED = {
    1: ("Impossible", "auto-resolvable"),
    2: ("No red flags", "no action needed"),
    3: ("Flag", "needs human review"),
    4: ("Flag", "needs human review"),
    5: ("No checkable claim", "no action needed"),
    6: ("No red flags", "no action needed"),
    7: ("No red flags", "no action needed"),
    8: ("No red flags", "no action needed"),
    9: ("No red flags", "no action needed"),
    # 10 to 20: real listings added 2026-11-14 (fixtures/README.md)
    10: ("No checkable claim", "no action needed"),
    11: ("No checkable claim", "needs human review"),
    12: ("No checkable claim", "needs human review"),
    13: ("No checkable claim", "needs human review"),
    14: ("No checkable claim", "no action needed"),
    15: ("No checkable claim", "no action needed"),
    16: ("No red flags", "no action needed"),
    17: ("No red flags", "no action needed"),
    18: ("No red flags", "no action needed"),
    19: ("No red flags", "no action needed"),
    20: ("No red flags", "no action needed"),
}


def drain(generator):
    events = []
    while True:
        try:
            events.append(next(generator))
        except StopIteration as stop:
            return events, stop.value


def listing_input(fixture_id: int, source: str):
    return LISTING_TEXT[fixture_id] if source == "text" else PNG


def run(fixture_id: int, source: str):
    model = ScriptedChatModel(script=full_script(BY_ID[fixture_id].claims))
    events, report = drain(run_listing(listing_input(fixture_id, source), model=model))
    return model, events, report


def test_there_are_twenty_fixtures_and_each_has_a_text_version():
    assert FIXTURE_IDS == list(range(1, 21))
    assert sorted(LISTING_TEXT) == FIXTURE_IDS
    assert sorted(EXPECTED) == FIXTURE_IDS


@pytest.mark.parametrize("source", ["text", "image"])
@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_fixture_gives_the_expected_verdict_and_routing(fixture_id, source):
    fixture = BY_ID[fixture_id]
    _, events, report = run(fixture_id, source)

    assert isinstance(events[-1], FinalReportEvent)
    assert events[-1].report == report
    assert (report.verdict.value, report.routing.value) == EXPECTED[fixture_id]
    assert report.verdict is fixture.verdict and report.routing is fixture.routing
    assert report.claims == fixture.claims
    # the same report as the frozen expected file
    expected = json.loads((EXPECTED_DIR / f"fixture_{fixture_id:02d}.json").read_text(encoding="utf-8"))
    assert json.loads(report.model_dump_json()) == expected


@pytest.mark.parametrize("source", ["text", "image"])
@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_fixture_report_validates_against_the_contract_models(fixture_id, source):
    _, events, report = run(fixture_id, source)

    # a strict round trip through JSON: every field has a contract type and no field is extra
    as_json = report.model_dump_json()
    assert EvidenceReport.model_validate_json(as_json, strict=True) == report
    assert report.schema_version == "1.0"
    assert isinstance(report.claims, Claims)
    assert isinstance(report.verdict, Verdict) and isinstance(report.routing, Routing)
    assert report.verdict_reason and report.routing_reason

    # always all six checks, in the fixed order, each the Phase 1 function's own result
    assert [check.check_id for check in report.checks] == CHECK_IDS
    for function, check in zip(ALL_CHECKS, report.checks, strict=True):
        assert isinstance(check, CheckResult)
        assert check == function(report.claims)
    not_assessed = [check for check in report.checks if check.status.value == "not_assessed"]
    assert len(report.not_assessed) == len(not_assessed)
    assert all(check.not_assessed_reason for check in not_assessed)

    # every event is a contract event and survives its own JSON
    for event in events:
        assert STREAM_EVENT_ADAPTER.validate_json(event.model_dump_json()) == event
    assert [event.seq for event in events] == list(range(len(events)))


@pytest.mark.parametrize("source", ["text", "image"])
@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_fixture_runs_through_all_three_subagents(fixture_id, source):
    _, events, _ = run(fixture_id, source)

    called = [(event.agent, event.tool) for event in events if event.type == "tool_call"]
    reader, checker, writer = SUBAGENT_NAMES
    assert called == [
        ("orchestrator", TASK),
        (reader, RECORD_CLAIMS),
        ("orchestrator", TASK),
        *((checker, name) for name in CHECK_TOOL_NAMES),
        ("orchestrator", TASK),
        (writer, ASSEMBLE_REPORT),
    ]
    assert all(event.ok for event in events if event.type == "tool_result")


@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_fixture_through_the_contract_entry_point(fixture_id, monkeypatch):
    import agent.runner as runner

    model = ScriptedChatModel(script=full_script(BY_ID[fixture_id].claims))
    monkeypatch.setattr(runner, "load_model", lambda: model)

    events, report = drain(claimcheck.run_listing(LISTING_TEXT[fixture_id]))
    assert isinstance(events[-1], FinalReportEvent) and events[-1].report == report
    assert (report.verdict.value, report.routing.value) == EXPECTED[fixture_id]


def test_fixture_9_reports_weight_and_dimensions_as_not_assessed():
    _, _, report = run(9, "text")
    status = {check.check_id: check.status.value for check in report.checks}
    assert status["label_consistency"] == "pass"
    assert status["dimension_bound"] == status["weight_bound"] == "not_assessed"


def test_fixture_1_is_decided_by_the_form_factor_and_sets_the_package_weight_aside():
    _, _, report = run(1, "text")
    status = {check.check_id: check.status.value for check in report.checks}
    assert status["form_factor_bound"] == "violated"
    assert status["weight_bound"] == status["dimension_bound"] == "not_assessed"
