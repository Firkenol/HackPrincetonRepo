"""Projector, magnifier and monocular listings through run_listing. Scripted model, no network.

The listing reader picks the category by the record tool it calls. The physics checker
asks list_checks which checks apply and runs them. The report is the pack's own,
computed in Python, and matches fixtures/expected/pack_<id>.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent import run_listing
from agent.prompts import LISTING_READER, PHYSICS_CHECKER
from agent.tests.fake_model import ScriptedChatModel, calls, checker_turns, reader_turns, say, writer_turns
from agent.tools import (
    ASSEMBLE_REPORT,
    CHECK_TOOL_NAMES,
    LIST_CHECKS,
    PACK_CHECK_TOOLS,
    PACK_RECORD_TOOLS,
    RECORD_CLAIMS,
    TOOLS_BY_AGENT,
)
from claimcheck.events import STREAM_EVENT_ADAPTER, FinalReportEvent
from claimcheck.models import PackEvidenceReport
from packs.fixtures_data import FIXTURES as ALL_PACK_FIXTURES
from packs.registry import PACKS

EXPECTED_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "expected"
FIXTURES = [f for f in ALL_PACK_FIXTURES if f.pack in PACKS]
IDS = [f.id for f in FIXTURES]
TASK = "task"


def drain(generator):
    events = []
    while True:
        try:
            events.append(next(generator))
        except StopIteration as stop:
            return events, stop.value


def _length(claim: dict) -> dict:
    return {**claim, "unit": "mm"}


def as_extraction(pack: str, claims) -> dict:
    """Pack claims written the way a model passes them to the pack's record tool."""
    data = claims.model_dump(mode="json", exclude_none=True)
    if pack == "projector_resolution":
        if "native_pixels" in data:
            px = dict(data["native_pixels"])
            data["native_pixels"] = {"width": px.pop("width_px"), "height": px.pop("height_px"), **px}
        return data
    if pack == "magnifier_lens":
        if "lens_diameter_mm" in data:
            data["lens_diameter"] = _length(data.pop("lens_diameter_mm"))
        return data
    for source, target in (("objective_mm", "objective"), ("fine_print_objective_mm", "fine_print_objective")):
        if source in data:
            data[target] = _length(data.pop(source))
    if "body_dimensions" in data:
        dims = dict(data["body_dimensions"])
        data["body_dimensions"] = {
            "length": dims.pop("length_mm"),
            "width": dims.pop("width_mm"),
            "height": dims.pop("height_mm"),
            "unit": "mm",
            **dims,
        }
    return data


def record(fixture):
    return calls((PACK_RECORD_TOOLS[fixture.pack], {"claims": as_extraction(fixture.pack, fixture.claims)}))


def pack_checks(pack: str):
    return calls(*((name, {}) for name in PACK_CHECK_TOOLS[pack]))


def full_script(fixture):
    return [
        *reader_turns(record(fixture)),
        *checker_turns(calls((LIST_CHECKS, {})), pack_checks(fixture.pack)),
        *writer_turns(),
        say(),
    ]


def run(fixture, script=None):
    model = ScriptedChatModel(script=script or full_script(fixture))
    events, report = drain(run_listing(fixture.listing_text, model=model))
    return model, events, report


def test_three_packs_with_three_fixtures_each():
    assert len(FIXTURES) == 9
    assert {f.pack for f in FIXTURES} == set(PACKS) == set(PACK_RECORD_TOOLS) == set(PACK_CHECK_TOOLS)


@pytest.mark.parametrize("fixture", FIXTURES, ids=IDS)
def test_pack_fixture_gives_the_expected_report(fixture):
    _, events, report = run(fixture)

    assert isinstance(events[-1], FinalReportEvent) and events[-1].report == report
    assert isinstance(report, PackEvidenceReport) and report.pack == fixture.pack
    assert report.verdict is fixture.verdict and report.routing is fixture.routing
    expected = json.loads((EXPECTED_DIR / f"pack_{fixture.id}.json").read_text(encoding="utf-8"))
    assert json.loads(report.model_dump_json()) == expected
    # the final event survives a trip through JSON as a pack report, not a battery report
    back = STREAM_EVENT_ADAPTER.validate_json(events[-1].model_dump_json())
    assert isinstance(back.report, PackEvidenceReport) and back.report == report


