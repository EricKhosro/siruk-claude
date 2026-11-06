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
| Litter | sold by the bag only — never per kg; no PLU, Քաշային off | 1441 (main unit stays kg because its stock and receipts are in kg); a new litter good is a plain **001 Հատ** piece with the bag EAN, like 0236 0237 and **1624** (Kotoffey hygienic 8.1 kg, 2026-11-05) | user 2026-10-23 |
| Old imported RC box goods | **deleted** 2026-10-23 by the user (15 goods, never received, no stock) — a good with no movement *can* be deleted | 1365 … 1407 (odd codes) | boxes are never sold |
| Retired duplicates | stay in the list, empty, no barcode | the 13 old codes of issue 0001, 1508, 1552 | can't be deleted |

## Picking a new scale PLU

- 2026-10-26: a new PLU is the lowest code missing from **both** `Scale/plu-codes-per-kg.csv` and `Scale/scale-codes-per-kg.csv` and from the latest ArmSoft export, after pulling the latest commits. Single-stick PLUs (00113/00114) are in the PLU file only, so checking one file once gave a duplicate. 00112 is retired (Kotoffey), not free. 00115 went to Monge Sterilised Cat Chicken 1 kg (good 1442, Siruk product 1432, variant 2225).
- 2026-10-26: good 1442 renamed "Կեր կատուների Monge STERILISED, հավ 10 կգ" (user: brand in the name so it can be found); EAN 8009470005135 on 003, PLU 00115 on 303, prices 35,500 / 3,650 — typed in the edit form by Claude, saved without a permission refusal this time.
- 2026-10-27: 00116 / 00117 / 00118 went to the single Trixie Nappy pads (goods 0197 / 0132 / 0129; Siruk variants 1318 / 1062 / 1061), in the PLU file only like the stick singles. Next free: 00119.
- 2026-10-27: 00119 / 00120 went to the new per-piece pads 1607 (Trixie charcoal 60×60, pack of 10 on 004) and 1612 (Petmil WC Premium 60×40, pack of 10 on 004). Next free: 00121.
- 2026-11-02: 00121 went to Monge Speciality Line Adult Hypo Salmon & Tuna 1 kg (new good 1619, Siruk 1444 variant 2241; bag on 003 × 15 = EAN 8009470006439). Next free: 00122.
- 2026-11-03: Siruk variant 2102 (Kotoffey litter, ArmSoft 1441) changed from 14.4 L (volume) to 8,100 g (mass) so the ArmSoft stock sync, which reads 1441 in kg, divides by the bag weight. The label still shows "8.1 kg (14.4 l)". Its sister bag 2029 (0236, counted in pieces in ArmSoft) went to 2,700 g the same day so both sizes read in kg (user). Both labels keep the litres: "2.7 kg (4.8 l)", "8.1 kg (14.4 l)".
- 2026-11-05 (user: "I don't like how half is litre, half is kg — make all kg"): every Kotoffey litter is now **mass**, size from the weight printed on the bag: Hygienic 2030 → 2,700 g, 2246 → 8,100 g; Dark Wood 2031 and Light Wood 2032 → 2,000 g. The labels keep the litres ("2 kg (6 l)"); the shop cards now read "…, 2.7 kg / 8.1 kg / 2 kg" with a per-kg price. The Litter product type's default is still volume, so a new litter variant must be sent as mass by hand. Other brands' litters (Ok-Lock, Eco-Premium, Trixie, Versele-Laga) are still litres.
- 2026-11-03 (user): **a bag that sold even 100 g loose is no longer a sealed bag.** ArmSoft counts a bag good in kg, so its stock = sealed bags (whole multiples of the 003 coefficient) + one open bag (the rest); a good with 0 sealed bags is re-ordered. `scripts/sealed-stock-report.py <turnover.xlsx> <goods.xml>` builds the sheet (order list, bags & packs, piece goods). It assumes one open bag per good at a time. Pouches and pads come in cases but sell one by one, so they count as pieces. First run: `final/sealed-stock-2026-11-03.xlsx`: 22 goods with only an open bag, 45 sold out.
- 2026-11-06 (user): **Glovo availability follows the same split.** A bag is orderable on Glovo only with a sealed bag left; its 1 kg (100 g) variant stays on while the open + sealed stock holds 1 kg (100 g); anything else needs 1 in stock. `scripts/glovo-portal.py stock <turnover.xlsx> <goods.xml>` applies it (dry run, then `--apply` on the user's yes). First run: 73 of 1,590 switched off (20 bags with only an open bag, 3 kg listings at 0, 48 piece goods at 0, 2 never received), `final/glovo/glovo-availability-2026-11-06.xlsx`. A product someone switched off by hand while ArmSoft shows stock is not switched back on: ask (that day both were stock errors → issue 0006).
- 2026-11-06 (user): **Siruk stock stays the placeholder 10, except when neither we nor the supplier have it** — then the variant goes to stock 0 (out of stock, not orderable; reason correction, note says why). Supplier check = hafo's live stock (`scripts/hafo-watch.py crawl` → `.siruk-cache/hafo-watch/snapshot.json`, match by EAN, then article code with spaces removed: hafo writes "AC 5421112", "MG 006067"); **Royal Canin: the supplier has none of what we lack, no hafo check** (user). A bag with only an opened bag goes to 0, its 1 kg stays. First run: 24 variants (8 RC, 6 not sold on hafo, 10 hafo at 0), `final/siruk-out-of-stock-2026-11-06.xlsx`, log `runs/2026-11-06/siruk-out-of-stock.csv`. All 24 had policy `deny` and no supplier link (a `dropship` one would show "Ships from supplier" at 0). Bring one back: receive stock on the variant.

## ADG codes (learned 2026-11-05)

- The HDM needs a classifier code on every receipt line (`adgCode`). Without one it refuses the line: error 192 "required", or 183 "wrong code". ArmSoft keeps the code on each good as **CPACode**, and its till sends `CPACode` as `adgCode` (decompiled `SamplePOSSaleWindow.xaml.cs`).
- Two lists:
  - Goods use the 4-digit customs code, ԱՏԳ ԱԱ (CNFEA). Food and treats are 2309, leads and collars 4201, plastic trays 3924, beds 6307, scratchers 4823, pads 4818, toys/plastics 3926.
  - Services use the dotted activity code, ԱԴԳՏ (CPA). ArmSoft's service **1473 "Delivery" = 49.42**.
- The 2026-10-27 ArmSoft export had a CPACode on all 1,559 records. Our new-good import files (`final/armsoft-*/new-good*.xml`) carry one too. Ops copies the code from ArmSoft's goods on import, so a good added to ArmSoft after the last Ops import has no ADG code in Ops until it is filled in.
- 2026-11-05: in the Ops dev database, Delivery was set to 49.42 and the 23 goods with no code were filled in:
  - 1605–1619 from our import files;
  - 1620–1623 with 2309, the code of every similar treat (only ArmSoft holds their real value);
  - 387807-OLD and 387817-OLD with 2309; 40211 with 3924.
