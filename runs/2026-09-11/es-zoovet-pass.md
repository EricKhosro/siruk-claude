# Re-run of the two worklists against trixie.es and zoovet.am — 2026-09-11

Both new sources (CLAUDE.md rules 2b / 7b, `reference/zoovet.md`, the country-TLD
section of `reference/brand-sites.md`) were run over the worklists this run left
behind: `needs-image.csv` (42 variants carrying watermarked hafo placeholders)
and `no-hafo-price.csv` (178 rows hafo could not price).

## 1. Images — 18 of 42 galleries replaced

Every hafo placeholder on these variants was **removed** and replaced with the
brand's own photos (rule 7a attaches a hafo picture only when nothing else has
one). 41 + 14 media references re-verified, 0 broken; every feature image was
looked at before and after the write.

| SKU | Product | Source | Images | Source name |
|---|---|---|---|---|
| 33445 | 413 | trixie.es `33445` | 6 | Ring, TPR, floatable, ø 17 cm |
| 34722 | 415 | trixie.es `34722` | 2 | Hippo |
| 35031 | 420 | trixie.es `3503` | 3 | 4 Longies, latex, 18 cm |
| 35041 | 421 | trixie.es `3504` | 6 | 12 faces, latex, ø 6 cm |
| 35263 | 423 | trixie.es `35263` | 6 | Animal, latex, 13 cm, sorted |
| 35821 | 426 | trixie.es `3582` | 2 | 4 toy figures with rope, plush, 17 cm |
| 33505 | 441 | trixie.es `33505` | 3 | Dog Disc, TPR, ø 18 cm |
| 35061 | 446 | trixie.es `3506` | 4 | 4 Longies, latex, 30–32 cm |
| 23026 | 453 | trixie.es `23026` | 3 | Long hair coat untangler, bamboo/metal, 10 × 17 cm |
| 2356 | 472 | trixie.es `2356` | 3 | Soft brush, 6 × 13 cm |
| 2900 | 574 | trixie.es `2900` | 1 | Herbal shampoo, 250 ml |
| 29411 | 590 | trixie.es `29411` | 1 | Dry foam shampoo (ref row: 450 ml) |
| 42424 | 598 | trixie.es `42424` | 1 | Matatabi play spray |
| 00265 | 331 | trixie.es `31501` | 2 | Denta Fun Chew Bites, 150 g |
| 24183 | 500 | zoovet.am | 4 | Расчёска-триммер зеленая для собак, 6 x 15 см |
| 34870 | 418 | zoovet.am | 2 | Игрушка Be Eco, пластиковый мяч на веревке, 6 x 13 см |
| 34871 | 419 | zoovet.am | 5 | Игрушка Be Eco, пластиковый попрыгунчик, 9 x 16 см |
| 32814 | 406 | zoovet.am | 1 | Игрушка цветной веревочный мяч для собак, 9 см |

How each was confirmed:

- **trixie.es** — the page's own `ref` row carries our article and the spec cell
  matches the invoice (33445 → `medidas: ø 11 cm`, 29411 → `capacidad: 450 ml`,
  2356 → `11 × 14 cm`), and every file taken carries the article in its name.
- **Four rows matched a trailing-1 vendor code** (35031→3503, 35041→3504,
  35821→3582, 35061→3506): each confirmed against the Armenian invoice line —
  size and type identical (18 cm latex animals, ø 6 cm animal balls, 17 cm plush
  with rope, 30–32 cm latex animals) — and 3504 is "ball animal" in trixie.de's
  own catalogue.
- **00265** is Trixie article **31501**: the invoice line ends "- 31501" and the
  pack in the photo prints `#31501`.
- **zoovet.am** — brand + type + every stated dimension match (24183: green
  trimmer comb 6 × 15 cm; 34870/34871: the Be Eco line, 6 × 13 and 9 × 16 cm),
  and the photos are the brands' own, unwatermarked.

Two things worth your eye:

