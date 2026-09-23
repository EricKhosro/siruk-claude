---
name: dry-food
description: Product-type spec for DRY FOOD (kibble, dry complete food) — categories, attribute family, the Chewy-style attributes and values a dry-food product carries, its variant axes and per-kg pricing. Read by /add-products for every dry-food row and by /manage-attributes when building the vocabulary.
---

# Dry Food — product-type spec

Chewy food filters (user decision 2026-09-10): **Special Diet, Health Feature,
Flavor, Ingredient, Packaging Type**, plus Lifestage and Breed Size.

## Where it is filed
Dog → **3 Dry Food** (a veterinary diet also → 5 Health Condition); Cat → **10
Dry Food**. Family **1 Dry Food**: product-weight, flavor, breed-size, lifestage,
special-diet, health-feature, packaging, ingredient.

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
| `lifestage` | Nursing, Puppy, Kitten, Adult, Senior, All Lifestages | from the line name / age band (table 1 of data-tables.md) |
| `breed-size` | Extra Small … Giant, All Breeds | from the line name ("Mini", "Maxi", "Medium") via table 3 of data-tables.md |
| `special-diet` | Chewy's 42 (+ our Hypoallergenic, Monoprotein, Sterilised) | the front-of-pack claim: "grain free" → Grain-Free, "sterilised" → Sterilised, "veterinary" → Veterinary Diet, "light" → Weight Control, "hypoallergenic" → Hypoallergenic, "monoprotein / single protein" → Monoprotein |
| `health-feature` | Chewy's 52 | the stated benefit: "urinary" → Urinary Tract Health, "digestion" → Digestive Health, "skin & coat" → Skin & Coat Health, "hairball" → Hairball Control, "joint" → Hip & Joint Support, "dental" → Dental & Breath Care |
| `flavor` | Chewy's 61 (+ our extras: Herring, Fish, Seabass…) | the named protein/flavour in the product name |
| `ingredient` | Chewy's 69 | first ingredient of the composition |
| `packaging` | Bag, Box, … Variety Pack | almost always **Bag** |
| `product-weight` | pack weight menu | **always** — including `per_kg` variants (rule reversed 2026-09-14). The numeric `weight` field prices the bag; this attribute is what the storefront filter and the pack-size dropdown read |

### Single-value consequence
Chewy's Special Diet, Health Feature and Ingredient are multi-tag; ours hold
one value each. Pick the claim the pack leads with (front-of-pack claim >
sub-line name > body text) and put the rest in `about_this_item` so it is at
least searchable. `ingredient` = the **first named ingredient** of the
composition (the headline protein), nothing else.

## Variant axes
Pack weight and flavour. Lifestage, breed size, special diet and health feature
**split products** (`reference/product-rules.md`). A flavour variant must carry
`flavor`.

The flavour never goes in the product Name (it is the label + `flavor`);
"BWild Adult Cat Hare 1.5 kg" is acceptable only while the product has one
variant — a second flavour or pack renames it to the line ("BWild Adult Cat")
and moves the flavour/weight into the labels. The register's `Kg` column adds a
per-kilo twin variant (`scripts/make-perkg-twin.py`, `weight: 1`).

## Pricing
`pricing_type: "per_kg"`: `price_per_kg` = hafo sale price ÷ pack kg (2
decimals), `weight` in kg; `price` is ignored by the API. `cost_price` = CSV
price. One hafo lookup per variant (`reference/pricing.md`).
