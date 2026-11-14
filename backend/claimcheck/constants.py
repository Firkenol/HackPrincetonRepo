"""Physical reference data. This is the only file that holds physical constants.

Rules for this file:
- Every value carries a Source with a URL and a short supporting quote.
- Energy ceilings are best-case values (the best cell on record for the chemistry),
  so honest products sit well below them.
- Never add a value without a source. If no source exists, leave the chemistry out:
  the checks then report "not assessed" instead of guessing.

Unit conversions used elsewhere (1 L = 1,000,000 mm3, 1 kg = 1000 g, 1 Ah = 1000 mAh)
are SI definitions and need no citation.
"""

from __future__ import annotations

from dataclasses import dataclass

ACCESSED = "2026-11-13"


@dataclass(frozen=True)
class Source:
    title: str
    publisher: str
    url: str
    locator: str  # where in the document the value appears
    quote: str  # short verbatim text supporting the value
    accessed: str = ACCESSED


@dataclass(frozen=True)
class Constant:
    key: str
    value: float
    unit: str
    description: str
    source: Source
    note: str = ""
    # False for a ceiling that lacks a primary source with comfortable headroom.
    # Exceeding such a ceiling is a soft "Flag", never "Impossible".
    hard_bound: bool = True


# --------------------------------------------------------------------------- sources

_AMPRIUS = Source(
    title="The All-New Amprius 500 Wh/kg Battery Platform is Here",
    publisher="Amprius Technologies press release, 23 March 2023",
    url="https://amprius.com/the-all-new-amprius-500-wh-kg-battery-platform-is-here/",
    locator="Paragraph on third-party testing by Mobile Power Solutions",
    quote="The results indicate that this cell model provides >504 Wh/kg and >1321 Wh/l at 25°C.",
)

_SNL_NIMH = Source(
    title="nikkel-metallhydridbatteri",
    publisher="Store norske leksikon (author Knut Hofstad, updated 3 October 2024)",
    url="https://snl.no/nikkel-metallhydridbatteri",
    locator="Fact box",
    quote="energitettheten kan variere fra 170 til 420 Wh/L",
)

_WIKI_NIMH = Source(
    title="Nickel–metal hydride battery",
    publisher=(
        "Wikipedia (revision 1380037960), citing K. Bullis, 'Old Battery Type Gets an "
        "Energy Boost', MIT Technology Review, 19 February 2015"
    ),
    url="https://en.wikipedia.org/wiki/Nickel%E2%80%93metal_hydride_battery",
    locator="History section",
    quote="allowing the specific energy to reach 140 watt-hours per kilogram.",
)

_NCR18650B = Source(
    title="Panasonic NCR18650B lithium-ion cell datasheet, version 13.11 R1",
    publisher="SANYO Energy (U.S.A.) Corporation / Panasonic, 2012",
    url=(
        "https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/"
        "196/Panasonic-NCR18650B-datasheet.pdf"
    ),
    locator="Specifications table and dimension drawing",
    quote="Nominal voltage 3.6V; Weight (max.) 48.5 g; Max. 18.5 mm; Max. 65.3 mm",
)

_P42A = Source(
    title="Molicel INR-21700-P42A product data sheet (INR21700P42A-V4-80092)",
    publisher="E-One Moli Energy Corp.",
    url="https://www.molicel.com/wp-content/uploads/INR21700P42A-V4-80092.pdf",
    locator="Physical characteristics",
    quote="Diameter 21.7 mm (Max); Height 70.2 mm (Max); Weight 70 g (Max)",
)

_EN92 = Source(
    title="Energizer EN92 product datasheet, form no. EN92EU0126",
    publisher="Energizer Brands, LLC",
    url="https://data.energizer.com/pdfs/EN92EU0126.pdf",
    locator="Specifications block and industry standard dimensions drawing",
    quote=(
        "Classification: Alkaline; Designation: ANSI-24A, IEC-LR03; Nominal Voltage: "
        "1.5 volts; Shelf Life: 10 years at 21°C; 10.50 / 44.50 mm maximum"
    ),
)

