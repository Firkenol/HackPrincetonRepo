"""POST /api/check and GET /api/reports/{run_id}, against the stub."""

from __future__ import annotations

import logging

import pytest
from claimcheck.events import STREAM_EVENT_ADAPTER

from api import runner, stub
from api.tests.conftest import FIXTURE_IDS, PNG, expected_report, parse_sse

VERDICTS = {"Impossible", "Flag", "No red flags", "No checkable claim"}
ROUTINGS = {"auto-resolvable", "needs human review", "no action needed"}


@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_sample_text_streams_the_recorded_report(client, fixture_id):
    response = client.post("/api/check", data={"text": stub.SAMPLE_TEXTS[fixture_id]})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(response.text)

    for event in events:
        STREAM_EVENT_ADAPTER.validate_python(event)  # every event is one of the contract's five types
    assert [e["seq"] for e in events] == list(range(len(events)))
    assert len({e["run_id"] for e in events}) == 1
    assert [e["type"] for e in events].count("final_report") == 1
    assert events[-1]["type"] == "final_report"

    calls = [e["call_id"] for e in events if e["type"] == "tool_call"]
    results = [e["call_id"] for e in events if e["type"] == "tool_result"]
    assert calls == results and len(calls) == 7  # extraction plus the six checks

    report = events[-1]["report"]
    assert report == expected_report(fixture_id)
    assert report["verdict"] in VERDICTS and report["routing"] in ROUTINGS


def test_screenshot_upload_replays_the_fixture_named_by_the_file(client):
    response = client.post("/api/check", files={"image": ("fixture_03.png", PNG, "image/png")})
    report = parse_sse(response.text)[-1]["report"]
    assert (report["verdict"], report["routing"]) == ("Flag", "needs human review")


def test_screenshot_matching_a_stored_fixture_image_by_content(client, tmp_path, monkeypatch):
    (tmp_path / "expected").symlink_to(expected_report.__globals__["EXPECTED_DIR"])
    (tmp_path / "fixture_01.png").write_bytes(PNG + b"one")
    monkeypatch.setenv("CLAIMCHECK_FIXTURES_DIR", str(tmp_path))
    response = client.post("/api/check", files={"image": ("upload.png", PNG + b"one", "image/png")})
    assert parse_sse(response.text)[-1]["report"]["verdict"] == "Impossible"


def test_unrecorded_listing_ends_in_an_error_event(client):
    events = parse_sse(client.post("/api/check", data={"text": "A listing with no recording."}).text)
    assert events[-1]["type"] == "error"
    assert "nine recorded fixtures" in events[-1]["message"]
    assert [e["seq"] for e in events] == list(range(len(events)))


@pytest.mark.parametrize(
    ("kwargs", "status"),
    [
        ({}, 400),
        ({"data": {"text": "   "}}, 400),
        ({"data": {"text": "fixture 1"}, "files": {"image": ("fixture_01.png", PNG, "image/png")}}, 400),
        ({"files": {"image": ("notes.txt", b"plain text", "text/plain")}}, 415),
        ({"files": {"image": ("renamed.png", b"plain text", "image/png")}}, 415),
    ],
)
def test_bad_requests_are_refused(client, kwargs, status):
    response = client.post("/api/check", **kwargs)
    assert response.status_code == status
    assert isinstance(response.json()["detail"], str)


def test_oversized_screenshot_is_refused(client, monkeypatch):
    monkeypatch.setenv("CLAIMCHECK_MAX_UPLOAD_MB", "0.001")
    response = client.post("/api/check", files={"image": ("fixture_01.png", PNG + b"\x00" * 4096, "image/png")})
    assert response.status_code == 413


