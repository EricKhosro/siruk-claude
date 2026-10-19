# ArmSoft sync — 2026-10-16 (afternoon)

Sources: ArmSoft `ExportAll_Latest.xml` (1,476 goods, codes 0001–1495; copied to
`Scale/armsoft-export-2026-10-16-pm.xml`) and `ExportAllPrices_Latest.xlsx` (1,510 code+unit
prices) vs the live Siruk catalogue re-read just now (968 products, 1,551 variants).
Compared with this morning's export (`Scale/armsoft-export-2026-10-16.xml`).

## Result
- **Every live Siruk variant reaches an ArmSoft good**, so there is **no new-goods file**. The
  Siruk products not fully in ArmSoft yet (Felix, Pro Plan, the 5 Trixie treats sold loose)
  already have goods. They are only missing barcodes, units and prices, and that is what
  these files add.
- **Every price ArmSoft already has matches Siruk.** `prices.xlsx` only adds the 77 prices that
  are missing.
- No barcode sits on two goods. No bad check digits.

## Your Royal Canin work: checked
- **All 22 RC bags are right** (1443–1465 without 1456): bag EAN on 003 and PLU on 303,
  exactly as planned.
- **RC boxes 1466 / 1467 / 1468** have their box EAN. You kept unit 002 (×12) on them.
- 19 of our old codes are deleted. **7 are still in ArmSoft, emptied of barcodes:** 1342, 1348,
  1350, 1353, 1356 (bags) and 1377, 1383 (boxes). They still carry their old prices. Delete them
  when ArmSoft allows it. Nothing points at them any more.

## Decision needed: 4 RC 12-boxes went the other way

| Product | Hand-made code | Our old code | Who has the barcode now |
|---|---|---|---|
| Light Weight Care in Jelly | 1469 ✔ | 1387 | 1469. **1387 was deleted this morning and is back** (no barcode, price 8,650) |
| Urinary Care in Gravy | 1470 (empty) | 1401 | **1401**: 9003579000359 |
| Renal in Gravy, fish | 1471 (empty) | 1399 | **1399**: 9003579000519 |
| Sensory Smell in Gravy | 1472 (empty) | 1403 | **1403**: 9003579018507. 1403 was also deleted this morning and is back |

This morning 1470–1472 held these barcodes. Now our old codes hold them, and 1470–1472 have lost
their English names and unit 002. Tell me which side to keep for these four. Until then they are
**not in the update file.** Their price is still open too (the old box goods sell at 8,650).

## Files, in import order

| # | File | What |
|---|---|---|
| 1 | `goods-update.xml` | 27 existing goods, each built from ArmSoft's own block (unchanged since this morning) with only the barcode / unit parts changed. 21 Felix (1474–1495 without 1478) get the pouch EAN. Pro Plan 1478 and Trixie 0403 / 0459 / 0516 / 0517 / 0552 become weight goods (303 kg + PLU, 003 bag + EAN). |
| 2 | `prices.xlsx` | 77 rows: code (text), price, unit, unit code, names, note. 22 RC bags × (bag + kg), 21 Felix at 200, Pro Plan bag + kg, 5 Trixie × (bag + kg). |
| or | `goods-update.xlsx` | **The by-hand version of 1 + 2 together**: Start here → 1 Felix (21) → 2 Weight goods (6) → 3 RC bag prices (22), every barcode and all 77 prices, with a tick column. |
| — | `changes.xlsx` | Every finding, one sheet each: goods to update, barcodes to add, units to add, prices to add, ArmSoft-only goods, Siruk with no good (empty), and the Siruk variants still holding the old RC code. |

ArmSoft may refuse to update an existing code from an XML import. **Try `goods-update.xml` on
one good first.** If it refuses, `changes.xlsx` → "goods to update" lists what to type in by hand.
The 003/303 prices of the 6 weight goods only land once those goods have the units. If ArmSoft
won't change the main unit of a good with movements, use this table:

| Good | Product | Bag | 003 bag price | 303 per kg | PLU | Bag EAN (003) |
|---|---|---|---|---|---|---|
| 0403 | Trixie Soft Snack Bony Mix XXL | 1.8 kg | 11,500 | 7,000 | 00107 | 4011905315263 |
| 0516 | Trixie Cookie Bones | 1.3 kg | 4,900 | 5,500 | 00108 | 4011905316628 |
| 0517 | Trixie Cookie Farmies | 1.3 kg | 4,900 | 5,500 | 00109 | 4011905316635 |
| 0552 | Trixie Cookie Giants with Lamb | 1.25 kg | 4,250 | 5,700 | 00110 | 4011905316642 |
| 0459 | Trixie Cookie Snack Loops | 1.3 kg | 5,980 | 6,600 | 00111 | 4011905316710 |
| 1478 | Pro Plan Sterilised Adult Renal Plus | 10 kg | 39,500 | 3,950 | 00106 | 7613033566547 |

## Still open (unchanged)
- Good **1442** "cat food STERILISED chicken 10 kg": unidentified (brand + EAN needed).
- **1473 Delivery** has no price.
- The odd-coded old box goods 1365–1407 (box EAN, 8,650) have no live Siruk variant: keep or retire.

## After the import
- Re-export, then `/armsoft-sync <export> verify`.
- Siruk still has the old RC codes (1342–1364) as `accounting_code` on 46 variants, and no
  `accounting_code` on Felix / Pro Plan. `scripts/backfill-variant-codes.py --overwrite` fixes
  them once ArmSoft is updated. It writes to Siruk, so it runs only after your go-ahead.
