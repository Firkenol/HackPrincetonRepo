"""What a listing can state for the power-budget pack.

Built from the claim types in claimcheck.models, so every claim carries found_in,
quote and confidence. There is no field for a seller, store or brand name.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from claimcheck.models import NumberClaim, TextClaim


class PowerKind(str, Enum):
    RATED = "rated"  # continuous or rated power
    PEAK = "peak"  # peak, surge, maximum momentary


class InputSource(str, Enum):
    US_HOUSEHOLD_OUTLET = "us_household_outlet"  # standard 15 A or 20 A, 125 V wall receptacle
    USB_PD = "usb_pd"  # USB Power Delivery is named
    USB_C = "usb_c"  # only the USB-C connector is named
    USB_BC_1_2 = "usb_bc_1_2"  # USB Battery Charging 1.2 is named
    USB_3 = "usb_3"  # a USB 3.x port is named as the power source
    USB_2 = "usb_2"  # a USB 2.0 port is named as the power source
    OTHER = "other"  # anything else: 240 V outlet, vehicle socket, hard-wired, solar


class EnergyStorage(str, Enum):
    NONE = "none"  # no battery: output is drawn from the input as it is delivered
    BUILT_IN = "built_in"  # battery, power bank, capacitor bank


class PowerClaim(NumberClaim):
    """A power figure in watts."""

    kind: PowerKind = PowerKind.RATED


class InputSourceClaim(TextClaim):
    value: InputSource


class EnergyStorageClaim(TextClaim):
    value: EnergyStorage


class PowerBudgetClaims(BaseModel):
    """Everything the listing states that this pack uses. Absent means not stated."""

    model_config = ConfigDict(extra="forbid")

    output_power_w: PowerClaim | None = Field(
        default=None,
        description=(
            "Electrical or heating power the product claims to deliver or draw, in watts. "
            "Not the cooling or heating capacity of a heat pump or air conditioner, and "
            "not an 'equivalent' wattage such as on LED lamps."
        ),
    )
    input_source: InputSourceClaim | None = Field(
        default=None, description="What the listing says the product is powered from."
    )
    energy_storage: EnergyStorageClaim | None = Field(
        default=None,
        description=(
            "Whether the product stores energy. 'none' for a product with no battery, such as "
            "a heater, a charger or a hub. Absent when the listing does not make it clear."
        ),
    )
