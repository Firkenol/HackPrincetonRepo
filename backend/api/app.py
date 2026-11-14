"""Routes of the Carnot API.

    POST /api/verify-listing    check one listing; streams the contract's events (SSE)
    POST /api/batch             run every listing in fixtures/; reports and counts
    GET  /api/batch             the latest batch run again, without running anything
    GET  /api/dashboard-stats   counts from the latest batch run
    GET  /api/samples           the fixture listings, for the sample picker
    GET  /api/fixtures/{name}   a fixture screenshot
    GET  /api/health            mode of the server

Every response says whether it is sample data: JSON bodies carry "mode" and
"sample_data", and every response has the X-Carnot-Mode header. The event stream also
opens with one "meta" frame carrying the same two fields; the frames after it are the
contract's stream events, unchanged.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from collections.abc import Iterator

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse

from api import fixtures, service
from claimcheck.events import ErrorEvent, StreamEvent, to_sse

log = logging.getLogger(__name__)

# backend/.env or the repo root .env, whichever exists. Real variables win.
load_dotenv()

MODE_HEADER = "X-Carnot-Mode"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MSG_STREAM_FAILED = "The listing could not be checked because the run failed."

app = FastAPI(title="Carnot API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=[MODE_HEADER],
)

latest_batch = service.LatestBatch()


def _json(body: dict, mode: str) -> JSONResponse:
    return JSONResponse(body, headers={MODE_HEADER: mode})


def sse_stream(events: Iterator[StreamEvent], mode: str, sample_id: str | None) -> Iterator[str]:
    """One meta frame, then each contract event as one SSE message.

    A stream always ends with final_report or error. If the run itself raises, the
    error event is added here, with a generic message.
    """
    meta = {**service.mode_fields(mode), "sample_id": sample_id}
    yield f"event: meta\ndata: {json.dumps(meta)}\n\n"
    seq, run_id = 0, uuid.uuid4().hex
    try:
        for event in events:
            seq, run_id = event.seq + 1, event.run_id
            yield to_sse(event)
    except Exception:
        log.exception("stream failed")
        yield to_sse(ErrorEvent(run_id=run_id, seq=seq, message=MSG_STREAM_FAILED))


@app.get("/api/health")
def health() -> JSONResponse:
    mode = service.current_mode()
    return _json({"status": "ok", **service.mode_fields(mode)}, mode)


@app.post("/api/verify-listing")
def verify_listing(
    image: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    sample: str | None = Form(default=None),
) -> StreamingResponse:
    """Check one listing. Send exactly one of: image (a file), text, or sample (a fixture id)."""
    text = text if text is not None and text.strip() else None
    sample = sample.strip() if sample and sample.strip() else None
    given = [part for part in (image, text, sample) if part is not None]
    if len(given) != 1:
        raise HTTPException(status_code=400, detail="Send exactly one of image, text or sample.")

    data: bytes | None = None
    if image is not None:
        data = image.file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="The image is too large.")

    fixture = None
    if sample is not None:
        fixture = fixtures.get_fixture(sample)
        if fixture is None:
            raise HTTPException(status_code=404, detail="No such sample.")

    mode = service.current_mode()
    events = service.stream_listing(text=text, image=data, sample=fixture, mode=mode)
    return StreamingResponse(
        sse_stream(events, mode, fixture.id if fixture else None),
        media_type="text/event-stream",
        headers={MODE_HEADER: mode, "Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/batch")
def batch() -> JSONResponse:
    mode = service.current_mode()
    run = service.run_batch(mode)
    latest_batch.set(run)
    return _json(run.as_json(), mode)


@app.get("/api/batch")
def latest_batch_run() -> JSONResponse:
    """The latest batch run, as POST /api/batch returned it. Lets a batch be run ahead of time and shown later."""
    mode = service.current_mode()
    run = latest_batch.get()
    if run is None:
        return _json({**service.mode_fields(mode), "has_run": False, "ran_at": None, "items": [], "counts": None}, mode)
    return _json({**run.as_json(), "has_run": True}, mode)


@app.get("/api/dashboard-stats")
def dashboard_stats() -> JSONResponse:
    mode = service.current_mode()
    return _json(service.dashboard_stats(latest_batch.get(), mode), mode)


@app.get("/api/samples")
def samples() -> JSONResponse:
    mode = service.current_mode()
    items = [
        {
            "id": fixture.id,
            "source": fixture.source,
            "listing_text": None if fixture.has_image else fixture.text,
            "image_url": service.image_url(fixture),
            "has_expected_report": fixture.expected_path is not None,
        }
        for fixture in fixtures.list_fixtures()
    ]
    return _json({**service.mode_fields(mode), "samples": items}, mode)


@app.get("/api/fixtures/{name}")
def fixture_image(name: str) -> Response:
    """A fixture's screenshot. For a listing captured in parts, fixture_NN.png is the stitched image."""
    stem, dot, suffix = name.rpartition(".")
    suffix = f"{dot}{suffix}".lower()
    fixture = fixtures.get_fixture(stem) if suffix in fixtures.IMAGE_SUFFIXES else None
    if fixture is None or not fixture.has_image:
        raise HTTPException(status_code=404, detail="No such fixture image.")
    if fixture.image_path is not None and fixture.image_path.name.lower() != name.lower():
        raise HTTPException(status_code=404, detail="No such fixture image.")
    data = fixture.image_bytes()
    media_type = "image/jpeg" if data[:3] == b"\xff\xd8\xff" else fixtures.MEDIA_TYPES[suffix] if fixture.image_path else "image/png"
    return Response(content=data, media_type=media_type)
