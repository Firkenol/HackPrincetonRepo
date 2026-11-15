"""The check packs the agent, the API and the web console know about.

One entry per pack: its id, the words used for it on screen, its claims model, its
checks and its evaluate function. To register a new pack, add it here.

power_budget is not listed: it has checks and tests but is not wired into the agent.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from claimcheck.models import CheckResult
from packs import magnifier_lens, monocular_optics, projector_resolution
from packs.common import PackReport


@dataclass(frozen=True)
class Pack:
    id: str
    label: str  # the product category in plain words, lower case
    claims_model: type[BaseModel]
    checks: tuple[Callable[[BaseModel], CheckResult], ...]
    evaluate: Callable[[BaseModel], PackReport]


PACKS: dict[str, Pack] = {
    pack.id: pack
    for pack in (
        Pack(
            projector_resolution.PACK_ID,
            "projector",
            projector_resolution.ProjectorClaims,
            projector_resolution.CHECKS,
            projector_resolution.evaluate,
        ),
        Pack(
            magnifier_lens.PACK_ID,
            "magnifying glass",
            magnifier_lens.MagnifierClaims,
            magnifier_lens.CHECKS,
            magnifier_lens.evaluate,
        ),
        Pack(
            monocular_optics.PACK_ID,
            "monocular",
            monocular_optics.MonocularClaims,
            monocular_optics.CHECKS,
            monocular_optics.evaluate,
        ),
    )
}
