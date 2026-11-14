"""Check-pack fixtures as hand-entered claims, with expected verdicts.

Two per pack: one honest listing and one impossible one. The listing text is written
for these tests and names no seller, store or brand. Keep ids stable: the expected
report for each fixture is fixtures/expected/pack_<id>.json.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from claimcheck.models import Routing, Verdict
from packs import power_budget as pb
from packs.common import PackReport


@dataclass(frozen=True)
class PackFixture:
    id: str
    pack: str
    listing_text: str
    claims: BaseModel
    evaluate: Callable[[BaseModel], PackReport]
    verdict: Verdict
    routing: Routing


def _heater(watts: float) -> pb.PowerBudgetClaims:
    return pb.PowerBudgetClaims(
        output_power_w=pb.PowerClaim(value=watts, found_in="title", quote=f"{watts:g}W"),
        input_source=pb.InputSourceClaim(
            value=pb.InputSource.US_HOUSEHOLD_OUTLET, found_in="bullet points", quote="standard 120V wall outlet"
        ),
        energy_storage=pb.EnergyStorageClaim(value=pb.EnergyStorage.NONE, found_in="description", quote="corded"),
    )


FIXTURES: list[PackFixture] = [
    PackFixture(
        "power_budget_honest",
        pb.PACK_ID,
        "Portable Ceramic Space Heater, 1500W. Corded, plugs into any standard 120V wall outlet.",
        _heater(1500),
        pb.evaluate,
        Verdict.NO_RED_FLAGS,
        Routing.NO_ACTION_NEEDED,
    ),
    PackFixture(
        "power_budget_impossible",
        pb.PACK_ID,
        "Portable Ceramic Space Heater, 5000W. Corded, plugs into any standard 120V wall outlet.",
        _heater(5000),
        pb.evaluate,
        Verdict.IMPOSSIBLE,
        Routing.AUTO_RESOLVABLE,
    ),
]

BY_ID = {f.id: f for f in FIXTURES}
