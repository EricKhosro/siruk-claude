---
name: supplements
description: Product-type spec for HEALTH & PHARMACY (vitamins, supplements, dewormers, dental care, ear/eye care, calming aids, medicated shampoos, first aid) — categories, attribute family, the Chewy-style attributes and values, variant axes and pricing. Read by /add-products for every supplement / pharmacy row and by /manage-attributes when building the vocabulary.
---

# Health & Pharmacy — product-type spec

Chewy health & pharmacy filters (user decision 2026-09-10): **Food Form,
Product Form, Active Ingredient, Special Diet, Flavor, Health Feature,
Lifestage, Breed Size, Material**.

## Where it is filed
The **leaf** under Dog → 41 Health & Pharmacy or Cat → 50 Health & Pharmacy
(created 2026-09-10 from Chewy's menu): Flea & Tick 42/51 · Vitamins &
Supplements 43/52 · Probiotics & Digestive Health 44/53 · Allergy & Itch
Relief 45/54 · Heartworm & Dewormers 46 (dog only) · Pharmacy & Prescriptions
47/55 · Anxiety & Calming Care 48/56 · Urinary Tract & Kidneys 57 (cat only)
· Test Kits 49/58. A product for both species goes in both leaves. Family **4 Supplements**: food-form, product-weight,
lifestage, health-feature, packaging, product-form, active-ingredient,
special-diet, flavor, breed-size, material.

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
| `product-form` | Chewy's 35 (Liquid, Capsule, Soft Chew, Chew, Tablet, Powder, Shampoo, Chewable Tablet, Spray, Wipes, Solution, Gel, Paste, Cleanser, Ointment, Cream, Collar, Lotion, Foam, Softgel, Pellet, Granules, Rinse, Diffuser, Purée, Concentrate, Wafer, Block, Crumble, Pill, Topical…) | **the main attribute for this type** — the physical form on the pack ("tablets", "paste", "drops" → Liquid, "spray") |
| `active-ingredient` | Chewy's 107 (Calcium … Ivermectin) | the headline active on the pack ("with glucosamine", "omega-3", "taurine", "L-carnitine"); a multi-vitamin with no headline → Vitamins & Minerals in `health-feature` and leave this empty |
| `health-feature` | Chewy's 52 (incl. pharmacy: Anti-Parasitic, First Aid, Ear Mite Treatment, Milk Replacer, Paw Care, Pest Control, Tear Stain Removal, Sun Protection…) | the stated purpose |
| `food-form` | Treats, Dry Food, Wet Food, Sticks, Freeze-Dried, Frozen, Food Topping, Air-Dried, Dehydrated, Liquid, Dried Fruits, Shelf Stable… (+ our Paste, Powder, Tablets) | only for edible supplements that are food-like (a topper, a snack-form supplement); otherwise empty |
| `special-diet` | Chewy's 42 (incl. Medicated, Low Sugar, Sugar Free) | claim on the pack |
| `flavor` | Chewy's 61 | only if a flavour is named ("chicken flavour tablets") |
| `lifestage` | Nursing, Puppy, Kitten, Adult, Senior, All Lifestages | explicit claim ("for puppies", "senior") |
| `breed-size` | Chewy's 6 | weight-banded dewormers / spot-ons ("for dogs 10–25 kg" → the matching band via table 3 of data-tables.md; flag if unsure) |
| `material` | Chewy's 46 | only for non-consumables (pill dispenser, dental brush, collar) |
| `packaging` | Bottle, Tube, Box, Tub, Shaker, Pouch… | from the format |
| `product-weight` | pack size menu | the unit size (ml or g — volumes need a real weight before `per_kg`, which never applies here anyway) |

### Single-value consequence
Chewy's Special Diet, Health Feature and Ingredient are multi-tag; ours hold
one value each. Pick the claim the pack leads with (front-of-pack claim >
sub-line name > body text) and put the rest in `about_this_item` so it is at
least searchable. `ingredient` = the **first named ingredient** of the
composition (the headline protein), nothing else.

## Variant axes
Pack size, flavour, product form (tablets vs powder of the same supplement).
Breed-size / weight-band versions of a dewormer are **separate products**.

## Pricing
`pricing_type: "fixed"`, `price` = hafo's row for that article code,
`cost_price` = CSV price. One hafo lookup per variant.

## Sourcing note
Canvit (`canvit.com/en/`) is the main supplement brand; Rx / veterinary items
get the **Rx Required** flag. Never fabricate an active ingredient or dose.
