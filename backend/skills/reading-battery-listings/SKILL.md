---
name: reading-battery-listings
description: Use when turning a battery listing's text into the Claims object for record_claims. Covers which field each stated value belongs in, package versus product measurements, power banks, and what to leave out.
---

# Reading a battery listing into claims

Record what the listing states, in the listing's own numbers. Never calculate, convert
or estimate. A field the listing is silent on is left out.

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
| 3.7 V, 7.4 V, 1.2 V | `nominal_voltage_v` | Battery nominal voltage only. Never a USB, output or charging voltage such as 5 V / 9 V / 12 V on a power bank. |
| 5200 mAh | `capacity_mah` | The labeled cell or pack capacity. |
| 38.48 Wh | `energy_wh` | Only if a Wh figure is printed. Never work it out. |
| "Rated capacity", "usable output" on a power bank | `output_capacity_mah` | Recorded, never compared. |
| Weight | `weight` with `kind` | See below. |
| L x W x H | `dimensions` with `kind` | For diameter x length, repeat the diameter as length and width. |
| "10-year shelf life" | `shelf_life_years` | |
| Codes printed on the product: R6, LR03 | `printed_codes` | Only when the text says the code is printed on the cell or pack. |
| Wording printed on the product: Heavy Duty | `printed_terms` | Same condition. |

`product_type`: `loose_cell` for single cells sold loose, `battery_pack` for assembled
packs such as hobby LiPo packs, `power_bank` for USB power banks, otherwise `unknown`.

## Units

Each field has a fixed unit: mAh, Wh, V, g, mm, years. Copy the number when the listing
uses that unit. If the listing gives the value only in another unit (Ah, kg, cm, inches,
ounces), leave the field out rather than converting, and do not put a converted number
in any field. The check will then report that property as not assessed.

## Package versus product

`kind` is `package` when the listing says package, packaging, shipping, box or parcel,
or labels the row "Package Dimensions" or "Item Package Weight". Otherwise `product`.
Package measurements are never used as a bound, so getting `kind` right matters more
than the number.

## Provenance

For every claim set:

- `found_in`: title, bullet points, spec table, description or label.
- `quote`: the few characters that state the claim, such as `12000mAh`.
- `confidence`: 1.0 when the text states the value plainly. Lower it (below 0.8) when
  the value is ambiguous, for example two different capacities appear, or it is unclear
  whether a voltage is nominal or an output.

## Never record

- A seller, store or brand name, in any field, including `quote`.
- Review counts, star ratings, prices.
- Anything inferred from what such products usually have.
