"""Orchestrator and subagent wiring, tool calls and report assembly, tested with a scripted model. No network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

import agent.model as model_module
from agent import run_listing
from agent.runner import MSG_EMPTY, MSG_FAILED, MSG_NO_CLAIMS, MSG_NO_MODEL
from agent.prompts import LISTING_READER, PHYSICS_CHECKER, REPORT_WRITER
from agent.tests.fake_model import (
    FULL_SCRIPT_TURNS,
    TASK,
    ScriptedChatModel,
    all_checks,
    calls,
    checker_turns,
    full_script,
    reader_turns,
    record,
    say,
    writer_turns,
)
from agent.tests.listings import LISTING_TEXT
from agent.tools import ASSEMBLE_REPORT, CHECK_TOOL_NAMES, LOOKUP_FORM_FACTOR, RECORD_CLAIMS, TOOL_NAMES, TOOLS_BY_AGENT
from claimcheck.checks import ALL_CHECKS
from claimcheck.events import STREAM_EVENT_ADAPTER, ErrorEvent, FinalReportEvent
from claimcheck.models import CheckResult
from tests.fixtures_data import BY_ID

EXPECTED_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "expected"
PHASE_2_FIXTURES = [1, 2, 6, 7, 8, 9]
TEXT_FIXTURES = [*PHASE_2_FIXTURES, *range(10, 21)]  # every fixture that has a text version


def drain(generator):
    events = []
    while True:
        try:
            events.append(next(generator))
        except StopIteration as stop:
            return events, stop.value


def run(fixture_id: int, script=None):
    model = ScriptedChatModel(script=script or full_script(BY_ID[fixture_id].claims))
    events, report = drain(run_listing(LISTING_TEXT[fixture_id], model=model))
    return model, events, report


# ------------------------------------------------------------------ acceptance


@pytest.mark.parametrize("fixture_id", TEXT_FIXTURES)
def test_fixture_text_gives_expected_verdict_and_routing(fixture_id):
    fixture = BY_ID[fixture_id]
    _, events, report = run(fixture_id)

    assert isinstance(events[-1], FinalReportEvent)
    assert events[-1].report == report
    assert report.verdict is fixture.verdict
    assert report.routing is fixture.routing
    # same report, byte for byte, as the frozen expected file
    expected = json.loads((EXPECTED_DIR / f"fixture_{fixture_id:02d}.json").read_text(encoding="utf-8"))
    assert json.loads(report.model_dump_json()) == expected


def test_fixture_9_reports_weight_and_dimensions_as_not_assessed():
    _, _, report = run(9)
    status = {c.check_id: c.status.value for c in report.checks}
    assert status["label_consistency"] == "pass"
    assert status["dimension_bound"] == status["weight_bound"] == "not_assessed"
    assert len(report.not_assessed) >= 2


def test_fixture_1_sets_the_package_weight_aside():
    _, _, report = run(1)
    status = {c.check_id: c.status.value for c in report.checks}
    assert status["form_factor_bound"] == "violated"
    assert status["weight_bound"] == "not_assessed"


# ---------------------------------------------------------------------- events


def test_events_follow_the_contract():
    _, events, _ = run(6)

    assert [e.seq for e in events] == list(range(len(events)))
    assert len({e.run_id for e in events}) == 1
    assert events[0].type == "agent_step"

    called = [e for e in events if e.type == "tool_call"]
    returned = [e for e in events if e.type == "tool_result"]
    assert [e.tool for e in called] == [TASK, RECORD_CLAIMS, TASK, *CHECK_TOOL_NAMES, TASK, ASSEMBLE_REPORT]
    assert {e.call_id for e in called} == {e.call_id for e in returned}
    assert all(e.ok for e in returned)
    # a tool's result never comes before its call
    position = {e.call_id: e.seq for e in called}
    assert all(e.seq > position[e.call_id] for e in returned)

    for event in events:
        assert STREAM_EVENT_ADAPTER.validate_json(event.model_dump_json()) == event


def test_check_tool_results_are_the_phase_1_check_results():
    _, events, report = run(6)
    results = {e.tool: e.result for e in events if e.type == "tool_result" and e.tool in CHECK_TOOL_NAMES}
    # the six checks run in parallel, so results may arrive in any order
    assert set(results) == set(CHECK_TOOL_NAMES)
    for check, reported in zip(ALL_CHECKS, report.checks, strict=True):
        from_tool = CheckResult.model_validate(results[check.__name__])
        assert from_tool == reported == check(BY_ID[6].claims)


def test_assemble_report_result_matches_the_final_report():
    _, events, report = run(1)
    result = next(e.result for e in events if e.type == "tool_result" and e.tool == ASSEMBLE_REPORT)
    assert result["verdict"] == report.verdict.value == "Impossible"
    assert result["routing"] == report.routing.value == "auto-resolvable"


def test_every_event_names_the_agent_it_came_from():
    _, events, _ = run(6)

    owner = {tool: agent for agent, tools in TOOLS_BY_AGENT.items() for tool in tools}
    for event in events:
        if event.type in ("tool_call", "tool_result"):
            assert event.agent == owner.get(event.tool, "orchestrator"), event.tool
    assert events[0].agent == "orchestrator" and events[-1].agent == "orchestrator"

    # each subagent starts with one step line, straight after the orchestrator delegates to it
    steps = [e.agent for e in events if e.type == "agent_step"]
    assert steps == ["orchestrator", LISTING_READER, PHYSICS_CHECKER, REPORT_WRITER]
    for index, event in enumerate(events):
        if event.type == "tool_call" and event.tool == TASK:
            assert events[index + 1].type == "agent_step"
            assert events[index + 1].agent == event.args["subagent_type"]


def test_delegation_events_show_the_subagent_and_nothing_a_model_wrote():
    _, events, _ = run(6)
    delegations = [e for e in events if e.type == "tool_call" and e.tool == TASK]
    assert [e.args for e in delegations] == [
        {"subagent_type": name} for name in (LISTING_READER, PHYSICS_CHECKER, REPORT_WRITER)
    ]
    finished = [e for e in events if e.type == "tool_result" and e.tool == TASK]
    assert len(finished) == 3
    assert all(e.result is None and e.summary == "The subagent finished." for e in finished)


# ---------------------------------------------------------------------- wiring


def _system(prompt) -> str:
    return " ".join(str(prompt[0].text).split())


def test_there_are_three_subagents_and_each_has_only_its_own_tools():
    model, _, _ = run(7)
    assert len(model.prompts) == FULL_SCRIPT_TURNS

    orchestrator = model.tools_per_prompt[0]
    assert TASK in orchestrator and not set(TOOL_NAMES) & set(orchestrator)
    assert all(name in _system(model.orchestrator_prompts()[0]) for name in TOOLS_BY_AGENT)

    for agent, own in TOOLS_BY_AGENT.items():
        bound = next(tools for tools in model.tools_per_prompt if own[0] in tools)
        assert set(own) <= set(bound), agent
        assert not (set(TOOL_NAMES) - set(own)) & set(bound), agent
        assert TASK not in bound, agent  # a subagent cannot delegate


def test_each_subagent_has_its_own_prompt_and_its_own_skill():
    model, _, _ = run(7)
    expected = {
        RECORD_CLAIMS: ("Extraction is your only job", "reading-battery-listings"),
        CHECK_TOOL_NAMES[0]: ("you never calculate", "running-claim-checks"),
        ASSEMBLE_REPORT: ("You add nothing to it", "assembling-evidence-reports"),
    }
    all_skills = {skill for _, skill in expected.values()}
    for tool, (phrase, skill) in expected.items():
        system = _system(model.prompts_with_tool(tool)[0])
        assert phrase in system, tool
        assert skill in system, tool
        # the skills folder of another subagent is not offered
        assert not any(f"/{other}/SKILL.md" in system for other in all_skills - {skill}), tool
    orchestrator = _system(model.orchestrator_prompts()[0])
    assert not any(f"/{skill}/SKILL.md" in orchestrator for skill in all_skills)


def test_only_the_listing_reader_is_shown_the_listing():
    model, _, _ = run(7)
    listing = LISTING_TEXT[7].strip()
    for prompt, tools in zip(model.prompts, model.tools_per_prompt, strict=True):
        text = "".join(str(m.content) for m in prompt[1:])
        if RECORD_CLAIMS in tools:
            assert listing in text
            assert prompt[1].type == "human" and prompt[2].type == "human"  # the task, then the listing
        else:
            assert listing not in text and "2200mAh" not in text


def test_model_sees_tool_output_on_its_next_turn():
    model, _, _ = run(1)
    after_checks = model.prompts_with_tool(CHECK_TOOL_NAMES[0])[1]
    tool_outputs = [m for m in after_checks if m.type == "tool" and m.name == "check_form_factor_bound"]
    assert len(tool_outputs) == 1
    assert json.loads(tool_outputs[0].content)["status"] == "violated"


def test_lookup_form_factor_reads_the_constants_file():
    lookups = calls((LOOKUP_FORM_FACTOR, {"code": "18650"}), (LOOKUP_FORM_FACTOR, {"code": "C"}))
    script = [
        *reader_turns(record(BY_ID[1].claims)),
        *checker_turns(lookups, all_checks()),
        *writer_turns(),
        say(),
    ]
    _, events, _ = run(1, script)
    # the two lookups run in parallel, so their results may arrive in either order
    by_known = {e.result["known"]: e.result for e in events if e.type == "tool_result" and e.tool == LOOKUP_FORM_FACTOR}
    found, missing = by_known[True], by_known[False]
    assert found["known"] is True and found["max_diameter_mm"] == 18.5 and found["max_height_mm"] == 65.3
    assert missing["known"] is False


# ------------------------------------------------- the model cannot bend the result


def test_model_text_never_reaches_events_or_report():
    made_up = "I calculate 9999 Wh, so this is verified."
    script = full_script(BY_ID[6].claims, closing=made_up)
    # prose beside a tool call, from the orchestrator and from the listing reader
    for turn in (0, 1):
        script[turn] = AIMessage(content="By my arithmetic 31337 Wh.", tool_calls=script[turn].tool_calls)
    _, events, report = run(6, script)

    everything = "".join(e.model_dump_json() for e in events)
    assert "9999" not in everything and "31337" not in everything and "verified" not in everything
    assert report.verdict.value == "No red flags"


def test_report_is_complete_when_the_model_skips_checks_and_assembly():
    script = [*reader_turns(record(BY_ID[1].claims)), AIMessage(content="Looks fine to me.")]
    _, events, report = run(1, script)

    assert isinstance(events[-1], FinalReportEvent)
    assert [c.check_id for c in report.checks] == [
        "label_consistency",
        "form_factor_bound",
        "dimension_bound",
        "weight_bound",
        "label_contradiction",
        "chemistry_mismatch",
    ]
    assert report.verdict.value == "Impossible"


def test_check_before_claims_is_rejected_then_recovers():
    script = [*checker_turns(), *full_script(BY_ID[2].claims)]
    _, events, report = run(2, script)

    results = [e for e in events if e.type == "tool_result" and e.tool != TASK]
    assert [e.ok for e in results[:6]] == [False] * 6
    assert all(e.result is None for e in results[:6])
    assert all(e.ok for e in results[6:])
    assert report.verdict is BY_ID[2].verdict


def test_invalid_claims_are_rejected_by_the_schema_then_corrected():
    bad = calls((RECORD_CLAIMS, {"claims": {"capacity": {"value": -700, "unit": "mAh", "found_in": "title", "confidence": 1}, "seller": "Some Store"}}))
    script = [*reader_turns(bad, record(BY_ID[2].claims)), *checker_turns(), *writer_turns(), say()]
    _, events, report = run(2, script)

    first = next(e for e in events if e.type == "tool_result")
    assert first.tool == RECORD_CLAIMS and first.ok is False and first.agent == LISTING_READER
    assert report.claims == BY_ID[2].claims
    assert "seller" not in report.model_dump_json()


def test_re_recording_claims_replaces_the_earlier_ones():
    script = [
        *reader_turns(record(BY_ID[1].claims)),
        *checker_turns(),
        *reader_turns(record(BY_ID[2].claims)),
        *checker_turns(),
        *writer_turns(),
        say(),
    ]
    _, _, report = run(2, script)
    assert report.claims == BY_ID[2].claims
    assert report.verdict is BY_ID[2].verdict


# ---------------------------------------------------------------------- failures


def _only_error(events, report, message):
    assert report is None
    assert len(events) == 1 or events[-1].type == "error"
    assert isinstance(events[-1], ErrorEvent) and events[-1].message == message
    assert [e.seq for e in events] == list(range(len(events)))


def test_no_claims_recorded_ends_with_an_error():
    model = ScriptedChatModel(script=[AIMessage(content="I cannot tell what this is.")])
    events, report = drain(run_listing("hello", model=model))
    _only_error(events, report, MSG_NO_CLAIMS)


def test_model_failure_ends_with_a_generic_error():
    # the script runs out on the second turn, which raises inside the agent
    model = ScriptedChatModel(script=reader_turns(record(BY_ID[1].claims))[:2])
    events, report = drain(run_listing(LISTING_TEXT[1], model=model))
    _only_error(events, report, MSG_FAILED)
    assert "script" not in events[-1].message


def test_empty_text_is_an_error():
    events, report = drain(run_listing("   \n", model=ScriptedChatModel(script=[])))
    _only_error(events, report, MSG_EMPTY)


# ----------------------------------------------------------------------- provider


def test_missing_model_settings_end_with_an_error(monkeypatch):
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("MODEL_ID", raising=False)
    events, report = drain(run_listing(LISTING_TEXT[2]))
    _only_error(events, report, MSG_NO_MODEL)


def test_load_model_passes_provider_and_id_to_init_chat_model(monkeypatch):
    seen = {}

    def fake_init(model, **kwargs):
        seen.update(model=model, **kwargs)
        return "the-model"

    monkeypatch.setattr(model_module, "init_chat_model", fake_init)
    monkeypatch.setenv("MODEL_PROVIDER", " some_provider ")
    monkeypatch.setenv("MODEL_ID", "some-model-id")

    assert model_module.is_configured()
    assert model_module.load_model() == "the-model"
    assert seen["model"] == "some-model-id" and seen["model_provider"] == "some_provider"


def test_load_model_requires_both_variables(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "some_provider")
    monkeypatch.delenv("MODEL_ID", raising=False)
    assert not model_module.is_configured()
    with pytest.raises(model_module.ModelNotConfigured):
        model_module.load_model()


# ------------------------------------------------------------- contract entry point


def test_claimcheck_run_listing_runs_the_agent(monkeypatch):
    import agent.runner as runner
    import claimcheck

    model = ScriptedChatModel(script=full_script(BY_ID[1].claims))
    monkeypatch.setattr(runner, "load_model", lambda: model)

    events, report = drain(claimcheck.run_listing(LISTING_TEXT[1]))
    assert isinstance(events[-1], FinalReportEvent) and events[-1].report == report
    assert report.verdict is BY_ID[1].verdict and report.routing is BY_ID[1].routing


def test_claimcheck_run_listing_ends_with_an_error_event_when_no_model_is_set(monkeypatch):
    import claimcheck

    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("MODEL_ID", raising=False)
    events, report = drain(claimcheck.run_listing(LISTING_TEXT[1]))
    _only_error(events, report, MSG_NO_MODEL)