@pytest.mark.parametrize("fixture", FIXTURES, ids=IDS)
def test_pack_run_calls_the_category_tools_in_order(fixture):
    _, events, _ = run(fixture)
    called = [e for e in events if e.type == "tool_call"]
    assert [e.tool for e in called] == [
        TASK,
        PACK_RECORD_TOOLS[fixture.pack],
        TASK,
        LIST_CHECKS,
        *PACK_CHECK_TOOLS[fixture.pack],
        TASK,
        ASSEMBLE_REPORT,
    ]
    owner = {tool: agent for agent, tools in TOOLS_BY_AGENT.items() for tool in tools}
    assert all(e.agent == owner[e.tool] for e in called if e.tool != TASK)
    listed = next(e.result for e in events if e.type == "tool_result" and e.tool == LIST_CHECKS)
    assert listed == {"category": PACKS[fixture.pack].label, "checks": list(PACK_CHECK_TOOLS[fixture.pack])}
    # every check result in the trace is the one in the report
    results = {e.result["check_id"]: e.result for e in events if e.type == "tool_result" and e.tool in PACK_CHECK_TOOLS[fixture.pack]}
    _, _, report = run(fixture)
    assert results == {c.check_id: json.loads(c.model_dump_json()) for c in report.checks}


@pytest.mark.parametrize("fixture", FIXTURES, ids=IDS)
def test_pack_run_says_nothing_it_must_not(fixture):
    _, events, report = run(fixture)
    text = json.dumps([json.loads(e.model_dump_json()) for e in events]).lower()
    for banned in ("verified", "seller", "fake", "counterfeit", "scam", "implausible"):
        assert banned not in text, banned
    assert report.verdict.value in {"Impossible", "Flag", "No red flags", "No checkable claim"}
    assert report.routing.value in {"auto-resolvable", "needs human review", "no action needed"}


def test_report_is_computed_even_if_the_model_skips_the_checks_and_the_writer():
    fixture = next(f for f in FIXTURES if f.id == "magnifier_lens_impossible")
    _, events, report = run(fixture, script=[*reader_turns(record(fixture)), say()])
    expected = json.loads((EXPECTED_DIR / f"pack_{fixture.id}.json").read_text(encoding="utf-8"))
    assert json.loads(report.model_dump_json()) == expected


def test_a_battery_check_on_a_pack_listing_is_rejected_and_changes_nothing():
    fixture = next(f for f in FIXTURES if f.id == "projector_resolution_flag")
    script = [
        *reader_turns(record(fixture)),
        *checker_turns(calls((CHECK_TOOL_NAMES[0], {})), pack_checks(fixture.pack)),
        *writer_turns(),
        say(),
    ]
    _, events, report = run(fixture, script=script)
    wrong = next(e for e in events if e.type == "tool_result" and e.tool == CHECK_TOOL_NAMES[0])
    assert wrong.ok is False and wrong.result is None and wrong.agent == PHYSICS_CHECKER
    assert report.pack == fixture.pack and report.verdict is fixture.verdict
    assert [c.check_id for c in report.checks] == ["native_resolution"]


def test_a_pack_check_on_a_battery_listing_is_rejected():
    from agent.tests.fake_model import full_script as battery_script
    from agent.tests.listings import LISTING_TEXT
    from claimcheck.models import EvidenceReport
    from tests.fixtures_data import BY_ID

    claims = BY_ID[1].claims
    script = battery_script(claims)
    # turn 4 is the physics checker's: it tries a magnifier check before the six battery checks
    script[4] = calls(("check_lens_diameter", {}), *((name, {}) for name in CHECK_TOOL_NAMES))
    events, report = drain(run_listing(LISTING_TEXT[1], model=ScriptedChatModel(script=script)))
    wrong = next(e for e in events if e.type == "tool_result" and e.tool == "check_lens_diameter")
    assert wrong.ok is False
    assert isinstance(report, EvidenceReport) and report.verdict.value == "Impossible"


