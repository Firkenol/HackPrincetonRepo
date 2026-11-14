"""Stand-in for the agent: replays fixtures/expected/ as a stream of contract events.

Selected with CLAIMCHECK_RUNNER=stub. It reads nothing from the listing. It only
decides which recorded report to replay:

- text equal to one of SAMPLE_TEXTS, or containing "fixture N"
- a file named fixture_NN.* (a Path, or an upload whose file name is passed as name_hint)
- upload bytes identical to a screenshot stored as fixtures/fixture_NN.*

Anything else ends in an error event, so the stub never invents a result.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from collections.abc import Generator
from pathlib import Path
from typing import Any

from claimcheck.events import AgentStepEvent, ErrorEvent, FinalReportEvent, StreamEvent, ToolCallEvent, ToolResultEvent

from api import settings

# Text versions of the nine SPEC fixtures. Kept identical to web/lib/samples.ts.
SAMPLE_TEXTS: dict[int, str] = {
    1: "18650 Li-ion rechargeable battery, 12000mAh 3.7V.\nSpec table: Package weight 0.600 kg. Package dimensions 15 x 15 x 15 cm.",
    2: "AA Ni-MH rechargeable battery, 700mAh 1.2V.",
    3: 'Title: Alkaline AA and AAA battery pack.\nProduct photo: cells are printed R6 and R03 and "Heavy Duty".',
    4: "Carbon zinc AA and AAA battery pack. 10-year shelf life.",
    5: "Carbon zinc AA and AAA heavy duty battery multipack.",
    6: "2S LiPo battery pack. Label: 7.4V 6200mAh 45.88Wh.\nSpec table: 139.5 x 47.5 x 26 mm, 315 g.",
    7: "3S LiPo battery pack. Label: 11.1V 2200mAh 24.42Wh.\nSpec table: 106 x 33 x 23 mm, 179 g.",
    8: "2S LiPo battery pack. Label: 7.4V 5200mAh 38.48Wh.\nSpec table: 25 x 47 x 139 mm, 307 g.",
    9: "2S LiPo battery pack. Label: 7.4V 5200mAh 38.48Wh.",
}

_NAME = re.compile(r"fixture[\s_-]*0*([1-9])(?!\d)", re.IGNORECASE)
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def _normalise(text: str) -> str:
    return " ".join(text.lower().split())


_BY_TEXT = {_normalise(text): fixture_id for fixture_id, text in SAMPLE_TEXTS.items()}


def _from_name(name: str) -> int | None:
    match = _NAME.search(name)
    return int(match.group(1)) if match else None


def _from_bytes(data: bytes) -> int | None:
    digest = hashlib.sha256(data).digest()
    for path in sorted(settings.fixtures_dir().glob("fixture_*")):
        if path.suffix.lower() in _IMAGE_SUFFIXES and hashlib.sha256(path.read_bytes()).digest() == digest:
            return _from_name(path.name)
    return None


def resolve_fixture_id(image_or_text: str | bytes | Path, name_hint: str | None = None) -> int | None:
    if isinstance(image_or_text, Path):
        return _from_name(image_or_text.name)
    if isinstance(image_or_text, bytes):
        return (_from_name(name_hint) if name_hint else None) or _from_bytes(image_or_text)
    return _BY_TEXT.get(_normalise(image_or_text)) or _from_name(image_or_text)


def _load(fixture_id: int) -> dict[str, Any]:
    path = settings.fixtures_dir() / "expected" / f"fixture_{fixture_id:02d}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _claim_count(claims: dict[str, Any]) -> int:
    return sum(len(v) if isinstance(v, list) else 1 for v in claims.values() if isinstance(v, (list, dict)))


def run_listing(
    image_or_text: str | bytes | Path, *, name_hint: str | None = None
) -> Generator[StreamEvent, None, Any]:
    """Same shape as claimcheck.run_listing: yields events, returns the report."""
    run_id = uuid.uuid4().hex
    base = settings.stub_delay_s()
    seq = -1

    def emit(event_type: type, pause: float = 1.0, **fields: Any) -> StreamEvent:
        nonlocal seq
        seq += 1
        if base:
            time.sleep(base * pause)
        return event_type(run_id=run_id, seq=seq, **fields)

    source = "pasted text" if isinstance(image_or_text, str) else "a screenshot"
    yield emit(AgentStepEvent, 0, agent="orchestrator", message=f"Received a listing as {source}.")

    fixture_id = resolve_fixture_id(image_or_text, name_hint)
    if fixture_id is None:
        yield emit(
            ErrorEvent,
            message=(
                "The stub replays only the nine recorded fixtures. Send one of the sample texts, "
                "text containing 'fixture N', or a screenshot named fixture_01 to fixture_09."
            ),
        )
        return None
    report = _load(fixture_id)

    yield emit(AgentStepEvent, agent="listing-reader", message="Reading the claims the listing itself states.")
    call_id = f"{run_id}-extract"
    yield emit(ToolCallEvent, agent="listing-reader", call_id=call_id, tool="extract_claims", args={})
    # Extraction is the slow model call in the real agent.
    yield emit(
        ToolResultEvent,
        5,
        agent="listing-reader",
        call_id=call_id,
        tool="extract_claims",
        summary=f"{_claim_count(report['claims'])} claims extracted.",
        result=report["claims"],
    )

    yield emit(AgentStepEvent, agent="physics-checker", message="Running the six checks on the extracted claims.")
    for index, check in enumerate(report["checks"]):
        call_id = f"{run_id}-{index}"
        tool = f"check_{check['check_id']}"
        yield emit(ToolCallEvent, agent="physics-checker", call_id=call_id, tool=tool)
        yield emit(
            ToolResultEvent,
            agent="physics-checker",
            call_id=call_id,
            tool=tool,
            summary=f"{check['status']}: {check['summary']}",
            result=check,
        )

    yield emit(AgentStepEvent, agent="report-writer", message="Assembling the evidence report.")
    final = emit(FinalReportEvent, 2, agent="report-writer", report=report)
    yield final
    return final.report
