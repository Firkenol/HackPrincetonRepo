"""Reference data for the monocular-optics pack.

This pack uses no physical constant. Both checks compare two values the listing
itself states: the objective lens against the body it sits in, and the headline
figure against the fine print. The file exists so every pack has the same layout.

The one threshold the pack uses, a rounding tolerance, is team policy and lives in
checks.py.
"""

from __future__ import annotations

from claimcheck.constants import Constant


def all_constants() -> list[Constant]:
    """Every Constant in this file: none."""
    return []
