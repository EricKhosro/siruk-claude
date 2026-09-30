# Import run 2026-09-28 — sirook.pdf (SIROOK supplier invoice, 29 lines)

Source: `~/Downloads/sirook.pdf` → transcribed to `runs/2026-09-28/sirook.csv`. Invoice prices are our **cost**; every line is Qty 1 → stock **10** (user rule). Sale price = hafo.am per article code (`price_source: variant`, hafo wholesale == invoice cost on every row).

## Summary

- **28 of 29 rows imported** as **26 new products** (ids 1203–1228, 28 variants). No row matched an existing product.
- **1 row held**: 6004Tx Trixie Lick made of Himalaya Salt 60 g — no sale price on hafo / zoovet / nemo, no sibling → `no-hafo-price.csv`.
- **New categories** (user-approved this run): Bird 95 → Food 96, Treats & Supplements 97; Small Animal 98 → Food 99, Hay 100, Treats 101, Supplements & Salt Licks 102, Bedding 103. ru/hy names set (`translate-categories.py`: problems none). No category tile images yet.
- Brands: none created (Versele-Laga 36, Trixie 8 already live).
- Translations: `verify-translations.py --only 1203…1228` → 0 missing (products, categories, brands).
- Media: `verify-media.sh 1203…1228` → 42 references, 40 distinct media, 0 broken.
- Variant axes: `backfill-variant-axes.py --ids 1215 1217` → nothing to set.
- `csv/AllAngineProduct-FINAL-2026-09-28.xlsx`: 29 rows appended as 01343–01371 above the totals (totals +29 qty, +49,220 AMD), with EAN, sale price, English name and demo link. Backup: `runs/2026-09-28/AllAngineProduct-FINAL-2026-09-28.before-append.xlsx`.
- Backend note: variants written with `sale_mode: pack`, fixed price, `unit` + `net_quantity` (2026-09-25 API). The server derived `product-weight` (it created 700 g and 108 g values on its own).

## Per product