- **Product 472 is mis-named.** The Armenian "Սանր նիկել կոմպլեկս 11 x 14 սմ"
  was read as "Comb Set, nickel-plated" but article 2356 is a **soft/slicker
  brush with a wooden handle and a cleaning comb** (trixie.es: "Soft brush";
  the photo shows exactly that). **Renamed 2026-09-11** to *Soft Brush with
  Comb, nickel-plated, 11 × 14 cm* (slug
  `trixie-soft-brush-with-comb-nickel-plated-11-14-cm`), with the ru/hy names
  rewritten to match: «Мягкая щётка с расчёской, никелированная, 11 × 14 см» /
  «Փափուկ խոզանակ սանրով, նիկելապատ, 11 × 14 սմ».
- **32814** (Rope Ball, ø 9 cm) was matched on brand + type + size only — there
  is no article number anywhere on zoovet and none printed on a rope ball. The
  photo is a knotted rope ball of that size; swap it if you know otherwise.

Also caught while doing this: the trixie.es files `PHO_PRO_CLIP_31501-1/-2` are
named for our article but show the **other** Chew Bites flavour (blue lamb pack,
pale bites). They were dropped; product 331 keeps the green parsley & peppermint
pack and its bites. The trap is now written into `reference/brand-sites.md`.

**24 variants still carry hafo placeholders** (`needs-image.csv`) — 20 Trixie
and the 4 Monge Gran Bonta rows. All were checked against trixie.de + its CDN,
trixie.es and zoovet.am. Three of them (31667, 36154, 24183 → now fixed) have a
trixie.es page that confirms the article but carries no photo keyed to it.

## 2. Prices — 5 of 178 rows priced from zoovet (11 after the approval round below)

`runs/2026-09-11/zoovet-priced.csv` — confirmed, ready to import:

| Article | Product | Cost | zoovet price | How it was confirmed |
|---|---|---|---|---|
| 25622Tx | Trixie 3-head toothbrush, 18 cm | 810 | **1250** | zoovet's only 3-head toothbrush; trixie.es confirms 25622 is 18 cm |
| 25061Tx | Trixie melamine bowl 0.4 l / 17 cm, white | 3625 | **4950** | every zoovet spec matches: 400 ml, 17 cm, melamine + rubber, Цвет Белый |
| 073252 | Inspector collar 75 cm | 3835 | **5750** | Inspector's only 75 cm collar; the box photo reads "длина 75 см" |
| 072022 | Rolf Club cat spray 200 ml | 3785 | **5550** | Rolf Club's only 200 ml cat spray; photo is that bottle |
| 387947 | Gemon Maxi Adult 32–80 kg, pork, 1.25 kg | 1300 | **1750** | same line, breed band, pack and flavour; zoovet's only 1.25 kg Gemon with pork |

All five beat cost. They are **priced, not imported** — each still needs the
normal pipeline (name, gallery, attributes, categories, translations), and
Inspector and Rolf Club would need `/create-brand` first.

`runs/2026-09-11/zoovet-candidates.csv` — 8 rows where zoovet has something
close but not provably the same article. They need a yes from you:

- **387957, 387967** (Gemon 1.25 kg, salmon/veg and veal-liver/veg) — those
  flavours are not on zoovet, but every 1.25 kg Gemon dog can there is 1750 and
  both rows share the confirmed 387947's cost of 1300. This is the sibling rule
  with a zoovet price instead of a hafo one, which the rules do not cover.
- **300657** (Gemon Sterilised pouch 100 g, chicken/turkey) — zoovet's 100 g
  Gemon pouches are 450–480; this flavour is not listed.
- **41592Tx** (cat collar with bell) — zoovet's is 1600 but states no colour or
  size.
- **31846Tx** (Premio pate liver/hemp 75 g, dog) — zoovet's Premio 75 g pate at
  1750 is the **cat** poultry one.
- **25257Tx** — identity conflict, do not price: trixie.es says article 25257 is
  the white/blue silicone steel bowl 1,4 l / ø 21 cm, the invoice says "with
  paws", and zoovet's 1.4 l / 21 cm bowl is the grey paws-and-bone one (its url
  even says 1.5 l).
