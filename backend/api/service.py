"""Runs behind the routes: live or replay, one listing or the whole fixtures folder.

Live mode calls claimcheck.run_listing, which runs the agent on a real model.

Replay mode is used when no model is configured. It serves the reports in
fixtures/expected/ and nothing else: a listing that is not one of the fixtures is not
checked, and the stream says so. Every replay response is marked as sample data.

The only numbers computed here are counts of reports.
"""

from __future__ import annotations

import os
import threading
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from api.fixtures import Fixture, list_fixtures, match_image, match_text
from claimcheck import replay_claims, replay_pack_claims, run_listing
from claimcheck.events import ErrorEvent, StreamEvent
from claimcheck.models import AnyReport, PackEvidenceReport, Routing, Verdict

REPLAY_ENV = "OFFSPEC_REPLAY"
LEGACY_REPLAY_ENV = "CARNOT_REPLAY"  # the name before the rename; still honoured
LIVE, REPLAY = "live", "replay"

MSG_REPLAY_ONLY = (
    "Sample data mode: no model is configured, so this listing was not checked. "
    "Choose one of the sample listings, or set MODEL_PROVIDER and MODEL_ID to check your own."
)
MSG_NO_EXPECTED = "No sample report is on file for this listing."
MSG_NO_LISTING = "This sample has no listing file to run."
MSG_BATCH_ITEM_FAILED = "This listing could not be checked."

Runner = Callable[[Any], Iterator[StreamEvent]]


def current_mode() -> str:
    """replay when no model is configured, or when OFFSPEC_REPLAY asks for it."""
    asked = os.environ.get(REPLAY_ENV, "").strip() or os.environ.get(LEGACY_REPLAY_ENV, "").strip()
    forced = asked.lower() in ("1", "true", "yes", "on")
    configured = bool(os.environ.get("MODEL_PROVIDER", "").strip() and os.environ.get("MODEL_ID", "").strip())
    return REPLAY if forced or not configured else LIVE


def mode_fields(mode: str) -> dict[str, Any]:
    """The marking every JSON response carries."""
    return {"mode": mode, "sample_data": mode == REPLAY}


def _error(message: str) -> Iterator[StreamEvent]:
    yield ErrorEvent(run_id=uuid.uuid4().hex, seq=0, message=message)


def _fixture_input(fixture: Fixture) -> Any:
    return fixture.image_bytes() if fixture.has_image else fixture.text


# ------------------------------------------------------------------ one listing


def replay_fixture(fixture: Fixture | None) -> Iterator[StreamEvent]:
    """The stream for a fixture in replay mode: the checks for its category on the claims of its expected report."""
    if fixture is None:
        return _error(MSG_REPLAY_ONLY)
    expected = fixture.expected_report()
    if expected is None:
        return _error(MSG_NO_EXPECTED)
    if isinstance(expected, PackEvidenceReport):
        return replay_pack_claims(expected.pack, expected.claims)
    return replay_claims(expected.claims)


def stream_listing(
    *, text: str | None, image: bytes | None, sample: Fixture | None, mode: str, runner: Runner | None = None
) -> Iterator[StreamEvent]:
    """The events for one request. Exactly one of text, image and sample is set."""
    if mode == REPLAY:
        if sample is None:
            sample = match_text(text) if text is not None else match_image(image or b"")
        return replay_fixture(sample)

    if sample is not None:
        listing = _fixture_input(sample)
        if listing is None:
            return _error(MSG_NO_LISTING)
        return (runner or run_listing)(listing)
    return (runner or run_listing)(text if text is not None else image)


# ------------------------------------------------------------------------ batch


def _drain(events: Iterator[StreamEvent]) -> tuple[AnyReport | None, str | None]:
    report, error = None, None
    for event in events:
        if event.type == "final_report":
            report = event.report
        elif event.type == "error":
            error = event.message
    return report, error


