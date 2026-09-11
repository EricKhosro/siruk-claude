---
name: grooming
description: Product-type spec for Grooming — categories, attribute family, the attributes and values this type carries, its variant axes and pricing type. Read by /add-products for every Grooming row and by /manage-attributes when building the vocabulary. Use when importing, re-attributing or reviewing Grooming products.
---

# Grooming — product-type spec

**Status: template pre-filled from the live admin (2026-09-10). The user will
edit this to say which attributes and values Grooming should show (Chewy-style).
Until it is edited, the live family below is the spec.**

## Where it is filed

Dog → 27 Grooming → {28 Brushes & Combs, 29 Shampoos & Conditioners, 30 Grooming Tools, 31 Paw & Nail Care, 32 Ear Care, 33 Skin Care}; Cat → 34 Grooming → {35 Brushes & Combs, 36 Shampoos & Conditioners, 37 Grooming Tools, 38 Paw & Nail Care, 39 Ear Care, 40 Skin Care}. Tree mirrors Chewy (created 2026-09-10 on user approval). Always the leaf.

## Attributes

Family **none yet — no attribute family for grooming; create one via /manage-attributes when the user lists the attributes** carries: none.
All picks from the closed menu `reference/attribute-values.json`, one value
per attribute per variant, with an evidence quote; empty beats a guess. Our
definitions in `reference/data-tables.md` beat the brand's wording.
Do not create values for this type without an explicit ask.

### Wanted (fill in — one line per attribute)

| Attribute | Values (or "from page, dedup synonyms") | Filter or variant axis? | Evidence rule |
|---|---|---|---|
| | | | |

## Variant axes

Size and colour (a brush in two sizes; a comb in two colours) — needs attributes before multi-variant products can be created.

## Pricing

`pricing_type: "fixed"`; `price` = hafo's row for **that** article code, `cost_price` = CSV
price (`reference/pricing.md`). One hafo lookup per variant.

## Notes

Chewy filters for grooming to consider: Breed Size, Coat Type, Color Family, Material, Grooming Feature (e.g. self-cleaning, detangling). 86 Trixie grooming rows are waiting on this spec.
