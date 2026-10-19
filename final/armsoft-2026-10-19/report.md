# ArmSoft sync: 2026-10-19

Sources: ArmSoft `Export_1019_1117.xml` (1,570 goods, codes 0001–1600; copied to
`Scale/armsoft-export-2026-10-19.xml`) and `MTPrices_last.xlsx` (1,516 code + unit prices), compared with
the live Siruk catalogue after today's import (1,617 variants). Invoices for the new
goods: `batches/2026-10-19-armsoft-1496/` (4 invoices in one scan, 18–17 Oct, supplier SIROOK / hafo).

## What changed in ArmSoft since 16 Oct
- **105 new goods, 1496–1600**, created by ArmSoft when the invoices were posted: no barcode, no price.
- The old RC codes 1342–1403 are gone. 1470–1472 now hold their box barcodes, so the RC duplicate cleanup is done.
- Every price ArmSoft already had matches Siruk.

## The 105 new goods
| | goods | what happened |
|---|---|---|
| Imported to Siruk, hafo price | 64 | 49 products (1360–1406, 1407–1408), hafo sale price, invoice cost, EAN, ArmSoft code, photos, en/ru/hy |
| Imported to Siruk, price from the nearest product | 19 | no rival sells them (hafo / zoovet / nemo checked twice, see `final/price-recommendations-2026-10-19.xlsx` → Rival check); user: "set the selling price from the nearest product" → our cost × that product's price/cost, rounded to 50 (sheet Approved). Products 1409–1426 + rod 45804 as a second variant on 1382 |
| Already on Siruk under an older good | 18 | 1510 1511 1527–1532 1547 1555 1574 1576–1580 1583 1587 (= 1030, 1051, 0436–0441, 0901, 1312, 1229, 0464–0469, 1224, 0803). Priced; barcodes stay on the old goods |
| Second copy of a good | 2 | 1552 = 1551 (CIAO EU004 twice on the invoice), 1508 = 1507 (rod 45804). Priced like their twin |
| Imported after Cat › Beds was created | 2 | 1571 Junior Cat Bed (product 1427, 9,000 nearest product) and 1582 cat hammock (1428, hafo 13,700) in the new Cat › Supplies › Beds (107); Luna cave 1365 added there too |

The invoices: `batches/2026-10-19-armsoft-1496/` — 4 invoices (17–18 Oct, SIROOK / hafo), all four reconcile with their printed totals
(55,340 + 2,055 + 86,305 + 117,975 = 261,675, the handwritten total). The last page of the 17 Oct invoice came separately (IMG_4192).

## Files, in order
| # | File | What |
|---|---|---|
| 1 | `prices.xlsx` → **Prices** | 150 rows: Code (text), Price, **Selling type** (piece / bag / kg), unit code, names, Siruk link, note. Every one of the 105 new goods, the 22 RC bags (bag + kg), Pro Plan 1478 bag |
| 2 | `prices.xlsx` → **Barcodes** | 82 new goods: code, unit 001, EAN (check digit OK, on no other good) |
| — | `prices.xlsx` → **Not priced** | 37 good/units Siruk has no price for, and why (RC boxes, Felix/Pro Plan case units, 1441 per kg, 1442, Delivery) |

## Result
**All 105 new goods are on siruk.am**: 85 as their own products/variants, 20 as the same product as an older good (18 duplicates + 1552 / 1508).

## Decisions for you
1. **Duplicate goods (18 + 2)**: which code the till keeps for each (the new invoice-made ones can't be deleted).
2. **Single sticks**: Mnyams Treat Sticks now also sell one stick (200, zoovet) on Siruk; ArmSoft 1599 / 1536 are the 10-stick packs and need a piece unit.
3. **Other multipacks**: sell singles too? Trixie Premio Sticks 5 × 5 g (zoovet singles 200), Ferma Kota Fedora sticks 3 × 5 g and purée 4 × 15 g, Derevenskie "Doktorskie" 6 pcs / 60 g, Mnyams Cream Treat purée 4 × 15 g (zoovet 280 a sachet).
4. **Barcodes to read off the pack**: GoSi mouse 1533, crab 1524, owl 1519 (no page prints one).

## Still open from before
- Felix / Pro Plan unit 002 (case of 26): no price; Pro Plan 1478's 002 unit is a copy error.
- RC boxes 1466–1472: no price (box variants archived on Siruk).
- 1441 litter per kg, 1442 unidentified cat food, 1473 Delivery.
