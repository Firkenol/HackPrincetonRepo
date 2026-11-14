"""Guards the frozen contract: event models, the entry point and the expected reports."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claimcheck import evaluate, replay_claims, run_listing
from claimcheck.events import STREAM_EVENT_ADAPTER, ErrorEvent, FinalReportEvent, to_sse
from claimcheck.models import EvidenceReport
from tests.fixtures_data import BY_ID, FIXTURES

EXPECTED_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "expected"


@pytest.mark.parametrize("fixture", FIXTURES, ids=[f"fixture_{f.id}" for f in FIXTURES])
def test_expected_report_matches_the_code(fixture):
    path = EXPECTED_DIR / f"fixture_{fixture.id:02d}.json"
    assert path.exists(), "run: python scripts/write_expected_reports.py"
    expected = json.loads(path.read_text(encoding="utf-8"))
    assert expected == json.loads(evaluate(fixture.claims).model_dump_json())
    # the stored file is itself a valid report
    assert EvidenceReport.model_validate(expected).verdict is fixture.verdict


def _drain(generator):
    events = []
    while True:
        try:
            events.append(next(generator))
        except StopIteration as stop:
            return events, stop.value


def test_replay_yields_ordered_events_and_returns_the_report():
    events, report = _drain(replay_claims(BY_ID[1].claims, run_id="run-1"))
    assert [e.seq for e in events] == list(range(len(events)))
    assert {e.run_id for e in events} == {"run-1"}
    assert [e.type for e in events].count("tool_call") == 6
    assert [e.type for e in events].count("tool_result") == 6
    calls = {e.call_id for e in events if e.type == "tool_call"}
    assert calls == {e.call_id for e in events if e.type == "tool_result"}
    assert isinstance(events[-1], FinalReportEvent)
    assert events[-1].report == report == evaluate(BY_ID[1].claims)


def test_every_event_round_trips_through_json():
    events, _ = _drain(replay_claims(BY_ID[6].claims))
    events.append(ErrorEvent(run_id="r", seq=99, message="Model call failed."))
    for event in events:
        parsed = STREAM_EVENT_ADAPTER.validate_json(event.model_dump_json())
        assert type(parsed) is type(event)
        assert parsed == event


def test_sse_framing():
    event = ErrorEvent(run_id="r", seq=0, message="x")
    frame = to_sse(event)
    assert frame.startswith("event: error\ndata: {") and frame.endswith("}\n\n")


def test_run_listing_is_reserved_for_phase_2():
    with pytest.raises(NotImplementedError):
        run_listing("18650 12000mAh 3.7V")
