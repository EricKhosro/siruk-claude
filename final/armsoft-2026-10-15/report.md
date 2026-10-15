# ArmSoft import — 2026-10-15

Replaces `final/armsoft-2026-10-14/` (never imported). Two separate imports:

| File | What | Import |
|---|---|---|
| `new-goods.xml` | 22 **new** goods 1474–1495 (Felix 75 g pouches, Pro Plan Renal Plus 10 kg with PLU 00106), the same file as yesterday | 1st |
| `new-goods-prices.xlsx` | their 23 prices (Pro Plan has 2: bag 003 and 1 kg 303) | 2nd |
| `update-loose-goods.xml` | 5 **existing** Trixie goods changed to weight goods: unit 303 (kg) default, alt unit 003 = bag (coef = bag kg), 003 barcode = bag EAN, 303 barcode = scale PLU | 3rd |
| `update-loose-prices.xlsx` | their 10 prices: bag on 003, per kg on 303 | 4th |

## The 5 loose goods — the same, to type in by hand
These were unit 001 (piece) with sales history, so ArmSoft may refuse to change the main unit through the XML.

| Good | Product | Bag | 003 bag price | 303 price per kg | PLU | Bag EAN (003) |
|---|---|---|---|---|---|---|
| 0403 | Trixie Soft Snack Bony Mix XXL | 1.8 kg | 11,500 | 7,000 | 00107 | 4011905315263 |
| 0516 | Trixie Cookie Bones | 1.3 kg | 4,900 | 5,500 | 00108 | 4011905316628 |
| 0517 | Trixie Cookie Farmies | 1.3 kg | 4,900 | 5,500 | 00109 | 4011905316635 |
| 0552 | Trixie Cookie Giants with Lamb | 1.25 kg | 4,250 | 5,700 | 00110 | 4011905316642 |
| 0459 | Trixie Cookie Snack Loops | 1.3 kg | 5,980 | 6,600 | 00111 | 4011905316710 |

Siruk sells them as **100 g**: 700 / 550 / 550 / 570 / 660 (user 2026-10-15; no rival sells them by 100 g). Bony Mix =
our bag rate +10%; the four cookies = zoovet.am's per-kg loose price +10%. The scale is per kg = 10 × that. Barcode on Siruk = the PLU.

## Kept in step
`csv/` = `Scale/all-xml-scale.xml`, `state/scale-codes.json`, `Scale/scale-codes-per-kg.csv`,
`Scale/plu-codes-per-kg.csv`, `final/Siruk-hx-303-prices-dog.xlsx`, `final/siruk-source-of-truth.csv/.xlsx`.

## After the import
Felix / Pro Plan variants still need `accounting_code` 1474–1495 and the Pro Plan 1 kg its PLU 00106:
`scripts/backfill-variant-codes.py --run runs/<date>`, then `--apply`. The Trixie 100 g variants already have theirs.
