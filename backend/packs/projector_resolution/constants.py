"""Reference data for the projector-resolution pack: pixel counts of named resolutions.

Rules for this file (the same as claimcheck/constants.py):
- Every value carries a Source with a URL and a short supporting quote.
- Never add a value without a source.

These values are definitions of the names, not physical ceilings. The check built on
them only ever gives a "Flag", so each is marked hard_bound=False.

TODO(physics teammate): the sources below are Wikipedia pages at fixed revisions. The
primary documents are ITU-R BT.2020 (3840 x 2160 and 7680 x 4320), ITU-R BT.709
(1920 x 1080) and SMPTE ST 296 (1280 x 720). The ITU landing page shows no pixel
figures and the PDFs were not read, so no quote from them is given here. Replace
these citations with the primary text, and read each quote below against its page:
they were retrieved by an automated fetch on the access date.
"""

from __future__ import annotations

from dataclasses import dataclass

from claimcheck.constants import Constant, Source

ACCESSED = "2026-11-14"

# --------------------------------------------------------------------------- sources

_WIKI_UHDTV_1 = Source(
    title="Ultra-high-definition television",
    publisher="Wikipedia (revision 1384353681)",
    url="https://en.wikipedia.org/wiki/Ultra-high-definition_television",
    locator="Technical details, Resolution section",
    quote="UHDTV-1 is 3840 pixels wide by 2160 pixels tall (8.3 megapixels)",
    accessed=ACCESSED,
)

_WIKI_UHDTV_2 = Source(
    title="Ultra-high-definition television",
    publisher="Wikipedia (revision 1384353681)",
    url="https://en.wikipedia.org/wiki/Ultra-high-definition_television",
    locator="Technical details, Resolution section",
    quote="UHDTV-2 is 7680 pixels wide by 4320 pixels tall (33.18 megapixels)",
    accessed=ACCESSED,
)

_WIKI_1080P = Source(
    title="1080p",
    publisher="Wikipedia (revision 1356574563)",
    url="https://en.wikipedia.org/wiki/1080p",
    locator="Lead section",
    quote=(
        "characterized by 1,920 pixels displayed across the screen horizontally and 1,080 pixels "
        "down the screen vertically"
    ),
    accessed=ACCESSED,
)

_WIKI_720P = Source(
    title="720p",
    publisher="Wikipedia (revision 1371586915)",
    url="https://en.wikipedia.org/wiki/720p",
    locator="Lead section",
    quote=(
        "All major HD broadcasting standards (such as SMPTE 292M) include a 720p format, which has "
        "a resolution of 1280×720."
    ),
    accessed=ACCESSED,
)

# ----------------------------------------------------------------- named resolutions


@dataclass(frozen=True)
class Resolution:
    name: str  # the NamedResolution value
    label: str  # as shown in a report
    width_px: Constant
    height_px: Constant


def _resolution(name: str, label: str, width: float, height: float, source: Source) -> Resolution:
    def side(which: str, value: float) -> Constant:
        return Constant(
            key=f"resolution_{name}_{which}_px",
            value=value,
            unit="px",
            description=f"{which.capitalize()} of {label} in pixels",
            source=source,
            note="A definition of the name, not a physical ceiling.",
            hard_bound=False,
        )

    return Resolution(name=name, label=label, width_px=side("width", width), height_px=side("height", height))


RESOLUTIONS: dict[str, Resolution] = {
    "720p": _resolution("720p", "720p", 1280.0, 720.0, _WIKI_720P),
    "1080p": _resolution("1080p", "1080p", 1920.0, 1080.0, _WIKI_1080P),
    "4k": _resolution("4k", "4K", 3840.0, 2160.0, _WIKI_UHDTV_1),
    "8k": _resolution("8k", "8K", 7680.0, 4320.0, _WIKI_UHDTV_2),
}


def all_constants() -> list[Constant]:
    """Every Constant in this file. The tests check each one has a citation."""
    return [c for r in RESOLUTIONS.values() for c in (r.width_px, r.height_px)]
