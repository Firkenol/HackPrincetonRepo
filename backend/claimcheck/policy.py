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

# Extraction confidence at or above this counts as high. Below it, a result is
# routed to a person whatever the verdict. Calibrate in Phase 3.
MIN_CONFIDENCE = 0.8
