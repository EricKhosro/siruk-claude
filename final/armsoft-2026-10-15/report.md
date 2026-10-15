# ArmSoft import — 2026-10-15

Replaces `final/armsoft-2026-10-14/` (never imported): yesterday's goods plus the Trixie treats
now sold loose. **Import `goods.xml` first, then `prices.xlsx`.**

## Files
- `goods.xml`: 27 goods.
  - 22 new goods **1474–1495** (Felix 75 g pouches + Pro Plan Renal Plus 10 kg, PLU 00106), the same as yesterday's `new-goods.xml`.
  - 5 existing Trixie goods turned into weight goods: unit 303 (kg) default, alt unit 003 (bag, coef = bag kg), barcode on 003 = the bag EAN, barcode on 303 = the new scale PLU.
- `prices.xlsx`: 33 rows. Yesterday's 23, plus 2 per Trixie good: the bag price on 003 and the per-kg price on 303.

## The 5 Trixie goods — to type in by hand if the XML is refused
ArmSoft may refuse to change the main unit of a good that already has movements (these were
unit 001 "piece"). If so, add the units by hand:

| Good | Product | Bag | Unit 003 (bag) price | Unit 303 (kg) price | Scale PLU | Bag EAN (on 003) |
|---|---|---|---|---|---|---|
| 0403 | Trixie Soft Snack Bony Mix XXL | 1.8 kg | 11,500 | 7,000 | 00107 | 4011905315263 |
| 0516 | Trixie Cookie Bones | 1.3 kg | 4,900 | 4,100 | 00108 | 4011905316628 |
| 0517 | Trixie Cookie Farmies | 1.3 kg | 4,900 | 4,100 | 00109 | 4011905316635 |
| 0552 | Trixie Cookie Giants with Lamb | 1.25 kg | 4,250 | 3,700 | 00110 | 4011905316642 |
| 0459 | Trixie Cookie Snack Loops | 1.3 kg | 5,980 | 5,100 | 00111 | 4011905316710 |

On the scale, the price is per kg. On Siruk the same goods are sold as **100 g** (700 / 410 / 410 /
370 / 510), and the 100 g variant's barcode is the PLU. Price = our bag rate +10% (user, 2026-10-15).

## Kept in step
`csv/all-xml-scale.xml` = `Scale/all-xml-scale.xml`, `state/scale-codes.json`,
`Scale/scale-codes-per-kg.csv`, `Scale/plu-codes-per-kg.csv`, `final/Siruk-hx-303-prices-dog.xlsx`,
`final/siruk-source-of-truth.csv/.xlsx` (5 new "100 g" rows; also on the "loose (PLU only)" sheet).

## After the import
The Felix / Pro Plan variants still need `accounting_code` 1474–1495 and the PLU on the Pro Plan 1 kg:
`scripts/backfill-variant-codes.py --run runs/<date>`, then `--apply`. The 5 Trixie 100 g variants
already carry their codes.
