"""Power-budget check: claimed output power cannot exceed what the stated input supplies.

Design rules (the same as claimcheck/checks.py):
- Arithmetic is done here in Python and recorded step by step.
- A hard result (VIOLATED) only comes from a cited limit that is a hard bound.
- When something needed is missing or unclear, the check says NOT_ASSESSED and
  explains why. It never guesses.
- Wording is about the claim, never about whoever listed the product.

The bound holds only when the output is drawn from the input as it is delivered. A
product with a battery can deliver more than its input supplies for a while, and a
peak figure can last a fraction of a second. Both cases are reported as not assessed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from claimcheck.arithmetic import fmt
from claimcheck.constants import Constant
from claimcheck.models import CheckResult, CheckStatus, Citation, Quantity, Step
from packs.common import (
    PackReport,
    cite,
    claim_q,
    comparison,
    const_q,
    evaluate_pack,
    exceeded,
    not_assessed,
    stated_step,
    step,
)
from packs.power_budget import constants as K
from packs.power_budget.models import EnergyStorage, InputSource, PowerBudgetClaims, PowerKind

PACK_ID = "power_budget"
POWER_BUDGET = "power_budget"
TITLES: dict[str, str] = {POWER_BUDGET: "Power budget (output ≤ input)"}

SOURCE_LABELS: dict[str, str] = {
    "us_household_outlet": "a standard US household outlet",
    "usb_pd": "USB Power Delivery",
    "usb_c": "a USB-C connection",
    "usb_bc_1_2": "USB Battery Charging 1.2",
    "usb_3": "a USB 3.x port",
    "usb_2": "a USB 2.0 port",
    "other": "another power source",
}

_SOFT_LIMIT_NOTE = (
    "Chargers often supply more over a USB connector than this standard defines, so exceeding "
    "it is reported as a flag rather than a hard result."
)


@dataclass
class _Supply:
    """The most power the stated input can supply, and how that figure was obtained."""

    watts: float
    limit: Constant  # the constant that decides whether the bound is hard
    inputs: list[Quantity] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    constants: list[Citation] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)


def _outlet_supply() -> _Supply:
    volts, amps = K.US_OUTLET_VOLTAGE_V, K.US_OUTLET_CURRENT_A
    watts = volts.value * amps.value
    return _Supply(
        watts=watts,
        limit=amps,
        inputs=[const_q(volts), const_q(amps)],
        steps=[
            step(
                "Most power the outlet can supply",
                "P_max = V × I",
                f"{fmt(volts.value)} V × {fmt(amps.value)} A",
                watts,
                "W",
            )
        ],
        constants=[cite(volts), cite(amps)],
        assumptions=[
            "The receptacle rating is not stated; the 20 A rating is used, which is the most lenient."
        ],
    )


def _usb_supply(source: str) -> _Supply:
    limit = K.USB_MAX_W[source]
    assumptions: list[str] = []
    if source == InputSource.USB_C.value:
        assumptions.append(
            "Only the USB-C connector is named; the highest power any USB standard defines for it "
            "(USB Power Delivery) is used, which is the most lenient."
        )
    if source == InputSource.USB_3.value:
        assumptions.append(
            "Single-lane or dual-lane operation is not stated; the dual-lane figure is used, "
            "which is the most lenient."
        )
    return _Supply(
        watts=limit.value,
        limit=limit,
        inputs=[const_q(limit)],
        steps=[
            stated_step(
                "Most power the input can supply", "P_max", limit.value, "W", "as defined by the USB standard"
            )
        ],
        constants=[cite(limit)],
        assumptions=assumptions,
    )


def check_power_budget(claims: PowerBudgetClaims) -> CheckResult:
    """Claimed output power must not exceed what the stated input can supply."""
    cid, title = POWER_BUDGET, TITLES[POWER_BUDGET]
    power, source, storage = claims.output_power_w, claims.input_source, claims.energy_storage

    if power is None:
        return not_assessed(cid, title, "No output power is stated.")
    kind_label = "Output power (peak)" if power.kind is PowerKind.PEAK else "Output power"
    inputs = [claim_q(kind_label, power, power.value, "W")]

    if source is None:
        return not_assessed(cid, title, "The listing does not state what the product is powered from.", inputs=inputs)
    source_key = source.value.value
    label = SOURCE_LABELS[source_key]
    inputs.append(claim_q("Stated input", source, label))

    if source.value is InputSource.OTHER:
        return not_assessed(
            cid,
            title,
            "The stated input is not a standard US household outlet or a named USB standard, "
            "so no supply limit is on file for it.",
            inputs=inputs,
        )
    if power.kind is PowerKind.PEAK:
        return not_assessed(
            cid,
            title,
            "The power figure is a peak value. A peak can last a fraction of a second, which the "
            "continuous rating of the input does not bound.",
            inputs=inputs,
        )
    if storage is None:
        return not_assessed(
            cid,
            title,
            "The listing does not make clear whether the product has a battery. A product with a "
            "battery can deliver more power than its input supplies, so the bound applies only "
            "when there is none.",
            inputs=inputs,
        )
    inputs.append(claim_q("Energy storage", storage, storage.value.value))
    if storage.value is EnergyStorage.BUILT_IN:
        return not_assessed(
            cid,
            title,
            "The product has a battery or other energy storage, so it can deliver more power "
            "than its input supplies for a time.",
            inputs=inputs,
        )

    supply = _outlet_supply() if source.value is InputSource.US_HOUSEHOLD_OUTLET else _usb_supply(source_key)
    over = power.value > supply.watts
    soft = over and not supply.limit.hard_bound

    if over:
        summary = (
            f"The listing claims {fmt(power.value)} W from {label}, which can supply at most "
            f"{fmt(supply.watts)} W. The claim is {fmt(power.value / supply.watts)}× that limit."
        )
        if soft:
            summary += f" {_SOFT_LIMIT_NOTE}"
    else:
        summary = (
            f"The claimed {fmt(power.value)} W is within the {fmt(supply.watts)} W that {label} can supply."
        )
    return CheckResult(
        check_id=cid,
        title=title,
        status=exceeded(supply.limit) if over else CheckStatus.PASS,
        summary=summary,
        inputs=[*inputs, *supply.inputs],
        formula="P_out ≤ P_max of the input",
        steps=[*supply.steps, comparison(power.value, supply.watts, "W", "limit")],
        constants=supply.constants,
        assumptions=supply.assumptions,
        notes=["Losses inside the product only lower the output further, which makes this bound lenient."],
    )


# ----------------------------------------------------------------------------- runner

CHECKS = (check_power_budget,)

# Claims that count as "a numeric claim was stated" when nothing could be tested.
NUMERIC_FIELDS = ("output_power_w",)


def evaluate(claims: PowerBudgetClaims) -> PackReport[PowerBudgetClaims]:
    """Run the pack on extracted claims and assemble the report."""
    return evaluate_pack(PACK_ID, claims, CHECKS, NUMERIC_FIELDS)
