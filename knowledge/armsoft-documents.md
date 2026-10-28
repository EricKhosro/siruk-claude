# ArmSoft documents — what each one is

Database "Siruk", warehouse 01. Receipts = Պահեստի մուտքի օրդեր (e-invoicing →
Գնման փաստաթղթեր); issue orders = Պահեստի ելքի օրդեր; tax invoices =
"Ստացված հարկային հաշիվներ".

## Reading the tax-invoice list

- It loads slowly and can look incomplete: use ribbon "Փոխել պարամետրերը",
  both periods from 01/01/25, and **Սերիա և համար** = the invoice number, then
  wait ~8 s. A6840667000 looked missing until filtered (2026-10-23).
- Open an invoice (double-click) → tabs Ընդհանուր (the **Մեկնաբանություն**
  field says "<number>հաշվի փոխարեն" when it replaces an earlier invoice),
  Մատակարար, Գնորդ, **Ապրանքացանկ** (the lines).
- Not every goods invoice is stock: equipment and supplies have no warehouse
  receipt, and that is right.

- **New invoices must be pulled** (PM, 2026-10-27): e-invoicing → "Ստացված
  հաշիվների ներմուծում" → source 1 e-invoicing (ուղիղ կապ). Run 2026-10-27 for
  01/10–27/10: 11 invoices, all already in; newest goods invoice A6840667000
  (21/10). The journal also holds non-stock invoices: B7599085058 (22/10,
  «ՏՈՊՐԱԿ ՄՈԼ», 255,000, no VAT) = shop carrier bags 28×24×14 and 37×32×20,
  supplies, no receipt; Ucom A4320961395 A5995523535 A3029868195 and
  Toz-Master A7715964500 = services.

## Documents (newest first)

| Doc | Date | What it is | Status |
|---|---|---|---|
| receipt **0022** | 27/10 | Pet House **A1412872447** (103,215 incl. VAT, 39 lines, 72 pcs): 29 existing goods at their last cost + 10 new goods 1605–1614 (imported the same day from `final/armsoft-2026-10-27/new-goods-1605-1614.xml`); 16 Nappy pads 0197 | posted by Claude |
| receipt **0021** | 27/10 | Pet House **A4477972797** (pulled with the e-invoice import, 57,865 incl. VAT): 0237 0238 litter ×1, 0040 Monge Kitten 10 kg (303 × 10 @ 2,700), 0049 Gemon Mini 20 kg (303 × 20 @ 1,000), 1499 Jimmy bed ×1. Bags booked in kg, not as 1 kg. All five already on Siruk, costs equal. User: under half of the order came; the nappy pads were not on it | posted by Claude (made from the XML, not from the e-invoice) |
| receipt **0020** | 27/10 | **settled 27/10: turned into a draft** after 0022 brought the real 16 pads (0197 stock 11 = 16 − 5 sold); delete is the user's. Was **temporary**: 0197 Nappy 60×90 × 8 pcs at 255 (2,040), no supplier — the delivery's e-invoice wasn't issued yet, a customer wanted it; fix when it arrives (state/open-items.csv) | posted by Claude, user asked |
| receipt **0019** | 23/10 | RC pouches: 12 × 625 on 1370 1378 1384 1388 1402 1400 1404 (52,500), the other half of issue 0002 | posted by Claude, user yes |
| issue **0002** | 23/10 | 1 box off each RC box good 1466–1472 (7 × 7,500) | posted by Claude |
| receipt **0018** | 23/10 | duplicates' stock onto the kept codes (10,264.11), other half of issue 0001 | posted |
| issue **0001** | 23/10 | 1 pc off each of the 13 old duplicate codes | posted |
| receipt **0017** | 23/10 | correction: 29 bag goods had been received as 1 kg; adds bag kg − 1 at price 0, per-kg cost on 1449 1451 1455 1456 (104,308.38) | posted |
| receipt **0016** | 22/10 | carriers 1601–1604 again, no supplier, at their **sale** prices (55,500), by narek.outstaffing | **duplicate** (user: carriers came once) — turned into a draft by Claude, **deleted by the user** 23/10; stock 1/1/0/1 |
| receipts 0013, 0014 | 22/10 | identical drafts of the bag fix | deleted by the user |
| receipt **0015** | 19/10 | Pet House A7873718283: carriers 1601–1604, 1 each (34,685) | ok |
| receipts 0011, 0012 | 20/10 | earlier bag fixes for 1461 and 1441 | ok |
| receipt **0009** | 18/10 | Pet House, cites **A3778015660** (204,338.28) | ok — invoice A6840667000 (21/10, 204,334.94) replaces A3778015660; 3.34 rounding |
| receipt **0007** | 01/10 | Zoo Ek A2516757106: RC boxes 1466–1472 at 7,500, bags 1443–1465 | ok (boxes moved by 0002/0019) |
| receipt **A6702909666** | 07/09 | Pet House: Trixie treats by the **kg** (0403 1.8 × 3,935 …) | ok — confirms per-kg cost |
| invoice **A7160667164** | 09/09 | ՅՈՒՆԻՏԵՔ: receipt printer TM-15A, scanner Sunlux XL-9620D, 18 till-paper rolls (156,710) | not stock — accountant books it as equipment |

