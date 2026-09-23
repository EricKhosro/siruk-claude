# Fixes to the final report — what was done (2026-09-23, afternoon)

Follow-up to `final-report-2026-09-23.md`. Everything below was written to the
demo admin and re-checked against the live site (snapshot re-read, register
audit re-run). The open list is rebuilt in `state/open-items.csv`: **262 items**,
down from 407.

## Before → after

| Check | Morning | Now |
|---|---|---|
| Register rows live on the site | 1,195 | **1,201** |
| Live prices differing from the register | 10 | **0** |
| Live variants priced at or below cost (rule 5) | 1 (Junior Clouds) | **0** |
| Per-kg problems (missing twin / wrongly per-kg) | 9 | **0** |
| Products with no attribute family (rule 8b) | 36 | **0** |
| Food products with no image at all | 7 | **0** |
| "First image not a clean packshot" | 42 | **8** |
| Variant axis attribute missing (rule 9a) | 12 | 8 (on 5 products — no source has the value) |
| Other missing attributes | 7 | **0** |
| Register rows with no article code | 125 | **103** |
| Held register prices (for the PM) | 72 | 72 — needs you |

## What was fixed

**Prices.** The 8 Trixie cat-treat prices written onto the wrong neighbour on
2026-09-16 now carry their own register price (Junior Clouds 650 → 1,200, no
longer below cost). Acana Light & Fit and Sport & Agility 11.4 kg: 45,000 →
50,000.

**Per-kg.** Nine packs were sold by the kilo although the register sells them
by the pack: 8 Acana bags and the Simple'n'Clean 5 l litter. All nine are now
fixed-price at the register price. The six Acana 11.4 kg dog bags got their
per-kg twin at the register's rate: Wild Prairie 6,600/kg, Light & Fit and
Sport & Agility 4,500, Puppy 4,000, Grasslands 5,400, Pacifica 5,050.

**Attribute families.** All 36 products have one now: 21 Accessories,
14 Grooming, and the Matatabi spray as Toys. `set-attribute-family.py` gained
the missing Toys rule, so it won't come back.

**Imported: the 6 rows that were ready.** hafo stores their codes with a space
inside (`MM 005617`, `BP 12960`), and `hafo-lookup.py` couldn't find them that
way. It now also searches the number on its own.

| New product | Variants | Photo from |
|---|---|---|
| 1181 Gemon Sterilised Cat | Beef 7 kg + 1 kg (2,900/kg) | monge.it (official) |
| 1182 Gemon Medium Adult Dog | Lamb & Rice 20 kg, Tuna & Rice 20 kg + both 1 kg (1,750/kg) | zoovet.am (confirmed: lamb label readable; tuna by name, price and per-kg rate) |
| 1183 Gemon Puppy & Junior Dog | Chicken & Rice 20 kg + 1 kg (1,800/kg) | nemo.am, **watermarked — placeholder** |
| 1179 Beaphar Duo Active Paste for Dogs | 100 g | beaphar.cz (article-keyed) |
| 1180 Beaphar Duo Active Paste for Cats | 100 g | beaphar.cz (article-keyed) |

All five have their family, attributes and register prices, with ru and hy
translations verified by `verify-translations.py` (0 missing). The English
text came from the brand site where it had some. Otherwise it was translated
from the shop page it was confirmed on: the Gemon 20 kg bags from zoovet and
nemo, the Beaphar pastes from the Czech site.

**Images.**
- 4lapy.ru, by barcode: the Monge Sensitive and Indoor cat 10 kg bags.
- club4paws.com: Club 4 Paws Premium Active and Large Breeds 14 kg. The photos
  were already researched on 2026-09-16, but the upload had failed.
- beaphar.cz: the Stop It cat spray (12527) and the No Stress collar (13228)
  replaced hafo's watermarked placeholder.
- zoovet.am: Myau Rabbit & Turkey Ragout replaced its placeholder.
- No real photo exists anywhere for Monge Adult and Kitten cat 10 kg or Myau
  Kitten 11 kg. They now carry hafo's watermarked photo as a placeholder
  (rule 7: never an empty gallery) and stay on the list.