_EVEREADY_1215 = Source(
    title="Eveready 1215 product datasheet, form no. 1215NA0218",
    publisher="Energizer Brands, LLC",
    url="https://data.energizer.com/pdfs/1215.pdf",
    locator="Specifications block",
    quote=(
        "AA SUPER HEAVY DUTY; Chemical System: Zinc-Manganese Dioxide (Zn/MnO2); "
        "Designation: ANSI-15D, IEC-R6; Battery Voltage: 1.5 Volts"
    ),
)

_CZ_HANDBOOK_GRADES = Source(
    title="Eveready Carbon Zinc Battery Handbook and Application Manual",
    publisher="Energizer Brands, LLC, 2018",
    url="https://data.energizer.com/pdfs/carbonzinc_appman.pdf",
    locator="Page 1, introduction",
    quote=(
        "Eveready Carbon Zinc batteries are marketed in three basic grades—General "
        "Purpose, Heavy Duty and Super Heavy Duty."
    ),
)

_CZ_HANDBOOK_STORAGE = Source(
    title="Eveready Carbon Zinc Battery Handbook and Application Manual",
    publisher="Energizer Brands, LLC, 2018",
    url="https://data.energizer.com/pdfs/carbonzinc_appman.pdf",
    locator="Page 8, table 'Service Maintenance (storage at 21°C)'",
    quote="1 year 90-100%; 2 years 80-90%; 3 years 75-85%; 4 years 65-80%",
)

_NIMH_HANDBOOK = Source(
    title="Nickel Metal Hydride (NiMH) Handbook and Application Manual, version NiMH02.01",
    publisher="Energizer Battery Manufacturing Inc., 2010",
    url="https://data.energizer.com/wp-content/uploads/2020/11/nimhhandbook_ver2-2.pdf",
    locator="Table 1, row 'Rated Voltage'",
    quote="Rated Voltage 1.25V vs. 1.5V",
)

_WIKI_NOMENCLATURE = Source(
    title="Battery nomenclature",
    publisher="Wikipedia, tables citing IEC 60086-1 ed. 10.0 and IEC 61951-2 ed. 2.0",
    url="https://en.wikipedia.org/wiki/Battery_nomenclature",
    locator="IEC 60086 letter-code table; secondary-cell table; IEC size-code table",
    quote=(
        "(none): Zinc | Ammonium chloride, Zinc chloride | Manganese dioxide | 1.5; "
        "L: Zinc | Alkali metal hydroxide | Manganese dioxide | 1.5; "
        "H: Hydrogen-absorbing alloy | Nickel oxide | 1.2; R6 | 14.5 | 50.5 | AA"
    ),
)

_WIKI_AA = Source(
    title="AA battery",
    publisher="Wikipedia, citing IEC 60086-2:2021 (Primary batteries, Part 2)",
    url="https://en.wikipedia.org/wiki/AA_battery",
    locator="Dimensions section",
    quote=(
        "An AA cell measures 49.5–50.5 mm (1.95–1.99 in) in length, including the button "
        "terminal—and 13.7–14.5 mm (0.54–0.57 in) in diameter."
    ),
)

_WIKI_LIION = Source(
    title="Lithium-ion battery",
    publisher="Wikipedia (revision 1385440650)",
    url="https://en.wikipedia.org/wiki/Lithium-ion_battery",
    locator="Infobox, 'Nominal cell voltage'",
    quote="3.6 / 3.7 / 3.8 / 3.85 V; LiFePO4 3.2 V",
)

# ------------------------------------------------------------------- energy ceilings
# Keys are Chemistry values from models.py. A chemistry with no entry has no vetted
# best-case ceiling, and the bound checks report "not assessed" for it.
# NiMH ceilings are soft (hard_bound=False) until a primary source with comfortable
# headroom is found: honest products must never get a hard result.
# Alkaline and zinc-carbon are deliberately absent: published figures for them are
# delivered energy at about 1.2 V average, which is not comparable with label math
# (1.5 V x mAh), so no published value is a safe ceiling.

MAX_WH_PER_L: dict[str, Constant] = {
    "li-ion": Constant(
        key="li_ion_max_wh_per_l",
        value=1321.0,
        unit="Wh/L",
        description="Highest volumetric energy density measured by a third-party lab for a lithium-ion cell",
        source=_AMPRIUS,
        note="About twice the 676 Wh/L of a leading commercial 18650 (Panasonic NCR18650B datasheet).",
    ),
    "nimh": Constant(
        key="nimh_max_wh_per_l",
        value=420.0,
        unit="Wh/L",
        description="Top of the published volumetric energy density range for NiMH cells",
        source=_SNL_NIMH,
        note=(
            "Secondary source with thin headroom over the highest AA ratings on sale, so "
            "exceeding it is a soft flag, not a hard result."
        ),
        hard_bound=False,
    ),
}

