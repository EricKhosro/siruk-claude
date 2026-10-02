# Production fixes — 2026-10-01

> **Update, end of day (PM decision): sold-by-weight is paused.** The 84 by-weight variants (71 products) described in §1 were deleted by the developers (the API can't delete a variant with stock history), and every one was replaced by a **"1 kg" pack variant** — sku `<bag>-KG`, price = the per-kg price, stock 10, the bag's photos and en/ru/hy texts, right after its bag. 61 are the old 1 kg variants put back in sale, 23 are new (Royal Canin). Verified on production: 84/84 present, pack, 1 kg, right price, stock 10, photos. Six have no description because their bag has none (1161–1165, 1178 — open item). The workflow now writes 1 kg pack variants and `siruk_payload.py` refuses `sale_mode: weight`. Section 1 below is kept as the history.

Production (`api.siruk.am`), written through `runs/2026-10-01-fix/*.py` (dry run first, every write read back). Final check (`verify.py`, a fresh read of all 876 products): **1 problem(s)** — ['name', 852, 'Travel Bottle with Bowl, 500 ml'].

## 1. Sold by weight

Every bag of a loose-sold product (the register's `Kg` column, `AllAngineProduct-FINAL-2026-09-28.xlsx`) now has its own by-weight twin: **61 twins on 48 products** — price = the Kg column per kg, 1 kg minimum and step, 10 kg stock, cost = bag cost ÷ bag kg, same texts (en/ru/hy), attributes and photos as the bag. The yesterday's import had **none** (only the old 1 kg *pack* twins). Royal Canin (`Price Royal Canin Nor _ SIRUK.xlsx`): all 23 dry products already had a correct by-weight variant — no change.

The 61 old 1 kg pack twins can't be deleted or converted (the backend locks any variant with stock history): sku renamed `<bag>-1KG`, label "1 kg", **stock 0** so they can't be bought. They still show as an out-of-stock "1 kg" option — **ask the developers to allow deleting a variant whose only history is its initial stock**.

Not done: All Breeds Puppy & Junior **800 g Lamb** (011257) — no Kg price in the sheet (never derived). Mini Adult 800 g Chicken shares its flavour with the 15 kg Chicken bag; the backend allows one weight variant per flavour, so the 15 kg twin serves it.

| Product | Bag | By-weight variant | Price / kg | Link |
|---|---|---|---|---|
| Mini Adult | MG006117 | Chicken, by weight | 2,900 | https://siruk.am/product/monge-mini-adult-chicken-rice-800-g/dp/1881/ |
| Mini Adult | MG006067 | Lamb & Rice, by weight | 3,400 | https://siruk.am/product/monge-mini-adult-chicken-rice-800-g/dp/1882/ |
| Mini Adult | MG006077 | Salmon & Rice, by weight | 3,400 | https://siruk.am/product/monge-mini-adult-chicken-rice-800-g/dp/1883/ |
| All Breeds Puppy & Junior | 011217 | Salmon & Rice, by weight | 3,800 | https://siruk.am/product/monge-all-breeds-puppy-junior-lamb-rice-800-g/dp/1884/ |
| All Breeds Puppy & Junior | 006487 | Beef & Rice, by weight | 2,950 | https://siruk.am/product/monge-all-breeds-puppy-junior-lamb-rice-800-g/dp/1885/ |
| Highest Protein Ranchlands | 5431112 | By weight | 5,700 | https://siruk.am/product/acana-highest-protein-ranchlands-11-4-kg/dp/1886/ |
| Classics Wild Coast | 5621212 | By weight | 4,350 | https://siruk.am/product/acana-classics-wild-coast-9-7-kg/dp/1880/ |
| Classics Prairie Poultry | 5601112 | By weight | 3,700 | https://siruk.am/product/acana-classics-prairie-poultry-9-7-kg/dp/1887/ |
| Classics Red Meat | 5611212 | By weight | 4,250 | https://siruk.am/product/acana-classics-red-meat-9-7-kg/dp/1888/ |
| Highest Protein Wild Prairie Dog | 5401112 | By weight | 6,600 | https://siruk.am/product/acana-highest-protein-wild-prairie-11-4-kg/dp/1889/ |
| Light & Fit | 5121112 | By weight | 4,500 | https://siruk.am/product/acana-light-and-fit-11-4-kg/dp/1890/ |
| Six Fish | 2815412 | By weight | 7,900 | https://siruk.am/product/orijen-six-fish-5-4-kg/dp/1891/ |
| Singles Yorkshire Pork | 5721212 | By weight | 4,600 | https://siruk.am/product/acana-singles-yorkshire-pork-11-4-kg/dp/1892/ |
| Sport & Agility | AC5301112 | By weight | 4,500 | https://siruk.am/product/acana-sport-and-agility-11-4-kg/dp/1893/ |
| Singles Grass-Fed Lamb | AC5701212 | By weight | 5,200 | https://siruk.am/product/acana-singles-grass-fed-lamb-11-4-kg/dp/1894/ |
| Puppy Small Breed | AC5026012 | By weight | 4,500 | https://siruk.am/product/acana-puppy-small-breed-6-kg/dp/1895/ |
| Puppy | AC5001112 | By weight | 4,000 | https://siruk.am/product/acana-puppy-11-4-kg/dp/1896/ |
| Adult Small Breed | AC5236012 | By weight | 4,500 | https://siruk.am/product/acana-adult-small-breed-6-kg/dp/1897/ |
| Highest Protein Grasslands Dog | AC5421112 | By weight | 5,400 | https://siruk.am/product/acana-highest-protein-grasslands-11-4-kg/dp/1898/ |
| Highest Protein Pacifica Dog | AC5411112 | By weight | 5,050 | https://siruk.am/product/acana-highest-protein-pacifica-11-4-kg/dp/1899/ |
| Singles Free-Run Duck | AC5711212 | By weight | 5,650 | https://siruk.am/product/acana-singles-free-run-duck-11-4-kg/dp/1900/ |
| All Breeds Adult | 011137 | Duck & Rice, by weight | 3,450 | https://siruk.am/product/monge-all-breeds-adult/dp/1901/ |
| All Breeds Adult | 011347 | Beef & Rice, by weight | 3,400 | https://siruk.am/product/monge-all-breeds-adult/dp/1902/ |
| All Breeds Adult | 011327 | Lamb & Rice, by weight | 3,550 | https://siruk.am/product/monge-all-breeds-adult/dp/1903/ |
| All Breeds Adult | 011307 | Salmon & Rice, by weight | 3,700 | https://siruk.am/product/monge-all-breeds-adult/dp/1904/ |
| All Breeds Adult | 011157 | Rabbit & Rice, by weight | 3,800 | https://siruk.am/product/monge-all-breeds-adult/dp/1905/ |
| All Breeds Adult | 011397 | Turkey & Rice, by weight | 3,600 | https://siruk.am/product/monge-all-breeds-adult/dp/1906/ |
| Mini Puppy & Junior | MG006107 | Chicken, by weight | 3,200 | https://siruk.am/product/monge-mini-puppy-junior/dp/1907/ |
| Mini Puppy & Junior | 005947 | Lamb & Rice, by weight | 3,550 | https://siruk.am/product/monge-mini-puppy-junior/dp/1908/ |
| Mini Puppy & Junior | 005937 | Salmon & Rice, by weight | 3,550 | https://siruk.am/product/monge-mini-puppy-junior/dp/1909/ |
| Mini Starter | MG006087 | Chicken, by weight | 3,800 | https://siruk.am/product/monge-mini-starter/dp/1910/ |
| Medium Puppy & Junior | MG006347 | Chicken, by weight | 2,950 | https://siruk.am/product/monge-medium-puppy-junior/dp/1911/ |
| Maxi Puppy & Junior | MG006027 | Chicken, by weight | 2,850 | https://siruk.am/product/monge-maxi-puppy-junior/dp/1912/ |
| Maxi Adult | 004417 | Chicken, by weight | 2,700 | https://siruk.am/product/monge-maxi-adult/dp/1913/ |
| BWild Low Grain All Breeds Adult | 011757 | Wild Boar, by weight | 3,600 | https://siruk.am/product/monge-bwild-low-grain-all-breeds-adult/dp/1914/ |
| BWild Low Grain All Breeds Adult | 011797 | Deer, by weight | 4,100 | https://siruk.am/product/monge-bwild-low-grain-all-breeds-adult/dp/1915/ |
| BWild Low Grain All Breeds Puppy & Junior | 011897 | Deer, by weight | 4,200 | https://siruk.am/product/monge-bwild-low-grain-all-breeds-puppy-junior/dp/1916/ |
| BWild Grain Free All Breeds Adult | 011737 | Lamb, Potatoes & Peas, by weight | 4,650 | https://siruk.am/product/monge-bwild-grain-free-all-breeds-adult/dp/1917/ |
| Hairball Cat | MG 004797 | Chicken, by weight | 3,700 | https://siruk.am/product/monge-hairball-cat/dp/1918/ |
| Indoor Cat | MG 004827 | Chicken, by weight | 3,700 | https://siruk.am/product/monge-indoor-cat/dp/1919/ |
| Kitten Cat | MG 004817 | Chicken, by weight | 3,600 | https://siruk.am/product/monge-kitten-cat/dp/1920/ |
| Sensitive Cat | MG 004837 | Chicken, by weight | 3,650 | https://siruk.am/product/monge-sensitive-cat/dp/1921/ |
| Adult Cat | MG 004807 | Chicken, by weight | 3,350 | https://siruk.am/product/monge-adult-cat/dp/1922/ |
| Kitten Cat | 297257 | Chicken & Rice, by weight | 2,550 | https://siruk.am/product/gemon-kitten-cat/dp/1923/ |
| Adult Cat | 297267 | Chicken & Turkey, by weight | 2,400 | https://siruk.am/product/gemon-adult-cat/dp/1924/ |
| Mini Adult Dog | MM005677 | Chicken & Rice, by weight | 1,500 | https://siruk.am/product/gemon-mini-adult-dog/dp/1925/ |
| Regular All Breeds Adult Dog | MM006177 | Chicken & Rice, by weight | 1,500 | https://siruk.am/product/gemon-regular-adult-dog/dp/1926/ |
| Adult Dog Kibbles | 009977 | Tuna, by weight | 1,150 | https://siruk.am/product/simba-adult-dog-kibbles/dp/1927/ |
| Adult Dog Kibbles | 009957 | Lamb, by weight | 1,150 | https://siruk.am/product/simba-adult-dog-kibbles/dp/1928/ |
| Premium Sterilised Dry Cat Food | 909665 | Chicken, by weight | 2,350 | https://siruk.am/product/club-4-paws-premium-sterilised-dry-cat-food/dp/1929/ |
| Premium Hairball Control Dry Cat Food | 909335 | Chicken, by weight | 2,350 | https://siruk.am/product/club-4-paws-premium-hairball-control-dry-cat-food/dp/1930/ |
| Premium Active Dry Dog Food | 909555 | Chicken, by weight | 1,700 | https://siruk.am/product/club-4-paws-premium-active-dry-dog-food/dp/1931/ |
| Premium Large Breeds Adult Dry Dog Food | 909645 | Chicken, by weight | 1,600 | https://siruk.am/product/club-4-paws-premium-large-breeds-adult-dry-dog-food/dp/1932/ |
| Premium Medium Breeds Adult Dry Dog Food | 909715 | Chicken, by weight | 1,600 | https://siruk.am/product/club-4-paws-premium-medium-breeds-adult-dry-dog-food/dp/1933/ |
| Premium Small Breeds Adult Dry Dog Food | 909545 | Chicken, by weight | 1,700 | https://siruk.am/product/club-4-paws-premium-small-breeds-adult-dry-dog-food/dp/1934/ |
| Premium Puppies Dry Dog Food | 909695 | Chicken, by weight | 1,700 | https://siruk.am/product/club-4-paws-premium-puppies-dry-dog-food/dp/1935/ |
| Kitten Dry Food | 902135 | By weight | 1,500 | https://siruk.am/product/myau-kitten-dry-food/dp/1936/ |
| Sterilised Cat | 297277 | Beef, by weight | 2,900 | https://siruk.am/product/gemon-sterilised-cat/dp/1937/ |
| Medium Adult Dog | MM005617 | Lamb & Rice, by weight | 1,750 | https://siruk.am/product/gemon-medium-adult-dog/dp/1938/ |
| Medium Adult Dog | GM005607 | Tuna & Rice, by weight | 1,750 | https://siruk.am/product/gemon-medium-adult-dog/dp/1939/ |
| Puppy & Junior Dog | MM005627 | Chicken & Rice, by weight | 1,800 | https://siruk.am/product/gemon-puppy-junior-dog/dp/1940/ |

## 2. Stock

**349 variants** set through `/stock/variants` (reason *correction*, note says why): every pack variant 10, every by-weight variant 10 kg, the retired 1 kg twins 0. 123 of them were at 1, 64 held real counts above 10 (lowered on your instruction), 7 toys were at 0. Plan with before/after: `stock-plan.json`.

## 3. Product names without the pack size

**126 products** renamed in en, ru and hy; slugs (URLs) unchanged. Stripping the size made three Acana pairs and the Trixie dental sets identical — they are **cat vs dog** products, not mis-split sizes, so the species went into the name instead ("… Cat" / "… Dog", "for Cats" / "for Dogs"). Accessory dimensions (cm, l/ø) and dose bands stay.

| id | Before (en) | After (en) | Link |
|---|---|---|---|
| 326 | Paté Adult 150 g | Paté Adult | https://siruk.am/product/simba-pate-adult-150g/dp/429/ |
| 331 | Denta Fun Chew Bites with Mint, 150 g | Denta Fun Chew Bites with Mint | https://siruk.am/product/trixie-denta-fun-chew-bites-with-mint-150-g/dp/435/ |
| 382 | Premio Stars with Chicken and Rice, 100 g | Premio Stars with Chicken and Rice | https://siruk.am/product/trixie-premio-stars-with-chicken-and-rice-100-g/dp/489/ |
| 398 | Sticks with Chicken and Fish, 300 g | Sticks with Chicken and Fish | https://siruk.am/product/trixie-sticks-with-chicken-and-fish-300-g/dp/505/ |
| 505 | Dental Hygiene Set | Dental Hygiene Set for Dogs | https://siruk.am/product/trixie-dental-hygiene-set/dp/612/ |
| 506 | Dental Hygiene Set, 50 g | Dental Hygiene Set for Cats | https://siruk.am/product/trixie-dental-hygiene-set-50-g/dp/613/ |
| 574 | Herbal Shampoo, 250 ml | Herbal Shampoo | https://siruk.am/product/trixie-herbal-shampoo-250-ml/dp/682/ |
| 579 | Colour Shampoo for White Dogs, 250 ml | Colour Shampoo for White Dogs | https://siruk.am/product/trixie-colour-shampoo-for-white-dogs-250-ml/dp/687/ |
| 580 | Colour Shampoo for Black Dogs, 250 ml | Colour Shampoo for Black Dogs | https://siruk.am/product/trixie-colour-shampoo-for-black-dogs-250-ml/dp/688/ |
| 590 | Dry Foam Shampoo, 450 ml | Dry Foam Shampoo | https://siruk.am/product/trixie-dry-foam-shampoo-450-ml/dp/698/ |
| 598 | Matatabi Spray, 175 ml | Matatabi Spray | https://siruk.am/product/trixie-matatabi-spray-175-ml/dp/706/ |
| 625 | Grill Puppy Chicken & Turkey 100 g | Grill Puppy Chicken & Turkey | https://siruk.am/product/monge-grill-puppy-chicken-turkey-100-g/dp/739/ |
| 627 | Grill Kitten Salmon 85 g | Grill Kitten Salmon | https://siruk.am/product/monge-grill-kitten-salmon-85-g/dp/745/ |
| 632 | VetSolution Urinary Struvite Cat 100 g | VetSolution Urinary Struvite Cat | https://siruk.am/product/monge-vetsolution-urinary-struvite-cat-100-g/dp/751/ |
| 634 | Adult Cat Pouch Pork 100 g | Adult Cat Pouch Pork | https://siruk.am/product/gemon-adult-cat-pouch-pork-100-g/dp/755/ |
| 637 | Monoprotein Adult Cat Salmon 1.5 kg | Monoprotein Adult Cat Salmon | https://siruk.am/product/monge-monoprotein-adult-cat-salmon-1-5-kg/dp/759/ |
| 638 | Monoprotein Sterilised Cat Beef 1.5 kg | Monoprotein Sterilised Cat Beef | https://siruk.am/product/monge-monoprotein-sterilised-cat-beef-1-5-kg/dp/760/ |
| 640 | Extra Small Puppy & Junior Chicken 800 g | Extra Small Puppy & Junior Chicken | https://siruk.am/product/monge-extra-small-puppy-junior-chicken-800-g/dp/762/ |
| 641 | Extra Small Adult Lamb & Rice 800 g | Extra Small Adult Lamb & Rice | https://siruk.am/product/monge-extra-small-adult-lamb-rice-800-g/dp/763/ |
| 642 | Sterilised Cat Chicken 1.5 kg | Sterilised Cat Chicken | https://siruk.am/product/monge-sterilised-cat-chicken-1-5-kg/dp/764/ |
| 643 | BWild Adult Cat Hare 1.5 kg | BWild Adult Cat Hare | https://siruk.am/product/monge-bwild-adult-cat-hare-1-5-kg/dp/765/ |
| 644 | BWild Grain Free Large Breed Cat Buffalo 1.5 kg | BWild Grain Free Large Breed Cat Buffalo | https://siruk.am/product/monge-bwild-grain-free-large-breed-cat-buffalo-1-5-kg/dp/766/ |
| 645 | BWild Grain Free Sterilised Cat Tuna with Peas 1.5 kg | BWild Grain Free Sterilised Cat Tuna with Peas | https://siruk.am/product/monge-bwild-grain-free-sterilised-cat-tuna-with-peas-1-5-kg/dp/767/ |
| 646 | VetSolution Gastrointestinal Cat 1.5 kg | VetSolution Gastrointestinal Cat | https://siruk.am/product/monge-vetsolution-gastrointestinal-cat-1-5-kg/dp/768/ |
| 647 | VetSolution Renal Cat 1.5 kg | VetSolution Renal Cat | https://siruk.am/product/monge-vetsolution-renal-cat-1-5-kg/dp/769/ |
| 648 | VetSolution Hepatic Cat 1.5 kg | VetSolution Hepatic Cat | https://siruk.am/product/monge-vetsolution-hepatic-cat-1-5-kg/dp/770/ |
| 649 | VetSolution Diabetic Cat 1.5 kg | VetSolution Diabetic Cat | https://siruk.am/product/monge-vetsolution-diabetic-cat-1-5-kg/dp/771/ |
| 650 | BWild Grain Free Puppy Duck 400 g | BWild Grain Free Puppy Duck | https://siruk.am/product/monge-bwild-grain-free-puppy-duck-400-g/dp/772/ |
| 652 | BWild Grain Free Mini Adult Dog Duck 400 g | BWild Grain Free Mini Adult Dog Duck | https://siruk.am/product/monge-bwild-grain-free-mini-adult-dog-duck-400-g/dp/776/ |
| 654 | Fresh Puppy Veal with Vegetables 400 g | Fresh Puppy Veal with Vegetables | https://siruk.am/product/monge-fresh-puppy-veal-with-vegetables-400-g/dp/788/ |
| 658 | Fresh Senior Dog Turkey with Vegetables 400 g | Fresh Senior Dog Turkey with Vegetables | https://siruk.am/product/monge-fresh-senior-dog-turkey-with-vegetables-400-g/dp/795/ |
| 665 | Excellence Medium Adult Lamb 1275 g | Excellence Medium Adult Lamb | https://siruk.am/product/special-dog-excellence-medium-adult-lamb-1275-g/dp/802/ |
| 666 | Excellence Maxi Adult Beef 1275 g | Excellence Maxi Adult Beef | https://siruk.am/product/special-dog-excellence-maxi-adult-beef-1275-g/dp/803/ |
| 667 | Excellence Adult Cat Beef 100 g | Excellence Adult Cat Beef | https://siruk.am/product/lechat-excellence-adult-cat-beef-100-g/dp/804/ |
| 668 | VetSolution Diabetic & Obesity Dog 400 g | VetSolution Diabetic & Obesity Dog | https://siruk.am/product/monge-vetsolution-diabetic-obesity-dog-400-g/dp/805/ |
| 670 | Sterilised Cat Paté Turkey 400 g | Sterilised Cat Paté Turkey | https://siruk.am/product/gemon-sterilised-cat-pat-turkey-400-g/dp/809/ |
| 671 | Adult Cat Paté Beef 400 g | Adult Cat Paté Beef | https://siruk.am/product/gemon-adult-cat-pat-beef-400-g/dp/810/ |
| 672 | Puppy & Junior Dog Pouch Chicken 100 g | Puppy & Junior Dog Pouch Chicken | https://siruk.am/product/gemon-puppy-junior-dog-pouch-chicken-100-g/dp/811/ |
| 673 | Adult Cat Chunks Salmon & Shrimp 415 g | Adult Cat Chunks Salmon & Shrimp | https://siruk.am/product/gemon-adult-cat-chunks-salmon-shrimp-415-g/dp/812/ |
| 674 | Sterilised Cat Chunks Tuna & White Fish 415 g | Sterilised Cat Chunks Tuna & White Fish | https://siruk.am/product/gemon-sterilised-cat-chunks-tuna-white-fish-415-g/dp/813/ |
| 675 | Sterilised Cat Pouch Tuna 100 g | Sterilised Cat Pouch Tuna | https://siruk.am/product/gemon-sterilised-cat-pouch-tuna-100-g/dp/814/ |
| 679 | Medium Adult Dog Chunks Veal & Liver 415 g | Medium Adult Dog Chunks Veal & Liver | https://siruk.am/product/gemon-medium-adult-dog-chunks-veal-liver-415-g/dp/821/ |
| 680 | Puppy & Junior Dog Chunks Chicken & Turkey 415 g | Puppy & Junior Dog Chunks Chicken & Turkey | https://siruk.am/product/gemon-puppy-junior-dog-chunks-chicken-turkey-415-g/dp/822/ |
| 681 | Mini Adult Dog Chunks Chicken & Rice 415 g | Mini Adult Dog Chunks Chicken & Rice | https://siruk.am/product/gemon-mini-adult-dog-chunks-chicken-rice-415-g/dp/823/ |
| 684 | Leo's Puppy Chunks Chicken & Turkey 415 g | Leo's Puppy Chunks Chicken & Turkey | https://siruk.am/product/monge-leo-s-puppy-chunks-chicken-turkey-415-g/dp/827/ |
| 685 | Leo's Adult Chunks Poultry 415 g | Leo's Adult Chunks Poultry | https://siruk.am/product/monge-leo-s-adult-chunks-poultry-415-g/dp/828/ |
| 686 | Gift Soft Sticks Adult Cat Rabbit with Sage 15 g | Gift Soft Sticks Adult Cat Rabbit with Sage | https://siruk.am/product/monge-gift-soft-sticks-adult-cat-rabbit-with-sage-15-g/dp/829/ |
| 687 | Gift Soft Sticks Kitten Trout with Chamomile 15 g | Gift Soft Sticks Kitten Trout with Chamomile | https://siruk.am/product/monge-gift-soft-sticks-kitten-trout-with-chamomile-15-g/dp/830/ |
| 688 | Gift Soft Sticks Adult Cat Pork with Rosehips & Cheese 15 g | Gift Soft Sticks Adult Cat Pork with Rosehips & Cheese | https://siruk.am/product/monge-gift-soft-sticks-adult-cat-pork-with-rosehips-cheese-15-g/dp/831/ |
| 689 | Gift Soft Sticks Hairball Cat Salmon with Artichoke 15 g | Gift Soft Sticks Hairball Cat Salmon with Artichoke | https://siruk.am/product/monge-gift-soft-sticks-hairball-cat-salmon-with-artichoke-15-g/dp/832/ |
| 691 | Gift Soft Sticks Sterilised Cat Duck with Lemon Balm & Cranberries 15 g | Gift Soft Sticks Sterilised Cat Duck with Lemon Balm & Cranberries | https://siruk.am/product/monge-gift-soft-sticks-sterilised-cat-duck-with-lemon-balm-cranberries-15-g/dp/834/ |
| 694 | Gift Sticks Puppy & Junior Pork with Milk 45 g | Gift Sticks Puppy & Junior Pork with Milk | https://siruk.am/product/monge-gift-sticks-puppy-junior-pork-with-milk-45-g/dp/837/ |
| 698 | Gift Filled & Crunchy Dental Cat Rabbit with Peppermint 60 g | Gift Filled & Crunchy Dental Cat Rabbit with Peppermint | https://siruk.am/product/monge-gift-filled-crunchy-dental-cat-rabbit-with-peppermint-60-g/dp/841/ |
| 699 | Gift Filled & Crunchy Kitten Trout with Milk 60 g | Gift Filled & Crunchy Kitten Trout with Milk | https://siruk.am/product/monge-gift-filled-crunchy-kitten-trout-with-milk-60-g/dp/842/ |
| 700 | Gift Filled & Crunchy Adult Cat Pork with Cheese 60 g | Gift Filled & Crunchy Adult Cat Pork with Cheese | https://siruk.am/product/monge-gift-filled-crunchy-adult-cat-pork-with-cheese-60-g/dp/843/ |
| 701 | Gift Filled & Crunchy Hairball Cat Salmon with Catnip 60 g | Gift Filled & Crunchy Hairball Cat Salmon with Catnip | https://siruk.am/product/monge-gift-filled-crunchy-hairball-cat-salmon-with-catnip-60-g/dp/844/ |
| 702 | Gift Filled & Crunchy Skin Support Cat Cod with Aloe Vera 60 g | Gift Filled & Crunchy Skin Support Cat Cod with Aloe Vera | https://siruk.am/product/monge-gift-filled-crunchy-skin-support-cat-cod-with-aloe-vera-60-g/dp/845/ |
| 703 | Gift Filled & Crunchy Sterilised Cat Duck with Cranberries 60 g | Gift Filled & Crunchy Sterilised Cat Duck with Cranberries | https://siruk.am/product/monge-gift-filled-crunchy-sterilised-cat-duck-with-cranberries-60-g/dp/846/ |
| 704 | Gift Meat Minis Hairball Cat Salmon with Plum 50 g | Gift Meat Minis Hairball Cat Salmon with Plum | https://siruk.am/product/monge-gift-meat-minis-hairball-cat-salmon-with-plum-50-g/dp/847/ |
| 705 | Gift Meat Minis Dental Cat Rabbit with Apple 50 g | Gift Meat Minis Dental Cat Rabbit with Apple | https://siruk.am/product/monge-gift-meat-minis-dental-cat-rabbit-with-apple-50-g/dp/848/ |
| 706 | Gift Meat Minis Kitten Trout with Blueberries 50 g | Gift Meat Minis Kitten Trout with Blueberries | https://siruk.am/product/monge-gift-meat-minis-kitten-trout-with-blueberries-50-g/dp/849/ |
| 707 | Gift Meat Minis Adult Cat Pork with Pineapple & Cheese 50 g | Gift Meat Minis Adult Cat Pork with Pineapple & Cheese | https://siruk.am/product/monge-gift-meat-minis-adult-cat-pork-with-pineapple-cheese-50-g/dp/850/ |
| 708 | Gift Meat Minis Sterilised Cat Duck with Pomegranate & Cranberries 50 g | Gift Meat Minis Sterilised Cat Duck with Pomegranate & Cranberries | https://siruk.am/product/monge-gift-meat-minis-sterilised-cat-duck-with-pomegranate-cranberries-50-g/dp/851/ |
| 710 | BWild Grain Free Large Breed Cat Paté Buffalo 100 g | BWild Grain Free Large Breed Cat Paté Buffalo | https://siruk.am/product/monge-bwild-grain-free-large-breed-cat-pat-buffalo-100-g/dp/856/ |
| 715 | VetSolution Dermatosis Dog 150 g | VetSolution Dermatosis Dog | https://siruk.am/product/monge-vetsolution-dermatosis-dog-150-g/dp/867/ |
| 716 | VetSolution Gastrointestinal Dog 150 g | VetSolution Gastrointestinal Dog | https://siruk.am/product/monge-vetsolution-gastrointestinal-dog-150-g/dp/868/ |
| 717 | VetSolution Renal Dog 150 g | VetSolution Renal Dog | https://siruk.am/product/monge-vetsolution-renal-dog-150-g/dp/869/ |
| 718 | VetSolution Recovery Dog 150 g | VetSolution Recovery Dog | https://siruk.am/product/monge-vetsolution-recovery-dog-150-g/dp/870/ |
| 719 | VetSolution Renal & Oxalate Cat 100 g | VetSolution Renal & Oxalate Cat | https://siruk.am/product/monge-vetsolution-renal-oxalate-cat-100-g/dp/871/ |
| 720 | VetSolution Recovery Cat 100 g | VetSolution Recovery Cat | https://siruk.am/product/monge-vetsolution-recovery-cat-100-g/dp/872/ |
| 721 | Fresh Adult Cat Chicken with Vegetables 85 g | Fresh Adult Cat Chicken with Vegetables | https://siruk.am/product/monge-fresh-adult-cat-chicken-with-vegetables-85-g/dp/873/ |
| 730 | Traditional Line Lemon Shampoo for Short Coats, 300 ml | Traditional Line Lemon Shampoo for Short Coats | https://siruk.am/product/iv-san-bernard-traditional-line-lemon-shampoo-for-short-coats-300-ml/dp/886/ |
| 731 | Traditional Line Green Apple Shampoo for Long Coats, 300 ml | Traditional Line Green Apple Shampoo for Long Coats | https://siruk.am/product/iv-san-bernard-traditional-line-green-apple-shampoo-for-long-coats-300-ml/dp/887/ |
| 732 | Traditional Line Lemon Conditioner for Short Coats, 300 ml | Traditional Line Lemon Conditioner for Short Coats | https://siruk.am/product/iv-san-bernard-traditional-line-lemon-conditioner-for-short-coats-300-ml/dp/888/ |
| 733 | Traditional Line Green Apple Conditioner for Long Coats, 300 ml | Traditional Line Green Apple Conditioner for Long Coats | https://siruk.am/product/iv-san-bernard-traditional-line-green-apple-conditioner-for-long-coats-300-ml/dp/889/ |
| 734 | Protective Shield Shampoo, 300 ml | Protective Shield Shampoo | https://siruk.am/product/iv-san-bernard-protective-shield-shampoo-300-ml/dp/890/ |
| 735 | Protective Shield Conditioner, 300 ml | Protective Shield Conditioner | https://siruk.am/product/iv-san-bernard-protective-shield-conditioner-300-ml/dp/891/ |
| 736 | Atami H270 Two-Phase Detangling Spray Conditioner, 300 ml | Atami H270 Two-Phase Detangling Spray Conditioner | https://siruk.am/product/iv-san-bernard-atami-h270-two-phase-detangling-spray-conditioner-300-ml/dp/892/ |
| 737 | Lactol Puppy Milk, 250 g | Lactol Puppy Milk | https://siruk.am/product/beaphar-lactol-puppy-milk-250-g/dp/893/ |
| 738 | Lactol Kitten Milk, 250 g | Lactol Kitten Milk | https://siruk.am/product/beaphar-lactol-kitten-milk-250-g/dp/894/ |
| 747 | 3D Flea & Tick Spray for Dogs, 200 ml | 3D Flea & Tick Spray for Dogs | https://siruk.am/product/rolf-club-3d-flea-tick-spray-for-dogs-200-ml/dp/903/ |
| 750 | SexControl Drops for Female Cats, 3 ml | SexControl Drops for Female Cats | https://siruk.am/product/rolf-club-sexcontrol-drops-for-female-cats-3-ml/dp/906/ |
| 751 | SexControl Drops for Male Cats, 3 ml | SexControl Drops for Male Cats | https://siruk.am/product/rolf-club-sexcontrol-drops-for-male-cats-3-ml/dp/907/ |
| 762 | Ear Drops for Dogs and Cats, 10 ml | Ear Drops for Dogs and Cats | https://siruk.am/product/inspector-ear-drops-for-dogs-and-cats-10-ml/dp/918/ |
| 779 | Mini Syrup for Puppies and Kittens, 10 ml | Mini Syrup for Puppies and Kittens | https://siruk.am/product/gelmintal-mini-syrup-for-puppies-and-kittens-10-ml/dp/935/ |
| 790 | Dental Gel with Silver Ions, 75 ml | Dental Gel with Silver Ions | https://siruk.am/product/cliny-dental-gel-with-silver-ions-75-ml/dp/946/ |
| 791 | Oral Care Liquid with Silver Ions, 300 ml | Oral Care Liquid with Silver Ions | https://siruk.am/product/cliny-oral-care-liquid-with-silver-ions-300-ml/dp/947/ |
| 792 | Oral Care Spray with Silver Ions, 100 ml | Oral Care Spray with Silver Ions | https://siruk.am/product/cliny-oral-care-spray-with-silver-ions-100-ml/dp/948/ |
| 793 | Eye Cleansing Lotion with Silver Ions, 50 ml | Eye Cleansing Lotion with Silver Ions | https://siruk.am/product/cliny-eye-cleansing-lotion-with-silver-ions-50-ml/dp/949/ |
| 794 | Ear Cleansing Lotion with Silver Ions, 50 ml | Ear Cleansing Lotion with Silver Ions | https://siruk.am/product/cliny-ear-cleansing-lotion-with-silver-ions-50-ml/dp/950/ |
| 795 | Hairball Malt Paste, 75 ml | Hairball Malt Paste | https://siruk.am/product/cliny-hairball-malt-paste-75-ml/dp/951/ |
| 871 | Liver Pâté with Hemp, 75 g | Liver Pâté with Hemp | https://siruk.am/product/trixie-liver-pate-with-hemp-75-g/dp/1027/ |
| 875 | 3D Spray for Cats, 200 ml | 3D Spray for Cats | https://siruk.am/product/rolf-club-3d-spray-for-cats-200-ml/dp/1032/ |
| 964 | Highest Protein Ranchlands, 11.4 kg | Highest Protein Ranchlands | https://siruk.am/product/acana-highest-protein-ranchlands-11-4-kg/dp/1122/ |
| 967 | Homestead Harvest, 4.5 kg | Homestead Harvest | https://siruk.am/product/acana-homestead-harvest-4-5-kg/dp/1125/ |
| 969 | Bountiful Catch, 4.5 kg | Bountiful Catch | https://siruk.am/product/acana-bountiful-catch-4-5-kg/dp/1127/ |
| 971 | Highest Protein Wild Prairie, 4.5 kg | Highest Protein Wild Prairie Cat | https://siruk.am/product/acana-highest-protein-wild-prairie-4-5-kg/dp/1129/ |
| 974 | Highest Protein Grasslands, 4.5 kg | Highest Protein Grasslands Cat | https://siruk.am/product/acana-highest-protein-grasslands-4-5-kg/dp/1132/ |
| 978 | Highest Protein Pacifica, 4.5 kg | Highest Protein Pacifica Cat | https://siruk.am/product/acana-highest-protein-pacifica-4-5-kg/dp/1136/ |
| 982 | Small Breed, 4.5 kg | Small Breed | https://siruk.am/product/orijen-small-breed-4-5-kg/dp/1140/ |
| 985 | Indoor Entree, 4.5 kg | Indoor Entree | https://siruk.am/product/acana-indoor-entree-4-5-kg/dp/1143/ |
| 988 | Classics Wild Coast, 9.7 kg | Classics Wild Coast | https://siruk.am/product/acana-classics-wild-coast-9-7-kg/dp/1146/ |
| 993 | Classics Prairie Poultry, 9.7 kg | Classics Prairie Poultry | https://siruk.am/product/acana-classics-prairie-poultry-9-7-kg/dp/1151/ |
| 1000 | Classics Red Meat, 9.7 kg | Classics Red Meat | https://siruk.am/product/acana-classics-red-meat-9-7-kg/dp/1158/ |
| 1006 | Highest Protein Wild Prairie, 11.4 kg | Highest Protein Wild Prairie Dog | https://siruk.am/product/acana-highest-protein-wild-prairie-11-4-kg/dp/1164/ |
| 1009 | Light & Fit, 11.4 kg | Light & Fit | https://siruk.am/product/acana-light-and-fit-11-4-kg/dp/1167/ |
| 1015 | Six Fish, 5.4 kg | Six Fish | https://siruk.am/product/orijen-six-fish-5-4-kg/dp/1173/ |
| 1018 | Singles Yorkshire Pork, 11.4 kg | Singles Yorkshire Pork | https://siruk.am/product/acana-singles-yorkshire-pork-11-4-kg/dp/1176/ |
| 1021 | Sport & Agility, 11.4 kg | Sport & Agility | https://siruk.am/product/acana-sport-and-agility-11-4-kg/dp/1179/ |
| 1024 | Singles Grass-Fed Lamb, 11.4 kg | Singles Grass-Fed Lamb | https://siruk.am/product/acana-singles-grass-fed-lamb-11-4-kg/dp/1182/ |
| 1026 | Puppy Small Breed, 6 kg | Puppy Small Breed | https://siruk.am/product/acana-puppy-small-breed-6-kg/dp/1184/ |
| 1029 | Puppy, 11.4 kg | Puppy | https://siruk.am/product/acana-puppy-11-4-kg/dp/1187/ |
| 1031 | Adult Small Breed, 6 kg | Adult Small Breed | https://siruk.am/product/acana-adult-small-breed-6-kg/dp/1189/ |
| 1033 | Highest Protein Grasslands, 11.4 kg | Highest Protein Grasslands Dog | https://siruk.am/product/acana-highest-protein-grasslands-11-4-kg/dp/1191/ |
| 1035 | Highest Protein Pacifica, 11.4 kg | Highest Protein Pacifica Dog | https://siruk.am/product/acana-highest-protein-pacifica-11-4-kg/dp/1193/ |
| 1036 | Singles Free-Run Duck, 11.4 kg | Singles Free-Run Duck | https://siruk.am/product/acana-singles-free-run-duck-11-4-kg/dp/1194/ |
| 1050 | Adult Cat Pouch, 85 g | Adult Cat Pouch | https://siruk.am/product/myau-adult-cat-pouch/dp/1339/ |
| 1051 | Kitten Pouch, 85 g | Kitten Pouch | https://siruk.am/product/myau-kitten-pouch/dp/1345/ |
| 1052 | Cat Paté, 75 g | Cat Paté | https://siruk.am/product/kormell-cat-pate/dp/1346/ |
| 1053 | Cat Pouch in Jelly, 75 g | Cat Pouch in Jelly | https://siruk.am/product/mooor-cat-pouch-jelly/dp/1349/ |
| 1054 | Adult Dog Pouch, 75 g | Adult Dog Pouch | https://siruk.am/product/justin-adult-dog-pouch/dp/1351/ |
| 1058 | DO IT YOURSELF Narciso Perfume, 125 ml | DO IT YOURSELF Narciso Perfume | https://siruk.am/product/iv-san-bernard-do-it-yourself-narciso-perfume/dp/1355/ |
| 1059 | DO IT YOURSELF Ocean Perfume, 125 ml | DO IT YOURSELF Ocean Perfume | https://siruk.am/product/iv-san-bernard-do-it-yourself-ocean-perfume/dp/1356/ |
| 1102 | Adult Dog Paté, 150 g | Adult Dog Paté | https://siruk.am/product/gemon-adult-dog-pate-150-g/dp/1578/ |
| 1144 | Traditional Plus Banana Shampoo for Medium Coats, 300 ml | Traditional Plus Banana Shampoo for Medium Coats | https://siruk.am/product/iv-san-bernard-traditional-plus-banana-shampoo/dp/1631/ |
| 1193 | Toothpaste Calcium+, 75 ml | Toothpaste Calcium+ | https://siruk.am/product/cliny-toothpaste-calcium-plus-75ml/dp/1750/ |

## 4. Merge

Gemon *Adult Dog Paté* 400 g cans (product 678) folded into the 150 g trays (1102) — one product, 5 variants (tray / can × flavour); 678 is discontinued (hidden) with stock 0, its skus suffixed `-OLD`. https://siruk.am/product/gemon-adult-dog-pate-150-g/dp/1578/

## 5. Photos per pack size

Every sized variant was looked at on contact sheets (all images of the 46 multi-size products, the first image of the 481 other sized variants). Replacements are keyed to our EAN / article and were checked by eye before upload; the bag's by-weight twin got the same gallery.

| Product | Variant | What was wrong | Now | Link |
|---|---|---|---|---|
| Adult Cat Pouch | 85 g | WATERMARK; HAFO | 2 image(s), first = new | https://siruk.am/product/myau-adult-cat-pouch/dp/1339/ |
| Adult Cat Pouch | 85 g | WRONG_PRODUCT; WATERMARK; HAFO | 2 image(s), first = new | https://siruk.am/product/myau-adult-cat-pouch/dp/1340/ |
| Adult Cat Pouch | 85 g | WATERMARK; HAFO | 2 image(s), first = new | https://siruk.am/product/myau-adult-cat-pouch/dp/1342/ |
| Adult Cat Pouch | 85 g | HAFO | 2 image(s), first = new | https://siruk.am/product/myau-adult-cat-pouch/dp/1343/ |
| Adult Cat Pouch | 85 g | WATERMARK; HAFO | 2 image(s), first = new | https://siruk.am/product/myau-adult-cat-pouch/dp/1344/ |
| Kitten Pouch | 85 g | WATERMARK; HAFO | 2 image(s), first = new | https://siruk.am/product/myau-kitten-pouch/dp/1345/ |
| Premium Sterilised Dry Cat Food | 14 kg | WRONG_SIZE | 1 image(s), first = new | https://siruk.am/product/club-4-paws-premium-sterilised-dry-cat-food/dp/1703/ |
| Premium Hairball Control Dry Cat Food | 14 kg | WRONG_SIZE | 2 image(s), first = new | https://siruk.am/product/club-4-paws-premium-hairball-control-dry-cat-food/dp/1705/ |
| Premium Medium Breeds Adult Dry Dog Food | 14 kg | WRONG_SIZE | 1 image(s), first = new | https://siruk.am/product/club-4-paws-premium-medium-breeds-adult-dry-dog-food/dp/1711/ |
| Premium Small Breeds Adult Dry Dog Food | 14 kg | WRONG_SIZE | 1 image(s), first = new | https://siruk.am/product/club-4-paws-premium-small-breeds-adult-dry-dog-food/dp/1713/ |
| Premium Puppies Dry Dog Food | 14 kg | WRONG_SIZE | 1 image(s), first = new | https://siruk.am/product/club-4-paws-premium-puppies-dry-dog-food/dp/1715/ |
| Filets | 300 g | SAME_AS_SIBLING | 3 image(s), first = new | https://siruk.am/product/trixie-filets/dp/458/ |
| Dental Hygiene Set for Cats | 50 g | WRONG_PRODUCT | 8 image(s), first = new | https://siruk.am/product/trixie-dental-hygiene-set-50-g/dp/613/ |
| Traditional Line Lemon Shampoo for Short Coats | 300 ml | NOT_PACKSHOT | 2 image(s), first = new | https://siruk.am/product/iv-san-bernard-traditional-line-lemon-shampoo-for-short-coats-300-ml/dp/886/ |
| Traditional Line Green Apple Shampoo for Long Coats | 300 ml | NOT_PACKSHOT | 2 image(s), first = new | https://siruk.am/product/iv-san-bernard-traditional-line-green-apple-shampoo-for-long-coats-300-ml/dp/887/ |
| Traditional Line Lemon Conditioner for Short Coats | 300 ml | NOT_PACKSHOT | 2 image(s), first = new | https://siruk.am/product/iv-san-bernard-traditional-line-lemon-conditioner-for-short-coats-300-ml/dp/888/ |
| Traditional Line Green Apple Conditioner for Long Coats | 300 ml | NOT_PACKSHOT | 2 image(s), first = new | https://siruk.am/product/iv-san-bernard-traditional-line-green-apple-conditioner-for-long-coats-300-ml/dp/889/ |
| Protective Shield Shampoo | 300 ml | NOT_PACKSHOT | 2 image(s), first = new | https://siruk.am/product/iv-san-bernard-protective-shield-shampoo-300-ml/dp/890/ |
| Protective Shield Conditioner | 300 ml | NOT_PACKSHOT | 2 image(s), first = new | https://siruk.am/product/iv-san-bernard-protective-shield-conditioner-300-ml/dp/891/ |
| Dumbbells | 300 g | WRONG_PRODUCT | 2 image(s), first = new | https://siruk.am/product/trixie-dumbbells/dp/460/ |
| Cat Pouch in Jelly | 75 g | HAFO | 1 image(s), first = new | https://siruk.am/product/mooor-cat-pouch-jelly/dp/1349/ |
| Cat Pouch in Jelly | 75 g | HAFO | 1 image(s), first = new | https://siruk.am/product/mooor-cat-pouch-jelly/dp/1350/ |
| Adult Dog Pouch | 75 g | HAFO | 1 image(s), first = new | https://siruk.am/product/justin-adult-dog-pouch/dp/1351/ |
| Stop It Indoor Repellent Spray | 200 ml | HAFO | 1 image(s), first = new | https://siruk.am/product/beaphar-stop-it-indoor-spray/dp/1354/ |
| DO IT YOURSELF Narciso Perfume | 125 ml | WATERMARK; HAFO | 1 image(s), first = new | https://siruk.am/product/iv-san-bernard-do-it-yourself-narciso-perfume/dp/1355/ |
| DO IT YOURSELF Ocean Perfume | 125 ml | WATERMARK; HAFO | 1 image(s), first = new | https://siruk.am/product/iv-san-bernard-do-it-yourself-ocean-perfume/dp/1356/ |
| Delights Pork Bones | 84 g | HAFO | 1 image(s), first = new | https://siruk.am/product/8in1-delights-pork-bones/dp/1758/ |
| New Neon Tape Lead | XS, 3 m, black/neon | HAFO | 2 image(s), first = new | https://siruk.am/product/flexi-new-neon-tape-lead-5-m/dp/1751/ |
| Crispy Muesli Guinea Pigs | 400 g | SAME_AS_SIBLING; HAFO | 2 image(s), first = new | https://siruk.am/product/versele-laga-crispy-muesli-guinea-pigs/dp/1773/ |
| Crispy Muesli Hamsters & Co | 400 g | HAFO | 2 image(s), first = new | https://siruk.am/product/versele-laga-crispy-muesli-hamsters-co/dp/1775/ |
| Crispy Muesli Guinea Pigs | 1 kg | SAME_AS_SIBLING; HAFO | 1 image(s), first = new | https://siruk.am/product/versele-laga-crispy-muesli-guinea-pigs/dp/1774/ |
| Chunks Adult | 1.23 kg | SAME_AS_SIBLING | 1 image(s), first = new | https://siruk.am/product/simba-chunks-adult/dp/417/ |
| Chunks Adult | 1.23 kg | SAME_AS_SIBLING | 1 image(s), first = new | https://siruk.am/product/simba-chunks-adult/dp/419/ |
| Chunks Adult | 1.23 kg | SAME_AS_SIBLING | 1 image(s), first = new | https://siruk.am/product/simba-chunks-adult/dp/421/ |
| All Breeds Puppy & Junior | 12 kg | WRONG_SIZE | 1 image(s), first = new | https://siruk.am/product/monge-all-breeds-puppy-junior-lamb-rice-800-g/dp/1573/ |
| Mini Puppy & Junior | 15 kg | WRONG_SIZE | 1 image(s), first = new | https://siruk.am/product/monge-mini-puppy-junior/dp/1663/ |
| Maxi Puppy & Junior | 15 kg | WRONG_SIZE | 1 image(s), first = new | https://siruk.am/product/monge-maxi-puppy-junior/dp/1669/ |
| Mini Adult | 15 kg | WRONG_SIZE | 2 image(s), first = new | https://siruk.am/product/monge-mini-adult-chicken-rice-800-g/dp/1575/ |
| Mini Adult | 15 kg | WRONG_SIZE | 2 image(s), first = new | https://siruk.am/product/monge-mini-adult-chicken-rice-800-g/dp/1576/ |
| Mini Adult | 15 kg | WRONG_SIZE | 2 image(s), first = new | https://siruk.am/product/monge-mini-adult-chicken-rice-800-g/dp/1577/ |
| All Breeds Puppy & Junior | 15 kg | WRONG_SIZE | 2 image(s), first = new | https://siruk.am/product/monge-all-breeds-puppy-junior-lamb-rice-800-g/dp/1574/ |
| Mini Puppy & Junior | 15 kg | WRONG_SIZE | 2 image(s), first = new | https://siruk.am/product/monge-mini-puppy-junior/dp/1659/ |
| Mini Puppy & Junior | 15 kg | WRONG_SIZE | 2 image(s), first = new | https://siruk.am/product/monge-mini-puppy-junior/dp/1661/ |
| Mini Starter | 15 kg | WRONG_SIZE | 2 image(s), first = new | https://siruk.am/product/monge-mini-starter/dp/1665/ |
| Medium Puppy & Junior | 15 kg | WRONG_SIZE | 2 image(s), first = new | https://siruk.am/product/monge-medium-puppy-junior/dp/1667/ |
| All Breeds Adult | 12 kg | WRONG_SIZE | 2 image(s), first = new | https://siruk.am/product/monge-all-breeds-adult/dp/1642/ |
| All Breeds Adult | 12 kg | WRONG_SIZE | 2 image(s), first = new | https://siruk.am/product/monge-all-breeds-adult/dp/1644/ |
| All Breeds Adult | 12 kg | WRONG_SIZE | 2 image(s), first = new | https://siruk.am/product/monge-all-breeds-adult/dp/1646/ |
| All Breeds Adult | 12 kg | WRONG_SIZE | 1 image(s), first = new | https://siruk.am/product/monge-all-breeds-adult/dp/1648/ |
| All Breeds Adult | 12 kg | WRONG_SIZE | 2 image(s), first = new | https://siruk.am/product/monge-all-breeds-adult/dp/1650/ |
| All Breeds Adult | 12 kg | WRONG_SIZE | 2 image(s), first = new | https://siruk.am/product/monge-all-breeds-adult/dp/1652/ |
| Maxi Adult | 12 kg | WRONG_SIZE | 2 image(s), first = new | https://siruk.am/product/monge-maxi-adult/dp/1671/ |
| BWild Low Grain All Breeds Adult | 12 kg | WRONG_SIZE | 2 image(s), first = new | https://siruk.am/product/monge-bwild-low-grain-all-breeds-adult/dp/1673/ |
| BWild Low Grain All Breeds Adult | 12 kg | WRONG_SIZE | 1 image(s), first = new | https://siruk.am/product/monge-bwild-low-grain-all-breeds-adult/dp/1675/ |
| BWild Low Grain All Breeds Puppy & Junior | 12 kg | WRONG_SIZE | 2 image(s), first = new | https://siruk.am/product/monge-bwild-low-grain-all-breeds-puppy-junior/dp/1677/ |
| BWild Grain Free All Breeds Adult | 12 kg | WRONG_SIZE | 2 image(s), first = new | https://siruk.am/product/monge-bwild-grain-free-all-breeds-adult/dp/1679/ |
| Hair & Skin Care Thin Slices | 12 × 85 g | 12-pack showed the single pouch | the 12-pack box shot moved first | https://siruk.am/product/royal-canin-hair-skin-care-thin-slices/dp/1835/ |
| Sensitivity Control Chicken with Rice | 12 × 85 g | 12-pack showed the single pouch | the 12-pack box shot moved first | https://siruk.am/product/royal-canin-sensitivity-control-chicken-with-rice/dp/1839/ |
| Light Weight Care Thin Slices | 12 × 85 g | 12-pack showed the single pouch | the 12-pack box shot moved first | https://siruk.am/product/royal-canin-light-weight-care-thin-slices/dp/1855/ |
| Light Weight Care Thin Slices | 12 × 85 g | 12-pack showed the single pouch | the 12-pack box shot moved first | https://siruk.am/product/royal-canin-light-weight-care-thin-slices/dp/1857/ |
| Renal Thin Slices in Gravy | 12 × 85 g | 12-pack showed the single pouch | the 12-pack box shot moved first | https://siruk.am/product/royal-canin-renal-thin-slices-in-gravy/dp/1867/ |
| Renal Thin Slices in Gravy | 12 × 85 g | 12-pack showed the single pouch | the 12-pack box shot moved first | https://siruk.am/product/royal-canin-renal-thin-slices-in-gravy/dp/1869/ |
| Urinary Care in Gravy | 12 × 85 g | 12-pack showed the single pouch | the 12-pack box shot moved first | https://siruk.am/product/royal-canin-urinary-care-in-gravy/dp/1871/ |
| Ageing 12+ Chunks in Jelly | 12 × 85 g | 12-pack showed the single pouch | the 12-pack box shot moved first | https://siruk.am/product/royal-canin-ageing-12-chunks-in-jelly/dp/1859/ |
| Urinary S/O Morsels in Gravy | 12 × 85 g | 12-pack showed the single pouch | the 12-pack box shot moved first | https://siruk.am/product/royal-canin-urinary-s-o-morsels-in-gravy/dp/1865/ |

## 6. Still showing a hafo photo (after all of the above)

**12 variants.** The Google / Google Lens step could not run in this session (the Claude Chrome extension was not connected and the devtools browser profile was held by another window) — it is the next thing to run on these.

| Product | Variant | sku | hafo at | Only hafo? | Searched, nothing usable | Link |
|---|---|---|---|---|---|---|
| Gran Bonta Chef Adult Dog | 1.23 kg | 041887 | 1 | yes | EAN 8009470041881 is not indexed anywhere (WebSearch '"8009470041881"', '"800947004188"'); | https://siruk.am/product/monge-gran-bonta-chef-adult-dog/dp/1303/ |
| Premium Adjustable Lead, double-layered | XS–S, 2.00 m/15 mm, light lilac | 200720 | 1 | yes | No image keyed to 200720 or EAN 4053032024847. The Trixie CDN probes all return 404; tiier | https://siruk.am/product/trixie-premium-adjustable-lead-double-layered/dp/1721/ |
| Cat Paté | 75 g | 83041J | 1 | yes | KorMell chicken paté 75 g (EAN …830414). No EAN-keyed page anywhere. garfield.by (which ca | https://siruk.am/product/kormell-cat-pate/dp/1346/ |
| Cat Paté | 75 g | 83042J | 1 | yes | KorMell beef & liver paté 75 g (EAN …830421). Same result as 1346. | https://siruk.am/product/kormell-cat-pate/dp/1347/ |
| Cat Paté | 75 g | 83047J | 1 | yes | KorMell duck paté 75 g (EAN …830476). Same result as 1346. | https://siruk.am/product/kormell-cat-pate/dp/1348/ |
| Kitten Cat | 10 kg | MG 004817 | 1 | yes | held: barcode page shows the retail bag, hafo the Breeders bag — PM to say which we sell | https://siruk.am/product/monge-kitten-cat/dp/1685/ |
| Kitten Cat | By weight | MG 004817-KG | 1 | yes | by-weight twin — follows its bag | https://siruk.am/product/monge-kitten-cat/dp/1920/ |
| Adult Cat | 10 kg | MG 004807 | 1 | yes | held: same as Kitten 10 kg | https://siruk.am/product/monge-adult-cat/dp/1689/ |
| Adult Cat | By weight | MG 004807-KG | 1 | yes | by-weight twin — follows its bag | https://siruk.am/product/monge-adult-cat/dp/1922/ |
| Kitten Dry Food | 11 kg | 902135 | 1 | yes | Мяу! kitten 11 kg looks rare/discontinued: not on hotline, catfeatdog (lists adult 11 kg o | https://siruk.am/product/myau-kitten-dry-food/dp/1717/ |
| Kitten Dry Food | By weight | 902135-KG | 1 | yes | by-weight twin — follows its bag | https://siruk.am/product/myau-kitten-dry-food/dp/1936/ |
| Litter Tray with Mesh | M | 03623K | 1 | yes | Inteko litter tray with mesh M (EAN 4605350036233). No page prints the EAN. poryadok.ru/sc | https://siruk.am/product/inteko-litter-tray-with-mesh/dp/1752/ |

## 7. For the PM

- **Gemon names vs cans** (the photos match the barcodes, the names don't): 679 *Medium Adult Dog Chunks Veal & Liver* — the can is Beef & Liver (Manzo e Fegato); 683 *Medium Adult Dog Paté* 1.25 kg — the cans are chunks (Bocconi); 681 *Mini Adult Dog Chunks Chicken* — Monge's can says Adult Medium, shops list the barcode as Mini. Rename?
- **Monge Best for Breeders 10 kg cat bags** (1685 Kitten, 1689 Adult): retail bag or Breeders bag — which do we sell?
- **Litter Tray with Mesh 03623K**: its EAN prefix 4605350 is Kaskad's, not Inteko's — check the brand.
- **Simba Chunks 1230 g**: the photos found are the right can size but the older label; Wild Game 1230 g still shows the 415 g can.
- **Monge 800 g bags** (761 All Breeds Puppy Lamb, 763 Extra Small Adult Lamb): the photo shows a bigger bag; no 800 g photo found.
- **Simba Adult Dog Kibbles 20 kg**: only the 4 kg bag photo exists anywhere we can reach.
- **Royal Canin Mother & Babycat 12 × 195 g**: no 12-pack photo exists (the sku is the single-can EAN).
- **Travel Bottle with Bowl, 500 ml** (852): capacity in the name of an accessory without a size label — keep?
- Developers: allow deleting the 61 retired `-1KG` variants (stock history = initial stock only).

## 8. siruk.am links (every product/variant touched or still open, in report order)

- https://siruk.am/product/monge-mini-adult-chicken-rice-800-g/dp/1881/
- https://siruk.am/product/monge-mini-adult-chicken-rice-800-g/dp/1882/
- https://siruk.am/product/monge-mini-adult-chicken-rice-800-g/dp/1883/
- https://siruk.am/product/monge-all-breeds-puppy-junior-lamb-rice-800-g/dp/1884/
- https://siruk.am/product/monge-all-breeds-puppy-junior-lamb-rice-800-g/dp/1885/
- https://siruk.am/product/acana-highest-protein-ranchlands-11-4-kg/dp/1886/
- https://siruk.am/product/acana-classics-wild-coast-9-7-kg/dp/1880/
- https://siruk.am/product/acana-classics-prairie-poultry-9-7-kg/dp/1887/
- https://siruk.am/product/acana-classics-red-meat-9-7-kg/dp/1888/
- https://siruk.am/product/acana-highest-protein-wild-prairie-11-4-kg/dp/1889/
- https://siruk.am/product/acana-light-and-fit-11-4-kg/dp/1890/
- https://siruk.am/product/orijen-six-fish-5-4-kg/dp/1891/
- https://siruk.am/product/acana-singles-yorkshire-pork-11-4-kg/dp/1892/
- https://siruk.am/product/acana-sport-and-agility-11-4-kg/dp/1893/
- https://siruk.am/product/acana-singles-grass-fed-lamb-11-4-kg/dp/1894/
- https://siruk.am/product/acana-puppy-small-breed-6-kg/dp/1895/
- https://siruk.am/product/acana-puppy-11-4-kg/dp/1896/
- https://siruk.am/product/acana-adult-small-breed-6-kg/dp/1897/
- https://siruk.am/product/acana-highest-protein-grasslands-11-4-kg/dp/1898/
- https://siruk.am/product/acana-highest-protein-pacifica-11-4-kg/dp/1899/
- https://siruk.am/product/acana-singles-free-run-duck-11-4-kg/dp/1900/
- https://siruk.am/product/monge-all-breeds-adult/dp/1901/
- https://siruk.am/product/monge-all-breeds-adult/dp/1902/
- https://siruk.am/product/monge-all-breeds-adult/dp/1903/
- https://siruk.am/product/monge-all-breeds-adult/dp/1904/
- https://siruk.am/product/monge-all-breeds-adult/dp/1905/
- https://siruk.am/product/monge-all-breeds-adult/dp/1906/
- https://siruk.am/product/monge-mini-puppy-junior/dp/1907/
- https://siruk.am/product/monge-mini-puppy-junior/dp/1908/
- https://siruk.am/product/monge-mini-puppy-junior/dp/1909/
- https://siruk.am/product/monge-mini-starter/dp/1910/
- https://siruk.am/product/monge-medium-puppy-junior/dp/1911/
- https://siruk.am/product/monge-maxi-puppy-junior/dp/1912/
- https://siruk.am/product/monge-maxi-adult/dp/1913/
- https://siruk.am/product/monge-bwild-low-grain-all-breeds-adult/dp/1914/
- https://siruk.am/product/monge-bwild-low-grain-all-breeds-adult/dp/1915/
- https://siruk.am/product/monge-bwild-low-grain-all-breeds-puppy-junior/dp/1916/
- https://siruk.am/product/monge-bwild-grain-free-all-breeds-adult/dp/1917/
- https://siruk.am/product/monge-hairball-cat/dp/1918/
- https://siruk.am/product/monge-indoor-cat/dp/1919/
- https://siruk.am/product/monge-kitten-cat/dp/1920/
- https://siruk.am/product/monge-sensitive-cat/dp/1921/
- https://siruk.am/product/monge-adult-cat/dp/1922/
- https://siruk.am/product/gemon-kitten-cat/dp/1923/
- https://siruk.am/product/gemon-adult-cat/dp/1924/
- https://siruk.am/product/gemon-mini-adult-dog/dp/1925/
- https://siruk.am/product/gemon-regular-adult-dog/dp/1926/
- https://siruk.am/product/simba-adult-dog-kibbles/dp/1927/
- https://siruk.am/product/simba-adult-dog-kibbles/dp/1928/
- https://siruk.am/product/club-4-paws-premium-sterilised-dry-cat-food/dp/1929/
- https://siruk.am/product/club-4-paws-premium-hairball-control-dry-cat-food/dp/1930/
- https://siruk.am/product/club-4-paws-premium-active-dry-dog-food/dp/1931/
- https://siruk.am/product/club-4-paws-premium-large-breeds-adult-dry-dog-food/dp/1932/
- https://siruk.am/product/club-4-paws-premium-medium-breeds-adult-dry-dog-food/dp/1933/
- https://siruk.am/product/club-4-paws-premium-small-breeds-adult-dry-dog-food/dp/1934/
- https://siruk.am/product/club-4-paws-premium-puppies-dry-dog-food/dp/1935/
- https://siruk.am/product/myau-kitten-dry-food/dp/1936/
- https://siruk.am/product/gemon-sterilised-cat/dp/1937/
- https://siruk.am/product/gemon-medium-adult-dog/dp/1938/
- https://siruk.am/product/gemon-medium-adult-dog/dp/1939/
- https://siruk.am/product/gemon-puppy-junior-dog/dp/1940/
- https://siruk.am/product/simba-pate-adult-150g/dp/429/
- https://siruk.am/product/trixie-denta-fun-chew-bites-with-mint-150-g/dp/435/
- https://siruk.am/product/trixie-premio-stars-with-chicken-and-rice-100-g/dp/489/
- https://siruk.am/product/trixie-sticks-with-chicken-and-fish-300-g/dp/505/
- https://siruk.am/product/trixie-dental-hygiene-set/dp/612/
- https://siruk.am/product/trixie-dental-hygiene-set-50-g/dp/613/
- https://siruk.am/product/trixie-herbal-shampoo-250-ml/dp/682/
- https://siruk.am/product/trixie-colour-shampoo-for-white-dogs-250-ml/dp/687/
- https://siruk.am/product/trixie-colour-shampoo-for-black-dogs-250-ml/dp/688/
- https://siruk.am/product/trixie-dry-foam-shampoo-450-ml/dp/698/
- https://siruk.am/product/trixie-matatabi-spray-175-ml/dp/706/
- https://siruk.am/product/monge-grill-puppy-chicken-turkey-100-g/dp/739/
- https://siruk.am/product/monge-grill-kitten-salmon-85-g/dp/745/
- https://siruk.am/product/monge-vetsolution-urinary-struvite-cat-100-g/dp/751/
- https://siruk.am/product/gemon-adult-cat-pouch-pork-100-g/dp/755/
- https://siruk.am/product/monge-monoprotein-adult-cat-salmon-1-5-kg/dp/759/
- https://siruk.am/product/monge-monoprotein-sterilised-cat-beef-1-5-kg/dp/760/
- https://siruk.am/product/monge-extra-small-puppy-junior-chicken-800-g/dp/762/
- https://siruk.am/product/monge-extra-small-adult-lamb-rice-800-g/dp/763/
- https://siruk.am/product/monge-sterilised-cat-chicken-1-5-kg/dp/764/
- https://siruk.am/product/monge-bwild-adult-cat-hare-1-5-kg/dp/765/
- https://siruk.am/product/monge-bwild-grain-free-large-breed-cat-buffalo-1-5-kg/dp/766/
- https://siruk.am/product/monge-bwild-grain-free-sterilised-cat-tuna-with-peas-1-5-kg/dp/767/
- https://siruk.am/product/monge-vetsolution-gastrointestinal-cat-1-5-kg/dp/768/
- https://siruk.am/product/monge-vetsolution-renal-cat-1-5-kg/dp/769/
- https://siruk.am/product/monge-vetsolution-hepatic-cat-1-5-kg/dp/770/
- https://siruk.am/product/monge-vetsolution-diabetic-cat-1-5-kg/dp/771/
- https://siruk.am/product/monge-bwild-grain-free-puppy-duck-400-g/dp/772/
- https://siruk.am/product/monge-bwild-grain-free-mini-adult-dog-duck-400-g/dp/776/
- https://siruk.am/product/monge-fresh-puppy-veal-with-vegetables-400-g/dp/788/
- https://siruk.am/product/monge-fresh-senior-dog-turkey-with-vegetables-400-g/dp/795/
- https://siruk.am/product/special-dog-excellence-medium-adult-lamb-1275-g/dp/802/
- https://siruk.am/product/special-dog-excellence-maxi-adult-beef-1275-g/dp/803/
- https://siruk.am/product/lechat-excellence-adult-cat-beef-100-g/dp/804/
- https://siruk.am/product/monge-vetsolution-diabetic-obesity-dog-400-g/dp/805/
- https://siruk.am/product/gemon-sterilised-cat-pat-turkey-400-g/dp/809/
- https://siruk.am/product/gemon-adult-cat-pat-beef-400-g/dp/810/
- https://siruk.am/product/gemon-puppy-junior-dog-pouch-chicken-100-g/dp/811/
- https://siruk.am/product/gemon-adult-cat-chunks-salmon-shrimp-415-g/dp/812/
- https://siruk.am/product/gemon-sterilised-cat-chunks-tuna-white-fish-415-g/dp/813/
- https://siruk.am/product/gemon-sterilised-cat-pouch-tuna-100-g/dp/814/
- https://siruk.am/product/gemon-medium-adult-dog-chunks-veal-liver-415-g/dp/821/
- https://siruk.am/product/gemon-puppy-junior-dog-chunks-chicken-turkey-415-g/dp/822/
- https://siruk.am/product/gemon-mini-adult-dog-chunks-chicken-rice-415-g/dp/823/
- https://siruk.am/product/monge-leo-s-puppy-chunks-chicken-turkey-415-g/dp/827/
- https://siruk.am/product/monge-leo-s-adult-chunks-poultry-415-g/dp/828/
- https://siruk.am/product/monge-gift-soft-sticks-adult-cat-rabbit-with-sage-15-g/dp/829/
- https://siruk.am/product/monge-gift-soft-sticks-kitten-trout-with-chamomile-15-g/dp/830/
- https://siruk.am/product/monge-gift-soft-sticks-adult-cat-pork-with-rosehips-cheese-15-g/dp/831/
- https://siruk.am/product/monge-gift-soft-sticks-hairball-cat-salmon-with-artichoke-15-g/dp/832/
- https://siruk.am/product/monge-gift-soft-sticks-sterilised-cat-duck-with-lemon-balm-cranberries-15-g/dp/834/
- https://siruk.am/product/monge-gift-sticks-puppy-junior-pork-with-milk-45-g/dp/837/
- https://siruk.am/product/monge-gift-filled-crunchy-dental-cat-rabbit-with-peppermint-60-g/dp/841/
- https://siruk.am/product/monge-gift-filled-crunchy-kitten-trout-with-milk-60-g/dp/842/
- https://siruk.am/product/monge-gift-filled-crunchy-adult-cat-pork-with-cheese-60-g/dp/843/
- https://siruk.am/product/monge-gift-filled-crunchy-hairball-cat-salmon-with-catnip-60-g/dp/844/
- https://siruk.am/product/monge-gift-filled-crunchy-skin-support-cat-cod-with-aloe-vera-60-g/dp/845/
- https://siruk.am/product/monge-gift-filled-crunchy-sterilised-cat-duck-with-cranberries-60-g/dp/846/
- https://siruk.am/product/monge-gift-meat-minis-hairball-cat-salmon-with-plum-50-g/dp/847/
- https://siruk.am/product/monge-gift-meat-minis-dental-cat-rabbit-with-apple-50-g/dp/848/
- https://siruk.am/product/monge-gift-meat-minis-kitten-trout-with-blueberries-50-g/dp/849/
- https://siruk.am/product/monge-gift-meat-minis-adult-cat-pork-with-pineapple-cheese-50-g/dp/850/
- https://siruk.am/product/monge-gift-meat-minis-sterilised-cat-duck-with-pomegranate-cranberries-50-g/dp/851/
- https://siruk.am/product/monge-bwild-grain-free-large-breed-cat-pat-buffalo-100-g/dp/856/
- https://siruk.am/product/monge-vetsolution-dermatosis-dog-150-g/dp/867/
- https://siruk.am/product/monge-vetsolution-gastrointestinal-dog-150-g/dp/868/
- https://siruk.am/product/monge-vetsolution-renal-dog-150-g/dp/869/
- https://siruk.am/product/monge-vetsolution-recovery-dog-150-g/dp/870/
- https://siruk.am/product/monge-vetsolution-renal-oxalate-cat-100-g/dp/871/
- https://siruk.am/product/monge-vetsolution-recovery-cat-100-g/dp/872/
- https://siruk.am/product/monge-fresh-adult-cat-chicken-with-vegetables-85-g/dp/873/
- https://siruk.am/product/iv-san-bernard-traditional-line-lemon-shampoo-for-short-coats-300-ml/dp/886/
- https://siruk.am/product/iv-san-bernard-traditional-line-green-apple-shampoo-for-long-coats-300-ml/dp/887/
- https://siruk.am/product/iv-san-bernard-traditional-line-lemon-conditioner-for-short-coats-300-ml/dp/888/
- https://siruk.am/product/iv-san-bernard-traditional-line-green-apple-conditioner-for-long-coats-300-ml/dp/889/
- https://siruk.am/product/iv-san-bernard-protective-shield-shampoo-300-ml/dp/890/
- https://siruk.am/product/iv-san-bernard-protective-shield-conditioner-300-ml/dp/891/
- https://siruk.am/product/iv-san-bernard-atami-h270-two-phase-detangling-spray-conditioner-300-ml/dp/892/
- https://siruk.am/product/beaphar-lactol-puppy-milk-250-g/dp/893/
- https://siruk.am/product/beaphar-lactol-kitten-milk-250-g/dp/894/
- https://siruk.am/product/rolf-club-3d-flea-tick-spray-for-dogs-200-ml/dp/903/
- https://siruk.am/product/rolf-club-sexcontrol-drops-for-female-cats-3-ml/dp/906/
- https://siruk.am/product/rolf-club-sexcontrol-drops-for-male-cats-3-ml/dp/907/
- https://siruk.am/product/inspector-ear-drops-for-dogs-and-cats-10-ml/dp/918/
- https://siruk.am/product/gelmintal-mini-syrup-for-puppies-and-kittens-10-ml/dp/935/
- https://siruk.am/product/cliny-dental-gel-with-silver-ions-75-ml/dp/946/
- https://siruk.am/product/cliny-oral-care-liquid-with-silver-ions-300-ml/dp/947/
- https://siruk.am/product/cliny-oral-care-spray-with-silver-ions-100-ml/dp/948/
- https://siruk.am/product/cliny-eye-cleansing-lotion-with-silver-ions-50-ml/dp/949/
- https://siruk.am/product/cliny-ear-cleansing-lotion-with-silver-ions-50-ml/dp/950/
- https://siruk.am/product/cliny-hairball-malt-paste-75-ml/dp/951/
- https://siruk.am/product/trixie-liver-pate-with-hemp-75-g/dp/1027/
- https://siruk.am/product/rolf-club-3d-spray-for-cats-200-ml/dp/1032/
- https://siruk.am/product/acana-highest-protein-ranchlands-11-4-kg/dp/1122/
- https://siruk.am/product/acana-homestead-harvest-4-5-kg/dp/1125/
- https://siruk.am/product/acana-bountiful-catch-4-5-kg/dp/1127/
- https://siruk.am/product/acana-highest-protein-wild-prairie-4-5-kg/dp/1129/
- https://siruk.am/product/acana-highest-protein-grasslands-4-5-kg/dp/1132/
- https://siruk.am/product/acana-highest-protein-pacifica-4-5-kg/dp/1136/
- https://siruk.am/product/orijen-small-breed-4-5-kg/dp/1140/
- https://siruk.am/product/acana-indoor-entree-4-5-kg/dp/1143/
- https://siruk.am/product/acana-classics-wild-coast-9-7-kg/dp/1146/
- https://siruk.am/product/acana-classics-prairie-poultry-9-7-kg/dp/1151/
- https://siruk.am/product/acana-classics-red-meat-9-7-kg/dp/1158/
- https://siruk.am/product/acana-highest-protein-wild-prairie-11-4-kg/dp/1164/
- https://siruk.am/product/acana-light-and-fit-11-4-kg/dp/1167/
- https://siruk.am/product/orijen-six-fish-5-4-kg/dp/1173/
- https://siruk.am/product/acana-singles-yorkshire-pork-11-4-kg/dp/1176/
- https://siruk.am/product/acana-sport-and-agility-11-4-kg/dp/1179/
- https://siruk.am/product/acana-singles-grass-fed-lamb-11-4-kg/dp/1182/
- https://siruk.am/product/acana-puppy-small-breed-6-kg/dp/1184/
- https://siruk.am/product/acana-puppy-11-4-kg/dp/1187/
- https://siruk.am/product/acana-adult-small-breed-6-kg/dp/1189/
- https://siruk.am/product/acana-highest-protein-grasslands-11-4-kg/dp/1191/
- https://siruk.am/product/acana-highest-protein-pacifica-11-4-kg/dp/1193/
- https://siruk.am/product/acana-singles-free-run-duck-11-4-kg/dp/1194/
- https://siruk.am/product/myau-adult-cat-pouch/dp/1339/
- https://siruk.am/product/myau-kitten-pouch/dp/1345/
- https://siruk.am/product/kormell-cat-pate/dp/1346/
- https://siruk.am/product/mooor-cat-pouch-jelly/dp/1349/
- https://siruk.am/product/justin-adult-dog-pouch/dp/1351/
- https://siruk.am/product/iv-san-bernard-do-it-yourself-narciso-perfume/dp/1355/
- https://siruk.am/product/iv-san-bernard-do-it-yourself-ocean-perfume/dp/1356/
- https://siruk.am/product/gemon-adult-dog-pate-150-g/dp/1578/
- https://siruk.am/product/iv-san-bernard-traditional-plus-banana-shampoo/dp/1631/
- https://siruk.am/product/cliny-toothpaste-calcium-plus-75ml/dp/1750/
- https://siruk.am/product/myau-adult-cat-pouch/dp/1340/
- https://siruk.am/product/myau-adult-cat-pouch/dp/1342/
- https://siruk.am/product/myau-adult-cat-pouch/dp/1343/
- https://siruk.am/product/myau-adult-cat-pouch/dp/1344/
- https://siruk.am/product/club-4-paws-premium-sterilised-dry-cat-food/dp/1703/
- https://siruk.am/product/club-4-paws-premium-hairball-control-dry-cat-food/dp/1705/
- https://siruk.am/product/club-4-paws-premium-medium-breeds-adult-dry-dog-food/dp/1711/
- https://siruk.am/product/club-4-paws-premium-small-breeds-adult-dry-dog-food/dp/1713/
- https://siruk.am/product/club-4-paws-premium-puppies-dry-dog-food/dp/1715/
- https://siruk.am/product/trixie-filets/dp/458/
- https://siruk.am/product/trixie-dumbbells/dp/460/
- https://siruk.am/product/mooor-cat-pouch-jelly/dp/1350/
- https://siruk.am/product/beaphar-stop-it-indoor-spray/dp/1354/
- https://siruk.am/product/8in1-delights-pork-bones/dp/1758/
- https://siruk.am/product/flexi-new-neon-tape-lead-5-m/dp/1751/
- https://siruk.am/product/versele-laga-crispy-muesli-guinea-pigs/dp/1773/
- https://siruk.am/product/versele-laga-crispy-muesli-hamsters-co/dp/1775/
- https://siruk.am/product/versele-laga-crispy-muesli-guinea-pigs/dp/1774/
- https://siruk.am/product/simba-chunks-adult/dp/417/
- https://siruk.am/product/simba-chunks-adult/dp/419/
- https://siruk.am/product/simba-chunks-adult/dp/421/
- https://siruk.am/product/monge-all-breeds-puppy-junior-lamb-rice-800-g/dp/1573/
- https://siruk.am/product/monge-mini-puppy-junior/dp/1663/
- https://siruk.am/product/monge-maxi-puppy-junior/dp/1669/
- https://siruk.am/product/monge-mini-adult-chicken-rice-800-g/dp/1575/
- https://siruk.am/product/monge-mini-adult-chicken-rice-800-g/dp/1576/
- https://siruk.am/product/monge-mini-adult-chicken-rice-800-g/dp/1577/
- https://siruk.am/product/monge-all-breeds-puppy-junior-lamb-rice-800-g/dp/1574/
- https://siruk.am/product/monge-mini-puppy-junior/dp/1659/
- https://siruk.am/product/monge-mini-puppy-junior/dp/1661/
- https://siruk.am/product/monge-mini-starter/dp/1665/
- https://siruk.am/product/monge-medium-puppy-junior/dp/1667/
- https://siruk.am/product/monge-all-breeds-adult/dp/1642/
- https://siruk.am/product/monge-all-breeds-adult/dp/1644/
- https://siruk.am/product/monge-all-breeds-adult/dp/1646/
- https://siruk.am/product/monge-all-breeds-adult/dp/1648/
- https://siruk.am/product/monge-all-breeds-adult/dp/1650/
- https://siruk.am/product/monge-all-breeds-adult/dp/1652/
- https://siruk.am/product/monge-maxi-adult/dp/1671/
- https://siruk.am/product/monge-bwild-low-grain-all-breeds-adult/dp/1673/
- https://siruk.am/product/monge-bwild-low-grain-all-breeds-adult/dp/1675/
- https://siruk.am/product/monge-bwild-low-grain-all-breeds-puppy-junior/dp/1677/
- https://siruk.am/product/monge-bwild-grain-free-all-breeds-adult/dp/1679/
- https://siruk.am/product/royal-canin-hair-skin-care-thin-slices/dp/1835/
- https://siruk.am/product/royal-canin-sensitivity-control-chicken-with-rice/dp/1839/
- https://siruk.am/product/royal-canin-light-weight-care-thin-slices/dp/1855/
- https://siruk.am/product/royal-canin-light-weight-care-thin-slices/dp/1857/
- https://siruk.am/product/royal-canin-renal-thin-slices-in-gravy/dp/1867/
- https://siruk.am/product/royal-canin-renal-thin-slices-in-gravy/dp/1869/
- https://siruk.am/product/royal-canin-urinary-care-in-gravy/dp/1871/
- https://siruk.am/product/royal-canin-ageing-12-chunks-in-jelly/dp/1859/
- https://siruk.am/product/royal-canin-urinary-s-o-morsels-in-gravy/dp/1865/
- https://siruk.am/product/monge-gran-bonta-chef-adult-dog/dp/1303/
- https://siruk.am/product/trixie-premium-adjustable-lead-double-layered/dp/1721/
- https://siruk.am/product/kormell-cat-pate/dp/1347/
- https://siruk.am/product/kormell-cat-pate/dp/1348/
- https://siruk.am/product/monge-kitten-cat/dp/1685/
- https://siruk.am/product/monge-adult-cat/dp/1689/
- https://siruk.am/product/myau-kitten-dry-food/dp/1717/
- https://siruk.am/product/inteko-litter-tray-with-mesh/dp/1752/

## 9. 1 kg variants (end of day)

- https://siruk.am/product/monge-mini-adult-chicken-rice-800-g/dp/1656/
- https://siruk.am/product/monge-mini-adult-chicken-rice-800-g/dp/1657/
- https://siruk.am/product/monge-mini-adult-chicken-rice-800-g/dp/1658/
- https://siruk.am/product/monge-all-breeds-puppy-junior-lamb-rice-800-g/dp/1654/
- https://siruk.am/product/monge-all-breeds-puppy-junior-lamb-rice-800-g/dp/1655/
- https://siruk.am/product/acana-highest-protein-ranchlands-11-4-kg/dp/1359/
- https://siruk.am/product/acana-classics-wild-coast-9-7-kg/dp/1360/
- https://siruk.am/product/acana-classics-prairie-poultry-9-7-kg/dp/1361/
- https://siruk.am/product/acana-classics-red-meat-9-7-kg/dp/1362/
- https://siruk.am/product/acana-highest-protein-wild-prairie-11-4-kg/dp/1722/
- https://siruk.am/product/acana-light-and-fit-11-4-kg/dp/1723/
- https://siruk.am/product/orijen-six-fish-5-4-kg/dp/1363/
- https://siruk.am/product/acana-singles-yorkshire-pork-11-4-kg/dp/1364/
- https://siruk.am/product/acana-sport-and-agility-11-4-kg/dp/1724/
- https://siruk.am/product/acana-singles-grass-fed-lamb-11-4-kg/dp/1365/
- https://siruk.am/product/acana-puppy-small-breed-6-kg/dp/1366/
- https://siruk.am/product/acana-puppy-11-4-kg/dp/1725/
- https://siruk.am/product/acana-adult-small-breed-6-kg/dp/1367/
- https://siruk.am/product/acana-highest-protein-grasslands-11-4-kg/dp/1726/
- https://siruk.am/product/acana-highest-protein-pacifica-11-4-kg/dp/1727/
- https://siruk.am/product/acana-singles-free-run-duck-11-4-kg/dp/1368/
- https://siruk.am/product/monge-all-breeds-adult/dp/1643/
- https://siruk.am/product/monge-all-breeds-adult/dp/1645/
- https://siruk.am/product/monge-all-breeds-adult/dp/1647/
- https://siruk.am/product/monge-all-breeds-adult/dp/1649/
- https://siruk.am/product/monge-all-breeds-adult/dp/1651/
- https://siruk.am/product/monge-all-breeds-adult/dp/1653/
- https://siruk.am/product/monge-mini-puppy-junior/dp/1660/
- https://siruk.am/product/monge-mini-puppy-junior/dp/1662/
- https://siruk.am/product/monge-mini-puppy-junior/dp/1664/
- https://siruk.am/product/monge-mini-starter/dp/1666/
- https://siruk.am/product/monge-medium-puppy-junior/dp/1668/
- https://siruk.am/product/monge-maxi-puppy-junior/dp/1670/
- https://siruk.am/product/monge-maxi-adult/dp/1672/
- https://siruk.am/product/monge-bwild-low-grain-all-breeds-adult/dp/1674/
- https://siruk.am/product/monge-bwild-low-grain-all-breeds-adult/dp/1676/
- https://siruk.am/product/monge-bwild-low-grain-all-breeds-puppy-junior/dp/1678/
- https://siruk.am/product/monge-bwild-grain-free-all-breeds-adult/dp/1680/
- https://siruk.am/product/monge-hairball-cat/dp/1682/
- https://siruk.am/product/monge-indoor-cat/dp/1684/
- https://siruk.am/product/monge-kitten-cat/dp/1686/
- https://siruk.am/product/monge-sensitive-cat/dp/1688/
- https://siruk.am/product/monge-adult-cat/dp/1690/
- https://siruk.am/product/gemon-kitten-cat/dp/1692/
- https://siruk.am/product/gemon-adult-cat/dp/1694/
- https://siruk.am/product/gemon-mini-adult-dog/dp/1696/
- https://siruk.am/product/gemon-regular-adult-dog/dp/1698/
- https://siruk.am/product/simba-adult-dog-kibbles/dp/1700/
- https://siruk.am/product/simba-adult-dog-kibbles/dp/1702/
- https://siruk.am/product/club-4-paws-premium-sterilised-dry-cat-food/dp/1704/
- https://siruk.am/product/club-4-paws-premium-hairball-control-dry-cat-food/dp/1706/
- https://siruk.am/product/club-4-paws-premium-active-dry-dog-food/dp/1708/
- https://siruk.am/product/club-4-paws-premium-large-breeds-adult-dry-dog-food/dp/1710/
- https://siruk.am/product/club-4-paws-premium-medium-breeds-adult-dry-dog-food/dp/1712/
- https://siruk.am/product/club-4-paws-premium-small-breeds-adult-dry-dog-food/dp/1714/
- https://siruk.am/product/club-4-paws-premium-puppies-dry-dog-food/dp/1716/
- https://siruk.am/product/myau-kitten-dry-food/dp/1718/
- https://siruk.am/product/gemon-sterilised-cat/dp/1731/
- https://siruk.am/product/gemon-medium-adult-dog/dp/1733/
- https://siruk.am/product/gemon-medium-adult-dog/dp/1735/
- https://siruk.am/product/gemon-puppy-junior-dog/dp/1737/
- https://siruk.am/product/royal-canin-maxi-adult/dp/1943/
- https://siruk.am/product/royal-canin-maxi-adult-5/dp/1944/
- https://siruk.am/product/royal-canin-maxi-puppy/dp/1945/
- https://siruk.am/product/royal-canin-maxi-starter-mother-babydog/dp/1946/
- https://siruk.am/product/royal-canin-medium-adult/dp/1947/
- https://siruk.am/product/royal-canin-medium-puppy/dp/1948/
- https://siruk.am/product/royal-canin-mini-adult/dp/1949/
- https://siruk.am/product/royal-canin-mini-puppy/dp/1950/
- https://siruk.am/product/royal-canin-mini-adult-8/dp/1951/
- https://siruk.am/product/royal-canin-maxi-joint-care/dp/1952/
- https://siruk.am/product/royal-canin-mini-starter-mother-babydog/dp/1953/
- https://siruk.am/product/royal-canin-fit-32/dp/1954/
- https://siruk.am/product/royal-canin-kitten/dp/1955/
- https://siruk.am/product/royal-canin-sterilised-37/dp/1956/
- https://siruk.am/product/royal-canin-hairball-care/dp/1957/
- https://siruk.am/product/royal-canin-hypoallergenic-cat/dp/1958/
- https://siruk.am/product/royal-canin-urinary-s-o-cat/dp/1959/
- https://siruk.am/product/royal-canin-hypoallergenic-dog/dp/1960/
- https://siruk.am/product/royal-canin-gastrointestinal-dog/dp/1961/
- https://siruk.am/product/royal-canin-urinary-s-o-dog/dp/1962/
- https://siruk.am/product/royal-canin-renal-dog/dp/1963/
- https://siruk.am/product/royal-canin-hepatic-dog/dp/1964/
- https://siruk.am/product/royal-canin-gastrointestinal-puppy/dp/1965/
