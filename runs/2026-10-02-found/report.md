# found.csv import — 2026-10-02 (production)

Input: `runs/2026-10-01-register/found.csv` (85 register rows identified on 2026-10-01). Price = the PM's register (rule 2c) for every row; stock 10; en/ru/hy shipped in the create call. No hafo photo was used anywhere.

| Outcome | Rows |
|---|---|
| New products created | 54 products / 76 variants (67 rows + their 1 kg twins) |
| Added as variants to live products | 7 rows → 1200 Delights Bones (3), 1190 Delights Sticks, 795, 1149, 1148 |
| Already live (not re-imported) | 3 — 198060 (956), 42804 (562), 35910 (266) |
| Held, not written | 11 — see below |

## Held (need you)

| Code | Item | Why |
|---|---|---|
| 11072S | Ոսկոր` S չափի, հավի համով, 55 գ | SUSPECT register 3950: 3.2x cost, 2.1x hafo 1900 |
| DL711856 | Հյուրասիրություն փոքր ցեղատեսակի շների համար՝ ճագարի ականջներ,55գ | register price 1000 <= cost 1000 (rule 5; hafo has 1550) |
| DL711876 | Հյուրասիրություն փոքր ցեղատեսակի շների համար՝ կալցիում ոսկորներ՝ բադի,55գ | register price 1000 <= cost 1000 (rule 5; hafo has 1550) |
| DL711866 | Հյուրասիրություն փոքր ցեաղտեսակի շների համար՝ կալցիում ոսկորներ՝ հավի, 55գ | register price 1000 <= cost 1000 (rule 5; hafo has 1550) |
| DL711526 | Հյուրասիրություն փոքր ցեղատեսակի շների համար՝ բադ,55գ | register price 1000 <= cost 1000 (rule 5; hafo has 1550) |
| DL711806 | Հյուրասիրություն փոքր ցեղատեսակի շների համար՝ բադի կրծքամիս,55գ | register price 1000 <= cost 1000 (rule 5; hafo has 1550) |
| DL711496 | Հյուրասիրություն փոքր ցեղատեսակի շների համար՝ հավի ձողիկներ 55գ | register price 1000 <= cost 1000 (rule 5; hafo has 1550) |
| DL711546 | Հյուրասիրություն փոքր ցեղատեսակի շների համար՝ հորթ,55գ | register price 1000 <= cost 1000 (rule 5; hafo has 1550) |
| DL711506 | Հյուրասիրություն փոքր ցեղատեսկի շների համար՝ հավի կրծքամիս 55գ | register price 1000 <= cost 1000 (rule 5; hafo has 1550) |
| DL711676 | Հյուրասիրություն փոքր ցեղատեսակի շների համար՝ ճագար 55գ | register price 1000 <= cost 1000 (rule 5; hafo has 1550) |
| 01672K | Վզնոց՝ երկշերտ կաշի, 12մմ*20-24սմ/00012101 | SUSPECT register 2500: 3.2x cost, 2.0x hafo 1250 |

Ten Dog Fest/Derevenskie Lakomstva 55 g treats have register price 1000 = cost (hafo sells them at 1550). Two register prices look like typos (3.2× cost). Give the right sale price and they go in.

## Created

| Product | Variant | sku | Price | Cost | Images | Link |
|---|---|---|---|---|---|---|
| Soft Flea Collar for Cats | Glitter, grey | 20632 | 2700 | 1675 | 9 | https://siruk.am/product/beaphar-soft-flea-collar-for-cats/dp/1966/ |
| Soft Flea Collar for Cats | Sparkle, assorted colours | 20629 | 2700 | 1675 | 9 | https://siruk.am/product/beaphar-soft-flea-collar-for-cats/dp/1967/ |
| Soft Flea Collar for Cats | Reflective, yellow | 20630 | 2700 | 1675 | 9 | https://siruk.am/product/beaphar-soft-flea-collar-for-cats/dp/1968/ |
| Calcium Dental Bones for Large Breeds | 105 g | 304016 | 2350 | 1420 | 3 | https://siruk.am/product/derevenskie-lakomstva-calcium-dental-bones-for-large-breeds/dp/1969/ |
| Premium Large Breeds Puppies Dry Dog Food | Chicken 14 kg | 909685 | 22500 | 18000 | 6 | https://siruk.am/product/club-4-paws-premium-large-breeds-puppies-dry-dog-food/dp/1970/ |
| Premium Large Breeds Puppies Dry Dog Food | 1 kg | 909685-KG | 1700 | 1286 | 6 | https://siruk.am/product/club-4-paws-premium-large-breeds-puppies-dry-dog-food/dp/1971/ |
| Sensitiv Tear Stain Remover | 50 ml | BP10264 | 4200 | 2610 | 1 | https://siruk.am/product/beaphar-sensitiv-tear-stain-remover/dp/1972/ |
| Flea & Tick Collar for Large Dogs | 85 cm, black | BP12155 | 2800 | 1735 | 2 | https://siruk.am/product/beaphar-flea-tick-collar-for-large-dogs/dp/1973/ |
| Kitty's + Taurine + Biotin | 75 tablets | BP12509 | 2050 | 1255 | 1 | https://siruk.am/product/beaphar-kitty-s-taurine-biotin/dp/1974/ |
| Kitty's + Cheese | 75 tablets | BP12511 | 2150 | 1320 | 1 | https://siruk.am/product/beaphar-kitty-s-cheese/dp/1975/ |
| Flea & Tick Collar for Dogs | 65 cm, black | BP12512 | 2350 | 1450 | 1 | https://siruk.am/product/beaphar-flea-tick-collar-for-dogs/dp/1976/ |
| Flea & Tick Collar for Dogs | 65 cm, green | BP10196 | 2350 | 1450 | 2 | https://siruk.am/product/beaphar-flea-tick-collar-for-dogs/dp/1977/ |
| Flea & Tick Collar for Dogs | 65 cm, orange | BP10199 | 2350 | 1450 | 1 | https://siruk.am/product/beaphar-flea-tick-collar-for-dogs/dp/1978/ |
| Macadamia Spray | 150 ml | BP12558 | 4700 | 2900 | 1 | https://siruk.am/product/beaphar-macadamia-spray/dp/1979/ |
| Flea & Tick Collar for Puppies | 65 cm, black | BP13207 | 2350 | 1450 | 2 | https://siruk.am/product/beaphar-flea-tick-collar-for-puppies/dp/1980/ |
| Chlorophyll Dental Bones for Small Breeds | Mint, 60 g | DL303976 | 1400 | 870 | 3 | https://siruk.am/product/derevenskie-lakomstva-chlorophyll-dental-bones-for-small-breeds/dp/1981/ |
| Medium Starter | Chicken 15 kg | MG006197 | 49500 | 38000 | 2 | https://siruk.am/product/monge-medium-starter/dp/1982/ |
| Medium Starter | 1 kg | MG006197-KG | 3400 | 2533 | 2 | https://siruk.am/product/monge-medium-starter/dp/1983/ |
| Adult Dry Dog Food | Veal & Rice 10 kg | PG901425 | 9100 | 7000 | 1 | https://siruk.am/product/gav-adult-dry-dog-food/dp/1984/ |
| Adult Dry Dog Food | 1 kg | PG901425-KG | 1000 | 700 | 1 | https://siruk.am/product/gav-adult-dry-dog-food/dp/1985/ |
| Adult Dry Dog Food | Meat Assortment 10 kg | PG900025 | 9100 | 7000 | 1 | https://siruk.am/product/gav-adult-dry-dog-food/dp/1986/ |
| Adult Dry Dog Food | 1 kg | PG900025-KG | 1000 | 700 | 1 | https://siruk.am/product/gav-adult-dry-dog-food/dp/1987/ |
| Classic Leather Puppy Collar | 15 mm, 24–30 cm | 01082K | 1250 | 780 | 1 | https://siruk.am/product/kaskad-classic-leather-puppy-collar/dp/1988/ |
| Classic Leather Collar | 12 mm, 20–24 cm, brown | 01662K | 850 | 530 | 1 | https://siruk.am/product/kaskad-classic-leather-collar/dp/1989/ |
| Funny Mouse Vinyl Toy | 11 cm | 02004K | 1700 | 1030 | 1 | https://siruk.am/product/kaskad-funny-mouse-vinyl-toy/dp/1990/ |
| Padded Leather Collar with Bells | 10 mm, 28 cm, pink | 04812K | 2100 | 1300 | 1 | https://siruk.am/product/kaskad-padded-leather-collar-with-bells/dp/1991/ |
| Meatballs with Rice | Turkey 85 g | 050026 | 2700 | 1675 | 3 | https://siruk.am/product/derevenskie-lakomstva-meatballs-with-rice/dp/1992/ |
| Excel Calcium | 155 tablets | 10940 | 3400 | 2125 | 7 | https://siruk.am/product/8in1-excel-calcium/dp/1993/ |
| Triple Flavour Twisted Sticks | 10 pcs / 70 g | 14460S | 2600 | 1610 | 4 | https://siruk.am/product/8in1-triple-flavour-twisted-sticks/dp/1994/ |
| Flavours Skewer Bites | 100 g | 15253S | 1950 | 1190 | 2 | https://siruk.am/product/8in1-flavours-skewer-bites/dp/1995/ |
| Calcium Bones for Medium & Large Breeds | Rabbit 90 g | 214946 | 2350 | 1450 | 3 | https://siruk.am/product/derevenskie-lakomstva-calcium-bones-for-medium-large-breeds/dp/1996/ |
| Prong Collar | 3.5 mm, 55 cm | 26455351 | 5150 | 3215 | 1 | https://siruk.am/product/kaskad-prong-collar/dp/1997/ |
| Premium Adult Dry Cat Food | Chicken 14 kg | CP909145 | 28000 | 23000 | 7 | https://siruk.am/product/club-4-paws-premium-adult-dry-cat-food/dp/1998/ |
| Premium Adult Dry Cat Food | 1 kg | CP909145-KG | 2100 | 1643 | 7 | https://siruk.am/product/club-4-paws-premium-adult-dry-cat-food/dp/1999/ |
| Premium Adult Dry Cat Food | Veal 14 kg | CP909205 | 28000 | 23000 | 7 | https://siruk.am/product/club-4-paws-premium-adult-dry-cat-food/dp/2000/ |
| Premium Adult Dry Cat Food | 1 kg | CP909205-KG | 2100 | 1643 | 7 | https://siruk.am/product/club-4-paws-premium-adult-dry-cat-food/dp/2001/ |
| Premium Adult Dry Cat Food | Rabbit 14 kg | 909155 | 28000 | 23000 | 7 | https://siruk.am/product/club-4-paws-premium-adult-dry-cat-food/dp/2002/ |
| Premium Adult Dry Cat Food | 1 kg | 909155-KG | 2100 | 1643 | 7 | https://siruk.am/product/club-4-paws-premium-adult-dry-cat-food/dp/2003/ |
| Premium Adult Dry Cat Food | Salmon 14 kg | REG00030 | 33150 | 25500 | 7 | https://siruk.am/product/club-4-paws-premium-adult-dry-cat-food/dp/2004/ |
| Premium Adult Dry Cat Food | 1 kg | REG00030-KG | 2500 | 1821 | 7 | https://siruk.am/product/club-4-paws-premium-adult-dry-cat-food/dp/2005/ |
| Sausages with Rice | Turkey 85 g | DL050046 | 2700 | 1675 | 3 | https://siruk.am/product/derevenskie-lakomstva-sausages-with-rice/dp/2006/ |
| Medallions with Rice for Mini Breeds | Turkey 55 g | DL050056 | 1950 | 1195 | 3 | https://siruk.am/product/derevenskie-lakomstva-medallions-with-rice-for-mini-breeds/dp/2007/ |
| Bones for Mini Breeds | Turkey 55 g | DL050066 | 1950 | 1195 | 3 | https://siruk.am/product/derevenskie-lakomstva-bones-for-mini-breeds/dp/2008/ |
| Chlorophyll Dental Bones for Medium Breeds | Mint, 70 g | DL303986 | 1400 | 870 | 3 | https://siruk.am/product/derevenskie-lakomstva-chlorophyll-dental-bones-for-medium-breeds/dp/2009/ |
| Calcium Dental Bones for Small Breeds | 60 g | DL303996 | 1550 | 965 | 3 | https://siruk.am/product/derevenskie-lakomstva-calcium-dental-bones-for-small-breeds/dp/2010/ |
| Calcium Dental Bones for Medium Breeds | 90 g | DL304006 | 1900 | 1160 | 3 | https://siruk.am/product/derevenskie-lakomstva-calcium-dental-bones-for-medium-breeds/dp/2011/ |
| Avocado Dental Chews for Small Breeds | 35 g | DL304036 | 950 | 580 | 3 | https://siruk.am/product/derevenskie-lakomstva-avocado-dental-chews-for-small-breeds/dp/2012/ |
| Dried Chicken Breasts | 90 g | DL711136 | 2350 | 1450 | 3 | https://siruk.am/product/derevenskie-lakomstva-dried-chicken-breasts/dp/2013/ |
| Dried Chicken Medallions | 90 g | DL711156 | 2350 | 1450 | 3 | https://siruk.am/product/derevenskie-lakomstva-dried-chicken-medallions/dp/2014/ |
| Chewy Bones | Chicken 90 g | DL711176 | 2350 | 1450 | 3 | https://siruk.am/product/derevenskie-lakomstva-chewy-bones/dp/2015/ |
| Twisted Chicken Sticks | 90 g | DL711196 | 2350 | 1450 | 3 | https://siruk.am/product/derevenskie-lakomstva-twisted-chicken-sticks/dp/2016/ |
| Tender Chicken Slices | 90 g | DL711206 | 2350 | 1450 | 3 | https://siruk.am/product/derevenskie-lakomstva-tender-chicken-slices/dp/2017/ |
| Dried Slices | Duck 90 g | DL711216 | 2350 | 1450 | 3 | https://siruk.am/product/derevenskie-lakomstva-dried-slices/dp/2018/ |
| Tender Strips | Duck 90 g | DL711226 | 2350 | 1450 | 3 | https://siruk.am/product/derevenskie-lakomstva-tender-strips/dp/2019/ |
| Wrapped Chew Sticks for Puppies | Chicken 90 g | DL711266 | 2350 | 1450 | 3 | https://siruk.am/product/derevenskie-lakomstva-wrapped-chew-sticks-for-puppies/dp/2020/ |
| Dried Rings for Puppies | Chicken 90 g | DL711276 | 2350 | 1450 | 3 | https://siruk.am/product/derevenskie-lakomstva-dried-rings-for-puppies/dp/2021/ |
| Breast Cartilage for Mini Breeds | Chicken 30 g | DL711406 | 1550 | 965 | 3 | https://siruk.am/product/derevenskie-lakomstva-breast-cartilage-for-mini-breeds/dp/2022/ |
| Calcium Bones for Puppies | Duck 90 g | DL711786 | 2350 | 1450 | 3 | https://siruk.am/product/derevenskie-lakomstva-calcium-bones-for-puppies/dp/2023/ |
| Excel Brewer's Yeast | 260 tablets | IN10860 | 4000 | 2480 | 2 | https://siruk.am/product/8in1-excel-brewer-s-yeast/dp/2024/ |
| Excel Multi Vitamin Senior | 70 tablets | IN10869 | 4650 | 2900 | 1 | https://siruk.am/product/8in1-excel-multi-vitamin-senior/dp/2025/ |
| Excel Brewer's Yeast Large Breed | 80 tablets | IN10952 | 4350 | 2705 | 1 | https://siruk.am/product/8in1-excel-brewer-s-yeast-large-breed/dp/2026/ |
| Delights Bones Strong XS | Chicken, 7 pcs / 140 g | IN11066 | 3400 | 2125 | 4 | https://siruk.am/product/8in1-delights-bones-strong-xs/dp/2027/ |
| Delights Twisted Sticks | Chicken, 10 pcs / 55 g | IN12247 | 2600 | 1610 | 4 | https://siruk.am/product/8in1-delights-twisted-sticks/dp/2028/ |
| Clumping Cat Litter | 2.7 kg (4.8 l) | KF5200111 | 1750 | 1090 | 5 | https://siruk.am/product/kotoffey-clumping-cat-litter/dp/2029/ |
| Hygienic Cat Litter | 2.7 kg (4.8 l) | KF5200211 | 1750 | 1090 | 5 | https://siruk.am/product/kotoffey-hygienic-cat-litter/dp/2030/ |
| Dark Wood Cat Litter | 2 kg (6 l) | KF5200311 | 1700 | 1060 | 5 | https://siruk.am/product/kotoffey-dark-wood-cat-litter/dp/2031/ |
| Light Wood Cat Litter | 2 kg (6 l) | KF5200411 | 1700 | 1060 | 2 | https://siruk.am/product/kotoffey-light-wood-cat-litter/dp/2032/ |
| Medium Adult | Chicken 15 kg | MG006147 | 39000 | 29500 | 1 | https://siruk.am/product/monge-medium-adult/dp/2033/ |
| Medium Adult | 1 kg | MG006147-KG | 2800 | 1967 | 1 | https://siruk.am/product/monge-medium-adult/dp/2034/ |
| Adult Dry Cat Food | Chicken 11 kg | PM902085 | 14500 | 12000 | 2 | https://siruk.am/product/myau-adult-dry-cat-food/dp/2035/ |
| Adult Dry Cat Food | 1 kg | PM902085-KG | 1400 | 1091 | 2 | https://siruk.am/product/myau-adult-dry-cat-food/dp/2036/ |
| Adult Dry Cat Food | Rabbit 11 kg | PM902075 | 14500 | 12000 | 1 | https://siruk.am/product/myau-adult-dry-cat-food/dp/2037/ |
| Adult Dry Cat Food | 1 kg | PM902075-KG | 1400 | 1091 | 1 | https://siruk.am/product/myau-adult-dry-cat-food/dp/2038/ |
| Adult Dry Cat Food | Meat, Rice & Vegetables 11 kg | PM902105 | 14500 | 12000 | 1 | https://siruk.am/product/myau-adult-dry-cat-food/dp/2039/ |
| Adult Dry Cat Food | 1 kg | PM902105-KG | 1400 | 1091 | 1 | https://siruk.am/product/myau-adult-dry-cat-food/dp/2040/ |
| Soft Ball | 4.5 cm | TX000751 | 500 | 310 | 5 | https://siruk.am/product/trixie-soft-ball/dp/2041/ |

## Added to live products

| Product | New variant | Change |
|---|---|---|
| 1200 Delights Bones (was "Delights Pork Bones") | S Chicken 35 g, L Chicken 85 g, L Beef 85 g | renamed (flavour in name = mis-split, rule 9); pork variant got its flavour + label |
| 1190 Delights Sticks (was "Delights Chicken Sticks") | Beef 3 pcs / 75 g | renamed; chicken variant labelled |
| 795 Hairball Malt Paste | Chicken 30 ml | old variant got flavour Malt, label "Malt 75 ml" |
| 1149 Classic Leather Collar with Braid | 30 mm, 49–58 cm | old variant got size 35 mm × 50–59 cm |
| 1148 Classic Leather Collar, padded | 12 mm, 20–24 cm, pink | old variant got size + colour "Color Varies" |

## New brands / vocabulary

- Brands: **Gav!** (45, Kormotech logo), **Kotoffey** (46, kotoffey.ru logo).
- `size` values 873–879 (Kaskad collar sizes, 85 cm, 55 cm/3.5 mm).

## To check

- 01664K joined 1148 (padded) — Kaskad's page lists it without the braid; hafo says pink, Kaskad says black/brown.
- 076912: hafo says 30 g, the EAN page 30 ml — imported as 30 ml.
- KF5200411 photo is identified by name (nemo.am), not EAN.
- 1286 Excel Calcium / 1319 Medium Adult keep the Latin line name in ru/hy (verifier lists them as untranslated).
- Checks: verify-media 290 refs / 240 media / 0 broken; every multi-variant product's selector reaches every variant.
