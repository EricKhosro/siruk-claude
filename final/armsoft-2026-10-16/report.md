# ArmSoft sync — 2026-10-16

Sources: ArmSoft `Export_All_FINAL_NEW.xml` (1,493 goods, codes 0001–1495; copied to
`Scale/armsoft-export-2026-10-16.xml`) and `Export_All_FINAL_NEW_PRICES.xlsx` (1,545 code+unit
prices) vs the live Siruk catalogue re-read today (968 products, 1,551 variants).

## Result
- Every live Siruk variant reaches an ArmSoft good. No Siruk product is missing from ArmSoft,
  so there is **no new-goods file**. Felix / Pro Plan were the products still pending, and they
  are now in ArmSoft as hand-made goods 1474–1495.
- Every price ArmSoft already has **matches Siruk**. The only price rows needed are for goods
  that have **no price** yet.
- No barcode in ArmSoft disagrees with Siruk. No bad check digits. No barcode sits on two goods,
  apart from the Royal Canin pairs below.

## Files, in import order

| # | File | What |
|---|---|---|
| 1 | `rc-1-free-barcodes.xml` | **Only if ArmSoft won't let you delete them.** The 25 old Royal Canin goods we imported (1342–1364 except 1355, plus 1369/1377/1383) with their barcodes/PLUs removed. Better: delete these 25 by hand, as you did with 1387/1403. |
| 2 | `goods-update.xml` | 52 existing goods, each built from ArmSoft's own block with only the barcode / unit parts changed: 22 RC bags (1443–1465 without 1456) get the bag EAN on 003 + the PLU on 303; 3 RC 12-boxes (1466–1468) get the box EAN; 21 Felix (1474–1495 without 1478) get the pouch EAN; Pro Plan 1478 + Trixie 0403/0459/0516/0517/0552 become weight goods. |
| 3 | `prices.xlsx` | 77 rows: code (text), price, unit, unit code, names, note. |
| — | `changes.xlsx` | Every finding, one sheet each: the goods to update, the RC pairs and their status, the Felix/Pro Plan code map, barcodes, units, prices, and the ArmSoft-only goods. |

ArmSoft may or may not update an existing code from an XML import. **Try `goods-update.xml` on
one good first.** If it won't, `changes.xlsx` → "goods to update" lists what to type in by hand.

## Royal Canin: only 6 of the 31 pairs are done
Done: 1456 (from 1355), 1469 (from 1387, deleted), 1470 (from 1401), 1471 (from 1399), 1472 (from 1403, deleted).
**Still to do: 25.** Our old codes still hold the barcodes and PLUs, and the hand-made codes have none:

| KEEP (hand-made) | old (ours) | PLU / box EAN |
|---|---|---|
| 1443–1455 | 1343, 1342, 1344–1354 | 00076, 00075, 00077–00087 |
| 1457–1465 | 1356–1364 | 00089–00097 |
| 1466 / 1467 / 1468 | 1369 / 1377 / 1383 | 12-box EAN |

The full pair list is in `changes.xlsx` → "Royal Canin pairs". Once the barcodes are moved, also
delete the stripped 1355, 1399 and 1401. Their prices still sit on the old codes, and
`prices.xlsx` puts the same prices on the KEEP codes.

## Felix / Pro Plan: ArmSoft made its own codes
Our 1474–1495 file was never imported. Someone created 1474–1495 by hand with the same 22
products in a different order (names "… 26x75g" + supplier SKU, no barcode, no price). We keep
**ArmSoft's codes**. They are matched by the SKU in the name, and Pro Plan's 12390976 is the
alternate code on the tax invoice for 12549935. The map is in `changes.xlsx` → "Felix-ProPlan codes".

## The 6 weight goods (if ArmSoft won't change the main unit, type these in)

| Good | Product | Bag | 003 bag price | 303 per kg | PLU | Bag EAN (003) |
|---|---|---|---|---|---|---|
| 0403 | Trixie Soft Snack Bony Mix XXL | 1.8 kg | 11,500 | 7,000 | 00107 | 4011905315263 |
| 0516 | Trixie Cookie Bones | 1.3 kg | 4,900 | 5,500 | 00108 | 4011905316628 |
| 0517 | Trixie Cookie Farmies | 1.3 kg | 4,900 | 5,500 | 00109 | 4011905316635 |
| 0552 | Trixie Cookie Giants with Lamb | 1.25 kg | 4,250 | 5,700 | 00110 | 4011905316642 |
| 0459 | Trixie Cookie Snack Loops | 1.3 kg | 5,980 | 6,600 | 00111 | 4011905316710 |
| 1478 | Pro Plan Sterilised Adult Renal Plus | 10 kg | 39,500 | 3,950 | 00106 | 7613033566547 |

The Trixie scale prices are per kg = 10 × Siruk's 100 g price.

## Decisions
- **Felix "26x75g" goods:** 200 per pouch on unit 001 is right (user, 2026-10-16).
- **RC 12-box goods 1466–1472:** unit 001 = one box of 12, with the barcode the user put on it
  (user, 2026-10-16). Still open: their **price** (none has one; the old box goods sell at 8,650),
  and unit 002 has coef 12, which ArmSoft reads as 12 boxes.
- **Good 1442** "cat food STERILISED chicken 10 kg" (hand-made, no barcode, no price): still unidentified.
- **1473 "Delivery"** has no price.

## After the import
- Re-export, then run `/armsoft-sync <export> verify`.
- Siruk: `scripts/backfill-variant-codes.py --run runs/2026-10-16 --overwrite` (planned today, no
  writes): 69 `accounting_code` (RC → 1443–1465, Felix/Pro Plan → ArmSoft's codes) + 1 barcode
  (Pro Plan 1 kg PLU 00106). Run `--apply` only after the import and your go-ahead.

## Kept in step
`csv/all-xml-scale.xml` = `Scale/all-xml-scale.xml` is now today's export minus the 28 old RC
codes, with the 52 updates applied (1,465 goods). `Scale/scale-codes-per-kg.csv` is re-keyed:
73 rows to the KEEP / ArmSoft codes, plus 16 variants from 2026-10-13 that were missing.
`state/scale-codes.json` (PLUs) is re-keyed the same way, and `state/open-items.csv` is updated.
