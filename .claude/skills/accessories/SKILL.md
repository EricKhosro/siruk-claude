---
name: accessories
description: Product-type spec for Accessories — categories, attribute family, the attributes and values this type carries, its variant axes and pricing type. Read by /add-products for every Accessories row and by /manage-attributes when building the vocabulary. Use when importing, re-attributing or reviewing Accessories products.
---

# Accessories — product-type spec

**Status: template pre-filled from the live admin (2026-09-10). The user will
edit this to say which attributes and values Accessories should show (Chewy-style).
Until it is edited, the live family below is the spec.**

## Where it is filed

Cat litter → Cat → 59 Litter → leaf by type (60 Clumping, 61 Scented, 62 Unscented, 63 Natural, 64 Lightweight, 65 Crystal). Litter boxes, scoops, mats → Cat → 66 Supplies → 67 Litter Boxes & Accessories. Everything else → 13 Accessories (flat, fallback) until the Supplies tree grows (Chewy: Beds, Bowls & Feeders, Collars/Leashes/Harnesses, Carriers & Travel, Crates, Clothing…).

## Attributes

Family **none yet** carries: none.
All picks from the closed menu `reference/attribute-values.json`, one value
per attribute per variant, with an evidence quote; empty beats a guess. Our
definitions in `reference/data-tables.md` beat the brand's wording.
Do not create values for this type without an explicit ask.

### Wanted (fill in — one line per attribute)

| Attribute | Values (or "from page, dedup synonyms") | Filter or variant axis? | Evidence rule |
|---|---|---|---|
| | | | |

## Variant axes

Size, colour, volume (litter 5 l / 8 l via `product-weight` 190/191).

## Pricing

`pricing_type: "fixed"`; litter sold by volume needs a real kg weight before `per_kg` (`reference/admin-api.md`). `price` = hafo's row for **that** article code, `cost_price` = CSV
price (`reference/pricing.md`). One hafo lookup per variant.

## Notes

Candidates for their own type later: Litter & Litter Boxes, Bowls & Feeders, Collars & Leashes, Beds, Carriers.
