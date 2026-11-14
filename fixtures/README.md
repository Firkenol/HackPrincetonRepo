# Fixtures

Screenshots of real listings, captured 2026-11-14, with the seller name, the
"Visit the ... Store" link and the delivery address covered before they were
committed. Product brand markings are left as they appear on the product.
No fixture, test or report records a seller, store or brand name.

`expected/fixture_NN.json` is the evidence report the check code produces for the
hand-entered claims of fixture NN (`backend/tests/fixtures_data.py`). Regenerate with
`python scripts/write_expected_reports.py` from `backend/`. Text versions of the
listings are `fixture_NN.txt` here and, identically, in `backend/agent/tests/listings.py`.

Fixtures 1 to 9 are the nine in SPEC.md; 1 to 7 have no screenshot yet. Fixtures 10 to
20 were added from the screenshots below. Where a listing needed two screens, `a` is
the top of the page and `b` the "About this item" section.

| Fixture | Screenshot(s) | Listing | Expected verdict | Expected routing |
|---|---|---|---|---|
| 8 | `fixture_08.jpg` | 2S LiPo 7.4 V 5200 mAh, label 38.48 Wh, 25 x 47 x 139 mm, 307 g | No red flags | no action needed |
| 9 | `fixture_09.jpg` | Same listing, top of page only: weight and dimensions not visible | No red flags | no action needed |
| 10 | `fixture_10a.jpg`, `fixture_10b.jpg` | AAA alkaline 4-pack, 1.5 V, cells read LR03/AM-4, "140 minutes", no capacity | No checkable claim | no action needed |
| 11 | `fixture_11a.jpg`, `fixture_11b.jpg` | 9 V alkaline 4-pack, 6LR61, 7-year shelf life | No checkable claim | needs human review |
| 12 | `fixture_12a.jpg`, `fixture_12b.jpg` | AAA alkaline 4-pack, 12-year shelf life | No checkable claim | needs human review |
| 13 | `fixture_13a.jpg`, `fixture_13b.jpg` | AAA alkaline 8-pack, 1.5 V, 10-year shelf life, cells read LR03 AM4 | No checkable claim | needs human review |
| 14 | `fixture_14a.jpg`, `fixture_14b.jpg` | 6 V spring lantern battery, "Super Heavy Duty", no chemistry or capacity stated | No checkable claim | no action needed |
| 15 | `fixture_15a.jpg`, `fixture_15b.jpg` | AAA 4-pack, card reads "Carbon zinc" and "Super Heavy Duty", 1.5 V | No checkable claim | no action needed |
| 16 | `fixture_16a.jpg`, `fixture_16b.jpg` | 1S LiPo pouch 3.7 V 2000 mAh, label 7.4 Wh, 34 x 10 x 50 mm, 35 g | No red flags | no action needed |
| 17 | `fixture_17a.jpg`, `fixture_17b.jpg` | 3S LiPo 11.1 V 1300 mAh, label 14.4 Wh, 72 x 36 x 23 mm, 119 g | No red flags | no action needed |
| 18 | `fixture_18a.jpg`, `fixture_18b.jpg` | LiPo pouch 3.7 V 3000 mAh, label 11.1 Wh, 36 x 10 x 65 mm, 49 g | No red flags | no action needed |
| 19 | `fixture_19a.jpg`, `fixture_19b.jpg` | LiPo pouch 4-pack 3.7 V 1000 mAh, label 3.7 Wh, 30 x 8 x 42 mm, 18 g | No red flags | no action needed |
| 20 | `fixture_20a.jpg`, `fixture_20b.jpg` | LiPo pouch 3.7 V 1100 mAh, label 4.1 Wh, 34.5 x 51 x 6.3 mm, 22 g | No red flags | no action needed |

Things in these screenshots worth knowing when judging extraction (Phase 3):

- Fixture 10 says "Capacity: 1.5v" in a bullet. That is a voltage, not a capacity; the
  extractor should not put it in `capacity_mah`.
- Fixture 11's 6LR61 code is printed on the retail card, not on the cells. The cells
  read only "Ultra alkaline".
- Fixture 13 and 10 have the IEC code on the cells themselves (LR03), which is what
  check 5 compares against the stated chemistry.
- Fixture 15's card shows a "6 Pack" badge while the title says 4 count. Not a
  checkable claim. Its spec table lists "Amperage 1.5 A", which is not a capacity.
- Fixtures 11, 12 and 13 route to "needs human review" only because they state a
  shelf life and `constants.py` has no alkaline shelf-life reference, so the claim
  counts as numeric but untested. See PROGRESS.md.
- Fixture 20 gives "Typical capacity 1100 mAh, Min capacity 1000 mAh"; the label's
  1100 mAh is the capacity claim.
- Fixture 16 and 18 list "Dimensions" in bullet points without saying package, so
  they are product dimensions.
