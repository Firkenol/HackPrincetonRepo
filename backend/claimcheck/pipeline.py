"""The one entry point: run_listing. Part of the frozen contract (see CONTRACT.md)."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from pathlib import Path

from claimcheck.checks import ALL_CHECKS
from claimcheck.events import (
    AgentStepEvent,
    FinalReportEvent,
    StreamEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from claimcheck.models import Claims, EvidenceReport
from claimcheck.verdict import evaluate

# str   -> pasted listing text
# bytes -> the bytes of a screenshot (PNG, JPEG or WebP)
# Path  -> a screenshot file on disk
ListingInput = str | bytes | Path


def run_listing(image_or_text: ListingInput) -> Generator[StreamEvent, None, EvidenceReport]:
    """Check one listing. Yields stream events, then returns the evidence report.

    The last event yielded is a FinalReportEvent carrying the same report that is
    returned, or an ErrorEvent if the run failed, in which case the return value is
    None. Callers that only stream can ignore the return value.

    Implemented by the deepagents agent in backend/agent/. Text input works; image
    input arrives in Phase 3.
    """
    # Imported here, not at the top: the agent package imports claimcheck, and this
    # keeps `import claimcheck` free of the agent's dependencies until a run starts.
    from agent.runner import run_listing as agent_run_listing

    return (yield from agent_run_listing(image_or_text))


def replay_claims(claims: Claims, run_id: str | None = None) -> Generator[StreamEvent, None, EvidenceReport]:
    """Development helper, not part of the frozen contract.

    Emits the same event types as run_listing for claims that are already
    extracted, using only the Phase 1 check functions. No model is called. It lets
    the API and the web UI be built and tested before the agent exists.
    """
    run_id = run_id or uuid.uuid4().hex
    seq = 0

    yield AgentStepEvent(run_id=run_id, seq=seq, agent="physics-checker", message="Running the six checks on the extracted claims.")
    for index, check in enumerate(ALL_CHECKS):
        call_id = f"{run_id}-{index}"
        seq += 1
        yield ToolCallEvent(run_id=run_id, seq=seq, agent="physics-checker", call_id=call_id, tool=check.__name__)
        result = check(claims)
        seq += 1
        yield ToolResultEvent(
            run_id=run_id,
            seq=seq,
            agent="physics-checker",
            call_id=call_id,
            tool=check.__name__,
            summary=f"{result.status.value}: {result.summary}",
            result=result.model_dump(mode="json"),
        )

    report = evaluate(claims)
    seq += 1
    yield AgentStepEvent(run_id=run_id, seq=seq, agent="report-writer", message="Assembling the evidence report.")
    seq += 1
    yield FinalReportEvent(run_id=run_id, seq=seq, agent="report-writer", report=report)
    return report
