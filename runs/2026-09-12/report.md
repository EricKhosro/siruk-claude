# Duplicate products folded into their real parent products — 2026-09-12

**131 duplicate products removed.** 197 catalogue entries that were really options of one product are now 66 products with 207 variants between them.

The trigger: sibling rows imported as separate products — `.../trixie-active-comfort-leather-collar-with-rhinestones-s-m-27-33-cm-15-mm-pink/dp/1108/` and `.../xxs-xs-17-21-cm-12-mm-pink/dp/1107/` were two products where Trixie sells one collar in two sizes.

## How a group was decided

Three signals, the first two authoritative in both directions — they merge AND they split:

| Signal | What it is | Why it is trusted |
|---|---|---|
| trixie.de | the article codes sit on the same official product page | Trixie's own variant table for that product |
| trixie.shop | the article codes are options of the same Shopify product | Trixie's own store, and it reaches discontinued lines |
| name | identical product name once the variant label is stripped, same brand, same categories | only where no official signal contradicts it |

The splitting half did real work: it kept the **three different Stainless Steel Bowl lines** apart (24851–55 heavy weight, 25071–74 non-slip, 25271–73 varnished), the **six Soft Brush lines**, and `Dog Socks XL/black` (19526), which is a different Trixie product from the grey 19500–19503 set.

## Two merges the cross-check threw out

- **Premium Adjustable Lead, XS–S: 2.00 m/15 mm, light lilac** (803, article 200720) — the name matched the 201301–201316 leads exactly, but trixie.shop puts every 2007xx article on *Premium Verlängerungsleine **doppellagig***, the double-layered lead. Left as its own product.
- **"Animals, latex, 13 cm"** (423, article 35263) — grouped with 35031/35061 by name, but trixiecz calls 35263 *Geometrické zvíře, plněný latex* while 35031/35061 are the *Longie* line. Left as its own product; the other two were merged and renamed **Longie, latex/polyester fleece**, which is what Trixie actually calls them.

## The variant axis

The storefront builds its variant selector from **attributes**, not from the variant label — checked live on product 874, whose second variant had no `flavor` and was unreachable: the selector rendered one option. So every merged product needed an axis whose value differs per variant.

Two attributes were created (approved beforehand) and four extended:

| Attribute | | New values | Filterable |
|---|---|---|---|
| `size` **28** | new — letter sizes `XXS–XS`…`XL` for collars, harnesses, leads and apparel; measurement strings (`0.45 l/ø 19 cm`, `9 × 15 cm`, `4 × 20 bags`) for bowls, brushes and packs | 59 | no — the value set is mixed on purpose, same call as `toy-size` |
| `pet-weight-range` **27** | new — the dose band printed on antiparasitic drops and tablets | 7 | yes |
| `color-family` 15 | existing — fuchsia → Pink, graphite → Grey, orchid → Purple, petrol → Teal, sand → Beige, curry → Yellow, chrome → Silver | 0 | yes |
| `flavor` 5 | Veal, Trout, Meat and Chicken and Vegetables — flavours earlier imports left blank because the value did not exist, which is what hid them | 4 | yes |
| `product-weight` 1 | 11 l, 120 g, 175 ml, 200 g, 750 ml | 5 | yes |
| `toy-size` 16 | 30–32 cm, 37 cm | 2 | no (unchanged) |

The full measurement stays in the variant label — the shopper still reads "XS–S, 22–35 cm/10 mm, black" on the page; only the letter size rides on `size`, so the vocabulary stays usable.

All 19 attributes, 713 values and 5 family names read back clean in en/ru/hy (`scripts/translate-attributes.py`: 0 mismatches).

## What changed per brand

| Brand | Duplicate products removed |
|---|---|
| Trixie | 113 |
| Monge | 9 |
| Inspector | 4 |
| Insectal | 3 |
| Club 4 Paws | 1 |
| Ok-Lock | 1 |

## The merged products

