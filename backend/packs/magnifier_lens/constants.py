"""Reference data for the magnifier-lens pack.

Rules for this file (the same as claimcheck/constants.py):
- Every value carries a Source with a URL and a short supporting quote.
- Never add a value without a source.

Only one value here has a source: the 250 mm near-point distance. Two other numbers
the check uses do not, and are therefore NOT constants. They are stated in every
report as assumptions (see REFERENCE_INDEX and the margin in checks.py).

TODO(physics teammate):
1. REFERENCE_INDEX = 1.5 has no citation. The textbook used below works its example
   with a glass of index 1.55, and gives no typical value. Find a source for the
   refractive index range of magnifier glass and acrylic, or confirm that the 2x
   margin in checks.py covers it (it covers every index up to 2.0).
2. The rule "a lens cannot be wider than twice its radius of curvature" is geometry
   (a spherical surface cannot be wider than its sphere) and the step from radius to
   focal length is the thin-lens lens maker's equation. Neither has a single citable
   value. Confirm the derivation in checks.py, including for thick lenses.
3. Makers use two conventions: M = 250 mm / f and M = 250 mm / f + 1. The check uses
   the first, as the brief specifies. The second gives a longer focal length for the
   same claimed power. Confirm the 2x margin is enough headroom for it.
"""

from __future__ import annotations

from claimcheck.constants import Constant, Source

ACCESSED = "2026-11-14"

_OPENSTAX_MAGNIFIER = Source(
    title="University Physics Volume 3, Section 2.7 The Simple Magnifier",
    publisher="OpenStax, Rice University",
    url="https://openstax.org/books/university-physics-volume-3/pages/2-7-the-simple-magnifier",
    locator="Equation 2.32, M = 25 cm / f for an image at infinity, and the sentence after it",
    quote=(
        "The resulting magnification is simply the ratio of the near-point distance to the focal "
        "length of the magnifying lens."
    ),
    accessed=ACCESSED,
)

NEAR_POINT_MM = Constant(
    key="near_point_distance_mm",
    value=250.0,
    unit="mm",
    description="Near-point distance used to define magnifying power",
    source=_OPENSTAX_MAGNIFIER,
    note="The source writes it as 25 cm. Magnifying power M = 250 mm ÷ focal length.",
)

# NOT a cited constant: see the TODO above. Reported as an assumption.
REFERENCE_INDEX = 1.5

# Where the lens maker's equation is taken from, named in the report's assumptions.
LENS_MAKERS_EQUATION_REFERENCE = (
    "OpenStax University Physics Volume 3, Section 2.4, Equation 2.21: 1/f = (n − 1)(1/R1 − 1/R2)"
)


def all_constants() -> list[Constant]:
    """Every Constant in this file. The tests check each one has a citation."""
    return [NEAR_POINT_MM]
