# Import run 2026-09-25 — the 11 "stuck" register rows

These 11 rows had a known code, a hafo confirmation and a register price, but
were not imported on 2026-09-23 because the brand site had no page for our pack.
This run is the first to use the new **barcode lookup** step
(`reference/image-sources.md` → "Barcode lookup").

**Result:** 8 created, 3 held. Every price is the register price (rule 2c),
above cost and within a few % of hafo's.

| Reg. row | Code | Product (admin id) | Label | Price / cost | Source of name, texts, photos |
|---|---|---|---|---|---|
| 00191 | IN10863 | Excel Multi Vitamin Puppy (**1195**) | 100 tablets | 4,300 / 2,675 | barcode: listex.info + aqplus.ru (both print EAN 4048422108634) |
| 00192 | IN10937 | Excel Multi Vitamin Small Breed (**1196**) | 70 tablets | 4,650 / 2,900 | barcode: listex.info + zooman.ru (EAN 4048422109372) |
| 00193 | IN12429 | Excel Glucosamine + MSM (**1197**) | 55 tablets | 8,200 / 5,125 | barcode: aqplus.ru + evinemama.com (EAN 4048422124290); watermarked copy dropped |
| 00115 | 074322 | SexControl Spot-On for Female Cats (**1198**) | 3 ml | 2,700 / 1,675 | brand site neoterica.ru; barcode pages confirm the Rolf Club listing → brand kept Rolf Club (22) |
| 01000 | 11244S | PRO Fillets Digest (**1199**) | 80 g | 1,950 / 1,190 | barcode: kelpi.pl + dobra-miska.cz |
| 01113 | 12207S | Delights Pork Bones (**1200**) | XS, 7 pcs / 84 g | 2,900 / 1,800 | identity by barcode (4 shop listings); text from hafo + the pack photo; **hafo placeholder photo only → needs-image.csv** |
| 00483 | DL711836 | Rabbit Ears for Puppies (**1201**) | Chicken, 90 g | 2,350 / 1,450 | brand site dogfest.com prints our EAN; settles the 2026-09-23 "different product" doubt |
| 01275 | 042718 | New Comfort Cord Lead (**1202**) | XS, 3 m, light blue | 6,450 / 4,155 | flexi.de image + archived flexi.de page; filed dog lead 69 + cat supplies 79 (for dogs, cats and small animals ≤ 8 kg) |

All 8: family set, English + ru + hy (`verify-translations.py --only …`: 0
missing), 18 images, 0 broken (`verify-media.sh`), storefront pages open with
the product title. Each first image was looked at.

## Held (3) — in `state/open-items.csv`

| Code | Why | Needed |
|---|---|---|
| 12625 Beaphar Vit Bits 35 g | register 2,600 = 3.2× cost 805 and 2.1× hafo 1,250 — the rule 2c typo guard | PM: confirm the sale price |
| 10778S 8in1 Delights Chicken Balls | hafo + register say **S** 2 pcs/40 g; the pages carrying our EAN 4048422107781 say **M** | PM: read the size off the pack |
| 703823 Mnyams Cream Treat tuna & scallop | identity fine (2 EAN pages + mnyams.ru), belongs on product 1137 — but the flavour menu has no *Scallop*, and *Tuna* / *Seafood & Fish* are taken by siblings, so the variant would be unreachable (rule 9a) | **Add flavour value "Scallop"?** |

## Things found on the way

- **Backend change:** `POST /products` now requires `variants.*.sale_mode`;
  `pricing_type` / `price_per_kg` read back null, `product-weight` is derived
  from the new `unit` + `net_quantity`, and the per-kg twins became 1 kg packs.
  Documented in `reference/admin-api.md`. `set-translation.py` was fixed to copy
  the new fields. **Open:** how per-kg (loose) selling is expressed now — ask the
  backend team before the next dry-food import. `register-audit.py` reports
  every twin as `TWIN-RATE-WRONG` because it still reads `price_per_kg` —
  false alarm until it is updated.
- **Planner bug:** `prepare-run.py` read "XS-8 kg" (a max dog weight) as a pack
  weight; cleared by hand for 042718 (rule 8a).
- **Planner gap:** `existing_candidates` missed the live Mnyams Cream Treat
  (1137) and the Rolf Club SexControl family (748–752); caught by hand.
- **UPCitemdb is loose:** it called 12207S "cowhide"; the pack says porkhide.
  Database hits are leads, never facts on their own.

## Files

`runs/2026-09-25/import/`: `rows.jsonl`, `cards/`, `barcode-sourced.csv`,
`needs-image.csv`, `holds.csv`, `card-import.py` (card → admin, through
`scripts/`). Spreadsheet for the PM:
`~/Downloads/AllAngineProduct-FINAL-2026-09-25.xlsx`: 1,224 in Siruk, 118 not.
