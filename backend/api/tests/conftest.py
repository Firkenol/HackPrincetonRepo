from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import store
from api.app import create_app

EXPECTED_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "expected"
FIXTURE_IDS = range(1, 10)
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16  # passes the image check; the stub never decodes it


def expected_report(fixture_id: int) -> dict:
    return json.loads((EXPECTED_DIR / f"fixture_{fixture_id:02d}.json").read_text(encoding="utf-8"))


def parse_sse(body: str) -> list[dict]:
    """Splits an SSE body into events and checks the framing the contract describes."""
    events = []
    for frame in body.strip().split("\n\n"):
        event_line, data_line = frame.split("\n")
        data = json.loads(data_line.removeprefix("data: "))
        assert event_line == f"event: {data['type']}"
        events.append(data)
    return events


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("CLAIMCHECK_RUNNER", "stub")
    monkeypatch.setenv("CLAIMCHECK_STUB_DELAY_MS", "0")
    monkeypatch.delenv("CLAIMCHECK_FIXTURES_DIR", raising=False)
    store.clear()
    return TestClient(create_app())
