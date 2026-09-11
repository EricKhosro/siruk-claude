---
name: treats
description: Product-type spec for TREATS (snacks, chews, dental sticks, training treats) — categories, attribute family, the Chewy-style attributes and values a treat carries, its variant axes and fixed pricing. Read by /add-products for every treat row and by /manage-attributes when building the vocabulary.
---

# Treats — product-type spec

Chewy treat filters (user decision 2026-09-10): **Flavor, Ingredient, Special
Diet, Breed Size, Health Feature, Lifestage, Packaging Type**.

## Where it is filed
Dog → **6 Treat**, or **7 Dog Bones, Bully Sticks & Chews** for natural chews /
bones / bully sticks; Cat → **14 Treat**. Family **3 Treats**: product-weight,
flavor, lifestage, special-diet, health-feature, breed-size, packaging,
ingredient.

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
| `flavor` | Chewy's 61 (incl. treat flavours: Cranberry, Smoked, Blueberry, Strawberry, Ginger, Mint, Vanilla, Honey, Cinnamon, Carob, Hickory, Ostrich…) | the named flavour/protein in the product name |
| `ingredient` | Chewy's 69 (incl. Bananas, Butternut Squash, Chia Seeds, Coconut Flour, Gelatin, Glycerin, Oat Flour, Oats, Pumpkin Puree…) | first ingredient of the composition |
| `special-diet` | Chewy's 42 (Grain-Free, Rawhide-Free, Sugar Free, Odor-Free, Low Phosphorus, Low Sodium…) | front-of-pack claim |
| `breed-size` | Chewy's 6 | only on a stated size ("for small dogs", "S/M/L" on dental sticks) |
| `health-feature` | Chewy's 52 | "dental" → Dental & Breath Care; "digestion" → Digestive Health; "calming" → Calming |
| `lifestage` | Puppy, Kitten, Adult, Senior, All Lifestages | explicit claim only ("puppy treats") |
| `packaging` | Bag, Pouch, Box, Tub, Tube, Can, Tray, Roll, Cup, Bottle, Shaker | from the format |
| `product-weight` | pack weight menu | the unit weight |

### Single-value consequence
Chewy's Special Diet, Health Feature and Ingredient are multi-tag; ours hold
one value each. Pick the claim the pack leads with (front-of-pack claim >
sub-line name > body text) and put the rest in `about_this_item` so it is at
least searchable. `ingredient` = the **first named ingredient** of the
composition (the headline protein), nothing else.

## Variant axes
Pack weight and flavour (a dental stick in S / M / L is a **breed-size split**,
not a variant — separate products, per the shelf test).

## Pricing
`pricing_type: "fixed"`, `price` = hafo's row for that article code,
`cost_price` = CSV price. One hafo lookup per variant.
