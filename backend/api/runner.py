"""Chooses what runs a listing: the real agent or the stub, by CLAIMCHECK_RUNNER.

Also wraps the run so the stream always ends in final_report or error, whatever
the runner does, and so nothing from the listing reaches the log.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterator
from pathlib import Path

from claimcheck.events import ErrorEvent, StreamEvent

from api import settings

log = logging.getLogger("claimcheck.api")

ListingInput = str | bytes | Path


def _start(payload: ListingInput, name_hint: str | None) -> Iterator[StreamEvent]:
    name = settings.runner_name()
    if name == "stub":
        from api import stub

        return stub.run_listing(payload, name_hint=name_hint)
    if name == "agent":
        from claimcheck import run_listing

        return run_listing(payload)
    raise RuntimeError("CLAIMCHECK_RUNNER must be 'agent' or 'stub'")


def run_events(payload: ListingInput, name_hint: str | None = None) -> Iterator[StreamEvent]:
    """Yields the run's events. The last one is always final_report or error.

    name_hint is the upload's file name. Only the stub uses it, to pick a fixture.
    """
    run_id: str | None = None
    seq = -1
    try:
        for event in _start(payload, name_hint):
            run_id, seq = event.run_id, event.seq
            yield event
            if event.type in ("final_report", "error"):
                if event.type == "final_report":
                    log.info("run %s finished: %s, %s", run_id, event.report.verdict.value, event.report.routing.value)
                else:
                    log.info("run %s ended with an error event", run_id)
                return
        message = "The run ended without a report."
    except NotImplementedError:
        message = "Listing analysis is not available in this build."
    except Exception as exc:  # noqa: BLE001 - the stream must end with an error event
        # Only the exception type is logged: its message could quote the listing.
        log.error("run %s failed with %s", run_id, type(exc).__name__)
        message = "The listing could not be analysed."
    yield ErrorEvent(run_id=run_id or uuid.uuid4().hex, seq=seq + 1, message=message)
