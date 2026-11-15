---
name: running-claim-checks
description: Use when running the check tools on the recorded claims, for a battery listing or a projector, magnifying glass or monocular listing. Explains which checks apply to which category, what each check tests, what the statuses mean, what lookup_form_factor is for, and what not to do with the results.
---

# Running the checks

Call `list_checks` first. It takes no arguments and returns the category of the
recorded listing and the names of the check tools for that category. Then call every
check it names, in one turn if you can. Do not call a check it does not name: a check
for another category returns an error.

Every check tool takes no arguments. It reads the claims the listing reader recorded
and returns the full working: inputs, formula, each arithmetic step, the constant used
and its source.

## Battery listings: all six, every time

| Tool | Tests | Worst outcome |
|---|---|---|
| `check_label_consistency` | Stated Wh against stated V x Ah | flag |
| `check_form_factor_bound` | Stated capacity against what a standard size code can hold | violated |
| `check_dimension_bound` | Wh per litre from product dimensions against the chemistry ceiling | violated |
| `check_weight_bound` | Wh per kg from product weight against the chemistry ceiling | violated |
| `check_label_contradiction` | Stated chemistry against codes and wording printed on the product | flag |
| `check_chemistry_mismatch` | A claim that is unusual for the stated chemistry | flag |

## Projector, magnifying glass and monocular listings

| Category | Tool | Tests | Worst outcome |
|---|---|---|---|
| projector | `check_native_resolution` | Pixel count of the headline resolution against the stated native resolution | flag |
| magnifying glass | `check_lens_diameter` | Listed lens diameter against the widest lens the claimed power allows | violated |
| monocular | `check_objective_fits_body` | Claimed objective lens diameter against the listed body width | flag |
| monocular | `check_fine_print_consistency` | Headline magnification and objective against any "actual" figure in the fine print | flag |

`lookup_form_factor` is for battery listings and is optional. Given a size code such as 18650 or AA, it returns the
standard dimensions on file and their source. The checks already use these, so call it
only to see what a size code means.

## Statuses

- `pass`: the claim was tested and is plausible. It is not a confirmation.
- `violated`: a hard physical bound is exceeded.
- `flag`: a contradiction or unusual claim that a person should look at.
- `not_assessed`: the listing did not give what the check needs. This is normal and is
  not a problem with the listing.

## What not to do

- Do not calculate anything. Do not redo, round or restate the arithmetic. The tool
  output is the record.
- Do not decide the verdict or routing. The report writer's tool does that.
- Do not call a check again hoping for a different result. The same claims give the
  same result.
- Do not try to correct the claims. If a check says no claims are recorded, stop and
  say so.
- A power bank's usable output being lower than its labeled cell capacity is normal
  conversion loss. It is never a finding, and no check tests it.
- A package weight or package size is never used as a bound. The weight and dimension
  checks set it aside and say so.

## Your reply

One sentence: the checks have run. State no number. Never write "verified", "genuine",
"fake" or "counterfeit", and speak about the claim, never about who is selling the
product.
