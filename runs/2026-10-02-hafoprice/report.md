# Price fallback import — 2026-10-02 (production)

User: "go over every single item in runs/2026-10-02-fallback/not-imported.csv — if the problem is
that you don't know the price to sell it use hafo's pricing … if the pricing isn't there use hafo
pricing or zoovet.am or nemo.am". The 38 rows there: 26 were blocked on price, 12 on something else
(identity conflicts 3, two possible articles 1, wrong-colour photo 1, Royal Canin skipped by you 5,
RC with no cost 1, and the Club 4 Paws pouch is identity *and* price).

## Imported — 15 rows, priced from hafo (the register price was = cost or a typo)

| Register | Code | Product | Variant | Register price | Price used (hafo) |
|---|---|---|---|---|---|
| 00425 | 11072S | 1313 Delights Bones Strong (+variant; renamed from "… XS", XS variant got size XS) | S, Chicken, 55 g | 3950 (typo) | 1900 |
| 00719 | 01672K | 1339 Kaskad Classic Double Leather Collar (new) | 12 mm, 20–24 cm | 2500 (typo) | 1250 |
| 00402 | 12625 | 1329 Beaphar Vit Bits (new) | 35 g | 2600 (typo) | 1250 |
| 00476 | DL711856 | 1337 Rabbit Ears with Lamb for Mini Breeds (new) | Lamb 55 g | 1000 = cost | 1550 |
| 00477 / 00478 | DL711876 / DL711866 | 1338 Calcium Bones for Mini Breeds (new, 2 flavours) | Duck / Chicken 55 g | 1000 = cost | 1550 |
| 00486 | DL711526 | 1294 Bones for Mini Breeds (+variant) | Duck 55 g | 1000 = cost | 1550 |
| 00487 / 00492 | DL711806 / DL711506 | 1333 Breasts for Mini Breeds (new, 2 flavours) | Duck / Chicken 55 g | 1000 = cost | 1550 |
| 00490 | DL711496 | 1332 Meat Sticks for Mini Breeds (new) | Chicken 55 g | 1000 = cost | 1550 |
| 00491 | DL711546 | 1335 Beef Slices for Mini Breeds (new) | Beef 55 g | 1000 = cost | 1550 |
| 00495 | DL711676 | 1336 Rabbit Slices for Mini Breeds (new) | Rabbit 55 g | 1000 = cost | 1550 |
| 00427 | 208986 | 1330 Tender Goose Slices for Mini Breeds (new) | Goose 55 g | 1000 = cost | 1550 |
| 00488 | 711536 | 1331 Duck Wedges for Mini Breeds (new) | Duck 55 g | 1000 = cost | 1550 |
| 00489 | DL711516 | 1334 Lamb Medallions for Mini Breeds (new) | Lamb 55 g | 1000 = cost | 1550 |

Sources: Derevenskie Lakomstva — derlak.ru (article = 7 + last 7 EAN digits; DL711856 found by EAN
search, art. 76051080); 8in1 — 8in1.eu; Beaphar Vit Bits — pages printing EAN 8711231126255
(biostyle.biz, pets24); Kaskad — kaskad-pet.ru (one photo only). Stock 10, en/ru/hy shipped.
**PM**: these 15 register prices are wrong in the register (cost typed as price, or a typo) — worth fixing there.

## Still not importable on price — zoovet.am / nemo.am searched, no same item

35718Tx rope toy 38 cm, 22858Tx bag dispenser, 2410Tx flea comb 15 cm (hafo's hit was a Tetra filter
at 104,500 — wrong row, guard added), 41590Tx reflective cat collar (zoovet's lookalike 950 < cost),
45765Tx plush bird, 45665Tx bear, 45689Tx monster, 6004 salt lick 60 g, 00025301 Kaskad collar 25 mm,
142535 Club 4 Paws jelly 85 g, Mnyams cushions 00462 / 00463 (00463: zoovet sells "chicken & cheese"
60 g at 800 — if the pack is that, 800 applies). Detail: `price-search.csv`; all stay in
`runs/2026-10-02-fallback/not-imported.csv` (now 23 rows) and `state/open-items.csv`.

## Workflow change

CLAUDE.md rule 2c, `reference/pricing.md` → "The register", `/add-products`: a register price that is
blank, ≤ cost or a typo no longer parks a row — hafo variant price → confirmed zoovet/nemo → sibling,
held only when none beats cost. `scripts/prepare-run.py` implements it, notes each override, and
refuses a hafo price from another brand or ≥ 2.5× cost & ≥ 2× register (or ≥ 5× cost).
