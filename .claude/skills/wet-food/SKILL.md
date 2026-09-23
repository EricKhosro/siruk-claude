---
name: wet-food
description: Product-type spec for WET FOOD (cans, pouches, trays, multipacks) — categories, attribute family, the Chewy-style attributes and values a wet-food product carries, its variant axes and fixed pricing. Read by /add-products for every wet-food row and by /manage-attributes when building the vocabulary.
---

# Wet Food — product-type spec

Chewy food filters (user decision 2026-09-10): **Special Diet, Health Feature,
Flavor, Ingredient, Packaging Type**, plus Lifestage and our Food Texture.

## Where it is filed
Dog → **4 Wet Food** (veterinary also → 5); Cat → **11 Wet Food**. Family
**2 Wet Food**: product-weight, flavor, lifestage, texture, special-diet,
health-feature, packaging, ingredient.

## Attributes
All picks from the closed menu `reference/attribute-values.json` (full lists in
`reference/chewy-attributes.json`), **one value per attribute per variant** —
the API rejects arrays (verified 2026-09-10) — with an evidence quote from the
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
| `product-weight` | pack weight menu (85 g, 100 g, 400 g…) | **always.** The **unit** weight, never the case (`12X85G` = twelve separately-sized cans → 85 g). A single tray/can prints its own weight (`415 g`, `1250 g`) |

### Single-value consequence
Chewy's Special Diet, Health Feature and Ingredient are multi-tag; ours hold
one value each. Pick the claim the pack leads with (front-of-pack claim >
sub-line name > body text) and put the rest in `about_this_item` so it is at
least searchable. `ingredient` = the **first named ingredient** of the
composition (the headline protein), nothing else.

## Variant axes
Pack weight, flavour and texture. A flavour or texture variant must carry that
attribute or the API rejects the second variant.

**Flavour and texture never go in the product Name**, and a brand giving each
flavour its own page is not a split signal. Packaging (85 g pouch vs 400 g can
vs 100 g tray) does split products here — the pack art changes — which is why
"Fresh Adult Dog" (cans) and "Fresh Adult Dog Paté" (trays) stay apart. Before
creating: find the line product and add the row as a variant; rename a
single-variant product whose Name carries the flavour (rule 9, CLAUDE.md).

## Pricing
`pricing_type: "fixed"`, `price` = hafo's row for that article code (one retail
unit), `cost_price` = CSV price. One hafo lookup per variant.