def test_recording_again_in_another_category_replaces_the_first():
    projector = next(f for f in FIXTURES if f.id == "projector_resolution_flag")
    magnifier = next(f for f in FIXTURES if f.id == "magnifier_lens_honest")
    script = [*reader_turns(record(projector), record(magnifier)), say()]
    _, _, report = run(magnifier, script=script)
    assert report.pack == "magnifier_lens" and report.verdict.value == "No red flags"


def test_units_are_converted_in_python():
    # 3 in is 76.2 mm: the model passes the value as shown and never converts it
    extraction = {
        "magnification": {"value": 30, "found_in": "title", "quote": "30X", "confidence": 1},
        "lens_diameter": {"value": 3, "unit": "in", "found_in": "spec table", "quote": "3 inch", "confidence": 1},
    }
    fixture = next(f for f in FIXTURES if f.id == "magnifier_lens_impossible")
    script = [*reader_turns(calls((PACK_RECORD_TOOLS["magnifier_lens"], {"claims": extraction}))), say()]
    _, events, report = run(fixture, script=script)
    assert report.claims["lens_diameter_mm"]["value"] == 76.2
    assert report.verdict.value == "Impossible"


@pytest.mark.parametrize(
    "extra",
    [{"seller": "Some Store"}, {"brand": "Some Brand"}, {"capacity": {"value": 1, "unit": "mAh", "found_in": "title", "confidence": 1}}],
    ids=["seller", "brand", "battery field"],
)
def test_a_pack_record_tool_rejects_unknown_fields(extra):
    fixture = next(f for f in FIXTURES if f.id == "monocular_optics_honest")
    bad = calls((PACK_RECORD_TOOLS[fixture.pack], {"claims": {**as_extraction(fixture.pack, fixture.claims), **extra}}))
    script = [*reader_turns(bad, record(fixture)), say()]
    _, events, report = run(fixture, script=script)
    first = next(e for e in events if e.type == "tool_result" and e.tool == PACK_RECORD_TOOLS[fixture.pack])
    assert first.ok is False and first.result is None and first.agent == LISTING_READER
    # as for a battery listing: nothing after the rejected call carries the name
    assert all("Some Store" not in e.model_dump_json() for e in events if e.seq > first.seq - 1)
    assert "Some Store" not in report.model_dump_json() and "Some Brand" not in report.model_dump_json()
    assert report.verdict is fixture.verdict


def test_the_word_verified_is_kept_out_of_a_pack_claim():
    fixture = next(f for f in FIXTURES if f.id == "projector_resolution_honest")
    extraction = as_extraction(fixture.pack, fixture.claims)
    extraction["claimed_resolution"]["quote"] = "Verified 1080p"
    bad = calls((PACK_RECORD_TOOLS[fixture.pack], {"claims": extraction}))
    _, events, report = run(fixture, script=[*reader_turns(bad, record(fixture)), say()])
    first = next(e for e in events if e.type == "tool_result" and e.tool == PACK_RECORD_TOOLS[fixture.pack])
    assert first.ok is False
    assert "verified" not in report.model_dump_json().lower()


def test_low_confidence_routes_to_a_person():
    fixture = next(f for f in FIXTURES if f.id == "magnifier_lens_honest")
    extraction = as_extraction(fixture.pack, fixture.claims)
    extraction["lens_diameter"]["confidence"] = 0.5
    script = [*reader_turns(calls((PACK_RECORD_TOOLS[fixture.pack], {"claims": extraction}))), say()]
    _, _, report = run(fixture, script=script)
    assert (report.verdict.value, report.routing.value) == ("No red flags", "needs human review")


def test_the_reader_is_offered_the_battery_tool_and_one_tool_per_pack():
    assert TOOLS_BY_AGENT[LISTING_READER] == (RECORD_CLAIMS, *PACK_RECORD_TOOLS.values())
    fixture = FIXTURES[0]
    model, _, _ = run(fixture)
    bound = set(model.tools_per_prompt[model.prompts.index(model.reader_prompts()[0])])
    assert set(TOOLS_BY_AGENT[LISTING_READER]) <= bound
    assert not set(TOOLS_BY_AGENT[PHYSICS_CHECKER]) & bound