def test_jpeg_and_webp_are_accepted(client):
    for name, data in (("fixture_02.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 8), ("fixture_02.webp", b"RIFF\x00\x00\x00\x00WEBPVP8 ")):
        assert parse_sse(client.post("/api/check", files={"image": (name, data)}).text)[-1]["type"] == "final_report"


def test_a_crashing_runner_gives_an_error_event_and_leaks_nothing(client, monkeypatch, caplog):
    def crashes_midway(payload, name_hint):
        for index, event in enumerate(stub.run_listing("fixture 1")):
            if index == 3:
                raise ValueError("Sold by ExampleStore")
            yield event

    monkeypatch.setattr(runner, "_start", crashes_midway)
    with caplog.at_level(logging.DEBUG):
        response = client.post("/api/check", data={"text": "Sold by ExampleStore: 18650 12000mAh"})
    events = parse_sse(response.text)
    assert events[-1] == {**events[-1], "type": "error", "seq": 3, "run_id": events[0]["run_id"], "message": "The listing could not be analysed."}
    assert "ExampleStore" not in response.text
    assert "ExampleStore" not in caplog.text
    assert "ValueError" in caplog.text


def test_a_runner_that_stops_early_still_ends_the_stream_with_an_error(client, monkeypatch):
    monkeypatch.setattr(runner, "_start", lambda payload, name_hint: iter(list(stub.run_listing("fixture 1"))[:2]))
    events = parse_sse(client.post("/api/check", data={"text": "x"}).text)
    assert (events[-1]["type"], events[-1]["seq"]) == ("error", 2)


def test_the_real_agent_is_the_default_and_reports_that_it_is_not_ready(client, monkeypatch):
    # Remove this test when run_listing is implemented in Phase 2.
    monkeypatch.delenv("CLAIMCHECK_RUNNER")
    assert client.get("/api/health").json() == {"status": "ok", "runner": "agent"}
    events = parse_sse(client.post("/api/check", data={"text": stub.SAMPLE_TEXTS[1]}).text)
    assert [e["type"] for e in events] == ["error"]
    assert events[0]["message"] == "Listing analysis is not available in this build."


def test_listing_text_and_file_names_are_not_logged(client, caplog):
    with caplog.at_level(logging.DEBUG):
        client.post("/api/check", data={"text": "ExampleStore fixture 6"})
        client.post("/api/check", files={"image": ("ExampleStore_fixture_06.png", PNG, "image/png")})
    assert "ExampleStore" not in caplog.text
    assert "No red flags, no action needed" in caplog.text


def _keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _keys(child)


@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_no_seller_or_store_field_in_any_event(client, fixture_id):
    events = parse_sse(client.post("/api/check", data={"text": f"fixture {fixture_id}"}).text)
    keys = {key.lower() for key in _keys(events)}
    assert not [k for k in keys if any(word in k for word in ("seller", "store", "brand", "merchant", "vendor"))]


def test_report_download(client):
    events = parse_sse(client.post("/api/check", data={"text": "fixture 6"}).text)
    run_id = events[-1]["run_id"]
    response = client.get(f"/api/reports/{run_id}")
    assert response.status_code == 200
    assert response.json() == expected_report(6)
    assert response.headers["content-type"] == "application/json"
    assert response.headers["content-disposition"] == f'attachment; filename="claimcheck-report-{run_id}.json"'


def test_report_download_for_an_unknown_or_failed_run(client):
    assert client.get("/api/reports/nope").status_code == 404
    events = parse_sse(client.post("/api/check", data={"text": "no recording"}).text)
    assert client.get(f"/api/reports/{events[-1]['run_id']}").status_code == 404


def test_cors_allows_the_local_frontend_only(client):
    preflight = {"Access-Control-Request-Method": "POST"}
    allowed = client.options("/api/check", headers={"Origin": "http://localhost:3000", **preflight})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    refused = client.options("/api/check", headers={"Origin": "http://elsewhere.example", **preflight})
    assert "access-control-allow-origin" not in refused.headers
    simple = client.post("/api/check", data={"text": "fixture 2"}, headers={"Origin": "http://localhost:3000"})
    assert simple.headers["access-control-allow-origin"] == "http://localhost:3000"
