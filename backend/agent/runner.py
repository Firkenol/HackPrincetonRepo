"""run_listing: the entry point CONTRACT.md defines, implemented by the agent.

Translates the messages of the orchestrator and its three subagents into the
contract's stream events, each labelled with the agent it came from. The report is
always built in Python (claimcheck.verdict.evaluate, or a check pack's evaluate) from
the claims the listing reader recorded; no prose a model writes reaches an event or the report.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Generator, Iterator
from pathlib import Path
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from agent.graph import ORCHESTRATOR, build_agent
from agent.images import ImageError, image_block, read_image
from agent.model import ModelNotConfigured, load_model
from agent.prompts import (
    IMAGE_USER_TEXT,
    LISTING_READER,
    ORCHESTRATOR_USER_IMAGE,
    ORCHESTRATOR_USER_TEXT,
    PHYSICS_CHECKER,
    REPORT_WRITER,
    SUBAGENT_NAMES,
    USER_TEMPLATE,
)
from agent.tools import (
    ASSEMBLE_REPORT,
    CHECK_TOOL_NAMES,
    LIST_CHECKS,
    LOOKUP_FORM_FACTOR,
    PACK_CHECK_TOOL_NAMES,
    PACK_RECORD_TOOL_NAMES,
    RECORD_CLAIMS,
    TOOL_NAMES,
    RunState,
    pack_report,
)
from claimcheck.events import (
    AgentStepEvent,
    ErrorEvent,
    FinalReportEvent,
    StreamEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from claimcheck.models import AnyReport
from claimcheck.verdict import evaluate

log = logging.getLogger(__name__)

ListingInput = str | bytes | Path

# Upper bound on graph steps for the orchestrator, and for each subagent. A normal
# run takes about a dozen in the orchestrator and fewer in a subagent.
RECURSION_LIMIT = 40

# The deepagents tool the orchestrator delegates with.
TASK = "task"

# Trace lines are fixed text. Model-written text is never shown.
_STEP_ON_DELEGATION = {
    LISTING_READER: "Recording what the listing states.",
    PHYSICS_CHECKER: "Running the checks on the recorded claims.",
    REPORT_WRITER: "Assembling the evidence report.",
}

MSG_EMPTY = "The listing text is empty."
MSG_NO_MODEL = "No model is configured. Set MODEL_PROVIDER and MODEL_ID."
MSG_FAILED = "The listing could not be checked because the model run failed."
MSG_NO_CLAIMS = "The listing could not be read into claims, so no check was run."
MSG_CHECKS_FAILED = "The checks could not be completed for this listing."


class _Emitter:
    """Stamps events with the run id and the next sequence number."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._seq = 0

    def __call__(self, event_type, agent: str = ORCHESTRATOR, **fields) -> StreamEvent:
        event = event_type(run_id=self.run_id, seq=self._seq, agent=agent, **fields)
        self._seq += 1
        return event


def _agent_name(name: Any) -> str:
    """The contract's agent label. Anything that is not one of the three subagents is the orchestrator."""
    return name if name in SUBAGENT_NAMES else ORCHESTRATOR


def _shown_args(tool: str, args: dict) -> dict:
    """Tool arguments as shown in the trace.

    The arguments of the claim and check tools are shown whole. A delegation shows
    only which subagent was chosen, not the task text the model wrote. Other tools
    (the built-in file tools) show nothing.
    """
    if tool in TOOL_NAMES:
        return args
    if tool == TASK and args.get("subagent_type") in SUBAGENT_NAMES:
        return {"subagent_type": args["subagent_type"]}
    return {}


def _parse(content: Any) -> Any:
    """Tool output as JSON where it is JSON, otherwise as plain text."""
    if not isinstance(content, str):
        return content
    try:
        return json.loads(content)
    except ValueError:
        return content


def _summary(tool: str, ok: bool, result: Any) -> str:
    if not ok:
        return "The tool call was rejected and can be retried."
    if tool == TASK:
        return "The subagent finished."
    if not isinstance(result, dict):
        return "Done."
    if tool in CHECK_TOOL_NAMES or tool in PACK_CHECK_TOOL_NAMES:
        return f"{result.get('status')}: {result.get('summary')}"
    if tool == RECORD_CLAIMS or tool in PACK_RECORD_TOOL_NAMES:
        return "Claims recorded."
    if tool == LIST_CHECKS:
        return "Checks listed."
    if tool == ASSEMBLE_REPORT:
        return f"{result.get('verdict')}, {result.get('routing')}."
    if tool == LOOKUP_FORM_FACTOR:
        return "Size code found." if result.get("known") else "Size code not on file."
    return "Done."


