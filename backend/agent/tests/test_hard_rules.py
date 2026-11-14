"""The hard rules from SPEC.md and CLAUDE.md, tested through run_listing. Scripted model, no network.

Each section is one rule. The scripted model plays a model that behaves, and then one
that does not: it writes its own verdict, names a seller, or says "verified". The
rule holds if nothing it wrote can reach an event or the report.
"""

from __future__ import annotations

import json
import re

import pytest
from langchain_core.messages import AIMessage

import agent.runner as runner_module
import agent.tools as tools_module
from agent import run_listing
from agent.extraction import ListingExtraction
from agent.prompts import LISTING_READER, PHYSICS_CHECKER, REPORT_WRITER
from agent.runner import MSG_CHECKS_FAILED, MSG_FAILED
from agent.tests.fake_model import (
    ScriptedChatModel,
    all_checks,
    as_extraction,
    calls,
    checker_turns,
    delegate,
    full_script,
    reader_turns,
    record,
    say,
    writer_turns,
)
from agent.tests.listings import LISTING_TEXT
from agent.tools import ASSEMBLE_REPORT, CHECK_TOOL_NAMES, RECORD_CLAIMS, RunState, build_tools
from claimcheck.checks import ALL_CHECKS
from claimcheck.events import ErrorEvent, FinalReportEvent
from claimcheck.models import Claims, EvidenceReport, Routing, Verdict
from claimcheck.policy import MIN_CONFIDENCE
from tests.fixtures_data import BY_ID, FIXTURES

FIXTURE_IDS = [fixture.id for fixture in FIXTURES]
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32

VERDICTS = {"Impossible", "Flag", "No red flags", "No checkable claim"}
ROUTINGS = {"auto-resolvable", "needs human review", "no action needed"}


def drain(generator):
    events = []
    while True:
        try:
            events.append(next(generator))
        except StopIteration as stop:
            return events, stop.value


def run_script(script, listing=LISTING_TEXT[1]):
    model = ScriptedChatModel(script=script)
    events, report = drain(run_listing(listing, model=model))
    return events, report


def run_claims(claims: Claims, listing=LISTING_TEXT[1]):
    return run_script(full_script(claims), listing)


def everything(events) -> str:
    """All the JSON a caller of run_listing receives."""
    return "\n".join(event.model_dump_json() for event in events)


def with_confidence(claims: Claims, confidence: float) -> Claims:
    """The same claims with every claim's confidence set to the given value."""

    def walk(node):
        if isinstance(node, dict):
            return {key: confidence if key == "confidence" else walk(value) for key, value in node.items()}
        if isinstance(node, list):
            return [walk(item) for item in node]
        return node

    return Claims.model_validate(walk(claims.model_dump(mode="json")))


def values_of(key: str, text: str) -> set[str]:
    """Every string value stored under the given JSON key, at any depth."""
    return set(re.findall(rf'"{key}"\s*:\s*"([^"]*)"', text))


# A model that ignores its instructions wherever it can write free text: prose beside
# tool calls, task descriptions, and every closing sentence.
SELLER = "Zentrovolt Outlet"
ROGUE_PROSE = f"Verified! Sold by {SELLER}. My verdict: Definitely fake. Routing: escalate to legal. 31337 Wh."


def rogue_script(claims: Claims) -> list[AIMessage]:
    def loud(turn: AIMessage) -> AIMessage:
        return AIMessage(content=ROGUE_PROSE, tool_calls=turn.tool_calls)

    return [
        delegate(LISTING_READER, ROGUE_PROSE),
        loud(record(claims)),
        say(ROGUE_PROSE),
        delegate(PHYSICS_CHECKER, ROGUE_PROSE),
        loud(all_checks()),
        say(ROGUE_PROSE),
        delegate(REPORT_WRITER, ROGUE_PROSE),
        loud(calls((ASSEMBLE_REPORT, {}))),
        say(ROGUE_PROSE),
        say(ROGUE_PROSE),
    ]


# ------------------------------------------- only the four verdicts and three routings


def test_the_contract_has_exactly_four_verdicts_and_three_routings():
    assert {verdict.value for verdict in Verdict} == VERDICTS
    assert {routing.value for routing in Routing} == ROUTINGS


@pytest.mark.parametrize("source", ["text", "image"])
@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_only_the_fixed_verdict_and_routing_strings_appear(fixture_id, source):
    listing = LISTING_TEXT[fixture_id] if source == "text" else PNG
    events, report = run_claims(BY_ID[fixture_id].claims, listing)

    assert report.verdict.value in VERDICTS and report.routing.value in ROUTINGS
    # wherever a verdict or routing is stored in what the caller receives
    text = everything(events)
    assert values_of("verdict", text) == {report.verdict.value}
    assert values_of("routing", text) == {report.routing.value}
    # the one trace line that states them
    summary = next(e.summary for e in events if e.type == "tool_result" and e.tool == ASSEMBLE_REPORT)
    assert summary == f"{report.verdict.value}, {report.routing.value}."


