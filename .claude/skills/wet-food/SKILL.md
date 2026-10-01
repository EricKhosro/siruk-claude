---
name: wet-food
description: Product-type spec for WET FOOD (cans, pouches, trays, multipacks) — categories, product type, how to pick the Chewy-style values a wet-food product carries, its net content (mass, multipacks as pack_count × content) and pack pricing. Read by /add-products for every wet-food row and by /manage-attributes when building the vocabulary.
---

# Wet Food — product-type spec

Chewy food filters (user decision 2026-09-10): **Special Diet, Health Feature,
Flavor, Ingredient, Packaging Type**, plus Lifestage and our Food Texture.

## Where it is filed
Dog → **4 Wet Food** (veterinary also → 5); Cat → **11 Wet Food**. Product
type **2 Wet Food** (`measure_type: mass`, `default_sale_mode: pack`).

**The live product type decides which attributes exist, their role (`option` /
`attribute`) and flags** — `reference/product-types.json`
(`scripts/product-types.py --dump`); it wins over this file. Read 2026-09-30:
`flavor`, `texture` and `packaging` are `option`; lifestage, special-diet,
health-feature, ingredient, breed-size are `attribute`. An
attribute the batch needs that the type lacks → the `attribute-manager` agent
before the import (CLAUDE.md 8b); a new **value** still needs an explicit ask
(rule 8).

## Attributes
All picks from the closed menu `reference/attribute-values.json` (full lists in
`reference/chewy-attributes.json`), **one value per attribute per variant**
(every attribute here is `select`) — with an evidence quote from the
brand page or the CSV row. Empty beats a guess. Our definitions in
`reference/data-tables.md` (lifestage bands, texture words) beat the brand's
wording. Do not create values for this type without an explicit ask.
Skipped on purpose from Chewy: Made In, Deals & Savings.

| Attribute | Values | How to fill |
|---|---|---|
| `lifestage` | Nursing, Puppy, Kitten, Adult, Senior, All Lifestages | from the line/age band (table 1 of data-tables.md) |
| `special-diet` | Chewy's 42 (+ Hypoallergenic, Monoprotein, Sterilised) | front-of-pack claim, as for dry food |
| `health-feature` | Chewy's 52 | stated benefit |
| `flavor` | Chewy's 61 + our extras | the named protein in the product name; "chicken & eggs" → our `Chicken and Eggs` |
| `texture` | Broth, Chunks in Gravy, Chunks in Jelly, Fillets, Minced, Mousse, Mousse & Shreds, Pate, Shredded, Stew | from the pack wording ("in gravy", "in jelly", "paté", "mousse"); vendor-string words in `reference/csv-formats.md` |
| `ingredient` | Chewy's 69 | first ingredient of the composition |
| `packaging` | Can, Pouch, Tray, Cup, Tub, Box, Variety Pack… | from the format: pouch / can / tray; a multipack of one flavour keeps its unit packaging, a mixed box → Variety Pack |

### Single-value consequence
Chewy's Special Diet, Health Feature and Ingredient are multi-tag; ours hold
one value each. Pick the claim the pack leads with (front-of-pack claim >
sub-line name > body text) and put the rest in `about_this_item` so it is at
least searchable. `ingredient` = the **first named ingredient** of the
composition (the headline protein), nothing else.

## Pack size — net content, not an attribute (CLAUDE.md 8a)
`measure_type: "mass"`, `content` = grams of **one** can/pouch/tray,
`pack_count` = how many in the pack we sell: a single 85 g pouch → `content
85, pack_count 1`; a 415 g / 1250 g tray → its own weight, `pack_count 1`; a
multipack sold as one unit ("12 × 85 g", `1X12X80G` variety box) → `content 85
/ 80, pack_count 12`. A vendor case of single cans (`12X85G` with a per-can
price) is still one can → `pack_count 1` (`reference/csv-formats.md`). The
server builds the label ("12 × 85 g") and the rate. No `product-weight`
attribute any more (retired 2026-09-29).

## Variant axes
Net content, flavour and texture (plus `packaging`, which the live type also
makes an option). Once one variant of a product carries an option, every
variant needs it (rule 9a); no two variants may share options + size.

**Flavour and texture never go in the product Name**, and a brand giving each
flavour its own page is not a split signal. Packaging (85 g pouch vs 400 g can
vs 100 g tray) does split products here — the pack art changes — which is why
"Fresh Adult Dog" (cans) and "Fresh Adult Dog Paté" (trays) stay apart.
OPEN: the live type makes `packaging` an `option` (a selector axis), which
contradicts this split rule; until the user decides, keep splitting and set
the one `packaging` value on every variant. Before
creating: find the line product and add the row as a variant; rename a
single-variant product whose Name carries the flavour (rule 9, CLAUDE.md).

## Pricing
`price` = hafo's row for that article code — the price of the pack we sell
(one retail unit, a multipack's whole price), `cost_price` = CSV price. The
server computes the rate. One hafo lookup per variant (`reference/pricing.md`).
