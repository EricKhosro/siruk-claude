# How each kind of good is set up in ArmSoft

The hard rules are in `.claude/skills/armsoft-sync/SKILL.md` → "Hard rules";
the clicks in `.claude/skills/armsoft-app/SKILL.md`. This is the "which shape,
and why" for each kind, with the goods that follow it.

| Kind | ArmSoft shape | Example goods | Why / since |
|---|---|---|---|
| Dry-food bag sold whole and per kg | main **303 kg** + Քաշային, alt **003 Պարկ** = bag kg, bag EAN on 003, 5-digit PLU on 303, both prices | 0001, 0009–0019, 1443–1465, 1478 | scale reads the PLU; stock counts kg |
| Treat tub/bag sold whole and per 100 g | main **303 kg** + Քաշային, alt **001 Հատ** = pack kg (user: use հատ, not պարկ), pack EAN on 001, PLU on 303; 303 price = 10 × the Siruk 100 g price | 0403 0459 0516 0517 0552 | 2026-10-23, after the ArmSoft update |
| Pack sold whole and one by one | main = the pack (**004 Փաթեթ**), alt **001 Հատ** = 1/N pack, pack EAN on 004, no EAN on the single | Treat Sticks 1599, 1536 (1,750 / 200) | keeps stock and past receipts (bought as packs) right |
| Pouches bought in boxes | one good per pouch, 001 Հատ, pouch EAN, pouch price; the till scans a pouch and types the count | RC 1366–1408 (even codes), Felix 1474–1495 (case unit 002 ×26 for receiving) | PM: Royal Canin is always sold one by one |
| Invoice-made box goods | keep (they have movements), no price, box EAN on 001; their stock is moved to the pouch goods | RC 1466–1472 | 2026-10-23 move: issue 0002 + receipt 0019 |
| Litter | sold by the bag only — never per kg; no PLU, Քաշային off | 1441 (main unit stays kg because its stock and receipts are in kg) | user 2026-10-23 |
| Old imported RC box goods | **deleted** 2026-10-23 by the user (15 goods, never received, no stock) — a good with no movement *can* be deleted | 1365 … 1407 (odd codes) | boxes are never sold |
| Retired duplicates | stay in the list, empty, no barcode | the 13 old codes of issue 0001, 1508, 1552 | can't be deleted |