| Product | Variants | Axis | Absorbed |
|---|---|---|---|
| [Trixie Premium Collar](https://demo.siruk.am/product/trixie-premium-collar/dp/1137/) | 22 | `size`, `color-family` | 21 |
| [Monge Fresh Adult Dog](https://demo.siruk.am/product/monge-fresh-adult-dog/dp/789/) | 6 | flavour / weight already on the variants | 2 |
| [Club 4 Paws Premium Adult Cat](https://demo.siruk.am/product/club-4-paws-premium-adult-cat/dp/879/) | 6 | flavour / weight already on the variants | 1 |
| [Trixie Stainless Steel Bowl, heavy weight](https://demo.siruk.am/product/trixie-stainless-steel-bowl-heavy-weight/dp/971/) | 5 | `size` | 4 |
| [Monge Fresh Adult Dog Paté](https://demo.siruk.am/product/monge-fresh-adult-dog-pat/dp/862/) | 5 | flavour / weight already on the variants | 1 |
| [Trixie Knot with Chicken](https://demo.siruk.am/product/trixie-knot-with-chicken/dp/625/) | 4 | `size` | 3 |
| [Monge Gran Bonta Adult Dog](https://demo.siruk.am/product/monge-gran-bonta-adult-dog/dp/796/) | 4 | flavour / weight already on the variants | 3 |
| [Trixie Premium Adjustable Lead](https://demo.siruk.am/product/trixie-premium-adjustable-lead/dp/961/) | 4 | `color-family` | 3 |
| [Trixie Stainless Steel Bowl with Rubber Base](https://demo.siruk.am/product/trixie-stainless-steel-bowl-with-rubber-base/dp/985/) | 4 | `size` | 3 |
| [Trixie Poisoned Bait Protection](https://demo.siruk.am/product/trixie-poisoned-bait-protection/dp/1012/) | 4 | `size` | 3 |
| [Trixie Dog Socks](https://demo.siruk.am/product/trixie-dog-socks/dp/1016/) | 4 | `size` | 3 |
| [Trixie Premium Reflect Collar](https://demo.siruk.am/product/trixie-premium-reflect-collar/dp/1072/) | 4 | `size` | 3 |
| [Trixie Greased Leather Collar Rustic](https://demo.siruk.am/product/trixie-greased-leather-collar-rustic/dp/1101/) | 4 | `size` | 3 |
| [Trixie Premium Trekking Harness](https://demo.siruk.am/product/trixie-premium-trekking-harness/dp/1124/) | 4 | `size`, `color-family` | 3 |
| [Trixie Y-Harness](https://demo.siruk.am/product/trixie-y-harness/dp/1131/) | 4 | `size`, `color-family` | 3 |
| [Trixie Playing Rope](https://demo.siruk.am/product/trixie-playing-rope/dp/511/) | 3 | `toy-size` | 2 |
| [Trixie Litter Scoop for Ultra Litter](https://demo.siruk.am/product/trixie-litter-scoop-for-ultra-litter/dp/539/) | 3 | `size` | 2 |
| [Trixie Soft Brush, bamboo](https://demo.siruk.am/product/trixie-soft-brush-bamboo/dp/557/) | 3 | `size` | 2 |
| [Trixie Soft Brush, rubber handle](https://demo.siruk.am/product/trixie-soft-brush-rubber-handle/dp/598/) | 3 | `size` | 2 |
| [Trixie Bone with Chicken](https://demo.siruk.am/product/trixie-bone-with-chicken/dp/635/) | 3 | `size` | 2 |
| [Monge Grill Sterilised Cat](https://demo.siruk.am/product/monge-grill-sterilised-cat/dp/748/) | 3 | flavour / weight already on the variants | 2 |
| [Inspector Quadro Tabs for Cats and Dogs](https://demo.siruk.am/product/inspector-quadro-tabs-for-cats-and-dogs/dp/919/) | 3 | `pet-weight-range` | 2 |
| [Insectal Combo Drops for Dogs](https://demo.siruk.am/product/insectal-combo-drops-for-dogs/dp/943/) | 3 | `pet-weight-range` | 2 |
| [Trixie BE NORDIC Bandana Collar](https://demo.siruk.am/product/trixie-be-nordic-bandana-collar/dp/956/) | 3 | `size`, `color-family` | 2 |
| [Trixie Stainless Steel Bowl, non-slip](https://demo.siruk.am/product/trixie-stainless-steel-bowl-non-slip/dp/982/) | 3 | `size` | 2 |
| [Trixie Stainless Steel Bowl with Paw Prints and Rubber Base](https://demo.siruk.am/product/trixie-stainless-steel-bowl-with-paw-prints-and-rubber-base/dp/995/) | 3 | `size` | 2 |
| [Trixie Stainless Steel Bowl, varnished](https://demo.siruk.am/product/trixie-stainless-steel-bowl-varnished/dp/1001/) | 3 | `size` | 2 |
| [Trixie Diapers for Male Dogs](https://demo.siruk.am/product/trixie-diapers-for-male-dogs/dp/1067/) | 3 | `size` | 2 |
| [Trixie Flash Light Collar, nylon](https://demo.siruk.am/product/trixie-flash-light-collar-nylon/dp/1083/) | 3 | `size` | 2 |
| [Trixie Chain Lead with Neoprene Hand Loop](https://demo.siruk.am/product/trixie-chain-lead-with-neoprene-hand-loop/dp/1089/) | 3 | `size`, `color-family` | 2 |
| [Trixie Comfort Soft Harness](https://demo.siruk.am/product/trixie-comfort-soft-harness/dp/1092/) | 3 | `size`, `color-family` | 2 |
| [Trixie Greased Leather Collar Rustic Heartbeat](https://demo.siruk.am/product/trixie-greased-leather-collar-rustic-heartbeat/dp/1099/) | 3 | `size`, `color-family` | 2 |
| [Trixie Active Comfort Leather Collar with Rhinestones](https://demo.siruk.am/product/trixie-active-comfort-leather-collar-with-rhinestones/dp/1106/) | 3 | `size`, `color-family` | 2 |
| [Trixie Soft Rope Lead](https://demo.siruk.am/product/trixie-soft-rope-lead/dp/1115/) | 3 | `size`, `color-family` | 2 |
| [Trixie Semi-Choke Collar with Nylon Chain](https://demo.siruk.am/product/trixie-semi-choke-collar-with-nylon-chain/dp/1170/) | 3 | `size`, `color-family` | 2 |
| [Trixie Premium Touring Harness](https://demo.siruk.am/product/trixie-premium-touring-harness/dp/1174/) | 3 | `size`, `color-family` | 2 |
| [Trixie Longie, latex/polyester fleece](https://demo.siruk.am/product/trixie-longie-latex-polyester-fleece/dp/527/) | 2 | `toy-size` | 1 |
| [Trixie Scoop for Feed or Litter](https://demo.siruk.am/product/trixie-scoop-for-feed-or-litter/dp/537/) | 2 | `size` | 1 |
| [Trixie Brush, wood, natural bristles](https://demo.siruk.am/product/trixie-brush-wood-natural-bristles/dp/569/) | 2 | `size` | 1 |
| [Trixie Soft Brush with Brush Cleaner, wooden handle](https://demo.siruk.am/product/trixie-soft-brush-with-brush-cleaner-wooden-handle/dp/577/) | 2 | `size` | 1 |
| [Trixie Rolls with Chicken](https://demo.siruk.am/product/trixie-rolls-with-chicken/dp/629/) | 2 | `size` | 1 |
| [Trixie Rolls with Duck](https://demo.siruk.am/product/trixie-rolls-with-duck/dp/638/) | 2 | `size` | 1 |
| [Trixie Simple'n'Clean Deodorising Spray](https://demo.siruk.am/product/trixie-simplenclean-deodorising-spray/dp/703/) | 2 | `product-weight` | 1 |
| [Trixie Bathrobe](https://demo.siruk.am/product/trixie-bathrobe/dp/716/) | 2 | `size` | 1 |
| [Trixie Toothpaste](https://demo.siruk.am/product/trixie-toothpaste/dp/718/) | 2 | `flavor` | 1 |
| [Monge Gran Bonta Chef Adult Dog](https://demo.siruk.am/product/monge-gran-bonta-chef-adult-dog/dp/800/) | 2 | flavour / weight already on the variants | 1 |
| [Inspector Quadro Drops for Cats](https://demo.siruk.am/product/inspector-quadro-drops-for-cats/dp/912/) | 2 | `pet-weight-range` | 1 |
| [Inspector Quadro Drops for Dogs](https://demo.siruk.am/product/inspector-quadro-drops-for-dogs/dp/914/) | 2 | `pet-weight-range` | 1 |
| [Insectal Combo Drops for Cats](https://demo.siruk.am/product/insectal-combo-drops-for-cats/dp/941/) | 2 | `pet-weight-range` | 1 |
| [Ok-Lock SMART Clumping Plant-Based Cat Litter](https://demo.siruk.am/product/ok-lock-smart-clumping-plant-based-cat-litter/dp/952/) | 2 | `product-weight` | 1 |
| [Trixie Slow Feeding Plastic Bowl](https://demo.siruk.am/product/trixie-slow-feeding-plastic-bowl/dp/979/) | 2 | `size` | 1 |
| [Trixie Melamine Bowl with Rubber Base](https://demo.siruk.am/product/trixie-melamine-bowl-with-rubber-base/dp/989/) | 2 | `size` | 1 |
| [Trixie Bowl, enamel/stainless steel](https://demo.siruk.am/product/trixie-bowl-enamel-stainless-steel/dp/992/) | 2 | `size` | 1 |
| [Trixie I.D. Tag](https://demo.siruk.am/product/trixie-i-d-tag/dp/1004/) | 2 | `color-family` | 1 |
| [Trixie Dog Poop Bags with Scent](https://demo.siruk.am/product/trixie-dog-poop-bags-with-scent/dp/1021/) | 2 | `size`, `color-family` | 1 |
| [Trixie Dog Poop Bags](https://demo.siruk.am/product/trixie-dog-poop-bags/dp/1022/) | 2 | `size` | 1 |
| [Trixie Protective Pants, mesh](https://demo.siruk.am/product/trixie-protective-pants-mesh/dp/1041/) | 2 | `size` | 1 |
| [Trixie Pads for Protective Pants](https://demo.siruk.am/product/trixie-pads-for-protective-pants/dp/1049/) | 2 | `size` | 1 |
| [Trixie Hygiene Pad Nappy](https://demo.siruk.am/product/trixie-hygiene-pad-nappy/dp/1062/) | 2 | `size` | 1 |
| [Trixie Diapers for Female Dogs](https://demo.siruk.am/product/trixie-diapers-for-female-dogs/dp/1065/) | 2 | `size` | 1 |
| [Trixie Silver Reflect Collar](https://demo.siruk.am/product/trixie-silver-reflect-collar/dp/1078/) | 2 | `size` | 1 |
| [Trixie Easy Flash USB Light Collar, silicone](https://demo.siruk.am/product/trixie-easy-flash-usb-light-collar-silicone/dp/1087/) | 2 | `color-family` | 1 |
| [Trixie BE NORDIC Leather Collar with Metal Buckle](https://demo.siruk.am/product/trixie-be-nordic-leather-collar-with-metal-buckle/dp/1095/) | 2 | `size` | 1 |
| [Trixie CityStyle Collar](https://demo.siruk.am/product/trixie-citystyle-collar/dp/1110/) | 2 | `size` | 1 |
| [Trixie Premium Semi-Choke Collar](https://demo.siruk.am/product/trixie-premium-semi-choke-collar/dp/1168/) | 2 | `color-family` | 1 |
| [Trixie Chain Collar, chrome-plated](https://demo.siruk.am/product/trixie-chain-collar-chrome-plated/dp/1178/) | 2 | `size` | 1 |

## Verified after the merge

| Check | Result |
|---|---|
| every sku still on the shelf | 207/207 — none lost |
| price, cost, stock, image count, `about_this_item` per sku | identical to the pre-merge backup on all 207 |
| catalogue size | 834 → 703 products |
| re-scan (`find-duplicate-products.py --refresh`) | 0 groups left; the one hand-split product listed with its evidence |
| ru/hy on the 66 merged products | complete (`verify-translations.py`) |
| the two products in the request | `/dp/1107` and `/dp/1108` are now [one collar](https://demo.siruk.am/product/trixie-active-comfort-leather-collar-with-rhinestones/dp/1286/) with a Size and a Color Family selector |

## Fixed along the way

**Product 874, Gemon All Breeds Adult Dog Chunks** — not a duplicate, but the same defect: its second variant (`387967`, Veal, Liver & Vegetables) carried no `flavor`, so the Flavor selector offered only Salmon and that variant could not be bought. It now has `flavor: Veal`. It was the only product in the catalogue whose *axis* had a hole; the rest of the holes found are on `ingredient`, which is informational.

**A trap worth knowing** — `scripts/set-translation.py` writes *every* variant, so a sku left out of the translation file gets the English text written into that locale. Translating one variant of product 1016 wiped the Armenian texts of its other two; both are restored, and the warning is now in `reference/admin-api.md` and the script guide.

## Still open

- **The category grid still draws one card per variant** — that is the storefront's own rule, not the data (`reference/product-rules.md`: "Category listing shows one card per variant; `/api/search` one per product"). What changed is that the cards now read as options of one product and all land on the same page: "Active Comfort Leather Collar with Rhinestones, Pink, XXS–XS" and "…, Pink, S–M" instead of two separately-named products. Collapsing the grid to one card per product is a frontend change; say the word and I will write it up for the dev team.
- **`size` is not filterable.** Its values mix letter sizes with measurement strings, so a sidebar facet would read badly — same call as `toy-size`. If you want collars filterable by size, the fix is to split the measurement strings onto their own attribute, not to flip the flag.
- Three products remain English-only in ru/hy from earlier imports, untouched here: 906 Towel with Pockets, 346 Junior Soft Snack Dots, 350 Soft Snack Bony Mix XXL. (MOT®-Fun, Longie, Turbinio and Twists are Latin brand names by policy.)
- The detection only has an authoritative second opinion for **Trixie**. Monge, Inspector, Insectal, Club 4 Paws and Ok-Lock groups rest on the name plus consecutive article codes within one line; each was read by hand, but a brand-site index for them would make the next sweep as strong as Trixie's.

## Links

- `runs/2026-09-12/variant-id-map.csv` — every old `/dp/<id>` and the id it became (207 rows).
- `runs/2026-09-12/merge-backup/` — the full pre-merge record of all 197 products in en/ru/hy.
- `runs/2026-09-12/merge-plan.json` — what was decided, per group and per variant.
