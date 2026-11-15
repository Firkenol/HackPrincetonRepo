"""Reference data for the power-budget pack: the most power each input can supply.

Rules for this file (the same as claimcheck/constants.py):
- Every value carries a Source with a URL and a short supporting quote.
- Limits are the most an input of that kind can supply, so honest products sit below.
- Never add a value without a source.

Hard and soft limits:
- The household outlet and USB Power Delivery limits are hard bounds.
- The USB 2.0, USB 3.x and USB BC 1.2 limits are soft (hard_bound=False). Chargers
  often supply more current over a USB connector than these standards define, and a
  listing may name "USB 2.0" for the connector rather than as a power limit. Exceeding
  a soft limit is a "Flag", never "Impossible".
"""

from __future__ import annotations

from claimcheck.constants import Constant, Source

ACCESSED = "2026-11-14"

# --------------------------------------------------------------------------- sources

_CFR_RECEPTACLE_RATINGS = Source(
    title="29 CFR 1910.304, Wiring design and protection",
    publisher="U.S. Occupational Safety and Health Administration, Code of Federal Regulations (eCFR)",
    url="https://www.ecfr.gov/current/title-29/section-1910.304",
    locator="Paragraph (b)(4)(ii), Table S-5 'Receptacle Ratings for Various Size Circuits'",
    quote="Circuit rating (amperes) 20: Receptacle rating (amperes) 15 or 20.",
    accessed=ACCESSED,
)

_CFR_RECEPTACLE_VOLTAGE = Source(
    title="29 CFR 1910.304, Wiring design and protection",
    publisher="U.S. Occupational Safety and Health Administration, Code of Federal Regulations (eCFR)",
    url="https://www.ecfr.gov/current/title-29/section-1910.304",
    locator="Paragraph (b)(3)(i)",
    quote=(
        "All 125-volt, single-phase, 15- and 20-ampere receptacles installed in bathrooms or on "
        "rooftops shall have ground-fault circuit-interrupter protection for personnel."
    ),
    accessed=ACCESSED,
)

_USB_PD_PAGE = Source(
    title="USB Charger (USB Power Delivery)",
    publisher="USB Implementers Forum",
    url="https://www.usb.org/usb-charger-pd",
    locator="Opening section and feature list",
    quote=(
        "the USB PD Revision 3.1 specification is a major update to enable delivering up to 240W "
        "of power over full featured USB Type-C® cable and connector."
    ),
    accessed=ACCESSED,
)

_TYPE_C_PDP_TABLE = Source(
    title="USB Type-C Cable and Connector Specification, Release 2.0, August 2019",
    publisher="USB 3.0 Promoter Group, published by the USB Implementers Forum",
    url="https://www.usb.org/sites/default/files/USB%20Type-C%20Spec%20R2.0%20-%20August%202019.pdf",
    locator="Section 4.6.2.1, Table 4-18 'USB Type-C Current Advertisement and PDP Equivalent'",
    quote=(
        "Default: 500 mA (USB 2.0) 2.5 W; 900 mA (USB 3.2 single-lane) 4.5 W; "
        "1,500 mA (USB 3.2 dual-lane) 7.5 W"
    ),
    accessed=ACCESSED,
)

_TYPE_C_PRECEDENCE_TABLE = Source(
    title="USB Type-C Cable and Connector Specification, Release 2.0, August 2019",
    publisher="USB 3.0 Promoter Group, published by the USB Implementers Forum",
    url="https://www.usb.org/sites/default/files/USB%20Type-C%20Spec%20R2.0%20-%20August%202019.pdf",
    locator="Section 4.6, Table 4-17 'Precedence of power source usage' and its note 1",
    quote="USB BC 1.2: 5 V, Up to 1.5 A. A USB BC 1.2 power consumer may consume up to 1.5 A",
    accessed=ACCESSED,
)

# ------------------------------------------------------------------ household outlet
# Power is rated voltage x rated current of the receptacle. The 20 A receptacle is the
# larger of the two standard ratings, so it gives the more lenient limit.

US_OUTLET_VOLTAGE_V = Constant(
    key="us_outlet_rated_voltage_v",
    value=125.0,
    unit="V",
    description="Voltage rating of standard US 15 A and 20 A receptacles",
    source=_CFR_RECEPTACLE_VOLTAGE,
    note="The rating is above the 120 V nominal supply, which makes the limit lenient.",
)

US_OUTLET_CURRENT_A = Constant(
    key="us_outlet_max_rated_current_a",
    value=20.0,
    unit="A",
    description="Highest receptacle rating on a standard US 15 A or 20 A branch circuit",
    source=_CFR_RECEPTACLE_RATINGS,
    note=(
        "Table S-4 of the same section limits the cord-and-plug load on a 20 A receptacle to "
        "16 A, so the full 20 A rating is lenient."
    ),
)

# ------------------------------------------------------------------------ USB limits
# Keys are InputSource values from models.py.

_USB_PD_MAX_W = Constant(
    key="usb_pd_max_w",
    value=240.0,
    unit="W",
    description="Most power USB Power Delivery defines (Revision 3.1, 48 V at 5 A)",
    source=_USB_PD_PAGE,
    note="The highest power level in any USB standard. Before Revision 3.1 the limit was 100 W.",
)

USB_MAX_W: dict[str, Constant] = {
    "usb_pd": _USB_PD_MAX_W,
    "usb_c": _USB_PD_MAX_W,
    "usb_bc_1_2": Constant(
        key="usb_bc_1_2_max_w",
        value=7.5,
        unit="W",
        description="Most power a USB Battery Charging 1.2 consumer may draw (5 V at 1.5 A)",
        source=_TYPE_C_PRECEDENCE_TABLE,
        note="5 V × 1.5 A = 7.5 W. Soft limit: chargers often supply more than the standard defines.",
        hard_bound=False,
    ),
    "usb_3": Constant(
        key="usb_3_port_max_w",
        value=7.5,
        unit="W",
        description="Most power a USB 3.2 port supplies by default (dual-lane, 5 V at 1,500 mA)",
        source=_TYPE_C_PDP_TABLE,
        note=(
            "Single-lane ports, which include every USB 3.0 port, supply 4.5 W. The dual-lane "
            "figure is used because it is the more lenient. Soft limit."
        ),
        hard_bound=False,
    ),
    "usb_2": Constant(
        key="usb_2_port_max_w",
        value=2.5,
        unit="W",
        description="Most power a USB 2.0 port supplies (5 V at 500 mA)",
        source=_TYPE_C_PDP_TABLE,
        note="Soft limit: a listing may name USB 2.0 for the connector rather than as a power limit.",
        hard_bound=False,
    ),
}

# ------------------------------------------------------------------------- registry


def all_constants() -> list[Constant]:
    """Every Constant in this file. The tests check each one has a citation."""
    return [US_OUTLET_VOLTAGE_V, US_OUTLET_CURRENT_A, *dict.fromkeys(USB_MAX_W.values())]