MAX_WH_PER_KG: dict[str, Constant] = {
    "li-ion": Constant(
        key="li_ion_max_wh_per_kg",
        value=504.0,
        unit="Wh/kg",
        description="Highest specific energy measured by a third-party lab for a lithium-ion cell",
        source=_AMPRIUS,
        note="About twice the 243 Wh/kg of a leading commercial 18650 (Panasonic NCR18650B datasheet).",
    ),
    "nimh": Constant(
        key="nimh_max_wh_per_kg",
        value=140.0,
        unit="Wh/kg",
        description="Highest reported specific energy for a NiMH cell (research cells)",
        source=_WIKI_NIMH,
        note="Secondary source, so exceeding it is a soft flag, not a hard result.",
        hard_bound=False,
    ),
}

# ------------------------------------------------------------------ nominal voltages
# NOMINAL is used when a listing gives capacity but no voltage. For lithium-ion it is
# the lower of the common values, which gives the lower (more lenient) energy.
# MIN / MAX bound what counts as a nominal per-cell voltage, to tell a battery
# voltage from an output voltage such as 5 V USB.

NOMINAL_CELL_VOLTAGE: dict[str, Constant] = {
    "li-ion": Constant("li_ion_nominal_v", 3.6, "V", "Nominal lithium-ion cell voltage", _NCR18650B),
    "nimh": Constant("nimh_nominal_v", 1.2, "V", "Nominal NiMH cell voltage", _WIKI_NOMENCLATURE),
    "alkaline": Constant("alkaline_nominal_v", 1.5, "V", "Nominal alkaline cell voltage", _EN92),
    "zinc-carbon": Constant("zinc_carbon_nominal_v", 1.5, "V", "Nominal zinc-carbon cell voltage", _EVEREADY_1215),
}

MIN_CELL_VOLTAGE: dict[str, Constant] = {
    "li-ion": Constant("li_ion_min_nominal_v", 3.2, "V", "Lowest nominal voltage in the lithium-ion family (LiFePO4)", _WIKI_LIION),
    "nimh": NOMINAL_CELL_VOLTAGE["nimh"],
    "alkaline": NOMINAL_CELL_VOLTAGE["alkaline"],
    "zinc-carbon": NOMINAL_CELL_VOLTAGE["zinc-carbon"],
}

MAX_CELL_VOLTAGE: dict[str, Constant] = {
    "li-ion": Constant("li_ion_max_nominal_v", 3.85, "V", "Highest nominal voltage in the lithium-ion family", _WIKI_LIION),
    "nimh": Constant("nimh_max_rated_v", 1.25, "V", "Highest rated voltage quoted for NiMH cells", _NIMH_HANDBOOK),
    "alkaline": NOMINAL_CELL_VOLTAGE["alkaline"],
    "zinc-carbon": NOMINAL_CELL_VOLTAGE["zinc-carbon"],
}

# --------------------------------------------------------------------- form factors
# Dimensions are the maximum envelope, so the computed volume is an upper bound.


@dataclass(frozen=True)
class FormFactor:
    code: str
    diameter_mm: Constant
    height_mm: Constant
    default_chemistry: str | None = None  # set where the size code implies a chemistry
    max_cell_mass_g: Constant | None = None  # used only to describe package weights


