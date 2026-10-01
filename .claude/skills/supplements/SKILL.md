---
name: supplements
description: Product-type spec for HEALTH & PHARMACY (vitamins, supplements, dewormers, dental care, ear/eye care, calming aids, medicated shampoos, first aid) — categories, product type, how to pick the Chewy-style values, net content per variant (count / ml / g), variant axes and pack pricing. Read by /add-products for every supplement / pharmacy row and by /manage-attributes when building the vocabulary.
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
· Test Kits 49/58. A product for both species goes in both leaves (the mirror
leaf in each tree — never a parent, which rolls its children up anyway).
**Cat has no dewormer leaf**, so a cat dewormer goes in 55 Pharmacy &
Prescriptions and a **dual-species dewormer is 46 + 55** (Inspector Quadro
Tabs 763–765, Gelmintal 779–780). A dog-only dewormer is just 46 — do **not**
also add 47, which holds only first-aid and SexControl.
Product type **4 Supplements** (`measure_type: volume`,
`default_sale_mode: pack` — but each variant picks its own measure, below).
**The live product type decides which attributes exist, their role (`option` /
`attribute`) and flags** — `reference/product-types.json`
(`scripts/product-types.py --dump`); it wins over this file. Read 2026-09-30:
`pet-weight-range`, `size` and `color-family` are `option`; food-form,
lifestage, health-feature, packaging, product-form, active-ingredient,
special-diet, flavor, breed-size, material are `attribute`. An attribute the
batch needs that the type lacks → the `attribute-manager` agent before the
import (CLAUDE.md 8b); a new value still needs an explicit ask (rule 8).

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

### Single-value consequence
Chewy's Special Diet, Health Feature and Ingredient are multi-tag; ours hold
one value each. Pick the claim the pack leads with (front-of-pack claim >
sub-line name > body text) and put the rest in `about_this_item` so it is at
least searchable. `ingredient` = the **first named ingredient** of the
composition (the headline protein), nothing else.

## Pack size — net content per variant (CLAUDE.md 8a; user, 2026-09-30)
The type says `volume`, but **each variant sends its own `measure_type`**:

| Pack | `measure_type` | `content` × `pack_count` |
|---|---|---|
| tablets, capsules, chews | `count` | `10 tablets` → `10 × 1`; `2 blisters × 10` → `10 × 2` |
| pipettes / spot-ons | `count` | `4 pipettes × 0.8 ml` → `4 × 1`; the ml per pipette stays in the label ("4–10 kg, 0.8 ml") |
| collars | `count` | `1 × 1`; the length (`75 cm`) is `size` 28, not content |
| liquids, drops, syrups, sprays | `volume` | ml, up to 3 decimals: `50 ml` → `50 × 1` |
| pastes, powders, gels | `mass` (or `volume` when the pack prints ml) | g as printed: `100 g` → `100 × 1` |

**Not** content: the dose band (`1–4 kg`, `over 16 kg` → `pet-weight-range`
27) or a collar length (`75 cm` → `size` 28). No `product-weight` attribute
any more (retired 2026-09-29).

## Variant axes
Net content and the type's options — and above all **the dose band**: "Quadro Drops for Dogs 1–4 kg / 4–10 kg / 10–25 kg /
40–60 kg" is ONE product with four variants on `pet-weight-range` 27 (the
axis created 2026-09-12; nine more bands added 2026-09-16, `up to 4 kg` …
`40–60 kg`). Same for "up to 10 kg / over 10 kg" syrups, tablets and spot-ons,
and for a flea collar's lengths (40 / 65 / 75 cm → `size` 28). What still
splits: species-specific packs the brand names separately ("for Female Cats"
vs "for Male Cats", "Spray for Dogs" vs "Spray for Cats") and a different
formulation ("Flea, Tick & Worm" vs "Flea & Tick"). The dose band stays in
the label ("4–10 kg, 0.8 ml") and on `pet-weight-range`, never in the content
(rule 8a). Once one variant carries an option, every variant needs it (rule 9a).
Flavour and product form (tablets vs powder of the same supplement) were
variant axes here before 2026-09-29, but the live type has `flavor` and
`product-form` as `attribute`, and spec-role values never tell variants apart.
A batch with such a line has the `attribute-manager` agent make that attribute
an `option` on the type first (CLAUDE.md 8b), then `product-types.py --check`.

## Pricing
`price` = hafo's row for that article code (the pack price), `cost_price` =
CSV price. One hafo lookup per variant.

## Sourcing note
Canvit (`canvit.com/en/`) is the main supplement brand; Rx / veterinary items
get the **Rx Required** flag. Never fabricate an active ingredient or dose.