def test_the_fixtures_between_them_give_every_verdict_and_every_routing():
    seen = [run_claims(fixture.claims)[1] for fixture in FIXTURES]
    assert {report.verdict.value for report in seen} == VERDICTS
    assert {report.routing.value for report in seen} == ROUTINGS


@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_a_model_cannot_supply_its_own_verdict_or_routing(fixture_id):
    fixture = BY_ID[fixture_id]
    events, report = run_script(rogue_script(fixture.claims))

    assert report.verdict is fixture.verdict and report.routing is fixture.routing
    text = everything(events)
    assert values_of("verdict", text) <= VERDICTS and values_of("routing", text) <= ROUTINGS
    for made_up in ("Definitely fake", "escalate to legal", "31337"):
        assert made_up not in text


def test_the_report_tool_takes_no_verdict_from_the_model():
    tools = {tool.name: tool for tool in build_tools(RunState())}
    # no arguments at all: nothing a model passes can change a check or the report
    for name in (*CHECK_TOOL_NAMES, ASSEMBLE_REPORT):
        assert tools[name].args == {}, name


def test_a_label_where_wh_is_not_v_times_ah_is_a_flag_not_impossible():
    claims = BY_ID[6].claims
    wrong = claims.model_copy(update={"energy_wh": claims.energy_wh.model_copy(update={"value": 60.0})})
    _, report = run_claims(wrong)
    assert report.verdict.value == "Flag" and report.routing.value == "needs human review"


# ------------------------------------------------------------ "verified" never appears


@pytest.mark.parametrize("source", ["text", "image"])
@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_verified_never_appears_in_events_or_report(fixture_id, source):
    listing = LISTING_TEXT[fixture_id] if source == "text" else PNG
    events, report = run_claims(BY_ID[fixture_id].claims, listing)
    assert "verif" not in everything(events).lower()
    assert "verif" not in report.model_dump_json().lower()


@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_verified_never_appears_even_when_every_model_says_it(fixture_id):
    events, report = run_script(rogue_script(BY_ID[fixture_id].claims))
    assert isinstance(events[-1], FinalReportEvent)
    assert "verif" not in everything(events).lower()


def test_verified_never_appears_when_the_listing_itself_says_it():
    listing = "VERIFIED genuine capacity! " + LISTING_TEXT[1] + "\nCapacity verified by our lab."
    events, _ = run_claims(BY_ID[1].claims, listing)
    assert "verif" not in everything(events).lower()


@pytest.mark.parametrize("field", ["quote", "found_in", "value"])
def test_a_claim_that_carries_the_word_verified_is_rejected(field):
    stated = {"value": "18650", "found_in": "title", "quote": "18650", "confidence": 1.0}
    stated[field] = "Verified 18650"
    bad = calls((RECORD_CLAIMS, {"claims": {"form_factors": [stated]}}))
    script = [*reader_turns(bad, record(BY_ID[1].claims)), *checker_turns(), *writer_turns(), say()]
    events, report = run_script(script)

    first = next(e for e in events if e.type == "tool_result")
    assert first.tool == RECORD_CLAIMS and first.ok is False and first.result is None
    assert report.claims == BY_ID[1].claims
    assert "verif" not in report.model_dump_json().lower()
    # the rejected call is shown in the trace as the model made it, and nowhere else
    assert [e.seq for e in events if "verif" in e.model_dump_json().lower()] == [first.seq - 1]


def test_fixed_trace_wording_never_says_verified():
    fixed = [value for name, value in vars(runner_module).items() if name.startswith("MSG_")]
    fixed += list(runner_module._STEP_ON_DELEGATION.values())
    assert fixed and all("verif" not in message.lower() for message in fixed)


# ------------------------------------------------- no seller or store name in a report


NAME_WORDS = ("seller", "store", "brand", "vendor", "shop", "merchant", "sold_by", "manufacturer")


def _objects(schema: dict):
    """Every object definition in a JSON schema, with its name."""
    yield "root", schema
    yield from schema.get("$defs", {}).items()


@pytest.mark.parametrize("model", [ListingExtraction, EvidenceReport], ids=["extraction", "report"])
def test_no_model_has_a_field_for_a_seller_store_or_brand(model):
    for name, definition in _objects(model.model_json_schema()):
        for field in definition.get("properties", {}):
            assert not any(word in field.lower() for word in NAME_WORDS), f"{name}.{field}"


