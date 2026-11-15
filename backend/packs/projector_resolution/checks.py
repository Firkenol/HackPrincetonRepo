"""Projector check: the resolution named in the headline against the native resolution.

Design rules (the same as claimcheck/checks.py):
- Arithmetic is done here in Python and recorded step by step.
- When something needed is missing, the check says NOT_ASSESSED and explains why.
- Wording is about the claim, never about whoever listed the product.

This check never gives a hard result. A projector can accept a 4K input signal and
show it at a lower native resolution, so a "4K" headline above the native pixel count
contradicts the spec table without breaking a physical bound. It is a "Flag".
"""

from __future__ import annotations

from claimcheck.arithmetic import fmt
from claimcheck.models import CheckResult, CheckStatus, Quantity
from packs.common import PackReport, cite, claim_q, const_q, evaluate_pack, not_assessed, step
from packs.projector_resolution import constants as K
from packs.projector_resolution.models import ProjectorClaims

PACK_ID = "projector_resolution"
NATIVE_RESOLUTION = "native_resolution"
TITLES: dict[str, str] = {NATIVE_RESOLUTION: "Headline resolution against native resolution"}

_SOFT_NOTE = (
    "A projector can accept an input signal at a higher resolution than it displays, so this "
    "is reported as a flag rather than a hard result."
)


def check_native_resolution(claims: ProjectorClaims) -> CheckResult:
    """Pixel count of the headline resolution divided by the native pixel count."""
    cid, title = NATIVE_RESOLUTION, TITLES[NATIVE_RESOLUTION]
    claimed, native_px, native_name = claims.claimed_resolution, claims.native_pixels, claims.native_name

    if claimed is None:
        return not_assessed(cid, title, "No resolution is named in the title or headline.")
    headline = K.RESOLUTIONS[claimed.value.value]
    inputs: list[Quantity] = [claim_q("Headline resolution", claimed, headline.label)]
    if native_px is None and native_name is None:
        return not_assessed(cid, title, "The listing does not state a native resolution.", inputs=inputs)

    constants = [headline.width_px, headline.height_px]
    inputs += [const_q(headline.width_px), const_q(headline.height_px)]
    if native_px is not None:
        width, height = native_px.width_px, native_px.height_px
        native_label = f"{fmt(width)} × {fmt(height)}"
        inputs += [
            claim_q("Native width", native_px, width, "px"),
            claim_q("Native height", native_px, height, "px"),
        ]
    else:
        native = K.RESOLUTIONS[native_name.value.value]
        width, height = native.width_px.value, native.height_px.value
        native_label = native.label
        inputs.append(claim_q("Native resolution", native_name, native.label))
        if native.name != headline.name:
            inputs += [const_q(native.width_px), const_q(native.height_px)]
            constants += [native.width_px, native.height_px]

    headline_pixels = headline.width_px.value * headline.height_px.value
    native_pixels = width * height
    ratio = headline_pixels / native_pixels
    over = ratio > 1

    if over:
        summary = (
            f"The headline names {headline.label} ({fmt(headline_pixels)} pixels) and the listing gives a "
            f"native resolution of {native_label} ({fmt(native_pixels)} pixels). The headline figure is "
            f"{fmt(ratio)}× the native pixel count. {_SOFT_NOTE}"
        )
    else:
        summary = (
            f"The headline names {headline.label} ({fmt(headline_pixels)} pixels), which is not above the "
            f"stated native resolution of {native_label} ({fmt(native_pixels)} pixels)."
        )
    sign = ">" if over else "≤"
    return CheckResult(
        check_id=cid,
        title=title,
        status=CheckStatus.FLAG if over else CheckStatus.PASS,
        summary=summary,
        inputs=inputs,
        formula="ratio = headline pixels ÷ native pixels, where pixels = width × height",
        steps=[
            step(
                "Pixels in the headline resolution",
                "P_headline = width × height",
                f"{fmt(headline.width_px.value)} × {fmt(headline.height_px.value)}",
                headline_pixels,
                "pixels",
            ),
            step(
                "Pixels in the native resolution",
                "P_native = width × height",
                f"{fmt(width)} × {fmt(height)}",
                native_pixels,
                "pixels",
            ),
            step(
                "Headline pixels divided by native pixels",
                "ratio = P_headline ÷ P_native",
                f"{fmt(headline_pixels)} ÷ {fmt(native_pixels)}",
                ratio,
                f"({sign} 1)",
            ),
        ],
        constants=[cite(c) for c in constants],
        notes=[_SOFT_NOTE] if over else [],
    )


# ----------------------------------------------------------------------------- runner

CHECKS = (check_native_resolution,)

# Claims that count as "a numeric claim was stated" when nothing could be tested.
NUMERIC_FIELDS = ("claimed_resolution",)


def evaluate(claims: ProjectorClaims) -> PackReport[ProjectorClaims]:
    """Run the pack on extracted claims and assemble the report."""
    return evaluate_pack(PACK_ID, claims, CHECKS, NUMERIC_FIELDS)
