"""End-to-end runs against a real model. Skipped unless a model is configured.

To run: set MODEL_PROVIDER, MODEL_ID and the provider's own credentials
(see .env.example), then:  pytest agent/tests/test_live.py -m live
"""

from __future__ import annotations

import pytest
from dotenv import load_dotenv

from agent import run_listing
from agent.model import is_configured
from agent.tests.listings import LISTING_TEXT
from tests.fixtures_data import BY_ID

load_dotenv()

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not is_configured(), reason="MODEL_PROVIDER and MODEL_ID are not set"),
]


@pytest.mark.parametrize("fixture_id", [1, 2, 6, 7, 8, 9])
def test_live_fixture(fixture_id):
    events = list(run_listing(LISTING_TEXT[fixture_id]))
    last = events[-1]
    assert last.type == "final_report", getattr(last, "message", "")
    assert last.report.verdict is BY_ID[fixture_id].verdict
    assert last.report.routing is BY_ID[fixture_id].routing
