"""Magnifier check: claimed magnifying power against the diameter of the lens.

Design rules (the same as claimcheck/checks.py):
- Arithmetic is done here in Python and recorded step by step.
- When something needed is missing or unclear, the check says NOT_ASSESSED and
  explains why. It never guesses.
- Wording is about the claim, never about whoever listed the product.

The reasoning, in two lines:
- Magnifying power fixes focal length: f = 250 mm ÷ M.
- A symmetric biconvex lens of index 1.5 has a focal length equal to its radius of
  curvature, and a lens cannot be wider than the sphere its surface is cut from. So
  its diameter cannot exceed 2 × f.

The bound does not apply to a Fresnel or flat sheet lens, which is reported as not
assessed.
"""

from __future__ import annotations

from claimcheck.arithmetic import fmt
from claimcheck.models import CheckResult, CheckStatus, Quantity
from packs.common import PackReport, cite, claim_q, comparison, const_q, evaluate_pack, not_assessed, step
from packs.magnifier_lens import constants as K
from packs.magnifier_lens.models import LensType, MagnifierClaims

PACK_ID = "magnifier_lens"
LENS_DIAMETER = "lens_diameter"
TITLES: dict[str, str] = {LENS_DIAMETER: "Lens diameter against claimed magnification"}

# TEAM POLICY, NOT PHYSICS. The 2 × f limit assumes glass of index 1.5. Denser glass
# allows a wider lens for the same focal length (up to 4 × f at index 2.0), and some
# makers quote power as 250 ÷ f + 1. A diameter above the limit but within this factor
# of it is therefore a flag. Only a diameter beyond it is reported as a hard result.
# The factor was chosen by the team; it has no source.
HARD_RESULT_MARGIN = 2.0

_ASSUMPTIONS = [
    "The lens is taken to be a single lens with two equally curved faces, made of material with a "
    f"refractive index of {fmt(K.REFERENCE_INDEX)}. For such a lens the focal length equals the radius of "
    f"curvature (lens maker's equation, {K.LENS_MAKERS_EQUATION_REFERENCE}). The index is an assumption "
    "with no cited source.",
    "A lens cannot be wider than the sphere its curved surface is part of, so its diameter cannot exceed "
    "twice the radius of curvature.",
    "Magnifying power is taken as 250 mm ÷ focal length, the convention for an image at infinity.",
    f"A diameter up to {fmt(HARD_RESULT_MARGIN)}× the limit is reported as a flag, not a hard result, to "
    "allow for denser glass and for the other convention for magnifying power. This margin is a team "
    "choice, not a physical constant.",
]


def check_lens_diameter(claims: MagnifierClaims) -> CheckResult:
    """Listed lens diameter must not exceed twice the focal length the claimed power implies."""
    cid, title = LENS_DIAMETER, TITLES[LENS_DIAMETER]
    power, diameter, lens_type = claims.magnification, claims.lens_diameter_mm, claims.lens_type

    if power is None:
        return not_assessed(cid, title, "No magnification is stated.")
    inputs: list[Quantity] = [claim_q("Claimed magnification", power, power.value, "×")]

    if lens_type is not None:
        inputs.append(claim_q("Lens type", lens_type, lens_type.value.value))
        if lens_type.value is LensType.FRESNEL:
            return not_assessed(
                cid,
                title,
                "The listing describes a Fresnel or flat sheet lens. Such a lens is not cut from a "
                "single sphere, so this bound does not apply to it.",
                inputs=inputs,
            )
    if diameter is None:
        return not_assessed(cid, title, "The listing does not state the diameter of the lens.", inputs=inputs)
    inputs.append(claim_q("Lens diameter", diameter, diameter.value, "mm"))

    near = K.NEAR_POINT_MM
    focal_mm = near.value / power.value
    limit_mm = 2 * focal_mm
    hard_mm = HARD_RESULT_MARGIN * limit_mm
    ratio = diameter.value / limit_mm
    over, hard = ratio > 1, diameter.value > hard_mm

    steps = [
        step(
            "Focal length implied by the claimed magnification",
            "f = 250 mm ÷ M",
            f"{fmt(near.value)} mm ÷ {fmt(power.value)}",
            focal_mm,
            "mm",
        ),
        step("Widest lens with that focal length", "D_max = 2 × f", f"2 × {fmt(focal_mm)} mm", limit_mm, "mm"),
        comparison(diameter.value, limit_mm, "mm", "limit"),
    ]
    if over:
        steps.append(
            step(
                "Diameter above which the result is hard",
                "D_hard = margin × D_max",
                f"{fmt(HARD_RESULT_MARGIN)} × {fmt(limit_mm)} mm",
                hard_mm,
                "mm",
            )
        )

    base = (
        f"A {fmt(power.value)}× lens has a focal length of {fmt(focal_mm)} mm, and a simple lens with that "
        f"focal length can be at most {fmt(limit_mm)} mm wide."
    )
    if hard:
        status = CheckStatus.VIOLATED
        summary = (
            f"{base} The listed lens diameter of {fmt(diameter.value)} mm is {fmt(ratio)}× that limit, "
            f"beyond the {fmt(HARD_RESULT_MARGIN)}× margin allowed for other lens materials."
        )
    elif over:
        status = CheckStatus.FLAG
        summary = (
            f"{base} The listed lens diameter of {fmt(diameter.value)} mm is {fmt(ratio)}× that limit. "
            f"This is within the {fmt(HARD_RESULT_MARGIN)}× margin allowed for other lens materials, so it "
            "is reported as a flag rather than a hard result."
        )
    else:
        status = CheckStatus.PASS
        summary = f"{base} The listed lens diameter of {fmt(diameter.value)} mm is within that limit."

    assumptions = list(_ASSUMPTIONS)
    if lens_type is None:
        assumptions.append("The listing does not describe a Fresnel or flat sheet lens, so an ordinary curved lens is assumed.")
    return CheckResult(
        check_id=cid,
        title=title,
        status=status,
        summary=summary,
        inputs=[
            *inputs,
            const_q(near),
            Quantity(name="Refractive index of the lens material", value=K.REFERENCE_INDEX, origin="assumption"),
            Quantity(name="Margin before a hard result", value=HARD_RESULT_MARGIN, unit="×", origin="assumption"),
        ],
        formula="D ≤ 2 × f, where f = 250 mm ÷ M",
        steps=steps,
        constants=[cite(near)],
        assumptions=assumptions,
    )


# ----------------------------------------------------------------------------- runner

CHECKS = (check_lens_diameter,)

# Claims that count as "a numeric claim was stated" when nothing could be tested.
NUMERIC_FIELDS = ("magnification",)


def evaluate(claims: MagnifierClaims) -> PackReport[MagnifierClaims]:
    """Run the pack on extracted claims and assemble the report."""
    return evaluate_pack(PACK_ID, claims, CHECKS, NUMERIC_FIELDS)
