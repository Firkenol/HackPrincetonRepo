"""Shared by every check pack: result helpers, the pack report, verdict and routing.

The verdict and routing rules are the ones in claimcheck/verdict.py, restated here
because that module is tied to the battery Claims model. Keep the two in step.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

from claimcheck import policy
from claimcheck.arithmetic import fmt
from claimcheck.constants import Constant
from claimcheck.models import CheckResult, CheckStatus, Citation, Quantity, Routing, Step, Verdict

ClaimsT = TypeVar("ClaimsT", bound=BaseModel)


class PackReport(BaseModel, Generic[ClaimsT]):
    """Evidence report for a check pack.

    Same fields as claimcheck.models.EvidenceReport, plus `pack`. The only other
    difference is that `claims` holds the pack's own claims model.
    """

    schema_version: Literal["1.0"] = "1.0"
    pack: str
    claims: ClaimsT
    checks: list[CheckResult]
    verdict: Verdict
    verdict_reason: str
    routing: Routing
    routing_reason: str
    assumptions: list[str] = Field(default_factory=list)
    not_assessed: list[str] = Field(default_factory=list)


# ----------------------------------------------------------------------- result helpers


def cite(c: Constant) -> Citation:
    return Citation(
        key=c.key,
        value=c.value,
        unit=c.unit,
        description=c.description,
        source_title=c.source.title,
        source_publisher=c.source.publisher,
        source_url=c.source.url,
        locator=c.source.locator,
        quote=c.source.quote,
        accessed=c.source.accessed,
        note=c.note,
        hard_bound=c.hard_bound,
    )


def claim_q(name: str, claim, value: float | str, unit: str = "") -> Quantity:
    return Quantity(
        name=name, value=value, unit=unit, origin="claim", found_in=claim.found_in, confidence=claim.confidence
    )


def const_q(c: Constant) -> Quantity:
    return Quantity(name=c.description, value=c.value, unit=c.unit, origin="constant")


def step(label: str, formula: str, substitution: str, result: float, unit: str) -> Step:
    return Step(
        label=label,
        formula=formula,
        substitution=substitution,
        result=result,
        unit=unit,
        text=f"{label}: {substitution} = {fmt(result)} {unit}".rstrip(),
    )


def stated_step(label: str, symbol: str, value: float, unit: str, how: str) -> Step:
    """A line for a value that is taken as given rather than computed."""
    return Step(
        label=label,
        formula=symbol,
        substitution=how,
        result=value,
        unit=unit,
        text=f"{label}: {fmt(value)} {unit} ({how})",
    )


def comparison(value: float, limit: float, unit: str, limit_name: str) -> Step:
    ratio = value / limit
    sign = ">" if value > limit else "≤"
    return Step(
        label="Comparison",
        formula=f"value ≤ {limit_name}",
        substitution=f"{fmt(value)} {unit} {sign} {fmt(limit)} {unit}",
        result=ratio,
        unit=f"× the {limit_name}",
        text=f"Comparison: {fmt(value)} {unit} {sign} {fmt(limit)} {unit} ({fmt(ratio)}× the {limit_name})",
    )


def not_assessed(
    check_id: str,
    title: str,
    reason: str,
    *,
    inputs: list[Quantity] | None = None,
    notes: list[str] | None = None,
) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        title=title,
        status=CheckStatus.NOT_ASSESSED,
        summary=f"Not assessed. {reason}",
        inputs=inputs or [],
        notes=notes or [],
        not_assessed_reason=reason,
    )


def exceeded(limit: Constant) -> CheckStatus:
    """Status for a claim above a limit: hard only when the limit is a hard bound."""
    return CheckStatus.VIOLATED if limit.hard_bound else CheckStatus.FLAG


# -------------------------------------------------------------------- verdict, routing


def claim_confidences(claims: BaseModel) -> list[float]:
    """Confidence of every claim in a pack's claims model."""
    found: list[float] = []
    for name in type(claims).model_fields:
        value = getattr(claims, name)
        for item in value if isinstance(value, list) else [value]:
            confidence = getattr(item, "confidence", None)
            if confidence is not None:
                found.append(confidence)
    return found


