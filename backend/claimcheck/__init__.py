"""OffSpec: checks whether a battery listing's own claims are physically possible.

Module map (each file has one job, so people can work in parallel):

- constants.py   Physical reference data. Every value carries a source citation.
- policy.py      Thresholds the team chose (tolerances, routing defaults). Not physics.
- models.py      Shared data contract: Claims in, CheckResult / EvidenceReport out.
- arithmetic.py  Plain numeric helpers. All math lives in Python, never in the model.
- checks.py      The six checks. Each takes Claims and returns a CheckResult.
- verdict.py     Combines check results into a verdict, routing and evidence report.
- events.py      Stream events sent to the browser.
- pipeline.py    run_listing, the one entry point the API calls.

models.py, events.py and the run_listing signature are a frozen contract.
See CONTRACT.md at the repo root before changing them.
"""

from claimcheck.models import Claims, EvidenceReport, Routing, Verdict
from claimcheck.pipeline import replay_claims, replay_pack_claims, run_listing
from claimcheck.verdict import evaluate

__all__ = ["Claims", "EvidenceReport", "Routing", "Verdict", "evaluate", "replay_claims", "replay_pack_claims", "run_listing"]
