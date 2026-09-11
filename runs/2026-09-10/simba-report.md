# Simba import — 2026-09-10

Source CSV: `csv/ALL_SIRUK_PRODUCTS.csv`, the 15 `Brand = Simba` rows (invoice
2026-09-06, Scan 3.pdf / Scan.pdf). Brand 19 Simba already existed.
Stock rule for this run (user, 2026-09-10): CSV `Qty Received` 1 → stock 10
(placeholder until stock is sorted with the provider); real quantities kept (12).

## Result

| Admin id | Name | Category | Variants | ru / hy |
|---|---|---|---|---|
| **324** | Chunks Adult (`simba-chunks-adult`) | 4 Dog › Wet Food | 9 | OK / OK |
| **325** | Chunkies Adult (`simba-chunkies-adult`) | 11 Cat › Wet Food | 4 | OK / OK |
| **326** | Paté Adult 150 g (`simba-pate-adult-150g`) | 4 Dog › Wet Food | 2 | OK / OK |

15 of 15 rows imported. 009267 (chicken & liver pâté 150 g) is not on hafo
and went to `no-hafo-price.csv` first; it was then imported through the new
**sibling-price fallback** (CLAUDE.md rule 2a, user rule 2026-09-10): same
product as 009257, same buy price 355 → same hafo sale price 480. Logged in
`sibling-priced.csv`. `no-hafo-price.csv` and `not-found.csv` are empty.

Checks after the run: `verify-media.sh 324 325 326` → 14 references, 10
media, 0 broken · `verify-translations.py` → 0 missing (products, categories,
brands) · `translate-attributes.py` → 17 attributes, 636 values read back in
en/ru/hy, 0 mismatches · `check-hafo-prices.py --only 324,325,326` → 14 match.

## Per row

Identity: article code → hafo (`confirmed: true`, `price_source: variant`,
wholesale == CSV cost on all 14). Source: monge.it Spanish product page + its
official English spec-sheet PDF. Sale price = hafo row; cost = CSV.

| Code | Invoice name | hafo price / cost | Product · variant (id) | Source page |
|---|---|---|---|---|
| 009017 | Պահածո շների Simba մսային 415գ | 600 / 440 | 324 · Beef 415 g (416, default) | /es/producto/simba-bocaditos-con-ternera/ + `Simba-dog-chunks-with-beef-ENG.pdf` |
| 009127 | … մսային 1,230գ | 1650 / 1180 | 324 · Beef 1230 g (417) | same |
| 009027 | … հավ և հնդկահավ 415գ | 600 / 440 | 324 · Chicken & Turkey 415 g (418) | …simba-bocaditos-con-pollo-y-pavo/ + `…chicken-and-turkey-ENG.pdf` |
| 009137 | … հավ և հնդկահավ 1,230գ | 1650 / 1180 | 324 · Chicken & Turkey 1230 g (419) | same |
| 009167 | … գառ 415գ | 600 / 440 | 324 · Lamb 415 g (420) | …simba-bocaditos-con-cordero/ + `…lamb-ENG.pdf` |
| 009147 | … գառ 1,230գ | 1650 / 1180 | 324 · Lamb 1230 g (421) | same |
| 009177 | … թռչնամիս 415գ | 600 / 440 | 324 · **Wild Game** 415 g (422) | …simba-bocaditos-con-carne-de-caza/ + `…wild-game-ENG.pdf` — EAN 8009470009171 = "Bocconi con Selvaggina" (web search of the hafo barcode); hafo's "poultry" is a mistranslation |
| 009157 | … թռչնամիս 1,230գ | 1650 / 1180 | 324 · **Wild Game** 1230 g (423) | same, EAN 8009470009157 |
| 009187 | … տավար և բանջարեղեն 1,230գ | 1650 / 1180 | 324 · Beef & Vegetables 1230 g (424) | …simba-bocaditos-con-ternera-y-verduras/ + `…beef-and-vegetables-ENG.pdf` |
| 009077 | Պահածո կատուների Simba հավի 415գ | 600 / 440 | 325 · Chicken 415 g (425, default) | …simba-bocaditos-con-pollo/ + `Simba-cat-chunkies-with-chicken-EN.pdf` |
| 009097 | … ձուկ 415գ | 600 / 440 | 325 · **Tuna** 415 g (426) | …simba-bocaditos-con-atun/ + `…tuna-EN-1.pdf` — EAN 8009470009096 = Chunkies with Tuna (hafo says "fish") |
| 009517 | … բադ 415գ | 600 / 440 | 325 · Guinea Fowl & Duck 415 g (427) | …simba-bocaditos-con-gallina-faraona-y-pato/ + `…guinea-fowl-and-duck-EN-1.pdf` (hafo says "duck"; the product is the guinea fowl & duck recipe, the only Simba cat duck can) |
| 009547 | … գառ 415գ | 600 / 440 | 325 · Lamb 415 g (428) | …simba-bocaditos-con-cordero-2/ + `…lamb-EN-1.pdf` |
| 009257 | SIMBA պաշտետ շների` տավարի համով, 150 գ | 480 / 355 | 326 · Beef & Peas 150 g (429, default) | …simba-pate-con-ternera-y-guisantes/ + `Simba-dog-pate-with-beef-and-peas-ENG.pdf` (hafo title "տավարի մսով և սիսեռով" = beef & peas) |
| 009267 | SIMBA պաշտետ շների` հավի համով, 150 գ | **480 via sibling 009257** / 355 (not on hafo) | 326 · Chicken & Liver 150 g (430) | …simba-pate-con-pollo-y-higado/ + `Simba-dog-pate-with-chicken-and-liver-ENG.pdf`; media 2769 |

