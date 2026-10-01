---
name: dry-food
description: Product-type spec for DRY FOOD (kibble, dry complete food) — categories, product type, how to pick the Chewy-style values a dry-food product carries, its net content (mass) and pack pricing. Read by /add-products for every dry-food row and by /manage-attributes when building the vocabulary.
---

# Dry Food — product-type spec

Chewy food filters (user decision 2026-09-10): **Special Diet, Health Feature,
Flavor, Ingredient, Packaging Type**, plus Lifestage and Breed Size.

## Where it is filed
Dog → **3 Dry Food** (a veterinary diet also → 5 Health Condition); Cat → **10
Dry Food**. Bird / small-animal food (96 / 99) uses this type too. Product type
**1 Dry Food** (`measure_type: mass`, `default_sale_mode: pack`).

**The live product type decides which attributes exist, their role (`option` /
`attribute`) and flags** — `reference/product-types.json`
(`scripts/product-types.py --dump`); it wins over this file. Read 2026-09-30:
`flavor` is the only `option`; breed-size, lifestage, special-diet,
health-feature, packaging, ingredient are `attribute` (specs / filters). An
attribute the batch needs that the type lacks → the `attribute-manager` agent
before the import (CLAUDE.md 8b); a new **value** still needs an explicit ask
(rule 8).

## Attributes
All picks from the closed menu `reference/attribute-values.json` (full lists in
`reference/chewy-attributes.json`), **one value per attribute per variant**
(every attribute here is `select`; only a `multiselect` attribute-role one may
hold more) — with an evidence quote from the brand page or the CSV row. Empty
beats a guess. Our definitions in `reference/data-tables.md` (lifestage bands,
texture words) beat the brand's wording. Do not create values for this type
without an explicit ask. Skipped on purpose from Chewy: Made
In, Deals & Savings.

| Attribute | Values | How to fill |
|---|---|---|
| `lifestage` | Nursing, Puppy, Kitten, Adult, Senior, All Lifestages | from the line name / age band (table 1 of data-tables.md) |
| `breed-size` | Extra Small … Giant, All Breeds | from the line name ("Mini", "Maxi", "Medium") via table 3 of data-tables.md |
| `special-diet` | Chewy's 42 (+ our Hypoallergenic, Monoprotein, Sterilised) | the front-of-pack claim: "grain free" → Grain-Free, "sterilised" → Sterilised, "veterinary" → Veterinary Diet, "light" → Weight Control, "hypoallergenic" → Hypoallergenic, "monoprotein / single protein" → Monoprotein |
| `health-feature` | Chewy's 52 | the stated benefit: "urinary" → Urinary Tract Health, "digestion" → Digestive Health, "skin & coat" → Skin & Coat Health, "hairball" → Hairball Control, "joint" → Hip & Joint Support, "dental" → Dental & Breath Care |
| `flavor` | Chewy's 61 (+ our extras: Herring, Fish, Seabass…) | the named protein/flavour in the product name |
| `ingredient` | Chewy's 69 | first ingredient of the composition |
| `packaging` | Bag, Box, … Variety Pack | almost always **Bag** |

### Single-value consequence
Chewy's Special Diet, Health Feature and Ingredient are multi-tag; ours hold
one value each. Pick the claim the pack leads with (front-of-pack claim >
sub-line name > body text) and put the rest in `about_this_item` so it is at
least searchable. `ingredient` = the **first named ingredient** of the
composition (the headline protein), nothing else.

## Pack size — net content, not an attribute (CLAUDE.md 8a)
Every bag is a `pack` variant with `measure_type: "mass"`, `content` in grams
(`1.5 kg` → `1500`, `800 g` → `800`) and `pack_count: 1`; a case of bags
(`6X1,5KG` on a vendor sheet) is still priced per retail bag → `content 1500`,
`pack_count 1`. The server builds the label and the ֏/kg rate. There is no
`product-weight` attribute any more (retired 2026-09-29).

## Variant axes
Net content and flavour (the type's option). Lifestage, breed size, special
diet and health feature **split products** (`reference/product-rules.md`). A
flavour variant must carry `flavor`, and once one variant of a product has it,
every variant needs it (rule 9a — `siruk_payload.py` refuses otherwise).

The flavour never goes in the product Name (it is the label + `flavor`);
"BWild Adult Cat Hare 1.5 kg" is acceptable only while the product has one
variant — a second flavour or pack renames it to the line ("BWild Adult Cat")
and moves the flavour/weight into the labels.

## Pricing
`price` = hafo's sale price for **that bag** (the pack price), `cost_price` =
CSV price; the per-kg rate is computed by the server — never send a rate or a
weight (`pricing_type` / `price_per_kg` / `weight` are gone, 2026-09-29). One
hafo lookup per variant (`reference/pricing.md`).
Loose sale (user rule 2026-09-30): a per-kg sale price (the register's `Kg` column, a price list's `Վաճառքի Գին կիլոգրամով`) adds a **by-weight variant** next to the bag: `sale_mode: "weight"`, `price` = the per-kg price, **`qty_min` 1 kg and `qty_step` 1 kg** (`1000` g each — user rule 2026-10-01: customers buy loose food in whole kilograms), no measure/content/pack_count, `cost_price` = bag cost ÷ bag kg, `initial_stock` in **grams** (placeholder 10 kg = 10000), SKU `<bag sku>-KG`, same attributes, texts and photos as the bag. The backend gives every weight variant the same size key, so a product gets one by-weight variant per option combination (per flavour/texture), not one per bag size. The 61 older `-KG` twins are 1 kg pack variants from before this rule — leave them unless asked. For wet food a small per-unit price (750 next to a 12 × 85 g pack) is not per kg (it is below cost per kg) but the price of one pouch → a 1 × 85 g pack variant.