def test_the_extraction_rejects_unknown_fields_at_every_level():
    for name, definition in _objects(ListingExtraction.model_json_schema()):
        if definition.get("type") == "object":
            assert definition.get("additionalProperties") is False, name


@pytest.mark.parametrize(
    "extra",
    [
        {"seller": SELLER},
        {"store_name": SELLER},
        {"capacity": {"value": 12000, "unit": "mAh", "found_in": "title", "confidence": 1.0, "seller": SELLER}},
        {"form_factors": [{"value": "18650", "found_in": "title", "confidence": 1.0, "brand": SELLER}]},
    ],
    ids=["seller", "store_name", "inside-a-claim", "inside-a-list"],
)
def test_a_seller_name_passed_as_a_field_is_rejected_and_never_stored(extra):
    bad = calls((RECORD_CLAIMS, {"claims": {**as_extraction(BY_ID[1].claims), **extra}}))
    script = [*reader_turns(bad, record(BY_ID[1].claims)), *checker_turns(), *writer_turns(), say()]
    events, report = run_script(script)

    first = next(e for e in events if e.type == "tool_result")
    assert first.tool == RECORD_CLAIMS and first.ok is False and first.result is None
    assert report.claims == BY_ID[1].claims
    assert SELLER not in report.model_dump_json()
    # nothing after the rejected call carries the name: not a tool result, not the report
    assert all(SELLER not in e.model_dump_json() for e in events if e.seq > first.seq - 1)


def test_a_rejected_call_leaves_nothing_recorded():
    bad = calls((RECORD_CLAIMS, {"claims": {**as_extraction(BY_ID[1].claims), "seller": SELLER}}))
    events, report = run_script([*reader_turns(bad), say()])
    assert report is None and isinstance(events[-1], ErrorEvent)


@pytest.mark.parametrize("source", ["text", "image"])
@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_a_seller_name_in_the_listing_does_not_reach_events_or_report(fixture_id, source):
    if source == "text":
        listing = f"Visit the {SELLER} Store\n{LISTING_TEXT[fixture_id]}\nSold by: {SELLER}\nShips from: {SELLER}"
    else:
        listing = PNG
    events, report = run_script(rogue_script(BY_ID[fixture_id].claims), listing)

    assert isinstance(events[-1], FinalReportEvent)
    text = everything(events)
    assert SELLER not in text and "Zentrovolt" not in text
    assert SELLER not in report.model_dump_json()


def test_the_listing_text_itself_is_never_copied_into_an_event():
    events, _ = run_claims(BY_ID[7].claims, LISTING_TEXT[7])
    text = everything(events)
    assert "Quadcopter" not in text and "RC Airplane" not in text


# ------------------------------------------- low-confidence extraction goes to a person


JUST_BELOW = MIN_CONFIDENCE - 0.01


@pytest.mark.parametrize("source", ["text", "image"])
@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_a_low_confidence_extraction_routes_to_human_review(fixture_id, source):
    fixture = BY_ID[fixture_id]
    listing = LISTING_TEXT[fixture_id] if source == "text" else PNG
    events, report = run_claims(with_confidence(fixture.claims, JUST_BELOW), listing)

    assert isinstance(events[-1], FinalReportEvent)
    assert report.routing.value == "needs human review"
    assert report.verdict is fixture.verdict  # confidence changes who looks, not the finding
    assert report.routing_reason


@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_confidence_at_the_threshold_keeps_the_fixture_routing(fixture_id):
    fixture = BY_ID[fixture_id]
    _, report = run_claims(with_confidence(fixture.claims, MIN_CONFIDENCE))
    assert report.routing is fixture.routing


def test_one_low_confidence_claim_is_enough():
    claims = BY_ID[6].claims
    unsure = claims.model_copy(update={"weight": claims.weight.model_copy(update={"confidence": 0.3})})
    _, report = run_claims(unsure)
    assert report.verdict.value == "No red flags" and report.routing.value == "needs human review"
    assert report.claims.weight.confidence == 0.3


def test_an_impossible_result_read_with_low_confidence_is_not_auto_resolved():
    _, report = run_claims(with_confidence(BY_ID[1].claims, 0.5))
    assert report.verdict.value == "Impossible" and report.routing.value == "needs human review"


def test_a_claim_without_a_confidence_is_rejected():
    extraction = as_extraction(BY_ID[2].claims)
    del extraction["capacity"]["confidence"]
    bad = calls((RECORD_CLAIMS, {"claims": extraction}))
    events, report = run_script([*reader_turns(bad), say()])
    assert next(e for e in events if e.type == "tool_result").ok is False
    assert report is None