def _messages(chunk: Any) -> Iterator[BaseMessage]:
    """New messages in one 'updates' chunk from an agent graph."""
    if not isinstance(chunk, dict):
        return
    for update in chunk.values():
        if not isinstance(update, dict):
            continue
        messages = update.get("messages")
        messages = getattr(messages, "value", messages)  # an Overwrite wrapper
        if isinstance(messages, BaseMessage):
            yield messages
        elif isinstance(messages, (list, tuple)):
            yield from (m for m in messages if isinstance(m, BaseMessage))


def run_listing(
    image_or_text: ListingInput, *, model: BaseChatModel | None = None
) -> Generator[StreamEvent, None, AnyReport | None]:
    """Check one listing. Yields stream events, then returns the evidence report.

    A battery listing gives an EvidenceReport. A listing the reader recorded with a
    pack's record tool gives that pack's PackEvidenceReport.

    The last event is a FinalReportEvent carrying the returned report, or an
    ErrorEvent, in which case the return value is None.

    model is for tests and callers that build their own; by default the model named
    by MODEL_PROVIDER and MODEL_ID is loaded.
    """
    emit = _Emitter(uuid.uuid4().hex)

    # listing_content goes to the listing reader only. The orchestrator is told just
    # what kind of input arrived.
    if isinstance(image_or_text, str):
        listing = image_or_text.strip()
        if not listing:
            yield emit(ErrorEvent, message=MSG_EMPTY)
            return None
        listing_content: str | list[dict] = USER_TEMPLATE.format(listing=listing)
        request = ORCHESTRATOR_USER_TEXT
        first_step = "Reading the listing text."
    else:
        try:
            data, mime_type = read_image(image_or_text)
        except ImageError as error:
            yield emit(ErrorEvent, message=str(error))
            return None
        listing_content = [{"type": "text", "text": IMAGE_USER_TEXT}, image_block(data, mime_type)]
        request = ORCHESTRATOR_USER_IMAGE
        first_step = "Reading the listing image."

    state = RunState()
    try:
        agent = build_agent(model or load_model(), state, listing_content)
    except ModelNotConfigured:
        yield emit(ErrorEvent, message=MSG_NO_MODEL)
        return None
    except Exception:
        log.exception("could not build the agent")
        yield emit(ErrorEvent, message=MSG_FAILED)
        return None

    yield emit(AgentStepEvent, message=first_step)
    tool_by_call: dict[str, str] = {}
    # A subagent runs in its own namespace of the stream. Its assistant messages carry
    # its name, which also labels the tool results that follow in that namespace.
    agent_by_namespace: dict[tuple, str] = {(): ORCHESTRATOR}
    try:
        stream = agent.stream(
            {"messages": [{"role": "user", "content": request}]},
            config={"recursion_limit": RECURSION_LIMIT},
            stream_mode="updates",
            subgraphs=True,
        )
        for namespace, chunk in stream:
            for message in _messages(chunk):
                if isinstance(message, AIMessage):
                    if namespace:
                        agent_by_namespace[namespace] = _agent_name(message.name)
                    who = agent_by_namespace.get(namespace, ORCHESTRATOR)
                    for call in message.tool_calls:
                        name, call_id = call["name"], call["id"] or uuid.uuid4().hex
                        args = call["args"] or {}
                        tool_by_call[call_id] = name
                        yield emit(ToolCallEvent, who, call_id=call_id, tool=name, args=_shown_args(name, args))
                        if name == TASK and args.get("subagent_type") in _STEP_ON_DELEGATION:
                            subagent = args["subagent_type"]
                            yield emit(AgentStepEvent, subagent, message=_STEP_ON_DELEGATION[subagent])
                elif isinstance(message, ToolMessage):
                    name = tool_by_call.get(message.tool_call_id, message.name or "unknown")
                    ok = message.status != "error"
                    # Only the claim and check tools return data for the trace. A
                    # delegation returns the subagent's own words, which are not shown.
                    result = _parse(message.content) if ok and name in TOOL_NAMES else None
                    yield emit(
                        ToolResultEvent,
                        agent_by_namespace.get(namespace, ORCHESTRATOR),
                        call_id=message.tool_call_id,
                        tool=name,
                        ok=ok,
                        summary=_summary(name, ok, result),
                        result=result,
                    )
    except Exception:
        log.exception("agent run failed")
        yield emit(ErrorEvent, message=MSG_FAILED)
        return None

    if not state.has_claims:
        yield emit(ErrorEvent, message=MSG_NO_CLAIMS)
        return None

    try:
        # Deterministic whatever the models did: if a check or the report writer was
        # skipped, the report is still complete and computed in Python.
        report = state.report or (pack_report(state) if state.pack_claims is not None else evaluate(state.claims))
    except Exception:
        log.exception("report assembly failed")
        yield emit(ErrorEvent, message=MSG_CHECKS_FAILED)
        return None

    yield emit(FinalReportEvent, report=report)
    return report
