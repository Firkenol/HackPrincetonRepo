"""End-to-end runs against a real model. Skipped unless a model is configured.

To run: set MODEL_PROVIDER, MODEL_ID and the provider's own credentials
(see .env.example), then:  pytest agent/tests/test_live.py

Image tests also need the screenshot for the fixture, saved as
fixtures/fixture_NN.png (or .jpg, .jpeg, .webp) with any seller name blurred.
A fixture without a screenshot is skipped.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from dotenv import load_dotenv

from agent import run_listing
from agent.model import is_configured
from agent.tests.listings import LISTING_TEXT
from claimcheck.checks import parse_iec_code
from claimcheck.policy import MIN_CONFIDENCE
from claimcheck.verdict import claim_confidences
from tests.fixtures_data import BY_ID, FIXTURES

load_dotenv()

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not is_configured(), reason="MODEL_PROVIDER and MODEL_ID are not set"),
]


def screenshot(fixture_id: int) -> Path | None:
    for suffix in ("png", "jpg", "jpeg", "webp"):
        path = FIXTURES_DIR / f"fixture_{fixture_id:02d}.{suffix}"
        if path.exists():
            return path
    return None


def final_report(listing):
    last = list(run_listing(listing))[-1]
    assert last.type == "final_report", getattr(last, "message", "")
    return last.report


@pytest.mark.parametrize("fixture_id", sorted(LISTING_TEXT))
def test_live_text_fixture(fixture_id):
    report = final_report(LISTING_TEXT[fixture_id])
    assert report.verdict is BY_ID[fixture_id].verdict
    assert report.routing is BY_ID[fixture_id].routing


@pytest.mark.parametrize("fixture", FIXTURES, ids=[f"fixture_{f.id}" for f in FIXTURES])
def test_live_image_fixture(fixture):
    path = screenshot(fixture.id)
    if path is None:
        pytest.skip(f"no screenshot at fixtures/fixture_{fixture.id:02d}.png")

    report = final_report(path)
    assert report.verdict is fixture.verdict
    # every claim says where it was found and how sure the reader was
    assert all(0 <= confidence <= 1 for confidence in claim_confidences(report.claims))
    if all(confidence >= MIN_CONFIDENCE for confidence in claim_confidences(report.claims)):
        assert report.routing is fixture.routing
    else:
        assert report.routing.value == "needs human review"


def test_live_fixture_3_reads_the_codes_printed_on_the_cells():
    path = screenshot(3)
    if path is None:
        pytest.skip("no screenshot at fixtures/fixture_03.png")

    report = final_report(path)
    assert report.verdict.value == "Flag"
    assert report.routing.value == "needs human review"
    systems = {parsed[1] for code in report.claims.printed_codes if (parsed := parse_iec_code(code.value))}
    assert "zinc-carbon" in systems
    assert all(code.found_in for code in report.claims.printed_codes)