- **40187Tx** (Classic tray 37 × 15 × 48, purple/white) — zoovet's same-size
  tray is the grey **Carlo** model: different line and colour.
- **22858Tx** (waste-bag dispenser, 20 bags) — zoovet has five dispensers from
  1200 to 3250 and the invoice line does not say which.

### Why only 5

zoovet's assortment barely overlaps what hafo could not price. The unpriced list
is 161 Trixie rows that are mostly **collars, harnesses and leads** — the
Premium adjustable nylon line in seven sizes × ten colours, CityStyle, BE NORDIC
leather. zoovet's Trixie range is 339 products, of which the collar/leash shelf
is 27 items: BE NORDIC wide, USB light-up, neoprene-padded, Fusion and Premium
leashes, cotton rope leads. It stocks **no harness at all**, none of the
Premium nylon collar sizes, no Berto litter box, no litter scoops, no dog
nappies, no 150 g Gemon pates and no 85 g Club 4 Paws jellies. Toys, bowls and
grooming were checked item by item; the five above are everything that matched.

The remaining 173 rows keep an empty `Sale Price (AMD)` in
`no-hafo-price.csv`, and each row's `Why no price` now records that zoovet was
checked (and names the candidate where there was one).

## Approval round — 2026-09-11, later the same day

The user approved the candidate list. Six rows took their proposed price and
moved into `zoovet-priced.csv` (11 rows priced from zoovet in total):

| Article | Cost → price | Note |
|---|---|---|
| 387957 Gemon salmon & veg 1.25 kg | 1300 → 1750 | flavour not on zoovet; price from same-line, same-pack, same-cost siblings |
| 387967 Gemon veal-liver & veg 1.25 kg | 1300 → 1750 | as above |
| 300657 Gemon Sterilised pouch 100 g | 340 → 450 | our flavour not listed; zoovet's Sterilised 100 g pouch is 450 |
| 41592Tx cat collar with bell | 1000 → 1600 | zoovet states no colour or size; its reflective bell collar (950) is below our cost |
| 31846Tx Premio pate 75 g, dog | 1435 → 1750 | **approved over the flag** — zoovet's 75 g Premio pate is the cat/poultry one |
| 40187Tx Classic tray 37 × 15 × 48 | 2905 → 5000 | **approved over the flag** — zoovet's same-size tray is the grey Carlo model |

Two were **withdrawn before applying**, because trixie.es settled the article
identity and the zoovet item turned out to be a different product — a price
from those would be a "similar product" price, which rule 2 forbids:

- **25257Tx** — ref 25257 on trixie.es is *Stainless steel bowl with silicone,
  1,4 l/ø 21 cm, white/blue* (siblings 25255 = 0,4 l/ø 14 cm, 25256 = 0,75 l/ø
  17 cm). zoovet's 1.4 l bowl is the grey paws-and-bone one. Also resolves the
  invoice wording: "ռետինապատ թաթիկներով" is the rubber-coated base, not paw
  prints, so the invoice and trixie.es agree after all.
- **22858Tx** — ref 22858 is *Poop bag dispenser, canvas w. artificial leather,
  1 × 20 bags*. zoovet's five dispensers are neoprene, nylon-with-belt,
  hard-case-with-zip, plastic-with-carabiner and nylon. None is ours.

167 rows remain unpriced.

## 3. Import of the priced rows — 2026-09-11

Ten of the eleven went in; each was identified from the manufacturer's own
data before anything was written.

