"""The Carnot API, tested through FastAPI's test client. No network, no real model.

Replay mode needs no model at all. Live mode is tested with the real agent driven by
the scripted model from agent/tests, so a request goes through the routes, run_listing,
the three subagents and the checks.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import agent
from agent.tests.fake_model import ScriptedChatModel, full_script
from agent.tests.listings import LISTING_TEXT
from api import app as app_module
from api import fixtures, service
from claimcheck.events import STREAM_EVENT_ADAPTER
from claimcheck.models import EvidenceReport
from tests.fixtures_data import BY_ID

REPO_FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"
FIXTURE_IDS = [f"fixture_{n:02d}" for n in range(1, 10)]
VERDICTS = {"Impossible", "Flag", "No red flags", "No checkable claim"}
ROUTINGS = {"auto-resolvable", "needs human review", "no action needed"}
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32

EXPECTED_COUNTS = {
    "by_verdict": {"Impossible": 1, "Flag": 2, "No red flags": 5, "No checkable claim": 1},
    "by_routing": {"auto-resolvable": 1, "needs human review": 2, "no action needed": 6},
}


def expected_json(fixture_id: str) -> dict:
    return json.loads((REPO_FIXTURES / "expected" / f"{fixture_id}.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.delenv(fixtures.FIXTURES_ENV, raising=False)
    monkeypatch.delenv(service.REPLAY_ENV, raising=False)
    app_module.latest_batch.clear()
    yield
    app_module.latest_batch.clear()


@pytest.fixture
def replay(monkeypatch) -> TestClient:
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("MODEL_ID", raising=False)
    return TestClient(app_module.app)


def scripted_runner(listing):
    """run_listing on the real agent, with a scripted model that reads the fixture correctly."""
    if isinstance(listing, Path):
        number = int(listing.stem[-2:])
    else:
        number = next((n for n, text in LISTING_TEXT.items() if text.split() == str(listing).split()), None)
    if number is None:
        return agent.run_listing(listing, model=ScriptedChatModel(script=[]))
    return agent.run_listing(listing, model=ScriptedChatModel(script=full_script(BY_ID[number].claims)))


@pytest.fixture
def live(monkeypatch) -> TestClient:
    monkeypatch.setenv("MODEL_PROVIDER", "scripted")
    monkeypatch.setenv("MODEL_ID", "scripted")
    monkeypatch.setattr(service, "run_listing", scripted_runner)
    return TestClient(app_module.app)


def frames(response) -> list[tuple[str, dict]]:
    """The SSE messages of a response as (event name, data)."""
    out = []
    for block in response.text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def check_stream(response, mode: str):
    """Assert the stream is well formed and return (meta, contract events)."""
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers[app_module.MODE_HEADER] == mode
    all_frames = frames(response)
    name, meta = all_frames[0]
    assert name == "meta" and meta["mode"] == mode and meta["sample_data"] is (mode == "replay")
    events = []
    for name, data in all_frames[1:]:
        event = STREAM_EVENT_ADAPTER.validate_python(data)
        assert event.type == name
        events.append(event)
    assert [e.seq for e in events] == list(range(len(events)))
    assert events[-1].type in ("final_report", "error")
    assert sum(e.type in ("final_report", "error") for e in events) == 1
    return meta, events


# ----------------------------------------------------------------------- the files


def test_fixture_text_files_match_the_listings_the_agent_tests_use():
    for number, text in LISTING_TEXT.items():
        on_disk = (REPO_FIXTURES / f"fixture_{number:02d}.txt").read_text(encoding="utf-8")
        assert on_disk == text


def test_all_nine_fixtures_are_found():
    found = fixtures.list_fixtures()
    assert [f.id for f in found] == FIXTURE_IDS
    assert all(f.expected_path and (f.text_path or f.image_path) for f in found)


# -------------------------------------------------------------------------- mode


def test_mode_is_replay_without_a_model_and_live_with_one(monkeypatch):
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("MODEL_ID", raising=False)
    assert service.current_mode() == "replay"
    monkeypatch.setenv("MODEL_PROVIDER", "some_provider")
    assert service.current_mode() == "replay"  # both are needed
    monkeypatch.setenv("MODEL_ID", "some-model")
    assert service.current_mode() == "live"
    monkeypatch.setenv(service.REPLAY_ENV, "1")
    assert service.current_mode() == "replay"


def test_every_json_response_is_marked(replay):
    for method, path in [("get", "/api/health"), ("get", "/api/dashboard-stats"), ("get", "/api/samples"), ("post", "/api/batch")]:
        response = getattr(replay, method)(path)
        assert response.status_code == 200, path
        assert response.json()["mode"] == "replay" and response.json()["sample_data"] is True, path
        assert response.headers[app_module.MODE_HEADER] == "replay", path


def test_live_responses_are_not_marked_as_sample_data(live):
    for path in ("/api/health", "/api/dashboard-stats", "/api/samples"):
        body = live.get(path).json()
        assert body["mode"] == "live" and body["sample_data"] is False


# ------------------------------------------------------- verify-listing, replay mode


@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_replay_sample_streams_the_expected_report(replay, fixture_id):
    meta, events = check_stream(replay.post("/api/verify-listing", data={"sample": fixture_id}), "replay")
    assert meta["sample_id"] == fixture_id
    assert events[-1].type == "final_report"
    assert json.loads(events[-1].report.model_dump_json()) == expected_json(fixture_id)
    assert sum(e.type == "tool_result" for e in events) == 6


@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_replay_recognises_a_pasted_fixture_text(replay, fixture_id):
    text = (REPO_FIXTURES / f"{fixture_id}.txt").read_text(encoding="utf-8")
    _, events = check_stream(replay.post("/api/verify-listing", data={"text": "  " + text.replace("\n", "\r\n")}), "replay")
    assert json.loads(events[-1].report.model_dump_json()) == expected_json(fixture_id)


def test_replay_does_not_pass_a_sample_report_off_as_the_result_for_another_listing(replay):
    _, events = check_stream(replay.post("/api/verify-listing", data={"text": "Some other battery, 99999mAh"}), "replay")
    assert [e.type for e in events] == ["error"]
    assert events[0].message == service.MSG_REPLAY_ONLY

    _, events = check_stream(replay.post("/api/verify-listing", files={"image": ("shot.png", PNG, "image/png")}), "replay")
    assert [e.type for e in events] == ["error"]


def test_replay_recognises_a_fixture_screenshot(replay, tmp_path, monkeypatch):
    (tmp_path / "expected").mkdir()
    (tmp_path / "expected" / "fixture_03.json").write_text(json.dumps(expected_json("fixture_03")), encoding="utf-8")
    (tmp_path / "fixture_03.png").write_bytes(PNG)
    monkeypatch.setenv(fixtures.FIXTURES_ENV, str(tmp_path))

    _, events = check_stream(replay.post("/api/verify-listing", files={"image": ("anything.png", PNG, "image/png")}), "replay")
    assert events[-1].report.verdict.value == "Flag"

    image = replay.get("/api/fixtures/fixture_03.png")
    assert image.status_code == 200 and image.content == PNG and image.headers["content-type"] == "image/png"
    samples = replay.get("/api/samples").json()["samples"]
    assert samples == [
        {"id": "fixture_03", "source": "image", "listing_text": None, "image_url": "/api/fixtures/fixture_03.png", "has_expected_report": True}
    ]


# --------------------------------------------------------- verify-listing, live mode


@pytest.mark.parametrize("fixture_id", FIXTURE_IDS)
def test_live_text_runs_the_agent_and_streams_its_events(live, fixture_id):
    text = (REPO_FIXTURES / f"{fixture_id}.txt").read_text(encoding="utf-8")
    meta, events = check_stream(live.post("/api/verify-listing", data={"text": text}), "live")
    assert meta["sample_id"] is None
    assert json.loads(events[-1].report.model_dump_json()) == expected_json(fixture_id)
    assert {e.agent for e in events} == {"orchestrator", "listing-reader", "physics-checker", "report-writer"}


def test_live_sample_runs_the_fixture_file(live):
    meta, events = check_stream(live.post("/api/verify-listing", data={"sample": "fixture_01"}), "live")
    assert meta["sample_id"] == "fixture_01" and meta["sample_data"] is False
    assert events[-1].report.verdict.value == "Impossible"


def test_live_image_upload_reaches_run_listing_as_bytes(monkeypatch, live):
    seen = []

    def runner(listing):
        seen.append(listing)
        return agent.run_listing(listing, model=ScriptedChatModel(script=full_script(BY_ID[3].claims)))

    monkeypatch.setattr(service, "run_listing", runner)
    _, events = check_stream(live.post("/api/verify-listing", files={"image": ("Some Store screenshot.png", PNG, "image/png")}), "live")
    assert seen == [PNG]
    assert events[-1].report.verdict.value == "Flag"
    assert "Some Store" not in "".join(e.model_dump_json() for e in events)


def test_a_failed_run_ends_the_stream_with_one_error_event(live):
    _, events = check_stream(live.post("/api/verify-listing", data={"text": "not a fixture"}), "live")
    assert events[-1].type == "error"

    _, events = check_stream(live.post("/api/verify-listing", files={"image": ("x.gif", b"GIF89a....", "image/gif")}), "live")
    assert [e.type for e in events] == ["error"]
    assert events[0].message == "The image must be a PNG, JPEG or WebP file."


def test_a_run_that_raises_still_ends_with_an_error_event(monkeypatch, live):
    def runner(listing):
        raise RuntimeError("boom: internal detail")
        yield  # pragma: no cover

    monkeypatch.setattr(service, "run_listing", runner)
    response = live.post("/api/verify-listing", data={"text": "anything"})
    _, events = check_stream(response, "live")
    assert [e.type for e in events] == ["error"]
    assert events[0].message == app_module.MSG_STREAM_FAILED and "boom" not in response.text


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"data": {"text": "   "}},
        {"data": {"text": "a", "sample": "fixture_01"}},
        {"data": {"text": "a"}, "files": {"image": ("x.png", PNG, "image/png")}},
    ],
    ids=["nothing", "blank-text", "text-and-sample", "text-and-image"],
)
def test_exactly_one_input_is_required(replay, kwargs):
    assert replay.post("/api/verify-listing", **kwargs).status_code == 400


def test_unknown_or_malformed_sample_is_404(replay):
    assert replay.post("/api/verify-listing", data={"sample": "fixture_77"}).status_code == 404
    assert replay.post("/api/verify-listing", data={"sample": "../../.env"}).status_code == 404


def test_an_oversized_upload_is_refused(replay):
    big = PNG + b"\x00" * app_module.MAX_UPLOAD_BYTES
    assert replay.post("/api/verify-listing", files={"image": ("x.png", big, "image/png")}).status_code == 413


@pytest.mark.parametrize("name", ["..%2F..%2F.env", "fixture_01.txt", "fixture_01.png", "expected", "fixture_01.json"])
def test_the_fixture_route_serves_only_fixture_screenshots(replay, name):
    assert replay.get(f"/api/fixtures/{name}").status_code == 404


# ------------------------------------------------------------------------- batch


def check_batch(body: dict, mode: str):
    assert body["mode"] == mode and body["sample_data"] is (mode == "replay")
    assert [item["id"] for item in body["items"]] == FIXTURE_IDS
    for item in body["items"]:
        assert item["error"] is None
        assert item["report"] == expected_json(item["id"])
        EvidenceReport.model_validate(item["report"])
        assert item["source"] == "text" and item["listing_text"] and item["image_url"] is None
    assert body["counts"] == {"total": 9, "errors": 0, **EXPECTED_COUNTS}
    assert set(body["counts"]["by_verdict"]) == VERDICTS and set(body["counts"]["by_routing"]) == ROUTINGS


def test_replay_batch_serves_every_expected_report_with_counts(replay):
    check_batch(replay.post("/api/batch").json(), "replay")


def test_live_batch_runs_every_fixture_file_through_the_agent(live):
    check_batch(live.post("/api/batch").json(), "live")


def test_live_batch_reports_a_failed_listing_without_failing_the_batch(monkeypatch, live):
    def runner(listing):
        if "fixture_02" in str(listing) or str(listing).split() == LISTING_TEXT[2].split():
            raise RuntimeError("boom")
        return scripted_runner(listing)

    monkeypatch.setattr(service, "run_listing", runner)
    body = live.post("/api/batch").json()
    failed = next(item for item in body["items"] if item["id"] == "fixture_02")
    assert failed["report"] is None and failed["error"] == service.MSG_BATCH_ITEM_FAILED
    assert body["counts"]["total"] == 8 and body["counts"]["errors"] == 1
    assert body["counts"]["by_verdict"]["No red flags"] == 4


def test_no_seller_or_store_field_in_any_api_response(replay):
    bodies = [replay.post("/api/batch").text, replay.get("/api/samples").text, replay.get("/api/dashboard-stats").text]

    def keys(node):
        if isinstance(node, dict):
            for key, value in node.items():
                yield key
                yield from keys(value)
        elif isinstance(node, list):
            for item in node:
                yield from keys(item)

    for body in bodies:
        for key in keys(json.loads(body)):
            assert not any(word in key.lower() for word in ("seller", "store", "brand", "vendor", "merchant")), key
        assert "verified" not in body.lower()


# ---------------------------------------------------------------- dashboard stats


def test_stats_before_any_batch_run_carry_no_numbers(replay):
    body = replay.get("/api/dashboard-stats").json()
    assert body["has_run"] is False and body["ran_at"] is None
    for key in ("listings_checked", "impossible_claims", "routed_to_human_review", "no_action_needed", "auto_resolvable"):
        assert body[key] is None


def test_stats_are_counted_from_the_latest_batch_run(replay):
    batch = replay.post("/api/batch").json()
    body = replay.get("/api/dashboard-stats").json()

    reports = [item["report"] for item in batch["items"]]
    assert body["has_run"] is True and body["ran_at"] == batch["ran_at"]
    assert body["listings_checked"] == len(reports) == 9
    assert body["impossible_claims"] == sum(r["verdict"] == "Impossible" for r in reports) == 1
    assert body["routed_to_human_review"] == sum(r["routing"] == "needs human review" for r in reports) == 2
    assert body["no_action_needed"] == sum(r["routing"] == "no action needed" for r in reports) == 6
    assert body["auto_resolvable"] == sum(r["routing"] == "auto-resolvable" for r in reports) == 1
    assert body["by_verdict"] == batch["counts"]["by_verdict"] and body["by_routing"] == batch["counts"]["by_routing"]


def test_stats_follow_the_fixtures_folder_not_fixed_numbers(replay, tmp_path, monkeypatch):
    (tmp_path / "expected").mkdir()
    for fixture_id in ("fixture_01", "fixture_03"):
        (tmp_path / "expected" / f"{fixture_id}.json").write_text(json.dumps(expected_json(fixture_id)), encoding="utf-8")
    monkeypatch.setenv(fixtures.FIXTURES_ENV, str(tmp_path))

    replay.post("/api/batch")
    body = replay.get("/api/dashboard-stats").json()
    assert (body["listings_checked"], body["impossible_claims"], body["routed_to_human_review"], body["no_action_needed"]) == (2, 1, 1, 0)


def test_stats_keep_the_marking_of_the_run_they_came_from(replay, monkeypatch):
    replay.post("/api/batch")
    monkeypatch.setenv("MODEL_PROVIDER", "scripted")
    monkeypatch.setenv("MODEL_ID", "scripted")
    body = replay.get("/api/dashboard-stats").json()
    assert body["sample_data"] is True and body["mode"] == "replay"


def test_cors_allows_the_local_web_app(replay):
    response = replay.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert app_module.MODE_HEADER.lower() in response.headers["access-control-expose-headers"].lower()