def count_reports(reports: list[AnyReport], errors: int = 0) -> dict[str, Any]:
    """Counts per verdict and per routing value. Every key is always present."""
    by_verdict = {verdict.value: 0 for verdict in Verdict}
    by_routing = {routing.value: 0 for routing in Routing}
    for report in reports:
        by_verdict[report.verdict.value] += 1
        by_routing[report.routing.value] += 1
    return {"total": len(reports), "errors": errors, "by_verdict": by_verdict, "by_routing": by_routing}


@dataclass
class BatchItem:
    id: str
    source: str
    listing_text: str | None
    image_url: str | None
    report: AnyReport | None
    error: str | None

    def as_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "listing_text": self.listing_text,
            "image_url": self.image_url,
            "report": self.report.model_dump(mode="json") if self.report else None,
            "error": self.error,
        }


@dataclass
class BatchRun:
    mode: str
    ran_at: str
    items: list[BatchItem] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, Any]:
        reports = [item.report for item in self.items if item.report is not None]
        return count_reports(reports, errors=sum(1 for item in self.items if item.report is None))

    def as_json(self) -> dict[str, Any]:
        return {
            **mode_fields(self.mode),
            "has_run": True,
            "ran_at": self.ran_at,
            "items": [item.as_json() for item in self.items],
            "counts": self.counts,
        }


def image_url(fixture: Fixture) -> str | None:
    if fixture.image_path:
        return f"/api/fixtures/{fixture.image_path.name}"
    return f"/api/fixtures/{fixture.id}.png" if fixture.image_parts else None


def run_batch(mode: str, runner: Runner | None = None) -> BatchRun:
    """Run every listing file in fixtures/. In replay mode, serve every expected report instead."""
    run = BatchRun(mode=mode, ran_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    for fixture in list_fixtures():
        if mode == REPLAY:
            if fixture.expected_path is None:
                continue
            report, error = fixture.expected_report(), None
        else:
            listing = _fixture_input(fixture)
            if listing is None:
                continue  # an expected report with no listing file: nothing to run
            try:
                report, error = _drain((runner or run_listing)(listing))
            except Exception:
                report, error = None, MSG_BATCH_ITEM_FAILED
            if report is None and error is None:
                error = MSG_BATCH_ITEM_FAILED
        run.items.append(
            BatchItem(
                id=fixture.id,
                source=fixture.source,
                listing_text=None if fixture.has_image else fixture.text,
                image_url=image_url(fixture),
                report=report,
                error=error,
            )
        )
    return run


# ---------------------------------------------------------------- dashboard stats


class LatestBatch:
    """The most recent batch run, kept in memory. The dashboard counts come from it."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._run: BatchRun | None = None

    def set(self, run: BatchRun) -> None:
        with self._lock:
            self._run = run

    def get(self) -> BatchRun | None:
        with self._lock:
            return self._run

    def clear(self) -> None:
        with self._lock:
            self._run = None


def dashboard_stats(latest: BatchRun | None, mode: str) -> dict[str, Any]:
    """Counts from the latest batch run. Before any run, has_run is false and every count is null."""
    if latest is None:
        return {
            **mode_fields(mode),
            "has_run": False,
            "ran_at": None,
            "listings_checked": None,
            "impossible_claims": None,
            "routed_to_human_review": None,
            "no_action_needed": None,
            "auto_resolvable": None,
            "errors": None,
            "by_verdict": None,
            "by_routing": None,
        }
    counts = latest.counts
    return {
        # the marking of the run the numbers came from, not of the server right now
        **mode_fields(latest.mode),
        "has_run": True,
        "ran_at": latest.ran_at,
        "listings_checked": counts["total"],
        "impossible_claims": counts["by_verdict"][Verdict.IMPOSSIBLE.value],
        "routed_to_human_review": counts["by_routing"][Routing.NEEDS_HUMAN_REVIEW.value],
        "no_action_needed": counts["by_routing"][Routing.NO_ACTION_NEEDED.value],
        "auto_resolvable": counts["by_routing"][Routing.AUTO_RESOLVABLE.value],
        "errors": counts["errors"],
        "by_verdict": counts["by_verdict"],
        "by_routing": counts["by_routing"],
    }