# ------------------------------------- a check that raises ends with an error, not a report


def _only_ends_in_error(events, report, message):
    assert report is None
    assert isinstance(events[-1], ErrorEvent) and events[-1].message == message
    assert [e.type for e in events].count("error") == 1
    assert not any(e.type == "final_report" for e in events)
    assert [e.seq for e in events] == list(range(len(events)))
    assert "boom" not in everything(events)


def _checks_with_one_raising(position: int):
    real = ALL_CHECKS[position]

    def broken(claims):
        raise ZeroDivisionError("boom: internal detail 12345")

    broken.__name__ = real.__name__
    return tuple(broken if index == position else check for index, check in enumerate(ALL_CHECKS))


@pytest.mark.parametrize("position", range(len(ALL_CHECKS)), ids=list(CHECK_TOOL_NAMES))
def test_a_check_that_raises_ends_with_an_error_event_and_returns_none(position, monkeypatch):
    monkeypatch.setattr(tools_module, "ALL_CHECKS", _checks_with_one_raising(position))
    events, report = run_script(full_script(BY_ID[6].claims))
    _only_ends_in_error(events, report, MSG_FAILED)


def test_a_failure_while_assembling_the_report_ends_with_an_error_event(monkeypatch):
    def broken(claims):
        raise RuntimeError("boom")

    monkeypatch.setattr(tools_module, "evaluate", broken)
    events, report = run_script(full_script(BY_ID[6].claims))
    _only_ends_in_error(events, report, MSG_FAILED)


def test_a_check_that_raises_after_the_model_skipped_the_checks_still_ends_with_an_error(monkeypatch):
    def broken(claims):
        raise RuntimeError("boom")

    monkeypatch.setattr(runner_module, "evaluate", broken)
    events, report = run_script([*reader_turns(record(BY_ID[6].claims)), say()])
    _only_ends_in_error(events, report, MSG_CHECKS_FAILED)


def test_a_check_that_raises_fails_through_the_contract_entry_point_too(monkeypatch):
    import claimcheck

    monkeypatch.setattr(tools_module, "ALL_CHECKS", _checks_with_one_raising(1))
    monkeypatch.setattr(runner_module, "load_model", lambda: ScriptedChatModel(script=full_script(BY_ID[1].claims)))
    events, report = drain(claimcheck.run_listing(LISTING_TEXT[1]))
    _only_ends_in_error(events, report, MSG_FAILED)


def test_a_failed_run_never_leaks_a_report_through_an_earlier_event(monkeypatch):
    monkeypatch.setattr(tools_module, "ALL_CHECKS", _checks_with_one_raising(5))
    events, _ = run_script(full_script(BY_ID[1].claims))
    assert not values_of("verdict", everything(events))


# ------------------------------------------------------------- the model never does math


def test_usable_output_below_cell_capacity_is_not_flagged():
    # a power bank: 10000 mAh cells at 3.7 V, 37 Wh, 6000 mAh rated output
    extraction = {
        "product_type": "power_bank",
        "chemistry": {"value": "li-ion", "found_in": "spec table", "confidence": 1.0},
        "nominal_voltage": {"value": 3.7, "unit": "V", "found_in": "spec table", "confidence": 1.0},
        "capacity": {"value": 10000, "unit": "mAh", "found_in": "title", "confidence": 1.0},
        "energy": {"value": 37, "unit": "Wh", "found_in": "spec table", "confidence": 1.0},
        "output_capacity": {"value": 6000, "unit": "mAh", "found_in": "spec table", "confidence": 1.0},
    }
    script = [*reader_turns(calls((RECORD_CLAIMS, {"claims": extraction}))), *checker_turns(), *writer_turns(), say()]
    events, report = run_script(script)

    assert report.verdict.value == "No red flags" and report.routing.value == "no action needed"
    assert report.claims.output_capacity_mah.value == 6000
    assert not any(check.status.value in ("flag", "violated") for check in report.checks)


def test_every_number_in_a_check_result_event_comes_from_the_python_check():
    events, report = run_claims(BY_ID[6].claims)
    by_tool = {e.tool: e.result for e in events if e.type == "tool_result" and e.tool in CHECK_TOOL_NAMES}
    for check, reported in zip(ALL_CHECKS, report.checks, strict=True):
        assert by_tool[check.__name__] == json.loads(check(BY_ID[6].claims).model_dump_json())
        assert by_tool[check.__name__] == json.loads(reported.model_dump_json())