- **Sale prices 1605–1614** set 2026-10-28 by Claude on the user's code/unit/price list (= Siruk prices): 2,400 · 3,200 · 350/pc · 13,900 · 16,000 · 6,200 · 4,350 · 220/pc · 4,650 · 4,650. Pack unit 004 of the pads 1607/1612 stays unpriced on purpose (user 2026-10-28: pads are sold one by one).

Receipts 0008 (A5393944409: 1496–1500) and 0010 (A9076732801: 1576 1577), both 18/10, checked 2026-10-27: every good is on Siruk.

Supplier codes seen: 0001 = Pet House («ՓԵԹ ՀԱՈՒՍ», ՀՎՀՀ 00169022; hafo.am's
wholesale prices match its invoices — likely the same company, not confirmed), 0005 = Zoo Ek («ԶՈՈ ԷԿՈ»), 000002 = Prestige Food.

## Invoice quantities vs ArmSoft receipts (checked 2026-10-26)

- Every goods line we hold (csv/products.csv + batches/) was compared with
  ArmSoft's supplier receipts and the 26/10 turnover, duplicates folded
  (`runs/2026-10-26/invoice-vs-armsoft-2026-10-26.xlsx`): 1,056 of 1,065
  matched goods agree. ArmSoft's received quantities are right wherever we can check.
- The invoices we have no scan of are all in e-invoicing → Ստացված
  հարկային հաշիվներ (29 invoices, 6,800,818.83). Checked 2026-10-26 on the
  e-invoice's Անվանացուցակ tab (footer = total quantity) against the
  receipts: A6833625890 81/81 lines (one bag each), A2516757106 30/30 (RC,
  one bag each), A2889221052 29, A7772326207 6, A9449097423 12,
  A0969245265 3, A6702909666 181.95 over 170 lines, A1938051747 600 (576
  invoice lines vs 574 receipt lines, same quantity). Every received
  quantity in ArmSoft matches its supplier e-invoice.
- Two goods where our scan transcription says 1 but the e-invoice says 2 (the e-invoice wins; our transcription was wrong):
  0592 (litter scoop L, 4046Tx) and 0773 (comb 22 cm, 23772Tx), both on A1938051747.
- **1456 RC Sterilised 15 kg — the 16 kg traced** (2026-10-26, operations
  journal): 01/10 receipt 0007 +1 (the bag, booked as 1 kg) · 15/10 till
  check 0000042 −1 kg loose (PLU 00088, 4,150) · 23/10 correction 0017 +14 ·
  25/10 till check 0000098 −1 **bag** (unit 003, 60,000 −10 % = 54,000), taken
  as −14 and −1 · 25/10 a **second receipt numbered 0017**, +1 kg at price 0,
  no supplier, no comment, author narek.outstaffing. Only one 15 kg bag ever
  came in. After the 1 kg loose sale the bag was sold whole with 14 kg left
  (likely the opened bag, hence −10 %), and the extra +1 kg covered the
  shortfall. Real: 15 kg in, 15 kg out, stock 0. ArmSoft's 16 kg sold
  overstates it by 1 kg. The user decided (2026-10-26) the +1 kg receipt
  stays as it is.
