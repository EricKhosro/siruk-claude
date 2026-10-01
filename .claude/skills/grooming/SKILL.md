---
name: grooming
description: Product-type spec for Grooming — categories, product type, how to pick the values this type carries, its net content, variant axes and pack pricing. Read by /add-products for every Grooming row and by /manage-attributes when building the vocabulary. Use when importing, re-attributing or reviewing Grooming products.
---

# Grooming — product-type spec

**Status: template pre-filled from the live admin (2026-09-10). The user will
edit this to say which attributes and values Grooming should show (Chewy-style).
Until it is edited, the live product type is the spec.**

## Where it is filed

Dog → 27 Grooming → {28 Brushes & Combs, 29 Shampoos & Conditioners, 30 Grooming Tools, 31 Paw & Nail Care, 32 Ear Care, 33 Skin Care}; Cat → 34 Grooming → {35 Brushes & Combs, 36 Shampoos & Conditioners, 37 Grooming Tools, 38 Paw & Nail Care, 39 Ear Care, 40 Skin Care}. Tree mirrors Chewy (created 2026-09-10 on user approval). Always the leaf.

**Dual species → both trees.** `category_ids` is a list. When the pack or brand
page says the product is for dogs *and* cats, file it in the **mirror leaf of
both** species' trees (the pattern already in the catalogue: Ear Care 32 + 39,
Shampoos 29 + 36, Grooming Tools 30 + 37, Paw & Nail 31 + 38, Skin Care
33 + 40, Flea & Tick 42 + 51, Vitamins 43 + 52, Pharmacy 47 + 55, Collars
69 + 79). Never add a parent — parents roll their children up. Never add a
species the brand does not claim. See `reference/product-rules.md`.


## Attributes

Product type **7 `grooming`** (created 2026-09-15 as a family, from
attributes that already existed; `measure_type: null`, `default_sale_mode:
pack`). **The live product type decides which attributes exist, their role
(`option` / `attribute`) and flags** — `reference/product-types.json`
(`scripts/product-types.py --dump`); it wins over this file. Read 2026-09-30:
`size` 28, `color-family` 15 and `flavor` 5 are `option`; `material` 12,
`breed-size` 4, `product-form` 18, `active-ingredient` 19, `health-feature` 7
are `attribute`. An attribute no product carries a value for simply does not
render, so the list is deliberately generous; the user has still to say which
Chewy-style filters grooming should really show (category filters now come
from each attribute's `is_filterable` on this type). An attribute the batch
needs that the type lacks → the `attribute-manager` agent before the import
(CLAUDE.md 8b). All picks from the closed menu
`reference/attribute-values.json`, one value per attribute per variant, with
an evidence quote; empty beats a guess. Our
definitions in `reference/data-tables.md` beat the brand's wording.
Do not create values for this type without an explicit ask.

### Wanted (fill in — one line per attribute)

| Attribute | Values (or "from page, dedup synonyms") | Option or attribute? filterable? | Evidence rule |
|---|---|---|---|
| | | | |

## Net content (CLAUDE.md 8a)

A shampoo, spray or lotion has net content — `measure_type: "volume"`,
`content` in ml (`250 ml` → `250`; `1 L` → `1000`), `pack_count 1`; a wipes
pack is `count` (`40 wipes` → `40`). A brush, comb or clipper has none. The
`product-weight` attribute that used to carry "250 ml" is retired
(2026-09-29). A physical size (brush S/L, a `9 × 15 cm` pad) is `size` 28,
never content.
A variant may carry `measure_type`/`content` although the type's own `measure_type` is `null` — `ProductRequest` has no type-level size rule (checked in siruk-web source 2026-09-30); send `measure_type` explicitly, since nothing pre-fills it.

## Variant axes

Net content and the type's options: size and colour (a brush in two sizes; a
comb in two colours) — `size` 28 and `color-family` 15, and a scent on
`flavor`, set per variant. Once one variant carries an option, every variant
needs it (rule 9a); `scripts/backfill-variant-axes.py` derives them from the
label for products that gained a sibling.

## Pricing

`price` = hafo's row for **that** article code (the pack price), `cost_price`
= CSV price (`reference/pricing.md`). One hafo lookup per variant.

## Notes

Chewy filters for grooming to consider: Breed Size, Coat Type, Color Family, Material, Grooming Feature (e.g. self-cleaning, detangling). 86 Trixie grooming rows are waiting on this spec.
