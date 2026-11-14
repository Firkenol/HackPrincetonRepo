"""Combine check results into a verdict, a routing label and the evidence report."""

from __future__ import annotations

from claimcheck import policy
from claimcheck.checks import (
    CHEMISTRY_MISMATCH,
    DIMENSION_BOUND,
    FORM_FACTOR_BOUND,
    LABEL_CONSISTENCY,
    WEIGHT_BOUND,
    run_all_checks,
)
from claimcheck.models import CheckResult, CheckStatus, Claims, EvidenceReport, Routing, Verdict

# A pass on one of these means a stated claim was tested and is plausible.
# The label-contradiction check is left out on purpose: markings that agree with the
# title are recorded, but agreement alone is not a tested claim. This keeps the tool
# quiet on listings that state nothing numeric.
CHECKS_THAT_TEST_A_CLAIM = frozenset(
    {LABEL_CONSISTENCY, FORM_FACTOR_BOUND, DIMENSION_BOUND, WEIGHT_BOUND, CHEMISTRY_MISMATCH}
)


def decide_verdict(checks: list[CheckResult]) -> tuple[Verdict, str]:
    violated = [c for c in checks if c.status is CheckStatus.VIOLATED]
    if violated:
        return Verdict.IMPOSSIBLE, " ".join(c.summary for c in violated)

    flagged = [c for c in checks if c.status is CheckStatus.FLAG]
    if flagged:
        return Verdict.FLAG, " ".join(c.summary for c in flagged)

    passed = [c for c in checks if c.status is CheckStatus.PASS and c.check_id in CHECKS_THAT_TEST_A_CLAIM]
    if passed:
        names = ", ".join(c.title for c in passed)
        return (
            Verdict.NO_RED_FLAGS,
            f"The claims that could be tested are physically plausible ({names}). "
            "This does not confirm that the claims are true.",
        )

    return Verdict.NO_CHECKABLE_CLAIM, "The listing states nothing numeric or testable, so no check could run."


def _confident(check: CheckResult) -> bool:
    return all(
        q.confidence >= policy.MIN_CONFIDENCE_FOR_AUTO_RESOLVE
        for q in check.inputs
        if q.origin == "claim" and q.confidence is not None
    )


def decide_routing(verdict: Verdict, checks: list[CheckResult]) -> tuple[Routing, str]:
    if verdict is Verdict.IMPOSSIBLE:
        violated = [c for c in checks if c.status is CheckStatus.VIOLATED]
        if any(_confident(c) for c in violated):
            return Routing.AUTO_RESOLVABLE, "A hard physical bound is violated and the calculation is reproducible."
        return (
            Routing.NEEDS_HUMAN_REVIEW,
            "A hard bound is violated, but at least one input was extracted with low confidence. "
            "A person should confirm the extracted values first.",
        )
    if verdict is Verdict.FLAG:
        return Routing.NEEDS_HUMAN_REVIEW, "A contradiction or unusual claim needs a person's judgment."
    if verdict is Verdict.NO_RED_FLAGS:
        return Routing(policy.ROUTING_WHEN_NO_RED_FLAGS), "Passing the checks does not settle whether the claims are true."
    return Routing(policy.ROUTING_WHEN_NO_CHECKABLE_CLAIM), "Nothing in the listing could be tested by calculation."


def evaluate(claims: Claims) -> EvidenceReport:
    """Run every check on the extracted claims and assemble the evidence report."""
    checks = run_all_checks(claims)
    verdict, verdict_reason = decide_verdict(checks)
    routing, routing_reason = decide_routing(verdict, checks)

    assumptions = list(dict.fromkeys(a for c in checks for a in c.assumptions))
    not_assessed = [f"{c.title}: {c.not_assessed_reason}" for c in checks if c.status is CheckStatus.NOT_ASSESSED]

    return EvidenceReport(
        claims=claims,
        checks=checks,
        verdict=verdict,
        verdict_reason=verdict_reason,
        routing=routing,
        routing_reason=routing_reason,
        assumptions=assumptions,
        not_assessed=not_assessed,
    )