def decide_verdict(checks: Sequence[CheckResult]) -> tuple[Verdict, str]:
    violated = [c for c in checks if c.status is CheckStatus.VIOLATED]
    if violated:
        return Verdict.IMPOSSIBLE, " ".join(c.summary for c in violated)

    flagged = [c for c in checks if c.status is CheckStatus.FLAG]
    if flagged:
        return Verdict.FLAG, " ".join(c.summary for c in flagged)

    passed = [c for c in checks if c.status is CheckStatus.PASS]
    if passed:
        names = ", ".join(c.title for c in passed)
        return (
            Verdict.NO_RED_FLAGS,
            f"The claims that could be tested are physically plausible ({names}). "
            "This does not confirm that the claims are true.",
        )

    return Verdict.NO_CHECKABLE_CLAIM, "The listing states nothing numeric or testable, so no check could run."


def _check_is_confident(check: CheckResult) -> bool:
    return all(
        q.confidence >= policy.MIN_CONFIDENCE
        for q in check.inputs
        if q.origin == "claim" and q.confidence is not None
    )


def decide_routing(
    verdict: Verdict, checks: Sequence[CheckResult], claims: BaseModel, numeric_fields: Sequence[str]
) -> tuple[Routing, str]:
    """Same three outcomes as the battery checks. numeric_fields names the claims that
    count as "a numeric claim was stated" when nothing could be tested."""
    if verdict is Verdict.IMPOSSIBLE:
        violated = [c for c in checks if c.status is CheckStatus.VIOLATED]
        if any(_check_is_confident(c) for c in violated):
            return Routing.AUTO_RESOLVABLE, "A hard physical bound is violated and the calculation is reproducible."
        return (
            Routing.NEEDS_HUMAN_REVIEW,
            "A hard bound is violated, but at least one input was extracted with low confidence. "
            "A person should confirm the extracted values first.",
        )
    if verdict is Verdict.FLAG:
        return Routing.NEEDS_HUMAN_REVIEW, "A contradiction or unusual claim needs a person's judgment."

    if any(conf < policy.MIN_CONFIDENCE for conf in claim_confidences(claims)):
        return (
            Routing.NEEDS_HUMAN_REVIEW,
            "At least one claim was extracted with low confidence, so a person should confirm what the listing states.",
        )
    if verdict is Verdict.NO_CHECKABLE_CLAIM and any(getattr(claims, name) is not None for name in numeric_fields):
        return (
            Routing.NEEDS_HUMAN_REVIEW,
            "The listing states a numeric claim, but the data needed to test it is missing or unusable.",
        )
    if verdict is Verdict.NO_RED_FLAGS:
        return Routing.NO_ACTION_NEEDED, "The claims that could be tested are plausible and were read with high confidence."
    return Routing.NO_ACTION_NEEDED, "The listing states nothing that a calculation can test."


def evaluate_pack(
    pack: str,
    claims: ClaimsT,
    checks: Sequence[Callable[[ClaimsT], CheckResult]],
    numeric_fields: Sequence[str],
) -> PackReport[ClaimsT]:
    """Run a pack's checks on its claims and assemble the report."""
    results = [check(claims) for check in checks]
    verdict, verdict_reason = decide_verdict(results)
    routing, routing_reason = decide_routing(verdict, results, claims, numeric_fields)
    return PackReport[type(claims)](
        pack=pack,
        claims=claims,
        checks=results,
        verdict=verdict,
        verdict_reason=verdict_reason,
        routing=routing,
        routing_reason=routing_reason,
        assumptions=list(dict.fromkeys(a for c in results for a in c.assumptions)),
        not_assessed=[f"{c.title}: {c.not_assessed_reason}" for c in results if c.status is CheckStatus.NOT_ASSESSED],
    )
