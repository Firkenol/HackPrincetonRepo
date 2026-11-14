---
name: running-claim-checks
description: Use after record_claims, when running the six check tools and assemble_report. Explains what each check tests, what the statuses mean, and how to word anything said about the result.
---

# Running the checks

All six check tools take no arguments. They read the claims saved by `record_claims`
and return the full working: inputs, formula, each arithmetic step, the constant used
and its source. Call all six every time, then `assemble_report`.

| Tool | Tests | Worst outcome |
|---|---|---|
| `check_label_consistency` | Stated Wh against stated V x Ah | flag |
| `check_form_factor_bound` | Stated capacity against what a standard size code can hold | violated |
| `check_dimension_bound` | Wh per litre from product dimensions against the chemistry ceiling | violated |
| `check_weight_bound` | Wh per kg from product weight against the chemistry ceiling | violated |
| `check_label_contradiction` | Stated chemistry against codes and wording printed on the product | flag |
| `check_chemistry_mismatch` | A claim that is unusual for the stated chemistry | flag |

## Statuses

- `pass`: the claim was tested and is plausible. It is not a confirmation.
- `violated`: a hard physical bound is exceeded.
- `flag`: a contradiction or unusual claim that a person should look at.
- `not_assessed`: the listing did not give what the check needs. This is normal and is
  not a problem with the listing.

## What not to do

- Do not redo, round or restate the arithmetic. The tool output is the record.
- Do not decide the verdict or routing. `assemble_report` returns them.
- Do not call a check again hoping for a different result. Call `record_claims` again
  only if the first extraction misread the listing.
- A power bank's usable output being lower than its labeled cell capacity is normal
  conversion loss. It is never a finding.

## Wording

The four verdicts are exactly "Impossible", "Flag", "No red flags" and "No checkable
claim". Never write "verified", "genuine", "fake" or "counterfeit". Speak about the
claim, never about who is selling the product.
