"""Stream events: what the backend sends to the browser while a listing is checked.

Part of the frozen contract (see CONTRACT.md). Events never carry seller or store names.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from claimcheck.models import EvidenceReport

AgentName = Literal["orchestrator", "listing-reader", "physics-checker", "report-writer"]


class _Event(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(description="Same for every event of one run_listing call.")
    seq: int = Field(ge=0, description="Position in the stream, starting at 0 and increasing by 1.")
    agent: AgentName = Field(default="orchestrator", description="Which agent the event comes from.")


class AgentStepEvent(_Event):
    """An agent started a step. Shown as one line in the live trace."""

    type: Literal["agent_step"] = "agent_step"
    message: str


class ToolCallEvent(_Event):
    """An agent called a tool."""

    type: Literal["tool_call"] = "tool_call"
    call_id: str = Field(description="Pairs this call with its tool_result.")
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)


class ToolResultEvent(_Event):
    """A tool returned. For a check tool, result is a CheckResult as JSON."""

    type: Literal["tool_result"] = "tool_result"
    call_id: str
    tool: str
    ok: bool = True
    summary: str = Field(default="", description="One line for the trace.")
    result: Any = Field(default=None, description="JSON-serialisable tool output.")


class FinalReportEvent(_Event):
    """Last event of a successful run."""

    type: Literal["final_report"] = "final_report"
    report: EvidenceReport


class ErrorEvent(_Event):
    """Last event of a failed run. The message is safe to display."""

    type: Literal["error"] = "error"
    message: str


StreamEvent = Annotated[
    Union[AgentStepEvent, ToolCallEvent, ToolResultEvent, FinalReportEvent, ErrorEvent],
    Field(discriminator="type"),
]

STREAM_EVENT_ADAPTER: TypeAdapter[StreamEvent] = TypeAdapter(StreamEvent)


def to_sse(event: _Event) -> str:
    """Frame an event as one Server-Sent Events message."""
    return f"event: {event.type}\ndata: {event.model_dump_json()}\n\n"
