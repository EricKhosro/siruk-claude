# How each kind of good is set up in ArmSoft

The hard rules are in `.claude/skills/armsoft-sync/SKILL.md` → "Hard rules";
the clicks in `.claude/skills/armsoft-app/SKILL.md`. This is the "which shape,
and why" for each kind, with the goods that follow it.

| Kind | ArmSoft shape | Example goods | Why / since |
|---|---|---|---|
| Dry-food bag sold whole and per kg | main **303 kg** + Քաշային, alt **003 Պարկ** = bag kg, bag EAN on 003, 5-digit PLU on 303, both prices | 0001, 0009–0019, 1443–1465, 1478 | scale reads the PLU; stock counts kg |
| Treat tub/bag sold whole and per 100 g | main **303 kg** + Քաշային, alt **001 Հատ** = pack kg (user: use հատ, not պարկ), pack EAN on 001, PLU on 303; 303 price = 10 × the Siruk 100 g price | 0403 0459 0516 0517 0552 | 2026-10-23, after the ArmSoft update |
| Pack sold whole only (was: also one by one) | main = the pack (**004 Փաթեթ**), pack EAN on 004; **no single-stick unit** | Mnyams Treat Sticks 1599, 1536 (1,750) | user 2026-10-26: individual sticks are not sold — Siruk singles 2193/2194 deleted, ArmSoft alt unit 001 Հատ (0.1 pack, 200) to remove |
| Pack sold one piece at a time (pads) | main **001 Հատ** = one piece, internal 5-digit code on 001 (from the PLU list), piece price; the pack EAN must not sell a piece — receiving-only pack unit or off | Trixie Nappy 0197 (00116, 004 ×8), 0132 (00117, 004 ×7), 0129 (00118, 004 ×7) — set 2026-10-27 | user 2026-10-27: the pads are sold one by one, never the pack; hafo's 410 / 160 / 230 are per pad though hafo labels them "8 / 7 pcs" |
| Pouches bought in boxes | one good per pouch, 001 Հատ, pouch EAN, pouch price; the till scans a pouch and types the count | RC 1366–1408 (even codes), Felix 1474–1495 (case unit 002 ×26 for receiving) | PM: Royal Canin is always sold one by one |
| Invoice-made box goods | keep (they have movements), no price, box EAN on 001; their stock is moved to the pouch goods | RC 1466–1472 | 2026-10-23 move: issue 0002 + receipt 0019 |
| Litter | sold by the bag only — never per kg; no PLU, Քաշային off | 1441 (main unit stays kg because its stock and receipts are in kg) | user 2026-10-23 |
| Old imported RC box goods | **deleted** 2026-10-23 by the user (15 goods, never received, no stock) — a good with no movement *can* be deleted | 1365 … 1407 (odd codes) | boxes are never sold |
| Retired duplicates | stay in the list, empty, no barcode | the 13 old codes of issue 0001, 1508, 1552 | can't be deleted |

## Picking a new scale PLU

- 2026-10-26: a new PLU is the lowest code missing from **both** `Scale/plu-codes-per-kg.csv` and `Scale/scale-codes-per-kg.csv` and from the latest ArmSoft export, after pulling the latest commits. Single-stick PLUs (00113/00114) are in the PLU file only, so checking one file once gave a duplicate. 00112 is retired (Kotoffey), not free. 00115 went to Monge Sterilised Cat Chicken 1 kg (good 1442, Siruk product 1432, variant 2225).
- 2026-10-26: good 1442 renamed "Կեր կատուների Monge STERILISED, հավ 10 կգ" (user: brand in the name so it can be found); EAN 8009470005135 on 003, PLU 00115 on 303, prices 35,500 / 3,650 — typed in the edit form by Claude, saved without a permission refusal this time.
- 2026-10-27: 00116 / 00117 / 00118 went to the single Trixie Nappy pads (goods 0197 / 0132 / 0129; Siruk variants 1318 / 1062 / 1061), in the PLU file only like the stick singles. Next free: 00119.
- 2026-10-27: 00119 / 00120 went to the new per-piece pads 1607 (Trixie charcoal 60×60, pack of 10 on 004) and 1612 (Petmil WC Premium 60×40, pack of 10 on 004). Next free: 00121.
