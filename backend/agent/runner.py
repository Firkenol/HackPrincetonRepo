"""run_listing: the entry point CONTRACT.md defines, implemented by the agent.

Translates the agent's messages into the contract's stream events. The report is
always built by claimcheck.verdict.evaluate from the claims the model recorded; no
text the model writes reaches an event or the report.
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

from agent.graph import build_agent
from agent.images import ImageError, image_block, read_image
from agent.model import ModelNotConfigured, load_model
from agent.prompts import IMAGE_USER_TEXT, USER_TEMPLATE
from agent.tools import ASSEMBLE_REPORT, CHECK_TOOL_NAMES, LOOKUP_FORM_FACTOR, RECORD_CLAIMS, RunState
from claimcheck.events import (
    AgentStepEvent,
    ErrorEvent,
    FinalReportEvent,
    StreamEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from claimcheck.models import EvidenceReport
from claimcheck.verdict import evaluate

log = logging.getLogger(__name__)

ListingInput = str | bytes | Path

# Upper bound on agent steps for one listing. A normal run takes about ten.
RECURSION_LIMIT = 40

# Trace lines are fixed text. Model-written text is never shown.
_STEP_BEFORE_TOOL = {
    RECORD_CLAIMS: "Recording what the listing states.",
    CHECK_TOOL_NAMES[0]: "Running the six checks on the recorded claims.",
    ASSEMBLE_REPORT: "Assembling the evidence report.",
}

MSG_EMPTY = "The listing text is empty."
MSG_NO_MODEL = "No model is configured. Set MODEL_PROVIDER and MODEL_ID."
MSG_FAILED = "The listing could not be checked because the model run failed."
MSG_NO_CLAIMS = "The listing could not be read into claims, so no check was run."


class _Emitter:
    """Stamps events with the run id and the next sequence number."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._seq = 0

    def __call__(self, event_type, **fields) -> StreamEvent:
        event = event_type(run_id=self.run_id, seq=self._seq, agent="orchestrator", **fields)
        self._seq += 1
        return event


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
    if not isinstance(result, dict):
        return "Done."
    if tool in CHECK_TOOL_NAMES:
        return f"{result.get('status')}: {result.get('summary')}"
    if tool == RECORD_CLAIMS:
        return "Claims recorded."
    if tool == ASSEMBLE_REPORT:
        return f"{result.get('verdict')}, {result.get('routing')}."
    if tool == LOOKUP_FORM_FACTOR:
        return "Size code found." if result.get("known") else "Size code not on file."
    return "Done."


def _messages(chunk: Any) -> Iterator[BaseMessage]:
    """New messages in one 'updates' chunk from the agent graph."""
    if not isinstance(chunk, dict):
        return
    for update in chunk.values():
        if not isinstance(update, dict):
            continue
        messages = update.get("messages")
        if isinstance(messages, BaseMessage):
            yield messages
        elif isinstance(messages, (list, tuple)):
            yield from (m for m in messages if isinstance(m, BaseMessage))


def run_listing(
    image_or_text: ListingInput, *, model: BaseChatModel | None = None
) -> Generator[StreamEvent, None, EvidenceReport | None]:
    """Check one listing. Yields stream events, then returns the evidence report.

    The last event is a FinalReportEvent carrying the returned report, or an
    ErrorEvent, in which case the return value is None.

    model is for tests and callers that build their own; by default the model named
    by MODEL_PROVIDER and MODEL_ID is loaded.
    """
    emit = _Emitter(uuid.uuid4().hex)

    if isinstance(image_or_text, str):
        listing = image_or_text.strip()
        if not listing:
            yield emit(ErrorEvent, message=MSG_EMPTY)
            return None
        content: str | list[dict] = USER_TEMPLATE.format(listing=listing)
        first_step = "Reading the listing text."
    else:
        try:
            data, mime_type = read_image(image_or_text)
        except ImageError as error:
            yield emit(ErrorEvent, message=str(error))
            return None
        content = [{"type": "text", "text": IMAGE_USER_TEXT}, image_block(data, mime_type)]
        first_step = "Reading the listing image."

    state = RunState()
    try:
        agent = build_agent(model or load_model(), state)
    except ModelNotConfigured:
        yield emit(ErrorEvent, message=MSG_NO_MODEL)
        return None
    except Exception:
        log.exception("could not build the agent")
        yield emit(ErrorEvent, message=MSG_FAILED)
        return None

    yield emit(AgentStepEvent, message=first_step)
    tool_by_call: dict[str, str] = {}
    announced: set[str] = set()
    try:
        stream = agent.stream(
            {"messages": [{"role": "user", "content": content}]},
            config={"recursion_limit": RECURSION_LIMIT},
            stream_mode="updates",
        )
        for chunk in stream:
            for message in _messages(chunk):
                if isinstance(message, AIMessage):
                    for call in message.tool_calls:
                        name, call_id = call["name"], call["id"] or uuid.uuid4().hex
                        tool_by_call[call_id] = name
                        step = _STEP_BEFORE_TOOL.get(name)
                        if step and name not in announced:
                            announced.add(name)
                            yield emit(AgentStepEvent, message=step)
                        yield emit(ToolCallEvent, call_id=call_id, tool=name, args=call["args"] or {})
                elif isinstance(message, ToolMessage):
                    name = tool_by_call.get(message.tool_call_id, message.name or "unknown")
                    ok = message.status != "error"
                    result = _parse(message.content) if ok else None
                    yield emit(
                        ToolResultEvent,
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

    if state.claims is None:
        yield emit(ErrorEvent, message=MSG_NO_CLAIMS)
        return None

    try:
        # Deterministic whatever the model did: if it skipped a check or the final
        # tool, the report is still complete and computed in Python.
        report = state.report or evaluate(state.claims)
    except Exception:
        log.exception("report assembly failed")
        yield emit(ErrorEvent, message="The checks could not be completed for this listing.")
        return None

    yield emit(FinalReportEvent, report=report)
    return report
