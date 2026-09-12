---
name: accessories
description: Product-type spec for Accessories — categories, attribute family, the attributes and values this type carries, its variant axes and pricing type. Read by /add-products for every Accessories row and by /manage-attributes when building the vocabulary. Use when importing, re-attributing or reviewing Accessories products.
---

# Accessories — product-type spec

**Status: template pre-filled from the live admin (2026-09-10). The user will
edit this to say which attributes and values Accessories should show (Chewy-style).
Until it is edited, the live family below is the spec.**

## Where it is filed

Cat litter → Cat → 59 Litter → leaf by type (60 Clumping, 61 Scented, 62 Unscented, 63 Natural, 64 Lightweight, 65 Crystal). Litter boxes, scoops, mats → Cat → 66 Supplies → 67 Litter Boxes & Accessories. Everything else → the **leaf** under Dog 68 Supplies / 75 Cleaning & Potty or Cat 66 Supplies / 80 Trees, Condos & Scratchers (created 2026-09-11 from the Chewy menu): 69 Collars, Leashes & Harnesses · 70 Bowls & Feeders · 71 Beds · 72 Clothing & Accessories · 73 Carriers & Travel · 74 Training & Behavior · 76 Pee Pads & Diapers · 77 Poop Bags & Scoopers · 78 Cleaners & Stain Removers · 79 Collars, Leashes & Harnesses (cat) · 81 Scratchers & Scratching Posts. **13 Accessories is NOT a product category** — `forProducts` omits it; a row landing there is a bug, not a fallback.

**Dual species → both trees.** `category_ids` is a list: a bowl, mat or collar the pack sells for dogs *and* cats goes in both leaves (e.g. 69 + 79). Never add a parent. See `reference/product-rules.md`.

## Attributes

Family **none yet** carries: none.
All picks from the closed menu `reference/attribute-values.json`, one value
per attribute per variant, with an evidence quote; empty beats a guess. Our
definitions in `reference/data-tables.md` beat the brand's wording.
Do not create values for this type without an explicit ask.

### Wanted (fill in — one line per attribute)

| Attribute | Values (or "from page, dedup synonyms") | Filter or variant axis? | Evidence rule |
|---|---|---|---|
| `size` (28) | letter sizes `XXS–XS` … `XL`; measurement strings (`0.45 l/ø 19 cm`, `9 × 15 cm`, `4 × 20 bags`) | **variant axis**, not filterable | the size/measurement the brand prints for that article |
| `color-family` (15) | the closed colour menu; map the brand's word (fuchsia → Pink, graphite → Grey, orchid → Purple, petrol → Teal, sand → Beige, curry → Yellow, chrome → Silver); a `x/y` colour takes the first | **variant axis** where the colour varies | the colour on the pack/page |
| `product-weight` (1) | volumes and pack weights (`5 l`, `11 l`, `175 ml`, `750 ml`) | filter | printed contents |
| `pet-weight-range` (27) | `0.5–2 kg` … `10–25 kg` | **variant axis** for antiparasitic drops/tablets | the dose band on the pack |

## Variant axes

**Size, colour, volume** — these override the food shelf test in
`reference/product-rules.md`, which splits on colour. One collar in six sizes
and five colours is ONE product with 30 options: that is how Trixie sells it,
and 131 duplicates created by the other reading were folded away on 2026-09-12
(`runs/2026-09-12/report.md`).

Keep the **full** measurement in the variant label ("XS–S, 22–35 cm/10 mm,
black") and put only the letter size on `size` — the label is what the shopper
reads, the attribute is what builds the selector. Every variant needs a value
on every axis the product uses, or the ones without it vanish from the dropdown
(`reference/admin-api.md`). Litter volumes stay on `product-weight` (5 l 190,
8 l 191, 11 l).

Before creating an accessory, check for siblings already in the catalogue:
`scripts/find-product.sh "<line name>"`, and `scripts/find-duplicate-products.py`
to sweep the whole catalogue.

## Pricing

`pricing_type: "fixed"`; litter sold by volume needs a real kg weight before `per_kg` (`reference/admin-api.md`). `price` = hafo's row for **that** article code, `cost_price` = CSV
price (`reference/pricing.md`). One hafo lookup per variant.

## Notes

Candidates for their own type later: Litter & Litter Boxes, Bowls & Feeders, Collars & Leashes, Beds, Carriers.
