"""The FastAPI application. Run with: uvicorn api.app:app --reload (from backend/)."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from claimcheck.events import to_sse

from api import settings, store
from api.runner import ListingInput, run_events

_MAGIC = (
    (b"\x89PNG\r\n\x1a\n", "PNG"),
    (b"\xff\xd8\xff", "JPEG"),
)


def is_screenshot(data: bytes) -> bool:
    """PNG, JPEG or WebP, judged by the file's first bytes rather than its name."""
    if any(data.startswith(magic) for magic, _ in _MAGIC):
        return True
    return data[:4] == b"RIFF" and data[8:12] == b"WEBP"


async def read_upload(upload: UploadFile) -> bytes:
    limit = settings.max_upload_bytes()
    data = await upload.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"The screenshot is larger than {limit // (1024 * 1024)} MB.")
    if not is_screenshot(data):
        raise HTTPException(415, "The file is not a PNG, JPEG or WebP image.")
    return data


def sse_stream(payload: ListingInput, name_hint: str | None) -> Iterator[str]:
    for event in run_events(payload, name_hint):
        if event.type == "final_report":
            store.save(event.run_id, event.report.model_dump(mode="json"))
        yield to_sse(event)


def create_app() -> FastAPI:
    app = FastAPI(title="ClaimCheck API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins(),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "runner": settings.runner_name()}

    @app.post("/api/check")
    async def check(image: UploadFile | None = File(None), text: str | None = Form(None)) -> StreamingResponse:
        """One listing in, a Server-Sent Events stream of contract events out."""
        has_text = bool(text and text.strip())
        if (image is not None) == has_text:
            raise HTTPException(400, "Send exactly one of image or text.")
        payload: ListingInput = text if has_text else await read_upload(image)  # type: ignore[arg-type]
        name_hint = image.filename if image is not None else None
        return StreamingResponse(
            sse_stream(payload, name_hint),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/reports/{run_id}")
    def download_report(run_id: str) -> JSONResponse:
        """The evidence report of a finished run, as a JSON file."""
        report = store.get(run_id)
        if report is None:
            raise HTTPException(404, "No report is held for this run id.")
        safe_id = "".join(c for c in run_id if c.isalnum() or c in "-_")[:64]
        return JSONResponse(report, headers={"Content-Disposition": f'attachment; filename="claimcheck-report-{safe_id}.json"'})

    return app


app = create_app()
