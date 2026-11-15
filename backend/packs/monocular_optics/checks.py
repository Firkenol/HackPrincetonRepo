"""Monocular checks: an "80x100"-style figure against the listed body size and the fine print.

Design rules (the same as claimcheck/checks.py):
- Arithmetic is done here in Python and recorded step by step.
- When something needed is missing or unclear, the check says NOT_ASSESSED and
  explains why. It never guesses.
- Listed package dimensions are unreliable and are never used as a bound.
- Wording is about the claim, never about whoever listed the product.

Check A. The objective lens sits across the body, so it cannot be wider than the body.
         The geometry is hard, but the body width comes from listed dimensions, which
         are often wrong or describe something else, so the result is a flag (owner's
         decision, 2026-11-14): a listing whose own figures cannot both be right goes
         to a person rather than being closed automatically.
Check B. A headline figure that differs from the "actual" figure in the fine print is
         a contradiction inside the listing. A flag, like the battery label checks.
"""

from __future__ import annotations

from claimcheck.arithmetic import fmt
from claimcheck.models import CheckResult, CheckStatus, MeasurementKind, Quantity, Step
from packs.common import PackReport, claim_q, comparison, evaluate_pack, not_assessed, stated_step, step
from packs.monocular_optics.models import MonocularClaims

PACK_ID = "monocular_optics"
OBJECTIVE_FITS_BODY = "objective_fits_body"
FINE_PRINT_CONSISTENCY = "fine_print_consistency"
TITLES: dict[str, str] = {
    OBJECTIVE_FITS_BODY: "Objective lens against body width",
    FINE_PRINT_CONSISTENCY: "Headline figures against the fine print",
}

# TEAM POLICY, NOT PHYSICS. Listed dimensions are rounded, often to the nearest
# millimetre or tenth of an inch. Two figures within this relative difference are
# treated as equal. The same 3% is used for the battery label check
# (claimcheck.policy.LABEL_WH_RELATIVE_TOLERANCE).
ROUNDING_TOLERANCE = 0.03


def check_objective_fits_body(claims: MonocularClaims) -> CheckResult:
    """The claimed objective diameter must not exceed the width of the listed body."""
    cid, title = OBJECTIVE_FITS_BODY, TITLES[OBJECTIVE_FITS_BODY]
    objective, body = claims.objective_mm, claims.body_dimensions

    if objective is None:
        return not_assessed(cid, title, "No objective lens diameter is stated.")
    inputs: list[Quantity] = [claim_q("Claimed objective diameter", objective, objective.value, "mm")]
    if body is None:
        return not_assessed(cid, title, "The listing does not state the dimensions of the monocular.", inputs=inputs)

    sides = sorted((body.length_mm, body.width_mm, body.height_mm), reverse=True)
    dims_text = f"{fmt(body.length_mm)} × {fmt(body.width_mm)} × {fmt(body.height_mm)} mm"
    inputs.append(claim_q("Listed dimensions", body, dims_text))
    if body.kind is MeasurementKind.PACKAGE:
        return not_assessed(
            cid,
            title,
            "Only package dimensions are stated. They describe the box, not the monocular, so they are not used.",
            inputs=inputs,
            notes=["The listed dimensions are package dimensions and were set aside."],
        )

    width_mm = sides[1]
    limit_mm = width_mm * (1 + ROUNDING_TOLERANCE)
    ratio = objective.value / width_mm
    over = objective.value > limit_mm

    if over:
        summary = (
            f"The listing claims a {fmt(objective.value)} mm objective lens, and gives body dimensions of "
            f"{dims_text}. The lens sits across the body, whose width is at most {fmt(width_mm)} mm. The "
            f"claimed lens is {fmt(ratio)}× that width, so the two figures cannot both be right. "
            "Listed dimensions are often inexact, so this is reported as a flag for a person to check."
        )
    else:
        summary = (
            f"The claimed {fmt(objective.value)} mm objective lens fits within the listed body width of "
            f"{fmt(width_mm)} mm."
        )
    return CheckResult(
        check_id=cid,
        title=title,
        status=CheckStatus.FLAG if over else CheckStatus.PASS,
        summary=summary,
        inputs=[
            *inputs,
            Quantity(name="Rounding tolerance", value=ROUNDING_TOLERANCE * 100, unit="%", origin="assumption"),
        ],
        formula="D_objective ≤ body width × (1 + rounding tolerance)",
        steps=[
            stated_step(
                "Body width available to the lens", "W", width_mm, "mm", "the second-longest listed side"
            ),
            step(
                "Body width with the rounding tolerance",
                "W_max = W × (1 + tolerance)",
                f"{fmt(width_mm)} mm × {fmt(1 + ROUNDING_TOLERANCE)}",
                limit_mm,
                "mm",
            ),
            comparison(objective.value, limit_mm, "mm", "limit"),
        ],
        assumptions=[
            "The objective lens faces along the longest side of the body, so it has to fit within the other "
            "two sides. The second-longest listed side is used as the width, which is the most lenient.",
            f"Listed dimensions are treated as rounded: a lens up to {fmt(ROUNDING_TOLERANCE * 100)}% wider "
            "than the listed width passes. This tolerance is a team choice, not a physical constant.",
            "The listed dimensions are taken to describe the monocular itself, as the listing states. Because "
            "listed dimensions can be wrong, exceeding this bound is reported as a flag, not a hard result.",
        ],
    )


