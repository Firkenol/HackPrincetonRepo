"""Thresholds chosen by the team. These are judgment calls, not physical constants.

Physical reference data lives in constants.py with citations. Change values here
freely; change values there only with a source.
"""

# Check 1. Stated Wh must match V x Ah within this relative tolerance. 3% covers
# rounding to the printed precision and the 3.6 V versus 3.7 V nominal-voltage
# convention for lithium-ion (a 2.8% difference).
LABEL_WH_RELATIVE_TOLERANCE = 0.03

# A stated voltage counts as a nominal battery voltage if it falls within the cited
# per-cell range times a whole number of cells, widened by this rounding tolerance.
VOLTAGE_ROUNDING_TOLERANCE = 0.02

# Highest series cell count considered when matching a stated voltage.
MAX_SERIES_CELLS = 14

# Listed dimensions are treated as not describing the cell when their volume differs
# from the standard size envelope by more than this factor in either direction.
FORM_FACTOR_MISMATCH_RATIO = 2.0

# An "Impossible" verdict is auto-resolvable only if every extracted input of the
# violated check has at least this confidence. Calibrate in Phase 3.
MIN_CONFIDENCE_FOR_AUTO_RESOLVE = 0.8

# OPEN DECISION (raised in the Phase 1 report): routing for listings that pass.
ROUTING_WHEN_NO_RED_FLAGS = "needs human review"
ROUTING_WHEN_NO_CHECKABLE_CLAIM = "needs human review"
