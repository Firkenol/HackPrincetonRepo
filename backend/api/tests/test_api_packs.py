"""The API with the pack listings (projector, magnifying glass, monocular) beside the battery ones.

Uses a copy of the repo's text fixtures: the nine battery listings and the nine pack
listings. Replay mode only, plus one live run with a scripted runner.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import fixtures, service
from api.app import app, latest_batch
from claimcheck import replay_pack_claims
from claimcheck.models import PackEvidenceReport
from packs.fixtures_data import BY_ID as PACK_FIXTURES
from packs.registry import PACKS

REPO_FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"
BATTERY_IDS = [f"fixture_{n:02d}" for n in range(1, 10)]
PACK_IDS = sorted(f"pack_{f.id}" for f in PACK_FIXTURES.values() if f.pack in PACKS)


@pytest.fixture(scope="module")
def all_fixtures(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("fixtures_with_packs")
    (root / "expected").mkdir()
    for fixture_id in (*BATTERY_IDS, *PACK_IDS, "pack_power_budget_honest"):
        shutil.copyfile(REPO_FIXTURES / f"{fixture_id}.txt", root / f"{fixture_id}.txt")
        shutil.copyfile(REPO_FIXTURES / "expected" / f"{fixture_id}.json", root / "expected" / f"{fixture_id}.json")
    return root


@pytest.fixture(autouse=True)
def _replay(monkeypatch, all_fixtures):
    monkeypatch.setenv(fixtures.FIXTURES_ENV, str(all_fixtures))
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("MODEL_ID", raising=False)
    monkeypatch.delenv(service.REPLAY_ENV, raising=False)
    latest_batch.clear()
    yield
    latest_batch.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def expected_json(fixture_id: str) -> dict:
    return json.loads((REPO_FIXTURES / "expected" / f"{fixture_id}.json").read_text(encoding="utf-8"))


def frames(response) -> list[tuple[str, dict]]:
    out = []
    for block in response.text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def test_pack_listings_are_found_after_the_battery_ones_and_unwired_packs_are_not():
    assert len(PACK_IDS) == 9
    assert [f.id for f in fixtures.list_fixtures()] == [*BATTERY_IDS, *PACK_IDS]
    assert fixtures.get_fixture("pack_power_budget_honest") is None
    assert fixtures.get_fixture("pack_../../secrets") is None
    report = fixtures.get_fixture("pack_magnifier_lens_impossible").expected_report()
    assert isinstance(report, PackEvidenceReport) and report.pack == "magnifier_lens"


def test_samples_list_the_pack_listings(client):
    samples = client.get("/api/samples").json()["samples"]
    assert [s["id"] for s in samples] == [*BATTERY_IDS, *PACK_IDS]
    projector = next(s for s in samples if s["id"] == "pack_projector_resolution_flag")
    assert projector["source"] == "text" and "Native resolution 1280 x 720" in projector["listing_text"]


@pytest.mark.parametrize("fixture_id", PACK_IDS)
def test_a_pack_sample_streams_its_checks_and_its_report(client, fixture_id):
    response = client.post("/api/verify-listing", data={"sample": fixture_id})
    assert response.status_code == 200
    events = frames(response)
    assert events[0] == ("meta", {"mode": "replay", "sample_data": True, "sample_id": fixture_id})
    assert events[-1][0] == "final_report"
    report = events[-1][1]["report"]
    assert report == expected_json(fixture_id)
    pack = PACKS[report["pack"]]
    called = [data["tool"] for name, data in events if name == "tool_call"]
    assert called == [check.__name__ for check in pack.checks]
    assert "verified" not in response.text.lower()


def test_a_pasted_pack_listing_is_matched_in_replay_mode(client):
    text = (REPO_FIXTURES / "pack_monocular_optics_flag.txt").read_text(encoding="utf-8")
    events = frames(client.post("/api/verify-listing", data={"text": text}))
    assert events[-1][0] == "final_report"
    assert events[-1][1]["report"]["verdict"] == "Flag"
    assert events[-1][1]["report"]["pack"] == "monocular_optics"


def test_batch_counts_battery_and_pack_listings_together(client):
    body = client.post("/api/batch").json()
    assert [item["id"] for item in body["items"]] == [*BATTERY_IDS, *PACK_IDS]
    assert all(item["report"] == expected_json(item["id"]) for item in body["items"])
    # nine battery listings: 1 / 2 / 5 / 1. Nine pack listings: 1 / 2 / 3 / 3.
    assert body["counts"]["total"] == 18 and body["counts"]["errors"] == 0
    assert body["counts"]["by_verdict"] == {"Impossible": 2, "Flag": 4, "No red flags": 8, "No checkable claim": 4}
    assert body["counts"]["by_routing"] == {"auto-resolvable": 2, "needs human review": 7, "no action needed": 9}
    stats = client.get("/api/dashboard-stats").json()
    assert stats["listings_checked"] == 18 and stats["impossible_claims"] == 2


def test_live_batch_passes_a_pack_report_through(client, monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "scripted")
    monkeypatch.setenv("MODEL_ID", "scripted")
    by_text = {" ".join(f.listing_text.split()): f for f in PACK_FIXTURES.values() if f.pack in PACKS}

    def runner(listing):
        fixture = by_text.get(" ".join(str(listing).split()))
        if fixture is None:
            return iter(())  # a battery listing: not what this test is about
        return replay_pack_claims(fixture.pack, fixture.claims.model_dump(mode="json"))

    run = service.run_batch(service.LIVE, runner=runner)
    packs = [item for item in run.items if item.id.startswith("pack_")]
    assert len(packs) == 9 and all(isinstance(item.report, PackEvidenceReport) for item in packs)
    assert all(item.as_json()["report"] == expected_json(item.id) for item in packs)