def check_fine_print_consistency(claims: MonocularClaims) -> CheckResult:
    """Headline magnification and objective must match any 'actual' figure in the fine print."""
    cid, title = FINE_PRINT_CONSISTENCY, TITLES[FINE_PRINT_CONSISTENCY]
    pairs = [
        ("magnification", "×", claims.magnification, claims.fine_print_magnification),
        ("objective diameter", "mm", claims.objective_mm, claims.fine_print_objective_mm),
    ]
    inputs: list[Quantity] = []
    steps: list[Step] = []
    differing: list[str] = []
    matching: list[str] = []
    for name, unit, headline, fine in pairs:
        if headline is None or fine is None:
            continue
        ratio = headline.value / fine.value
        inputs += [
            claim_q(f"Headline {name}", headline, headline.value, unit),
            claim_q(f"Fine-print {name}", fine, fine.value, unit),
        ]
        steps.append(
            step(
                f"Headline {name} divided by the fine-print value",
                "ratio = headline ÷ fine print",
                f"{fmt(headline.value)} ÷ {fmt(fine.value)}",
                ratio,
                "×",
            )
        )
        text = f"{name} {fmt(headline.value)} {unit} in the headline and {fmt(fine.value)} {unit} in the fine print"
        if abs(ratio - 1) > ROUNDING_TOLERANCE:
            differing.append(f"{text} ({fmt(ratio)}×)")
        else:
            matching.append(text)

    if not steps:
        return not_assessed(
            cid, title, "The listing states no separate 'actual' magnification or objective size to compare with the headline."
        )
    if differing:
        summary = (
            f"The listing gives two different figures for the same property: {'; '.join(differing)}. "
            "The listing contradicts itself, which is reported as a flag."
        )
    else:
        summary = f"The headline and the fine print agree: {'; '.join(matching)}."
    return CheckResult(
        check_id=cid,
        title=title,
        status=CheckStatus.FLAG if differing else CheckStatus.PASS,
        summary=summary,
        inputs=[
            *inputs,
            Quantity(name="Rounding tolerance", value=ROUNDING_TOLERANCE * 100, unit="%", origin="assumption"),
        ],
        formula="ratio = headline value ÷ fine-print value; the two agree when the ratio is within the tolerance of 1",
        steps=steps,
        assumptions=[
            f"Two figures within {fmt(ROUNDING_TOLERANCE * 100)}% of each other are treated as equal. "
            "This tolerance is a team choice, not a physical constant."
        ],
    )


# ----------------------------------------------------------------------------- runner

CHECKS = (check_objective_fits_body, check_fine_print_consistency)

# Claims that count as "a numeric claim was stated" when nothing could be tested.
NUMERIC_FIELDS = ("magnification", "objective_mm")


def evaluate(claims: MonocularClaims) -> PackReport[MonocularClaims]:
    """Run the pack on extracted claims and assemble the report."""
    return evaluate_pack(PACK_ID, claims, CHECKS, NUMERIC_FIELDS)
