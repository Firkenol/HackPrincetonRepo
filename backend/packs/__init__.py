"""Extra check packs: checks for claims outside batteries.

Each pack is a folder with the same three files:

- models.py     What a listing can state for this pack, built from the claim types in
                claimcheck.models (which stay unchanged).
- constants.py  The pack's physical reference data. Every value has a cited source.
- checks.py     Plain Python checks. Each takes the pack's claims and returns a
                claimcheck.models.CheckResult. CHECKS lists them; evaluate() runs
                them and returns a PackReport.

common.py holds what the packs share: result helpers, PackReport, and the verdict and
routing rules, which follow claimcheck/verdict.py.

Packs: power_budget.
"""