| id | Product | Variant | SKU | EAN | hafo price | cost | category | source | attributes (evidence) |
|---|---|---|---|---|---|---|---|---|---|
| 1203 | Prestige Premium Canaries | 800 g | 421171V | 5410340211717 | 4050 | 2700 | 96 | https://www.versele.com/en/vl/prestige-premium/products/prestigepremium-canaries0825kg | health-feature: “Optimal intestinal functioning and digestion (Florastimul)” |
| 1204 | Prestige Budgies | 1 kg | 421620V | 5410340216200 | 2100 | 1400 | 96 | https://www.versele.com/en/vl/prestige/products/prestige-budgies1kg4kg | — |
| 1205 | Prestige Premium Budgies | 800 g | 421699V | 5410340216996 | 3450 | 2300 | 96 | https://www.versele.com/en/vl/prestige-premium/products/prestigepremium-budgies | health-feature: “help maintain vitality, strong immunity, and a healthy plumage” |
| 1206 | Prestige Premium Exotic Parrots Nuts | 750 g | 421782V | 5410340217825 | 5250 | 3500 | 96 | https://www.versele.com/en/vl/prestige-premium/products/prestigepremium-exoticparrotsnuts | special-diet: “No colourants” |
| 1207 | Prestige Parrots | 1 kg | 421795V | 5410340217955 | 3300 | 2200 | 96 | https://www.versele.com/en/vl/prestige/products/prestige-parrots1kg3kg | — |
| 1208 | Prestige Premium Loro Parque African Parrot Mix | 1 kg | 422201V | 5410340222010 | 4900 | 3265 | 96 | https://www.versele.com/en/vl/prestige-premium/products/prestigepremium-loroparqueafricanparrotmix1kg10kg15kg | health-feature: “help maintain vitality, strong immunity, and a healthy plumage” |
| 1209 | Prestige Premium Loro Parque African Parakeet Mix | 1 kg | 422220V | 5410340222201 | 4300 | 2865 | 96 | https://www.versele.com/en/vl/prestige-premium/products/prestigepremium-loroparqueafricanparakeetmix1kg | health-feature: “Enriched seed mixture: vitamins, amino acids & minerals = optimal condition” |
| 1210 | Nature Cuni Junior | 700 g | 461407V | 5410340614075 | 3200 | 2135 | 99 | https://www.versele.com/en/vl/nature/products/nature-cunijunior | special-diet: “Grain-free formula, for a good digestion”; health-feature: “Grain-free formula with high fiber content for healty teeth” |
| 1211 | Nature Cavia | 700 g | 461409V | 5410340614099 | 3000 | 2000 | 99 | https://www.versele.com/en/vl/nature/products/nature-cavia | special-diet: “Grain-free formula, for good digestion”; health-feature: “Grain-free formula with high fiber content for healty teeth” |
| 1212 | Nature Cuni | 700 g | 461448V | 5410340614488 | 2850 | 1900 | 99 | https://www.versele.com/en/vl/nature/products/nature-cuni | special-diet: “Grain-free formula, for good digestion”; health-feature: “Healthy teeth | Full of fibre for healthy teeth” |
| 1213 | Nature Original Cuni | 750 g | 461455V | 5410340614556 | 3000 | 2000 | 99 | https://www.versele.com/en/vl/nature/products/nature-originalcuni | health-feature: “The fibres, herbs, vegetables and fruits contained in the mixture account for excellent digestion” |
| 1214 | Nature Original Cavia | 750 g | 461457V | 5410340614570 | 3000 | 2000 | 99 | https://www.versele.com/en/vl/nature/products/nature-originalcavia | health-feature: “The fibres, herbs, vegetables and fruits contained in the mixture account for excellent digestion” |
| 1215 | Crispy Muesli Guinea Pigs | 400 g | 461698V | 5410340616987 | 1050 | 700 | 99 | fallback: hafo.am/products/ker-covaxozukneri-hamar-crispy (fallback: old pack) + zoovet photo | health-feature: “hafo: Կերը արդյունավետ է մարսողական համակարգի գործունեության ... համար (effective for digestive function)” |
| 1215 | Crispy Muesli Guinea Pigs | 1 kg | 461711V | 5410340617113 | 1900 | 1265 | 99 | fallback: hafo.am/products/ker-covaxozukneri-hamar-crispy (fallback: old pack) + zoovet photo | health-feature: “hafo: Կերը արդյունավետ է մարսողական համակարգի գործունեության ... համար” |
| 1216 | Crispy Muesli Hamsters & Co | 400 g | 461699V | 5410340616994 | 1150 | 765 | 99 | fallback: hafo.am/products/ker-hamsterneri-hamar-crispy (fallback: old pack) + zoovet photo | — |
| 1217 | Nature Snack | Berries 85 g | 461434V | 5410340614341 | 1950 | 1300 | 101 | https://www.versele.com/en/vl/nature/products/nature-snackberries ; …/nature-snackfruities | flavor: “A delicious natural mixture including grapes, rosehips, juniper berries, ash berries and cranberries” |
| 1217 | Nature Snack | Fruities 85 g | 461435V | 5410340614358 | 1950 | 1300 | 101 | https://www.versele.com/en/vl/nature/products/nature-snackberries ; …/nature-snackfruities | flavor: “A delicious natural mixture including pineapple, papaya, coconut, grapes and apricot” |
| 1218 | Nature Snack Cereals | 500 g | 461438V | 5410340614389 | 2550 | 1700 | 101 | https://www.versele.com/en/vl/nature/products/nature-snackcereals | — |
| 1219 | Nature Snack Fibres | 500 g | 461440V | 5410340614402 | 2550 | 1700 | 101 | https://www.versele.com/en/vl/nature/products/nature-snackfibres | special-diet: “a tasty snack mixture full of high-fibre herb and vegetable chunks” |
| 1220 | Natural Hay | 1 kg | 424131V | 5410340241318 | 2600 | 1735 | 100 | https://www.versele.com/en/vl/verselelaga/products/verselelaga-naturalhay | special-diet: “Rich in raw cellulose”; health-feature: “Rich in raw cellulose, promotes digestion” |
| 1221 | Nature Timothy Hay Beetroot & Tomato | 500 g | 424194V | 5410340241943 | 6000 | 3750 | 100 | https://www.versele.com/en/vl/nature/products/nature-timothyhaybeetroottomato | special-diet: “timothy hay with a high crude fibre content”; health-feature: “ensures good digestion and healthy teeth” |
| 1222 | Natural Wood Woodchips | 1 kg | 424128V | 5410340241288 | 1600 | 1000 | 103 | https://www.versele.com/en/vl/verselelaga/products/verselelaga-naturalwoodwoodchipspresspack | material: “Natural litter - woodchips” |
| 1223 | Calcium Stone with Sepia | 40 g | 50540 | 4011905505404 | 1100 | 685 | 97 | https://www.trixie.de/en/productworld/bird/supplementary-feed/supplementary-feed/calcium-stone-with-sepia-1001457722-1001457782?itemNo=50540 | product-form: “Calcium Stone … pressed, with holder”; active-ingredient: “calcium sulfate (74.5 %)” |
| 1224 | Iodine Pecking Stone | 90 g | 5105 | 4011905051055 | 800 | 500 | 97 | fallback: trixie.es/Iodine-Pecking-Stone (Ref. 5105) + koelle-zoo.de / e-zooo.com (90 g, EAN 4011905051055) | product-form: “Iodine pecking stone”; active-ingredient: “Iodine pecking stone (Jodpickstein)” |
| 1225 | Pecking Stone with Seashells | 30 g | 5108 | 4011905051086 | 600 | 375 | 97 | https://www.trixie.de/en/productworld/bird/supplementary-feed/supplementary-feed/pecking-stone-with-seashells-1001457722-1001457773?itemNo=5108 | product-form: “Pecking Stone”; health-feature: “eases moulting” |
| 1226 | Salt Lick | 2 × 54 g | 6000 | 4011905060002 | 750 | 465 | 102 | https://www.trixie.de/en/productworld/small-animal/small-animal-snacks/supplementary-feed/salt-lick-1001435943-1001456951?itemNo=6000 | product-form: “Salt Lick … with holder” |
| 1227 | Clay Stone with Carrot | 100 g | 60146 | 4011905601465 | 1600 | 1000 | 101 | https://www.trixie.de/en/productworld/small-animal/small-animal-snacks/small-animal-treats/clay-stone-with-carrot-1001435941-1001456838?itemNo=60146 | flavor: “Sort: carrot” |
| 1228 | Hay Bale with Beetroot and Parsnip | 200 g, ø 10 × 18 cm | 60795 | 4053032015487 | 3350 | 2090 | 101 | https://www.trixie.de/en/productworld/small-animal/small-animal-snacks/small-animal-treats/hay-bale-with-beetroot-and-parsnip-1001435941-1001456860?itemNo=60795 | special-diet: “grain-free” |