- Rejected on inspection: 4lapy's Monge Adult photo (the 1.5 kg bag, not our
  10 kg one), zoovet's Myau rabbit pouch (100 g, ours is 85 g) and zoovet's
  Gran Bonta can (a different line).

**The 42 "confirm by eye".** I looked at every first image. 34 are clean
product shots already. The Slow Feeding Bowl now leads with the product
instead of a dog eating. The 8 still open are listed below.

**Attributes.**
- Poop Bags and Rolls: the missing size, taken from their own labels.
- Malt Bits Original: flavour Malt.
- Gift Soft Sticks Cod: its label was literally the SKU `08527MG`. It's now
  "15 g" with a product weight (3 sticks / 15 g per the register).
- Mini Drops: dose band 0.5–2 kg.
- Flea, Tick & Worm Collar: 75 cm.
- The four Matatabi Lollies: 11, 13.5, 20 and 23 cm.
- New values created, each with ru/hy, read back with 0 mismatches:
  size `6 pcs./70 g`, `11 cm`, `13.5 cm`, `20 cm`, `23 cm`; flavour `Malt`.

**Codeless register rows.** `identify-by-name.py` now also searches nemo.am
and zoovet.am. Re-run over all 124 rows, it found **22 exact matches**: hafo's
row name is identical to the register's and the cost is equal to the dram.
Their codes are in `match-overrides.json` and logged in
`identified-by-name.csv`. Every weaker hit was rejected because one axis
differed (a collar colour, a bone count, a flavour, a pack size).

## What is still open, and why

1. **72 held register prices.** 69 have the sale price equal to cost, and
   3 look like typos: Monge Solo pork 150 g at 9,600, Trixie cat collar 4207
   at 3,600, stainless bowl 0.75 l at 9,400. Only you or the PM can decide
   these.
2. **39 rows with a known code, not imported yet.** 22 of them were
   identified today: a cat spot-on (074322), a bio collar (10665), 3 dog
   supplement tablets (IN10863, IN10937, IN12429), a catnip treat (12623),
   2 chew items (10778S, 10250S), 6 DL treats, a chicken treat (14612S),
   4 dog biscuits (504026–504056), a chew bone (12207S), a flexi Neon lead
   (FX023508) and a calcium paste (077412). The other 17 are the older
   blocks: 9 priced at cost in the register, 2 brands with no website
   (Dogman, Inteko), 5 with no brand page and 1 typo price. Next step:
   `/add-products` on these rows. Their brands still need confirming from
   hafo.
3. **103 rows with no article code.** Each line in `open-items.csv` names the
   best candidate found. They need a hand check (rule 6).
4. **9 Trixie variants with no image at all**: Tennis Ball, Grooming Glove,
   3 BE NORDIC bowls, 4 Premium Adjustable Lead colours. Nothing keyed to
   these articles exists on Trixie's sites, the approved shops, hafo or a web
   search. They need photos taken in the shop.
5. **23 variants whose only photo is a watermarked placeholder**: the Myau,
   Mooor, KorMell and Justin pouches, Gran Bonta Chef, Stop It Indoor, one
   lead colour, and today's Monge/Myau/Gemon placeholders.
6. **8 first images that aren't clean packshots.** Six Iv San Bernard bottles
   have only the brand's group shot, one lead has only an in-use photo, and
   the bowl has only a group of sizes.
7. **8 variants missing an axis value no source gives.** Playing Rope ×3,
   Comb, Litter Scoop S and Plastic Bowl lack a colour; Quadro Drops
   1–4 / 4–10 kg lack a volume.
8. One old attribute value, product-weight `Less than 1 KG`, has no ru/hy
   translation.
9. Six live variants aren't in the register, so they're on the site but not
   in stock: `register-extras.csv`.

## Tooling changed today

- `hafo-lookup.py`: finds codes hafo stores with a space or no-break space.
- `4lapy-lookup.py --scan <brand>` reads every page of a brand once and caches
  barcode → offer, so `--ean` needs no network afterwards.
- `set-attribute-family.py`: new rule, toy leaves → Toys.
- `state/carried-items.json`: open items only an eye can judge, which the
  worklist rebuild keeps.
