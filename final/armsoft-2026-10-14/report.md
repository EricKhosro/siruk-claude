# ArmSoft import — batch 2026-10-14-siruk (Felix + Pro Plan)

## Files
- `new-goods.xml` — 22 new goods, codes **1474–1495**, same format as the goods export
  (Accountant 6.0). Parses cleanly.
- `prices.xlsx` — 23 price rows: column A `Code` (text), B `Price (AMD)`, then unit, unit code,
  Armenian name, English name, note. Pro Plan 1495 has two rows: bag (003) and 1 kg (303).

Import order: **new-goods.xml first, then the prices.**

## The goods
| Codes | What | Unit | Price |
|---|---|---|---|
| 1474–1481 | Felix Tasty Chunks 75 g: beef, chicken, chicken & tomato, lamb, rabbit, salmon, trout, turkey | 001 piece | 200 |
| 1482 | Felix Tasty Chunks Kitten, chicken 75 g | 001 | 200 |
| 1483–1486 | Felix Double Yummy 75 g: beef & poultry, lamb & chicken, salmon & trout, turkey & liver | 001 | 200 |
| 1487–1489 | Felix Meat Slices 75 g: beef, chicken, duck | 001 | 200 |
| 1490–1492 | Felix Sensations in Sauce 75 g: beef & tomato, cod & tomato, turkey & bacon | 001 | 200 |
| 1493–1494 | Felix Tasty Pâté 75 g: beef & lamb, chicken & rabbit | 001 | 200 |
| 1495 | Pro Plan Sterilised Adult Renal Plus, turkey 10 kg — sold loose (IsWeight, unit 303, alt 003 × 10) | 003 bag / 303 kg | 39,500 / 3,950 |

Every good carries its pack EAN (from purina.ru). Pro Plan 1495: bag EAN 7613033566547 on unit
003, and the **new scale PLU 00106** on unit 303 (00103 is unused but was skipped on purpose —
the next free after 00105).

## Why codes start at 1474
The 2026-10-13 goods export (`Scale/armsoft-export-2026-10-13-final.xml`) ends at **1473**:
1442–1472 are the goods someone created by hand (Royal Canin bags and 12 × 85 g boxes; still an
open decision in `state/open-items.csv`), 1473 is "Delivery". No Felix / Pro Plan good exists yet.
None of our 22 EANs nor PLU 00106 is used by any good in that export.
**If goods were created by hand after 2026-10-13 (e.g. for this delivery), check before importing
— a code or barcode clash means a fresh export and a rebuild.**

## Kept in step
`csv/all-xml-scale.xml` = `Scale/all-xml-scale.xml` (target, now 1,461 goods) and
`Scale/scale-codes-per-kg.csv` hold the new goods. The target also got the 5 barcodes ArmSoft and
Siruk already carry since 2026-10-13 (goods 0159, 0160, 0901, 1003, and 0902 Dermobrush Fantasia
8022767060181) — no ArmSoft change needed for those.

## After the import
Siruk's variants still need `accounting_code` (1474–1495) and the 1 kg variant its PLU barcode
00106: `scripts/backfill-variant-codes.py --run runs/<date>` plans it, `--apply` writes it (asks first).