Rich text: every variant has *about*; *ingredients* and *feeding* where the source prints them. Left empty (not stated by source): Natural Hay ingredients+feeding, Salt Lick ingredients+feeding, feeding on Woodchips, Calcium Stone, Pecking Stone with Seashells, Clay Stone, Hay Bale.
Crispy (1215, 1216): our 400 g / 1 kg are the pre-2025 packs. versele.com only shows the relaunch (different EANs, new recipe), so texts come from hafo's page for our codes (fallback) and the lead photo from zoovet (identity confirmed: brand + line + species + 400 g, zoovet price = hafo price).

## Identity notes

- 461440V (invoice: “Nature, for rodents, vegetables 500 g”) = **Nature Snack Fibres** by EAN 5410340614402; 461438V = **Nature Snack Cereals**.
- 5105Tx: trixie.es lists Ref. 5105 as “Iodine pecking stone, 20 g”; hafo (TX 051051 = 90 g), the invoice, koelle-zoo.de and e-zooo.com (EAN 4011905051055 = Jodpickstein groß 90 g) agree on **90 g** → `barcode-sourced.csv`.
- 60795Tx: invoice says “parsley”; trixie.de (GTIN 4053032015487 = hafo EAN) is Hay Bale with **Beetroot and Parsnip** (parsley is a minor ingredient).
- 6000Tx: the article is a 2 × 54 g pack (trixie.de, hafo “Քանակ՝ 2 հատ”) → label “2 × 54 g”.

## Flagged / questions for you

- **6004Tx sale price?** Trixie Himalaya salt lick 60 g, cost 625 — send a price and it goes into category 102.
- **Wanted but missing vocabulary**: flavor “Berries” and “Fruit Mix” (Nature Snack variants use Cranberry / Pineapple as stand-ins, each a named headline ingredient); lifestage “Junior/Young” for small animals (Nature Cuni Junior “up to 8 months”, left empty). Add them?
- Nature Snack Cereals (hamsters/rats/mice) and Snack Fibres (rabbits/guinea pigs) were kept as separate products from Nature Snack Berries/Fruities: different target animals and 500 g vs 85 g. Say if you'd rather have one “Nature Snack” with four variants.
- Bird / Small Animal have no category tile images yet.

## Worklists

- `no-hafo-price.csv` — 6004Tx.  `not-found.csv` — empty.  `zoovet-priced.csv` / `sibling-priced.csv` — none (every imported row hafo-priced).
- `needs-image.csv` — the 3 Crispy variants (hafo placeholder last; the 1 kg leads with the 400 g pack shot).
- `barcode-sourced.csv` — 5105Tx (size), 6004Tx (identity).
- `needs-packshot.csv` — none written. Lead images are the brand's own packshots (Versele `<EAN>pack`, Trixie `PHO_PRO_CLIP`) or the zoovet pack shots; 6 were viewed by eye (Cuni Junior, 5105, 6000, 60146, both Crispy), the rest were not individually viewed.
- All open items folded into `state/open-items.csv`.
