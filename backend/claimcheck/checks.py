"""The six checks. Each takes Claims and returns a CheckResult.

Design rules:
- Arithmetic is done here in Python and recorded step by step.
- A hard result (VIOLATED) only comes from a bound with a cited best-case ceiling
  and a measurement that describes the product itself.
- When something needed is missing or unreliable, the check says NOT_ASSESSED and
  explains why. It never guesses.
- Wording is about the claim, never about whoever listed the product.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from claimcheck import arithmetic as ar
from claimcheck import constants as K
from claimcheck import policy
from claimcheck.arithmetic import fmt
from claimcheck.models import (
    CHEMISTRY_LABELS,
    CheckResult,
    CheckStatus,
    Citation,
    Claims,
    MeasurementKind,
    ProductType,
    Quantity,
    Step,
    TextClaim,
)

LABEL_CONSISTENCY = "label_consistency"
FORM_FACTOR_BOUND = "form_factor_bound"
DIMENSION_BOUND = "dimension_bound"
WEIGHT_BOUND = "weight_bound"
LABEL_CONTRADICTION = "label_contradiction"
CHEMISTRY_MISMATCH = "chemistry_mismatch"

TITLES: dict[str, str] = {
    LABEL_CONSISTENCY: "Label consistency (Wh = V × Ah)",
    FORM_FACTOR_BOUND: "Form-factor bound",
    DIMENSION_BOUND: "Dimension bound (Wh/L)",
    WEIGHT_BOUND: "Weight bound (Wh/kg)",
    LABEL_CONTRADICTION: "Label contradiction",
    CHEMISTRY_MISMATCH: "Chemistry mismatch",
}

# ---------------------------------------------------------------------------- helpers


def _cite(c: K.Constant) -> Citation:
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


_SOFT_CEILING_NOTE = (
    "This ceiling comes from a secondary source with little headroom, so exceeding it is "
    "reported as a flag rather than a hard result."
)


def _exceeded(ceiling: K.Constant) -> CheckStatus:
    """Status for a claim above a ceiling: hard only when the ceiling is a hard bound."""
    return CheckStatus.VIOLATED if ceiling.hard_bound else CheckStatus.FLAG


def _soft_suffix(exceeded: bool, ceiling: K.Constant) -> str:
    return f" {_SOFT_CEILING_NOTE}" if exceeded and not ceiling.hard_bound else ""


def _claim_q(name: str, claim, value: float | str, unit: str = "") -> Quantity:
    return Quantity(
        name=name, value=value, unit=unit, origin="claim", found_in=claim.found_in, confidence=claim.confidence
    )


def _const_q(c: K.Constant) -> Quantity:
    return Quantity(name=c.description, value=c.value, unit=c.unit, origin="constant")


def _step(label: str, formula: str, substitution: str, result: float, unit: str) -> Step:
    return Step(
        label=label,
        formula=formula,
        substitution=substitution,
        result=result,
        unit=unit,
        text=f"{label}: {substitution} = {fmt(result)} {unit}".rstrip(),
    )


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _not_assessed(
    check_id: str,
    reason: str,
    *,
    inputs: list[Quantity] | None = None,
    notes: list[str] | None = None,
) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        title=TITLES[check_id],
        status=CheckStatus.NOT_ASSESSED,
        summary=f"Not assessed. {reason}",
        inputs=inputs or [],
        notes=notes or [],
        not_assessed_reason=reason,
    )


def _label(chem: str | None) -> str:
    return CHEMISTRY_LABELS.get(chem or "", "unknown chemistry")


def _known_form_factors(claims: Claims) -> list[tuple[TextClaim, K.FormFactor]]:
    found = []
    for claim in claims.form_factors:
        ff = K.FORM_FACTORS.get(claim.value.strip().upper().replace(" ", ""))
        if ff:
            found.append((claim, ff))
    return found


def _envelope_mm3(ff: K.FormFactor) -> float:
    return ar.cylinder_volume_mm3(ff.diameter_mm.value, ff.height_mm.value)


def _largest_form_factor(claims: Claims) -> tuple[TextClaim, K.FormFactor, str | None] | None:
    """The stated size with the largest envelope, which gives the most lenient bound."""
    known = _known_form_factors(claims)
    if not known:
        return None
    claim, ff = max(known, key=lambda pair: _envelope_mm3(pair[1]))
    assumption = None
    if len(known) > 1:
        codes = ", ".join(f.code for _, f in known)
        assumption = f"Several sizes are listed ({codes}); the largest ({ff.code}) is used, which is the most lenient."
    return claim, ff, assumption


def _effective_chemistry(claims: Claims) -> tuple[str | None, str | None]:
    """Stated chemistry, or the chemistry a size code implies. Returns (chemistry, assumption)."""
    if claims.chemistry:
        return claims.chemistry.value.value, None
    for _, ff in _known_form_factors(claims):
        if ff.default_chemistry:
            return (
                ff.default_chemistry,
                f"Chemistry not stated; {ff.code} is a {_label(ff.default_chemistry)} size code, "
                f"so {_label(ff.default_chemistry)} is assumed.",
            )
    if claims.product_type is ProductType.POWER_BANK:
        return "li-ion", "Chemistry not stated; power banks use lithium-ion cells, so lithium-ion is assumed."
    return None, None


def series_cells(voltage_v: float, chem: str | None) -> int | None:
    """How many cells in series a stated voltage corresponds to.

    Returns None if the chemistry has no voltage range on file (cannot judge),
    0 if the voltage is not a nominal battery voltage for the chemistry (for
    example a 5 V USB output on a lithium-ion product), otherwise the cell count.
    """
    if chem not in K.MIN_CELL_VOLTAGE:
        return None
    low = K.MIN_CELL_VOLTAGE[chem].value * (1 - policy.VOLTAGE_ROUNDING_TOLERANCE)
    high = K.MAX_CELL_VOLTAGE[chem].value * (1 + policy.VOLTAGE_ROUNDING_TOLERANCE)
    for n in range(1, policy.MAX_SERIES_CELLS + 1):
        if n * low <= voltage_v <= n * high:
            return n
    return 0


def _voltage_range_text(chem: str) -> str:
    low, high = K.MIN_CELL_VOLTAGE[chem].value, K.MAX_CELL_VOLTAGE[chem].value
    return f"{fmt(low)} V per cell" if low == high else f"{fmt(low)}–{fmt(high)} V per cell"


def _ceiling(table: dict[str, K.Constant], chem: str | None) -> tuple[K.Constant | None, str | None, str | None]:
    """Best-case ceiling for a chemistry. Returns (constant, assumption, reason_if_none)."""
    if chem is None:
        key = max(table, key=lambda k: table[k].value)
        return (
            table[key],
            f"Chemistry not stated; the highest ceiling on file ({_label(key)}) is used, which is the most lenient.",
            None,
        )
    if chem in table:
        return table[chem], None, None
    return None, None, f"No vetted best-case ceiling is on file for {_label(chem)}."


@dataclass
class _Energy:
    """The energy claim under test and how it was obtained."""

    wh: float
    inputs: list[Quantity] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    constants: list[Citation] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _resolve_energy(claims: Claims) -> _Energy | None:
    """The most demanding energy figure the listing states.

    Either the Wh printed on the label, or voltage x capacity. If both exist the
    larger one is tested: every stated claim has to be physically possible.
    """
    chem, chem_assumption = _effective_chemistry(claims)
    notes: list[str] = []

    from_capacity: _Energy | None = None
    if claims.capacity_mah:
        cap = claims.capacity_mah
        inputs: list[Quantity] = []
        constants: list[Citation] = []
        assumptions: list[str] = []
        voltage: float | None = None

        stated_v = claims.nominal_voltage_v
        if stated_v:
            if series_cells(stated_v.value, chem) == 0:
                notes.append(
                    f"The stated {fmt(stated_v.value)} V is not a nominal battery voltage for {_label(chem)} "
                    f"({_voltage_range_text(chem)}); it may be an output voltage, so it is not used to compute energy."
                )
            else:
                voltage = stated_v.value
                inputs.append(_claim_q("Nominal voltage", stated_v, stated_v.value, "V"))
        if voltage is None and chem in K.NOMINAL_CELL_VOLTAGE:
            nominal = K.NOMINAL_CELL_VOLTAGE[chem]
            voltage = nominal.value
            constants.append(_cite(nominal))
            inputs.append(Quantity(name="Nominal voltage (assumed)", value=voltage, unit="V", origin="assumption"))
            assumptions.append(
                f"No usable nominal voltage is stated; the nominal {_label(chem)} cell voltage of "
                f"{fmt(voltage)} V is assumed."
            )
            if chem_assumption:
                assumptions.append(chem_assumption)
        if voltage is not None:
            ah = ar.mah_to_ah(cap.value)
            wh = ar.energy_wh(voltage, cap.value)
            inputs.append(_claim_q("Capacity", cap, cap.value, "mAh"))
            steps = [
                _step("Capacity in Ah", "Q = mAh ÷ 1000", f"{fmt(cap.value)} mAh ÷ 1000", ah, "Ah"),
                _step("Energy implied by the stated capacity", "E = V × Q", f"{fmt(voltage)} V × {fmt(ah)} Ah", wh, "Wh"),
            ]
            from_capacity = _Energy(wh, inputs, steps, constants, assumptions)

    from_label: _Energy | None = None
    if claims.energy_wh:
        e = claims.energy_wh
        step = Step(
            label="Energy stated on the label",
            formula="E",
            substitution="as printed",
            result=e.value,
            unit="Wh",
            text=f"Energy stated on the label: {fmt(e.value)} Wh",
        )
        from_label = _Energy(e.value, [_claim_q("Energy", e, e.value, "Wh")], [step])

    candidates = [c for c in (from_label, from_capacity) if c]
    if not candidates:
        return None
    chosen = max(candidates, key=lambda c: c.wh)
    if len(candidates) == 2 and from_label.wh != from_capacity.wh:
        notes.append(
            f"The label gives {fmt(from_label.wh)} Wh and the stated capacity implies {fmt(from_capacity.wh)} Wh; "
            "the larger figure is tested."
        )
    chosen.notes = notes
    return chosen



@dataclass
class _NearCeiling:
    """A finished product whose claim is under the cell ceiling but implausibly close to it."""

    step: Step
    threshold: Quantity
    sentence: str
    assumption: str


def _near_cell_ceiling(claims: Claims, value: float, ceiling: K.Constant, unit: str, energy: "_Energy") -> _NearCeiling | None:
    """Soft review flag for power banks. The threshold is team policy, not a physical limit."""
    if claims.product_type is not ProductType.POWER_BANK:
        return None
    fraction = policy.FINISHED_PRODUCT_CEILING_FRACTION
    limit = ceiling.value * fraction
    if value <= limit:
        return None
    share = value / ceiling.value
    step = Step(
        label="Share of the cell ceiling",
        formula="value ÷ ceiling",
        substitution=f"{fmt(value)} {unit} ÷ {fmt(ceiling.value)} {unit}",
        result=share,
        unit="× the cell ceiling",
        text=(
            f"Share of the cell ceiling: {fmt(value)} {unit} ÷ {fmt(ceiling.value)} {unit} = {fmt(share)}, "
            f"above the review threshold of {fmt(fraction)}"
        ),
    )
    threshold = Quantity(
        name="Review threshold for finished products (team policy, not a physical limit)",
        value=fraction,
        unit="× the cell ceiling",
        origin="assumption",
    )
    assumed_voltage = next((q for q in energy.inputs if q.name == "Nominal voltage (assumed)"), None)
    depends = (
        f" This result depends on an assumed nominal voltage of {fmt(assumed_voltage.value)} V; "
        "the listing does not state one."
        if assumed_voltage is not None
        else ""
    )
    sentence = (
        f" No physical bound is exceeded, but the claim is {fmt(share)} of the ceiling for a bare cell. "
        "A power bank also carries a case and electronics, so a figure this close to the cell ceiling is "
        f"unusual and is flagged for review (team threshold: {fmt(fraction)} of the ceiling).{depends}"
    )
    assumption = (
        f"A power bank above {fmt(fraction)} of the bare-cell ceiling is flagged for review. "
        "This threshold is a team policy choice, not a physical limit."
    )
    return _NearCeiling(step, threshold, sentence, assumption)


def _cell_count(claims: Claims) -> tuple[int, str | None]:
    if claims.cell_count:
        return max(1, int(claims.cell_count.value)), None
    return 1, "Cell count not stated; the capacity claim is taken as covering one cell."


def _comparison(value: float, limit: float, unit: str, limit_name: str) -> Step:
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


# ------------------------------------------------------------ 1. label consistency


def check_label_consistency(claims: Claims) -> CheckResult:
    """Stated Wh must equal V x Ah within a small rounding tolerance."""
    cid = LABEL_CONSISTENCY
    notes: list[str] = []
    if claims.output_capacity_mah:
        notes.append(
            "A rated or usable output capacity is also listed. It is not compared with the labeled "
            "cell capacity: output below cell capacity is normal conversion loss."
        )

    e, v, q = claims.energy_wh, claims.nominal_voltage_v, claims.capacity_mah
    missing = [name for name, c in (("Wh", e), ("capacity", q)) if c is None]
    if missing:
        return _not_assessed(cid, f"Needs Wh and capacity both stated; not stated: {', '.join(missing)}.", notes=notes)

    chem, chem_assumption = _effective_chemistry(claims)
    if v is None or series_cells(v.value, chem) == 0:
        if v is not None:
            notes.append(
                f"The stated {fmt(v.value)} V is not a nominal battery voltage for {_label(chem)} "
                f"({_voltage_range_text(chem)}); it may be an output voltage, so it is not used."
            )
        return _implied_voltage_check(claims, chem, chem_assumption, notes)

    ah = ar.mah_to_ah(q.value)
    computed = ar.energy_wh(v.value, q.value)
    diff = ar.relative_difference(e.value, computed)
    tolerance = policy.LABEL_WH_RELATIVE_TOLERANCE
    ok = diff <= tolerance

    steps = [
        _step("Capacity in Ah", "Q = mAh ÷ 1000", f"{fmt(q.value)} mAh ÷ 1000", ah, "Ah"),
        _step("Energy from voltage and capacity", "E = V × Q", f"{fmt(v.value)} V × {fmt(ah)} Ah", computed, "Wh"),
        _step(
            "Difference from the label",
            "|E_label − E| ÷ E",
            f"|{fmt(e.value)} Wh − {fmt(computed)} Wh| ÷ {fmt(computed)} Wh",
            diff * 100,
            "%",
        ),
    ]
    base = f"Label states {fmt(e.value)} Wh; {fmt(v.value)} V × {fmt(ah)} Ah = {fmt(computed)} Wh."
    if ok:
        summary = f"{base} The difference of {fmt(diff * 100)}% is within the {fmt(tolerance * 100)}% tolerance."
    else:
        summary = (
            f"{base} The difference of {fmt(diff * 100)}% exceeds the {fmt(tolerance * 100)}% tolerance, "
            "so the three label values cannot all be correct."
        )
    return CheckResult(
        check_id=cid,
        title=TITLES[cid],
        status=CheckStatus.PASS if ok else CheckStatus.FLAG,
        summary=summary,
        inputs=[
            _claim_q("Energy", e, e.value, "Wh"),
            _claim_q("Nominal voltage", v, v.value, "V"),
            _claim_q("Capacity", q, q.value, "mAh"),
        ],
        formula="E (Wh) = V (V) × Q (Ah)",
        steps=steps,
        notes=notes,
    )


def _implied_voltage_check(claims: Claims, chem: str | None, chem_assumption: str | None, notes: list[str]) -> CheckResult:
    """Label consistency when no usable voltage is printed, as on most power banks.

    Wh ÷ Ah is the voltage the label implies. It has to be a nominal battery voltage
    for the chemistry. Soft flag only.
    """
    cid = LABEL_CONSISTENCY
    e, q = claims.energy_wh, claims.capacity_mah
    if chem not in K.MIN_CELL_VOLTAGE:
        return _not_assessed(
            cid,
            "No usable voltage is stated, and the voltage implied by Wh ÷ Ah cannot be judged because "
            "the chemistry is not stated or has no voltage range on file.",
            notes=notes,
        )

    ah = ar.mah_to_ah(q.value)
    implied = e.value / ah
    cells = series_cells(implied, chem)
    range_text = _voltage_range_text(chem)
    if cells:
        outcome = f"matches {cells} cell{'s' if cells > 1 else ''} in series at {range_text}"
        summary = (
            f"Label states {fmt(e.value)} Wh and {fmt(q.value)} mAh; {fmt(e.value)} Wh ÷ {fmt(ah)} Ah = "
            f"{fmt(implied)} V, a nominal {_label(chem)} voltage ({range_text})."
        )
    else:
        outcome = f"matches no whole number of cells at {range_text}"
        summary = (
            f"Label states {fmt(e.value)} Wh and {fmt(q.value)} mAh; {fmt(e.value)} Wh ÷ {fmt(ah)} Ah = "
            f"{fmt(implied)} V, which is not a nominal {_label(chem)} voltage ({range_text}). "
            "The energy and capacity on the label do not fit together."
        )
    steps = [
        _step("Capacity in Ah", "Q = mAh ÷ 1000", f"{fmt(q.value)} mAh ÷ 1000", ah, "Ah"),
        _step("Voltage implied by the label", "V = E ÷ Q", f"{fmt(e.value)} Wh ÷ {fmt(ah)} Ah", implied, "V"),
        Step(
            label="Comparison",
            formula="V = whole number of cells × nominal cell voltage",
            substitution=f"{fmt(implied)} V {outcome}",
            text=f"Comparison: {fmt(implied)} V {outcome}",
        ),
    ]
    low, high = K.MIN_CELL_VOLTAGE[chem], K.MAX_CELL_VOLTAGE[chem]
    return CheckResult(
        check_id=cid,
        title=TITLES[cid],
        status=CheckStatus.PASS if cells else CheckStatus.FLAG,
        summary=summary,
        inputs=[_claim_q("Energy", e, e.value, "Wh"), _claim_q("Capacity", q, q.value, "mAh"), _const_q(low), _const_q(high)],
        formula="V (V) = E (Wh) ÷ Q (Ah)",
        steps=steps,
        constants=[_cite(low)] if low is high else [_cite(low), _cite(high)],
        assumptions=[chem_assumption] if chem_assumption else [],
        notes=notes,
    )


# ------------------------------------------------------------- 2. form-factor bound


def check_form_factor_bound(claims: Claims) -> CheckResult:
    """A size code fixes the volume, and volume caps the energy."""
    cid = FORM_FACTOR_BOUND
    if not claims.form_factors:
        return _not_assessed(cid, "No standard size code is stated.")
    largest = _largest_form_factor(claims)
    if largest is None:
        codes = ", ".join(c.value for c in claims.form_factors)
        return _not_assessed(cid, f"Size code {codes} is not in the form-factor table.")
    ff_claim, ff, ff_assumption = largest

    energy = _resolve_energy(claims)
    if energy is None:
        return _not_assessed(cid, "No capacity or energy claim is stated.")

    chem, chem_assumption = _effective_chemistry(claims)
    ceiling, ceiling_assumption, reason = _ceiling(K.MAX_WH_PER_L, chem)
    if ceiling is None:
        return _not_assessed(cid, reason, notes=energy.notes)

    stated_v, stated_cells = claims.nominal_voltage_v, claims.cell_count
    if stated_v:
        n_series = series_cells(stated_v.value, chem)
        if n_series == 0:
            return _not_assessed(
                cid,
                f"The stated {fmt(stated_v.value)} V is not a single-cell nominal voltage, so the number "
                "of cells behind the claim is unknown.",
                notes=energy.notes,
            )
        if n_series and n_series >= 2 and (stated_cells is None or stated_cells.value < n_series):
            return _not_assessed(
                cid,
                f"The stated {fmt(stated_v.value)} V implies at least {n_series} cells in series and the "
                "cell count is not stated, so a single-cell bound does not apply.",
                notes=energy.notes,
            )
    n_cells, cells_assumption = _cell_count(claims)

    d, h = ff.diameter_mm.value, ff.height_mm.value
    cell_mm3 = _envelope_mm3(ff)
    cell_l = ar.mm3_to_litres(cell_mm3)
    total_l = cell_l * n_cells
    cap_wh = ceiling.value * total_l
    violated = energy.wh > cap_wh

    steps = list(energy.steps)
    steps.append(
        _step(
            f"{ff.code} envelope volume",
            "V = π × (d ÷ 2)² × h",
            f"π × ({fmt(d)} mm ÷ 2)² × {fmt(h)} mm = {fmt(cell_mm3)} mm³",
            cell_l,
            "L",
        )
    )
    if n_cells > 1:
        steps.append(_step(f"Volume of {n_cells} cells", "V_total = n × V", f"{n_cells} × {fmt(cell_l)} L", total_l, "L"))
    steps.append(
        _step(
            "Most energy that volume can hold",
            "E_max = ceiling × V",
            f"{fmt(ceiling.value)} Wh/L × {fmt(total_l)} L",
            cap_wh,
            "Wh",
        )
    )
    steps.append(_comparison(energy.wh, cap_wh, "Wh", "cap"))

    size = f"{n_cells} {ff.code}-size cells" if n_cells > 1 else f"one {ff.code}-size cell"
    if violated:
        summary = (
            f"The claim amounts to {fmt(energy.wh)} Wh. The envelope of {size} is at most {fmt(total_l)} L, "
            f"which holds no more than {fmt(cap_wh)} Wh at the best-case {_label(chem)} ceiling of "
            f"{fmt(ceiling.value)} Wh/L. The claim is {fmt(energy.wh / cap_wh)}× that cap."
            f"{_soft_suffix(violated, ceiling)}"
        )
    else:
        summary = (
            f"The claim amounts to {fmt(energy.wh)} Wh, within the {fmt(cap_wh)} Wh that the envelope of {size} "
            f"can hold at the best-case {_label(chem)} ceiling of {fmt(ceiling.value)} Wh/L."
        )
    return CheckResult(
        check_id=cid,
        title=TITLES[cid],
        status=_exceeded(ceiling) if violated else CheckStatus.PASS,
        summary=summary,
        inputs=[_claim_q("Size code", ff_claim, ff.code), *energy.inputs, _const_q(ff.diameter_mm), _const_q(ff.height_mm), _const_q(ceiling)],
        formula="E ≤ ceiling (Wh/L) × π × (d ÷ 2)² × h",
        steps=steps,
        constants=[*energy.constants, _cite(ff.diameter_mm), _cite(ff.height_mm), _cite(ceiling)],
        assumptions=_dedupe(
            [a for a in (*energy.assumptions, chem_assumption, ceiling_assumption, ff_assumption, cells_assumption) if a]
        ),
        notes=energy.notes,
    )


# --------------------------------------------------------------- 3. dimension bound


def check_dimension_bound(claims: Claims) -> CheckResult:
    """Stated product dimensions give a volume; Wh/L must be under the best-case ceiling."""
    cid = DIMENSION_BOUND
    dims = claims.dimensions
    if dims is None:
        return _not_assessed(cid, "Dimensions are not stated.")

    box_mm3 = ar.box_volume_mm3(dims.length_mm, dims.width_mm, dims.height_mm)
    box_l = ar.mm3_to_litres(box_mm3)
    dims_text = f"{fmt(dims.length_mm)} × {fmt(dims.width_mm)} × {fmt(dims.height_mm)} mm"
    dims_input = _claim_q(f"Dimensions ({dims.kind.value})", dims, dims_text)

    largest = _largest_form_factor(claims)
    envelope_ratio = None
    if largest:
        _, ff, _ = largest
        n_cells, _ = _cell_count(claims)
        envelope_ratio = box_l / (ar.mm3_to_litres(_envelope_mm3(ff)) * n_cells)

    if dims.kind is MeasurementKind.PACKAGE:
        notes = [
            f"The listed dimensions ({dims_text}) are package dimensions. Package figures often describe "
            "the shipping box or are placeholders, so they are not used as a bound."
        ]
        if dims.length_mm == dims.width_mm == dims.height_mm:
            notes.append("All three dimensions are equal, a common placeholder pattern.")
        if envelope_ratio is not None:
            notes.append(f"The listed volume is {fmt(envelope_ratio)}× the {ff.code} envelope, so it does not describe the cell.")
        return _not_assessed(cid, "The listed dimensions describe the package, not the product.", inputs=[dims_input], notes=notes)

    limit = policy.FORM_FACTOR_MISMATCH_RATIO
    if envelope_ratio is not None and not (1 / limit <= envelope_ratio <= limit):
        return _not_assessed(
            cid,
            f"The listed dimensions give {fmt(envelope_ratio)}× the volume of the stated {ff.code} size, so they "
            "look like a placeholder or the packaging. The form-factor bound is used instead.",
            inputs=[dims_input],
        )

    energy = _resolve_energy(claims)
    if energy is None:
        return _not_assessed(cid, "No capacity or energy claim is stated.", inputs=[dims_input])
    chem, chem_assumption = _effective_chemistry(claims)
    ceiling, ceiling_assumption, reason = _ceiling(K.MAX_WH_PER_L, chem)
    if ceiling is None:
        return _not_assessed(cid, reason, inputs=[dims_input], notes=energy.notes)

    density = energy.wh / box_l
    violated = density > ceiling.value
    steps = [
        *energy.steps,
        _step(
            "Volume from the stated dimensions",
            "V = L × W × H",
            f"{fmt(dims.length_mm)} mm × {fmt(dims.width_mm)} mm × {fmt(dims.height_mm)} mm = {fmt(box_mm3)} mm³",
            box_l,
            "L",
        ),
        _step("Energy density", "E ÷ V", f"{fmt(energy.wh)} Wh ÷ {fmt(box_l)} L", density, "Wh/L"),
        _comparison(density, ceiling.value, "Wh/L", "ceiling"),
    ]
    verb = "exceeds" if violated else "is under"
    summary = (
        f"{fmt(energy.wh)} Wh in {fmt(box_l)} L is {fmt(density)} Wh/L, which {verb} the best-case "
        f"{_label(chem)} ceiling of {fmt(ceiling.value)} Wh/L.{_soft_suffix(violated, ceiling)}"
    )
    near = None if violated else _near_cell_ceiling(claims, density, ceiling, "Wh/L", energy)
    status = _exceeded(ceiling) if violated else CheckStatus.PASS
    inputs = [*energy.inputs, dims_input, _const_q(ceiling)]
    extra_assumptions: list[str] = []
    if near:
        status, summary = CheckStatus.FLAG, summary + near.sentence
        steps.append(near.step)
        inputs.append(near.threshold)
        extra_assumptions.append(near.assumption)
    return CheckResult(
        check_id=cid,
        title=TITLES[cid],
        status=status,
        summary=summary,
        inputs=inputs,
        formula="E ÷ (L × W × H) ≤ ceiling (Wh/L)",
        steps=steps,
        constants=[*energy.constants, _cite(ceiling)],
        assumptions=_dedupe([a for a in (*energy.assumptions, chem_assumption, ceiling_assumption, *extra_assumptions) if a]),
        notes=[*energy.notes, "The bounding box is at least as large as the product, which makes this bound lenient."],
    )


# ------------------------------------------------------------------ 4. weight bound


def check_weight_bound(claims: Claims) -> CheckResult:
    """Wh/kg from the stated product weight must be under the best-case ceiling."""
    cid = WEIGHT_BOUND
    weight = claims.weight
    if weight is None:
        return _not_assessed(cid, "Weight is not stated.")
    weight_input = _claim_q(f"Weight ({weight.kind.value})", weight, weight.value_g, "g")

    if weight.kind is MeasurementKind.PACKAGE:
        notes = [
            f"The listed weight ({fmt(weight.value_g)} g) is a package weight. Package figures often include "
            "packaging or are placeholders, so they are not used as a bound."
        ]
        largest = _largest_form_factor(claims)
        if largest and largest[1].max_cell_mass_g:
            ff = largest[1]
            n_cells, _ = _cell_count(claims)
            ratio = weight.value_g / (ff.max_cell_mass_g.value * n_cells)
            if not (1 / policy.FORM_FACTOR_MISMATCH_RATIO <= ratio <= policy.FORM_FACTOR_MISMATCH_RATIO):
                notes.append(
                    f"It is {fmt(ratio)}× the maximum mass of one {ff.code} cell ({fmt(ff.max_cell_mass_g.value)} g), "
                    "so it describes the package or is a placeholder, not the cell."
                )
        return _not_assessed(cid, "The listed weight describes the package, not the product.", inputs=[weight_input], notes=notes)

    energy = _resolve_energy(claims)
    if energy is None:
        return _not_assessed(cid, "No capacity or energy claim is stated.", inputs=[weight_input])
    chem, chem_assumption = _effective_chemistry(claims)
    ceiling, ceiling_assumption, reason = _ceiling(K.MAX_WH_PER_KG, chem)
    if ceiling is None:
        return _not_assessed(cid, reason, inputs=[weight_input], notes=energy.notes)

    kg = ar.g_to_kg(weight.value_g)
    specific = energy.wh / kg
    violated = specific > ceiling.value
    steps = [
        *energy.steps,
        _step("Weight in kg", "m = g ÷ 1000", f"{fmt(weight.value_g)} g ÷ 1000", kg, "kg"),
        _step("Specific energy", "E ÷ m", f"{fmt(energy.wh)} Wh ÷ {fmt(kg)} kg", specific, "Wh/kg"),
        _comparison(specific, ceiling.value, "Wh/kg", "ceiling"),
    ]
    verb = "exceeds" if violated else "is under"
    summary = (
        f"{fmt(energy.wh)} Wh at {fmt(kg)} kg is {fmt(specific)} Wh/kg, which {verb} the best-case "
        f"{_label(chem)} ceiling of {fmt(ceiling.value)} Wh/kg.{_soft_suffix(violated, ceiling)}"
    )
    near = None if violated else _near_cell_ceiling(claims, specific, ceiling, "Wh/kg", energy)
    status = _exceeded(ceiling) if violated else CheckStatus.PASS
    inputs = [*energy.inputs, weight_input, _const_q(ceiling)]
    extra_assumptions: list[str] = []
    if near:
        status, summary = CheckStatus.FLAG, summary + near.sentence
        steps.append(near.step)
        inputs.append(near.threshold)
        extra_assumptions.append(near.assumption)
    return CheckResult(
        check_id=cid,
        title=TITLES[cid],
        status=status,
        summary=summary,
        inputs=inputs,
        formula="E ÷ m ≤ ceiling (Wh/kg)",
        steps=steps,
        constants=[*energy.constants, _cite(ceiling)],
        assumptions=_dedupe([a for a in (*energy.assumptions, chem_assumption, ceiling_assumption, *extra_assumptions) if a]),
        notes=energy.notes,
    )


# ------------------------------------------------------------ 5. label contradiction

_IEC_RE = re.compile(r"^(?:IEC)?(\d*)([A-Z]{1,2})(\d+)")


def parse_iec_code(text: str) -> tuple[str, str] | None:
    """Read an IEC designation such as R6, LR03 or 6F22. Returns (code, chemistry) or None."""
    cleaned = re.sub(r"[\s\-_/.]", "", text.upper())
    match = _IEC_RE.match(cleaned)
    if not match:
        return None
    cells, letters, size = match.groups()
    system, shape = (letters[0], letters[1]) if len(letters) == 2 else ("", letters)
    if shape not in K.IEC_SHAPE_LETTERS or system not in K.IEC_SYSTEM_LETTERS:
        return None
    return f"{cells}{letters}{size}", K.IEC_SYSTEM_LETTERS[system]


def _grade_term(text: str) -> str | None:
    lowered = text.lower()
    return next((term for term in K.CARBON_ZINC_GRADE_TERMS if term in lowered), None)


def check_label_contradiction(claims: Claims) -> CheckResult:
    """The stated chemistry must agree with the codes printed on the product."""
    cid = LABEL_CONTRADICTION
    if claims.chemistry is None:
        return _not_assessed(cid, "No chemistry is stated in the listing text.")
    stated = claims.chemistry.value.value

    inputs = [_claim_q("Stated chemistry", claims.chemistry, _label(stated))]
    evidence: list[tuple[str, str]] = []  # (what is printed, chemistry it indicates)
    notes: list[str] = []
    for code in claims.printed_codes:
        parsed = parse_iec_code(code.value)
        if parsed is None:
            notes.append(f"Printed code '{code.value}' is not a recognised IEC designation and was not used.")
            continue
        inputs.append(_claim_q("Printed code", code, parsed[0]))
        evidence.append((f"{parsed[0]} (IEC designation for {_label(parsed[1])})", parsed[1]))
    used_grade = False
    for term in claims.printed_terms:
        grade = _grade_term(term.value)
        if grade is None:
            continue
        used_grade = True
        inputs.append(_claim_q("Printed wording", term, term.value))
        evidence.append((f"'{term.value}' (a carbon-zinc grade name)", "zinc-carbon"))

    if not evidence:
        return _not_assessed(cid, "No designation code or grade wording was read from the product itself.", inputs=inputs, notes=notes)

    conflicts = [text for text, chem in evidence if chem != stated]
    constants = [_cite(K.IEC_EXAMPLE_ZINC_CARBON), _cite(K.IEC_EXAMPLE_ALKALINE)]
    if used_grade:
        constants.append(_cite(K.CARBON_ZINC_GRADES))
    if conflicts:
        summary = (
            f"The listing states {_label(stated)}, but the product is marked {' and '.join(conflicts)}. "
            "The listing text and the product markings disagree."
        )
    else:
        summary = f"The product markings ({', '.join(text for text, _ in evidence)}) agree with the stated chemistry ({_label(stated)})."
    notes.append(
        "IEC designations: no letter before R means zinc-carbon (R6, R03); L means alkaline (LR6, LR03); "
        "H means NiMH (HR6, HR03). Source: IEC 60086-1 letter codes."
    )
    return CheckResult(
        check_id=cid,
        title=TITLES[cid],
        status=CheckStatus.FLAG if conflicts else CheckStatus.PASS,
        summary=summary,
        inputs=inputs,
        constants=constants,
        notes=notes,
    )


# ------------------------------------------------------------- 6. chemistry mismatch


def check_chemistry_mismatch(claims: Claims) -> CheckResult:
    """A claim unusual for the stated chemistry. Soft flag only."""
    cid = CHEMISTRY_MISMATCH
    shelf = claims.shelf_life_years
    if shelf is None:
        return _not_assessed(cid, "No shelf-life claim is stated.")
    chem, _ = _effective_chemistry(claims)
    if chem is None:
        return _not_assessed(cid, "No chemistry is stated to compare the shelf-life claim against.")
    reference = K.MAX_PUBLISHED_STORAGE_YEARS.get(chem)
    if reference is None:
        return _not_assessed(cid, f"No shelf-life reference is on file for {_label(chem)}.")

    unusual = shelf.value > reference.value
    sign = ">" if unusual else "≤"
    step = Step(
        label="Comparison",
        formula="claimed shelf life ≤ longest published storage period",
        substitution=f"{fmt(shelf.value)} years {sign} {fmt(reference.value)} years",
        result=shelf.value / reference.value,
        unit="× the published period",
        text=f"Comparison: {fmt(shelf.value)} years {sign} {fmt(reference.value)} years",
    )
    if unusual:
        summary = (
            f"The listing claims a {fmt(shelf.value)}-year shelf life for a {_label(chem)} product. Published "
            f"storage data for this chemistry runs to {fmt(reference.value)} years "
            f"({reference.note.rstrip('.').lower()}). A shelf life of {fmt(K.ALKALINE_SHELF_LIFE_REFERENCE.value)} years is what alkaline datasheets "
            "state. The claim is unusual for the stated chemistry."
        )
    else:
        summary = (
            f"The claimed {fmt(shelf.value)}-year shelf life is within the {fmt(reference.value)} years of "
            f"published storage data for {_label(chem)}."
        )
    return CheckResult(
        check_id=cid,
        title=TITLES[cid],
        status=CheckStatus.FLAG if unusual else CheckStatus.PASS,
        summary=summary,
        inputs=[
            _claim_q("Shelf life", shelf, shelf.value, "years"),
            _claim_q("Stated chemistry", claims.chemistry, _label(chem)) if claims.chemistry else Quantity(name="Chemistry", value=_label(chem), origin="assumption"),
            _const_q(reference),
        ],
        steps=[step],
        constants=[_cite(reference), _cite(K.ALKALINE_SHELF_LIFE_REFERENCE)],
    )


# ----------------------------------------------------------------------------- runner

ALL_CHECKS = (
    check_label_consistency,
    check_form_factor_bound,
    check_dimension_bound,
    check_weight_bound,
    check_label_contradiction,
    check_chemistry_mismatch,
)


def run_all_checks(claims: Claims) -> list[CheckResult]:
    return [check(claims) for check in ALL_CHECKS]
