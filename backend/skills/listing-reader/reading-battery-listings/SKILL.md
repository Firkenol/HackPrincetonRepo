---
name: reading-battery-listings
description: Use when reading a battery listing, pasted text or an image (screenshot or product photo), into the claims for record_claims. Covers which field each stated value belongs in, units, codes printed on the product, confidence, package versus product measurements, and what to leave out.
---

# Reading a battery listing into claims

Record what the listing states, in the listing's own numbers and units, with one call
to `record_claims`. Never calculate, convert or estimate. A field the listing is silent
on is left out. You do not run checks or judge the listing; other agents do that from
what you record.

## Field by field

| Listing says | Field | Notes |
|---|---|---|
| Li-ion, lithium-ion, LiPo, Li-polymer, LiFePO4 | `chemistry.value = "li-ion"` | All rechargeable lithium is `li-ion`. |
| Ni-MH, NiMH | `"nimh"` | |
| Alkaline | `"alkaline"` | |
| Carbon zinc, zinc carbon, zinc chloride | `"zinc-carbon"` | "Heavy duty" alone is a grade term, not a chemistry statement. |
| Ni-Cd | `"nicd"` | |
| Lithium (non-rechargeable), Li-FeS2, CR-series | `"lithium-primary"` | |
| 18650, 21700, AA, AAA | `form_factors` | One entry per size code. |
| 2S, 3S, "2 cell pack" | `cell_count` | The number of cells the stated capacity covers. A multipack of loose cells each rated on its own is 1, or left out. |
| 3.7 V, 7.4 V, 1.2 V | `nominal_voltage` | Battery nominal voltage only. Never a USB, output or charging voltage such as 5 V / 9 V / 12 V on a power bank. |
| 5200 mAh, 5.2 Ah | `capacity` | The labeled cell or pack capacity. |
| 38.48 Wh | `energy` | Only if a Wh figure is shown. Never work it out. |
| "Rated capacity", "usable output" on a power bank | `output_capacity` | Only when the listing labels a figure this way. Never a copy of `capacity`. Recorded, never compared. |
| Weight | `weight` with `kind` | See below. |
| L x W x H | `dimensions` with `kind` | All three sides must be stated. For diameter x length, repeat the diameter as length and width. See "Partial measurements". |
| "10-year shelf life" | `shelf_life` | |
| Codes printed on the product: R6, LR03 | `printed_codes` | See "Images" below. |
| Grade wording printed on a cell: Heavy Duty | `printed_terms` | Grade wording only. See "Images" below. |

`product_type`: `loose_cell` for single cells sold loose, `battery_pack` for assembled
packs such as hobby LiPo packs, `power_bank` for USB power banks, otherwise `unknown`.

## Partial measurements

A listing often gives one measurement only, such as "just 0.63 inches thick" or "0.39-inch
slim". That is not `dimensions`. Leave `dimensions` out, and never repeat the one number
for the other sides: a made-up box gives a made-up result. Record the weight if it is
stated; the weight check does not need dimensions.

A multipack of separate items (a 2-pack of power banks, a 4-pack of AAA cells) is rated
per item. Record the capacity, weight and dimensions of one item, and leave `cell_count`
out or set it to 1. `cell_count` is for cells wired together inside one pack, such as 2S.

## Units

Give the number and the unit exactly as shown. `record_claims` converts in Python and
returns the stored value in standard units, so you never convert.

| Field | Units accepted |
|---|---|
| `capacity`, `output_capacity` | mAh, Ah |
| `energy` | Wh, mWh |
| `nominal_voltage` | V, mV |
| `weight` | g, kg, mg, oz, lb |
| `dimensions` | mm, cm, m, in (one unit for all three sides) |
| `shelf_life` | years, months |

If the listing uses a unit that is not in the table, or mixes units in one measurement
(for example pounds and ounces together), leave the field out. Do not convert it
yourself. When the same value is shown in two units, record the one in the left-most
unit of the table.

## Images

The listing may arrive as a screenshot of a product page or a photo of the product.

- Read the page text (title, bullet points, spec table) exactly as you would pasted text.
- Then look at the product itself in the picture. Small print on the cell jacket or the
  pack label is evidence: designation codes such as R6, R03, LR6, LR03, FR6, HR6, 6F22
  go in `printed_codes`, one entry per code, and grade wording such as "Heavy Duty" or
  "Super Heavy Duty" goes in `printed_terms`. Use `found_in: "product photo"`.
- Other print on the product is not a claim: slogans, product-line names, brand words,
  and words such as "Power Bank", "Ultra", "Max" or "Charge". Do not record it anywhere.
- Record the chemistry the title or description states in `chemistry`, even if the
  codes on the product suggest another. Do not reconcile them; a check compares them.
- Do not guess characters you cannot read. Leave the claim out, or record it with low
  confidence if most of it is legible.
- Ignore store names, logos, brand marks, prices, ratings and reviews.

## Package versus product

`kind` is `package` when the listing says package, packaging, shipping, box or parcel,
or labels the row "Package Dimensions" or "Item Package Weight". Otherwise `product`.
Package measurements are never used as a bound, so getting `kind` right matters more
than the number.

## Provenance

Every claim needs:

- `found_in`: title, bullet points, spec table, description, label or product photo.
- `quote`: the few characters that state the claim, such as `12000mAh`.
- `confidence`: 1.0 when the text states the value plainly and is sharp. Below 0.8 when
  the value is ambiguous (two different capacities appear, or it is unclear whether a
  voltage is nominal or an output) or hard to read (small, blurred, cropped, glare).
  Anything below 0.8 sends the listing to a person, which is the right outcome when
  you are unsure.

## Never record

- A seller, store or brand name, in any field, including `quote`.
- Review counts, star ratings, prices.
- Anything inferred from what such products usually have.
- The word "verified", in any field. If the listing uses it next to a value, quote
  only the value. `record_claims` rejects a claim that contains it.

## When record_claims returns an error

The message names the field and the problem. Fix that field, or leave it out if the
listing does not state it in an accepted form, and call `record_claims` again with the
full set of claims. A new call replaces the earlier one.

## Your reply

One sentence: the claims are recorded. Do not repeat the claims, give an opinion on
the listing, or name a seller, store or brand.
