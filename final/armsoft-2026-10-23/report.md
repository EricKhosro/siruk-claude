# ArmSoft sync — 2026-10-23 (done in ArmSoft directly)

Sources, exported by Claude from ArmSoft itself: goods XML (1,574 goods, codes 0001–1604,
`Scale/armsoft-export-2026-10-23.xml`) and the price list (1,670 rows,
`Scale/armsoft-prices-2026-10-23.xlsx`). Check: `scripts/armsoft-gaps.py`.

## Done in ArmSoft
- **81 barcodes added** (unit 001) to the invoice-made goods 1496–1600, from the 2026-10-21
  list (Siruk variant EANs, check digit OK, on no other good). Verified in a fresh export
  (`Scale/armsoft-export-2026-10-23-after.xml`): 81/81 exact, nothing else changed, no
  barcode on two goods. ArmSoft also filled each good's main barcode.
- Missing good + unit rows: 142 → 61.

## Left for you — `todo.xlsx`
1. **Move 18 barcodes** (sheet 1): the EAN still sits on the old duplicate code (1030, 1051,
   0436–0441, 0901, 1312, 1229, 0464–0466, 0468, 0469, 1224, 0803). Delete it there, add it on
   the new code (1510 …). Deleting was blocked by the permission check, so I didn't do it.
2. **Read off the pack** (sheet 2): 1519, 1524, 1533, 1599, 1442. 1508 / 1552 are second
   copies of 1507 / 1551.
3. **Decide** (sheet 4): RC box goods 1466–1472 hold stock and the box EAN but are never sold
   as boxes. 1441 has a kg unit with no PLU and no price. 1478 has no kg unit, but Siruk sells
   1 kg (PLU 00106).

## Not needed (sheet 3), per your rules today
- Case units Felix 002 (×26) and RC 002 (×12): pouches are sold one by one.
- 1478: units 001 and 003 are the same (×1). Its unit 002 ×26 was copied by mistake and should be removed.

## Not done
- Nothing written to Siruk. Prices: every single-unit good already had one.

## Afternoon: your answers applied (verified in `Scale/armsoft-export-2026-10-23-after2.xml`)
- **18 barcodes moved**: removed from the old duplicate goods (edit form → Barcodes tab) and added on
  1510 1511 1527–1532 1547 1555 1574 1576–1580 1583 1587. All 18 exact, no barcode on two goods.
- **RC boxes 1466–1472 renamed** as 12-pack boxes (e.g. "Կատվի կեր RC Kitten Gravy 12×85գ տուփ" /
  "Royal Canin Kitten Wet — In Gravy, 12 × 85 g box"). Unit stays հատ (001) = one box. On 1466–1469
  unit 002 is now ×1 instead of ×12. Box EAN still on 001. No price.
- **1441 litter**: kg unit (303) got scale PLU **00112** (new, recorded in `state/scale-codes.json`
  and `Scale/plu-codes-per-kg.csv`). Its **price was refused** by the permission check: type
  **600 AMD/kg** yourself (bag 4,500 ÷ 8.1 kg = 556, +10% like the Trixie loose treats).
- **1478 Pro Plan**: unit 303 (kg, 0.1 of the 10 kg bag) added. It is **not the main unit yet**, and
  there's no PLU or price on it.

## 1478 Pro Plan: now a weight good (your go-ahead)
Main unit **303 kg** (weight good, main barcode = PLU **00106**). Bag 003 = 10 kg with the bag EAN
07613033566547. Piece 001 = 10 kg. The stray 002 (×26, copied from Felix) is removed. Checked in an export.
**You still need to type the 303 price: 3,950 AMD/kg** (Siruk's 1 kg variant). Its bag prices (39,500) stay.
Note: stock booked earlier in pieces (bags) is now read in kg, so check the 1478 stock figure.