FORM_FACTORS: dict[str, FormFactor] = {
    "18650": FormFactor(
        code="18650",
        diameter_mm=Constant("ff_18650_diameter", 18.5, "mm", "18650 maximum diameter", _NCR18650B),
        height_mm=Constant("ff_18650_height", 65.3, "mm", "18650 maximum height", _NCR18650B),
        default_chemistry="li-ion",
        max_cell_mass_g=Constant("ff_18650_mass", 48.5, "g", "Maximum mass of an 18650 cell", _NCR18650B),
    ),
    "21700": FormFactor(
        code="21700",
        diameter_mm=Constant("ff_21700_diameter", 21.7, "mm", "21700 maximum diameter", _P42A),
        height_mm=Constant("ff_21700_height", 70.2, "mm", "21700 maximum height", _P42A),
        default_chemistry="li-ion",
        max_cell_mass_g=Constant("ff_21700_mass", 70.0, "g", "Maximum mass of a 21700 cell", _P42A),
    ),
    "AA": FormFactor(
        code="AA",
        diameter_mm=Constant("ff_aa_diameter", 14.5, "mm", "AA maximum diameter", _WIKI_AA),
        height_mm=Constant("ff_aa_height", 50.5, "mm", "AA maximum length", _WIKI_AA),
    ),
    "AAA": FormFactor(
        code="AAA",
        diameter_mm=Constant("ff_aaa_diameter", 10.5, "mm", "AAA maximum diameter", _EN92),
        height_mm=Constant("ff_aaa_height", 44.5, "mm", "AAA maximum height", _EN92),
    ),
}

# ------------------------------------------------------- IEC designations (check 5)
# The letter before the shape letter names the electrochemical system. "" means no
# system letter, as in R6 or R03.

IEC_CODES_SOURCE = _WIKI_NOMENCLATURE
IEC_SHAPE_LETTERS = frozenset({"R", "F", "P", "S"})
IEC_SYSTEM_LETTERS: dict[str, str] = {
    "": "zinc-carbon",
    "L": "alkaline",
    "H": "nimh",
    "K": "nicd",
    "F": "lithium-primary",
    "C": "lithium-primary",
    "B": "lithium-primary",
    "E": "lithium-primary",
}

# Datasheets that show the two designations in use on real products.
IEC_EXAMPLE_ZINC_CARBON = Constant(
    "iec_r6_example", 6, "IEC size", "R6 designates a zinc-carbon AA cell", _EVEREADY_1215
)
IEC_EXAMPLE_ALKALINE = Constant(
    "iec_lr03_example", 3, "IEC size", "LR03 designates an alkaline AAA cell", _EN92
)

# Grade names printed on carbon-zinc cells. Longest first so the most specific wins.
CARBON_ZINC_GRADE_TERMS: tuple[str, ...] = ("super heavy duty", "heavy duty", "general purpose")
CARBON_ZINC_GRADES = Constant(
    "carbon_zinc_grades", 3, "grades", "Grade names used for carbon-zinc cells", _CZ_HANDBOOK_GRADES
)

# --------------------------------------------------------------- shelf life (check 6)
# Only chemistries listed here get a shelf-life comparison. Alkaline is not listed as
# a limit: brands quote 10 years or more, so there is no safe threshold to apply.

MAX_PUBLISHED_STORAGE_YEARS: dict[str, Constant] = {
    "zinc-carbon": Constant(
        key="zinc_carbon_max_published_storage_years",
        value=4.0,
        unit="years",
        description="Longest storage period with published service retention for carbon-zinc cells",
        source=_CZ_HANDBOOK_STORAGE,
        note="At 4 years the handbook reports 65-80% of fresh service retained.",
    ),
}

ALKALINE_SHELF_LIFE_REFERENCE = Constant(
    key="alkaline_shelf_life_reference_years",
    value=10.0,
    unit="years",
    description="Shelf life stated on an alkaline cell datasheet, for comparison",
    source=_EN92,
)

# ------------------------------------------------------------------------- registry


def all_constants() -> list[Constant]:
    """Every Constant in this file. The test suite checks each one has a citation."""
    found: list[Constant] = []
    for table in (
        MAX_WH_PER_L,
        MAX_WH_PER_KG,
        NOMINAL_CELL_VOLTAGE,
        MIN_CELL_VOLTAGE,
        MAX_CELL_VOLTAGE,
        MAX_PUBLISHED_STORAGE_YEARS,
    ):
        found.extend(table.values())
    for ff in FORM_FACTORS.values():
        found.extend(c for c in (ff.diameter_mm, ff.height_mm, ff.max_cell_mass_g) if c)
    found.extend(
        [IEC_EXAMPLE_ZINC_CARBON, IEC_EXAMPLE_ALKALINE, CARBON_ZINC_GRADES, ALKALINE_SHELF_LIFE_REFERENCE]
    )
    return found
