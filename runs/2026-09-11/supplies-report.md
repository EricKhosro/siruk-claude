# 2026-09-11 — unblocking the 208 "no product category" rows

Input: `runs/2026-09-11/blocked-no-category.csv` (208 rows). Every one was
blocked for the same reason — 13 Accessories is not a product category and the
tree had no Supplies / Cleaning & Potty / Scratchers branch. Fixed by creating
the missing leaves from Chewy's own Dog and Cat menus.

## Categories created (14, `scripts/create-category.py`)

| id | path | slug |
|---|---|---|
| 68 | Dog › Supplies | `dog-supplies` |
| 69 | Dog › Supplies › Collars, Leashes & Harnesses | `dog-supplies-collars-leashes-harnesses` |
| 70 | Dog › Supplies › Bowls & Feeders | `dog-supplies-bowls-feeders` |
| 71 | Dog › Supplies › Beds | `dog-supplies-beds` |
| 72 | Dog › Supplies › Clothing & Accessories | `dog-supplies-clothing-accessories` |
| 73 | Dog › Supplies › Carriers & Travel | `dog-supplies-carriers-travel` |
| 74 | Dog › Supplies › Training & Behavior | `dog-supplies-training-behavior` |
| 75 | Dog › Cleaning & Potty | `dog-cleaning-potty` |
| 76 | Dog › Cleaning & Potty › Pee Pads & Diapers | `dog-cleaning-pee-pads-diapers` |
| 77 | Dog › Cleaning & Potty › Poop Bags & Scoopers | `dog-cleaning-poop-bags-scoopers` |
| 78 | Dog › Cleaning & Potty › Cleaners & Stain Removers | `dog-cleaning-cleaners-stain-removers` |
| 79 | Cat › Supplies › Collars, Leashes & Harnesses | `cat-supplies-collars-leashes-harnesses` |
| 80 | Cat › Trees, Condos & Scratchers | `cat-trees-condos-scratchers` |
| 81 | Cat › Trees, Condos & Scratchers › Scratchers & Scratching Posts | `cat-trees-scratchers-posts` |

All 14 carry ru + hy names (`scripts/translate-categories.py`, verified —
"problems: none"). Spec kept at `runs/2026-09-11/new-categories.json`.

Only the leaves these rows fill were created. Chewy's remaining empty ones —
Dog Crates/Pens & Gates, Dog Tech & Smart Home, Vacuums & Steam Cleaners, Cat
Tech/Beds/Carriers/Bowls, Trees & Condos, Wall Shelves, Window Perches — were
deliberately left out (user call: no empty categories on the storefront).

## Where the 208 rows went

Classification used each row's trixie.de productworld shelf, with name
overrides where Trixie's shelf and Chewy's disagree (muzzles, dog socks,
cooling mats, car seat covers, place mats). `scripts/_recat-blocked-2026-09-11.py`.

| destination | rows |
|---|---|
| 69 Dog Collars, Leashes & Harnesses | 107 |
| 70 Dog Bowls & Feeders | 43 |
| 76 Dog Pee Pads & Diapers | 14 |
| 77 Dog Poop Bags & Scoopers | 9 |
| 79 Cat Collars, Leashes & Harnesses | 7 |
| 78 Dog Cleaners & Stain Removers | 6 + 1 Mr. Fresh |
| 72 Dog Clothing & Accessories | 5 |
| 74 Dog Training & Behavior | 4 + 2 Mr. Fresh |
| 81 Cat Scratchers & Scratching Posts | 2 |
| 71 Dog Beds | 2 |
| 73 Dog Carriers & Travel | 1 |
| 30 Dog Grooming Tools *(already existed)* | 1 |
| 67 Cat Litter Boxes & Accessories *(already existed)* | 4 Mr. Fresh |

0 rows unclassified.

Judgement calls worth knowing:
- **Muzzles** (Poisoned Bait Protection) → Training & Behavior, not Clothing.
- **Lint rollers / textile brushes** → Cleaners & Stain Removers (Trixie files
  them under "textile cleaning"; Chewy has no closer leaf).
- **ID tags** → Collars, Leashes & Harnesses (Chewy's own placement).
- **Cat behaviour and odour sprays → 67 Litter Boxes & Accessories** (user
  call). Chewy's Cat menu has no Cleaning or Training node; the Dog side has
  both, so the same four products would sit in different-looking places if we
  mirrored Dog. Worth revisiting if a Cat › Cleaning branch is ever wanted.

## Mr. Fresh — the 7 sprays

Brand 27 already existed (no logo yet — `/create-brand` never ran for it).
Identity confirmed by hand, per rule 6: neoterica.ru carries no article code
for this line, so each hafo code was matched to its neoterica page by pack
artwork (read off the hafo photo) and, for 076412, by the barcode printed on
the back label — `4607092 07641 6` against article `07641 2`.

Prices are all hafo `price_source: "variant"`, each beating its cost:

| code | product | pack | cost | sale | category |
|---|---|---|---|---|---|
| 075732 | Expert Stain & Odour Eliminator 3-in-1 for Cats & Ferrets | 500 ml | 1965 | 3150 | 67 |
| 075762 | Expert Stain & Odour Eliminator 3-in-1 for Dogs | 500 ml | 1965 | 3150 | 78 |
| 076412 | Expert Anti-Soiling Spray for Cats | 200 ml | 1960 | 3140 | 67 |
| 076472 | Expert Anti-Chewing Spray for Dogs | 200 ml | 1685 | 2700 | 74 |
| 076482 | Expert Anti-Scratching Spray for Cats | 200 ml | 1685 | 2700 | 67 |
| 076492 | Expert Anti-Soiling Spray for Dogs | 200 ml | 1960 | 3140 | 74 |
| 076502 | Expert Litter Training Spray for Cats | 200 ml | 1685 | 2700 | 67 |

Images: both neoterica.ru shots per product (front packshot first, back label
second) — unwatermarked brand-site photos, so **no hafo placeholders** and
nothing for `needs-image.csv`. Descriptions, active ingredients and directions
are translated from the brand page; ru + hy for all 7 names and all 20 text
strings were added to `reference/translations.json` before the run.

Qty is blank in the CSV for all 7, so stock 10 (the standing placeholder).

## Open questions

- **13 Accessories** is now genuinely redundant — it holds nothing and cannot
  hold products. Delete it, or keep the empty node? (Not touched.)
- **Mr. Fresh has no logo.** Run `/create-brand "Mr. Fresh"` to attach one.
- Cat sprays in 67 (see above) — revisit if a Cat › Cleaning branch is wanted.