| Article | Product | Where it went | Price (cost) |
|---|---|---|---|
| 25622Tx | **868** 3-headed Toothbrush, 18 cm | Dog → Grooming → Grooming Tools (30) | 1250 (810) |
| 41592Tx | **869** Batik Collar with Bell, purple/blue | Cat → Supplies → Collars, Leashes & Harnesses (79) | 1600 (1000) |
| 40187Tx | **870** Classic Litter Tray, 37 × 15 × 47 cm, purple/white | Cat → Supplies → Litter Boxes & Accessories (67) | 5000 (2905) |
| 31846Tx | **871** Liver Pâté with Hemp, 75 g | Dog → Treat (6), family Treats | 1750 (1435) |
| 25061Tx | **872** Melamine Bowl with Stainless Steel Insert, 0.4 l / ø 17 cm, white | Dog → Supplies → Bowls & Feeders (70) | 4950 (3625) |
| 387957 | **874** All Breeds Adult Dog Chunks — Salmon & Vegetables 1250 g | Dog → Wet Food (4), family Wet Food | 1750 (1300) |
| 387967 | **874** — Veal, Liver & Vegetables 1250 g | same product, second variant | 1750 (1300) |
| 387947 | **682** Maxi Adult Dog Chunks — Pork & Rice 1250 g | variant added to the existing product | 1750 (1300) |
| 072022 | **875** 3D Spray for Cats, 200 ml | Cat → Health & Pharmacy → Flea & Tick (51) | 5550 (3785) |
| 073252 | **877** Flea, Tick & Worm Collar for Large Dogs, 75 cm | Dog → Health & Pharmacy → Flea & Tick (42) | 5750 (3835) |

All ten carry official photos (20 media, 0 broken on `verify-media.sh`),
English bullets/composition where the source had them, and ru + hy names and
texts. Stock 10 (the Qty=1 placeholder rule).

Identity, per row:

- **25622 / 41592 / 31846** — live pages on trixie.de (3-headed toothbrush,
  collar, Liver Pâté with hemp); galleries from the CDN.
- **41592** also confirmed on trixiecz.cz: `Kód 41592`, "Barva: fialová, modrá"
  — the invoice's blue and purple exactly. (Its EAN 4011905692784 does **not**
  encode the article; Trixie EANs only sometimes do.)
- **40187** — trixiecz.cz `Kód 40187`, EAN 4011905401874, "Classic toaleta …
  37 × 15 × **47** cm fialová/bílá"; the invoice's "48" is wrong, so the tray
  is named 47 cm like its mint-green sibling (product 328).
- **387947 / 387957 / 387967** — monge.it, joined on the EAN in the image file
  name: the vendor code is the **EAN core + 7** (8009470387941 → 387947), a rule
  that holds on twelve other Gemon codes already in the catalogue. Names,
  composition, analytical constituents and feeding text are the manufacturer's.
- **25061** — the only row with no manufacturer page anywhere (not on
  trixie.de, .es, trixiecz or trixie.shop). Named descriptively from the zoovet
  spec rows, which match the invoice on every field, with zoovet's photo.
- **072022** — neoterica.ru, images keyed `R421_*` = the code the invoice
  prints. **073252** — neoterica's page for the 75 cm collar (its photos are
  hash-named, so identity rests on the page being the only 75 cm Inspector
  collar, which the zoovet box shot corroborates).

Three things done along the way, each backed by the manufacturer:

- **682 renamed** "Maxi Adult Dog Paté Beef & Rice 1250 g" → **"Maxi Adult Dog
  Chunks"**: it now holds two flavours, so the flavour leaves the name (product
  rules), and monge.it calls the line *Chunks*, not *Paté*. ru/hy updated.
- **877** was created with `FORCE=1`: the duplicate guard flagged product 741,
  which is the *Rolf Club* 3D collar 75 cm — same size, different brand.
- **387967** carries no `flavor` value: the menu has no *Veal*, and the earlier
  run left the same field empty on product 679. Wanted vocabulary from this
  batch: **Veal** (flavor), **75 g** and **1250 g** (product-weight).

### Held back: 300657

Gemon Adult Sterilised pouch 100 g, chicken & turkey — approved at 450, not
imported. monge.it's chicken & turkey Sterilised Chunkies 100 g is article
**300647** (EAN 8009470300643), and no 30065x exists in the catalogue; since
the vendor code is the EAN core + 7, our 300657 would be a different article.
Confirm whether the invoice code is a typo for 300647 and it goes in at 450.

### Colour note

The official photo for **40187** (and the Czech distributor's copy of it) shows
a **blue-grey/white** tray, while both the invoice and the Czech page title say
purple/white. The photo is article-keyed, so it was attached; if what arrived is
purple, that gallery needs a new picture.