## Attributes (family 2 Wet Food), evidence from the spec sheets

Set on every variant:
- `lifestage` Adult — "complete pet food for adult dogs of all sizes" / "for adult cat"
- `texture` Chunks in Gravy — "Chunks in gravy formulated with…"; pâté: Pate — "Paté formulated with…"
- `packaging` Can — "Do not open the can, if it is dented or swollen"; pâté: Tray — "Do not open the alutray"
- `special-diet` No Artificial Colorants — "No added colours or preservatives"
- `flavor` — the recipe name on the sheet (Beef, Chicken & Turkey, Lamb, Wild Game, Beef & Vegetables, Chicken, Tuna, Guinea Fowl & Duck, Beef & Peas); chicken & liver pâté tagged **Chicken** ("chicken 12%, liver 6%") — no "Chicken & Liver" value in the menu (wanted below)
- `product-weight` — "Pack size: 415g - 1230g" / "150g - 300g", per CSV row
- `ingredient` — first named ingredient of the composition: Beef ("beef 6%", "beef 8%", "beef 7,5%"), Chicken ("chicken 10%", "chicken 12%"), Lamb ("lamb 5%", "lamb 6%")

Left empty:
- `ingredient` on Wild Game ("wild game 6%"), Tuna ("tuna 6%"), Guinea Fowl & Duck ("guinea fowl 5%") — no matching value in the ingredient menu (wanted below)
- `health-feature` — flagged candidate, not set: "specific combination of vitamins A-D3-E" → Vitamins & Minerals? It is body text, not a front-of-pack claim (below the confidence gate).

Rich text per variant (en, ru, hy): about (sheet description + pack bullets:
oven cooked / steam cooked, no added colours or preservatives, no cruelty
test, made in Italy, pack size), ingredients (composition, analytical
constituents, additives), feeding (instructions + the daily-intake table).

## Vocabulary created this run (user approved 2026-09-10, ru/hy applied)

| Attribute | Value | id |
|---|---|---|
| product-weight | 415 g | 678 |
| product-weight | 1230 g | 679 |
| flavor | Chicken & Turkey | 680 |
| flavor | Wild Game | 681 |
| flavor | Beef & Vegetables | 682 |
| flavor | Guinea Fowl & Duck | 683 |
| flavor | Beef & Peas | 684 |

## Flagged candidates (human yes/no)

- `health-feature` = Vitamins & Minerals on all 14 variants — evidence
  "developed with a specific combination of vitamins A-D3-E".

## Wanted but missing

- `flavor` value **Chicken & Liver** (1 variant, 009267) — the other Simba
  combos got exact values today; this one arrived after that approval and is
  tagged Chicken meanwhile. Add and retag?
- `ingredient` values **Tuna** (1 variant, "tuna 6%"), **Guinea Fowl** (1,
  "guinea fowl 5%"), **Wild Game / Game** (2, "wild game 6%") — add?

## Images

One official packshot per flavour (monge.it, 427×625, the only image the
site publishes per product); shared by the 415 g and 1230 g variants of the
same recipe. All looked at: product alone on white, animal printed on the
label. Media 2739–2766. No `needs-packshot.csv` entries.

## Product 326 after the fallback

Renamed "Paté Adult Beef & Peas 150 g" → **"Paté Adult 150 g"**
(`simba-pate-adult-150g`): flavour now varies, so it left the Name for the
labels; 150 g stays because the pack is still single. ru "Паштет Adult 150 г",
hy "Պաշտետ Adult 150 գ". `check-hafo-prices.py --only 326` → 009257 match,
009267 **sibling match** (new status; `SIBLING MISMATCH` when the sibling's
hafo price moves).

## Notes for next time

- monge.it lists Simba only in `/es/`; the English spec-sheet PDFs on those
  pages are the source (`reference/brand-sites.md` § Simba).
- hafo's Armenian flavour word is a translation and can be wrong (poultry =
  wild game, fish = tuna); the EAN in `barcodes[]` is the reliable join
  (`reference/hafo.md`).
- `scripts/check-hafo-prices.py` now accepts hafo maker "Monge" for the
  Simba and Gemon brands (`MAKER_ALIASES`); before the patch it reported the
  13 Monge-maker rows as "not on hafo under simba".
- `scripts/build-simba.py` regenerates the payloads and translation files.
