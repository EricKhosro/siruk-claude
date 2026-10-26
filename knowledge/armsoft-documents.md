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

## Documents (newest first)

| Doc | Date | What it is | Status |
|---|---|---|---|
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

Supplier codes seen: 0001 = Pet House («ՓԵԹ ՀԱՈՒՍ», ՀՎՀՀ 00169022; hafo.am's
wholesale prices match its invoices — likely the same company, not confirmed), 0005 = Zoo Ek («ԶՈՈ ԷԿՈ»), 000002 = Prestige Food.
