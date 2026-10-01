---
name: accessories
description: Product-type spec for Accessories — categories, product type (and the Litter type), how to pick the values they carry, net content, variant axes and pack pricing. Read by /add-products for every Accessories row and by /manage-attributes when building the vocabulary. Use when importing, re-attributing or reviewing Accessories products.
---

# Accessories — product-type spec

**Status: template pre-filled from the live admin (2026-09-10). The user will
edit this to say which attributes and values Accessories should show (Chewy-style).
Until it is edited, the live product type is the spec.**

## Where it is filed

Cat litter → Cat → 59 Litter → leaf by type (60 Clumping, 61 Scented, 62 Unscented, 63 Natural, 64 Lightweight, 65 Crystal). Litter boxes, scoops, mats → Cat → 66 Supplies → 67 Litter Boxes & Accessories. Everything else → the **leaf** under Dog 68 Supplies / 75 Cleaning & Potty or Cat 66 Supplies / 80 Trees, Condos & Scratchers (created 2026-09-11 from the Chewy menu): 69 Collars, Leashes & Harnesses · 70 Bowls & Feeders · 71 Beds · 72 Clothing & Accessories · 73 Carriers & Travel · 74 Training & Behavior · 76 Pee Pads & Diapers · 77 Poop Bags & Scoopers · 78 Cleaners & Stain Removers · 79 Collars, Leashes & Harnesses (cat) · 81 Scratchers & Scratching Posts. **13 Accessories is NOT a product category** — `forProducts` omits it; a row landing there is a bug, not a fallback.

**Dual species → both trees.** `category_ids` is a list: a bowl, mat or collar the pack sells for dogs *and* cats goes in both leaves (e.g. 69 + 79). Never add a parent. See `reference/product-rules.md`.

## Attributes

Product type **8 `accessories`** (created 2026-09-15 as a family, from
attributes that already existed; `measure_type: null`). Cat litter is its own
type, **9 `litter`** (`measure_type: volume`). **The live product type decides
which attributes exist, their role (`option` / `attribute`) and flags** —
`reference/product-types.json` (`scripts/product-types.py --dump`); it wins
over this file. Read 2026-09-30: Accessories — `size` 28 and `color-family` 15
are `option`; `material` 12, `breed-size` 4, `pet-weight-range` 27,
`product-form` 18 are `attribute`. Litter — `material` 12, `product-form` 18,
`health-feature` 7, all `attribute`. An attribute no product carries a value
for does not render, so the lists are deliberately generous; the user has
still to say which filters these types should show (category filters come
from each attribute's `is_filterable` on the type). An attribute the batch
needs that a type lacks → the `attribute-manager` agent before the import
(CLAUDE.md 8b).
All picks from the closed menu `reference/attribute-values.json`, one value
per attribute per variant, with an evidence quote; empty beats a guess. Our
definitions in `reference/data-tables.md` beat the brand's wording.
Do not create values for this type without an explicit ask.

### Wanted (fill in — one line per attribute)

| Attribute | Values (or "from page, dedup synonyms") | Role on the live type | Evidence rule |
|---|---|---|---|
| `size` (28) | letter sizes `XXS–XS` … `XL`; measurement strings (`0.45 l/ø 19 cm`, `9 × 15 cm`, `4 × 20 bags`) | **option** (variant axis) | the size/measurement the brand prints for that article |
| `color-family` (15) | the closed colour menu; map the brand's word (fuchsia → Pink, graphite → Grey, orchid → Purple, petrol → Teal, sand → Beige, curry → Yellow, chrome → Silver); a `x/y` colour takes the first | **option** (variant axis where the colour varies) | the colour on the pack/page |
| `pet-weight-range` (27) | `0.5–2 kg` … `10–25 kg` | attribute here — the dose-band **axis** lives on the Supplements type, where antiparasitic drops/tablets belong | the dose band on the pack |

## Net content (CLAUDE.md 8a)

The printed contents that used to go on `product-weight` (retired 2026-09-29)
are the variant's net content now: **litter** `measure_type: "volume"`,
`content` in ml (`5 l` → `5000`, `11 l` → `11000`) — or `mass` in g when the
bag prints only kg; a cleaner or spray `volume` (`750 ml` → `750`); a count
pack `count` (`pack_count` for "4 × …"). A collar, bowl or bed has none: its
physical size is `size` 28, never content.
A variant may carry `measure_type`/`content` although the type's own `measure_type` is `null` — `ProductRequest` has no type-level size rule (checked in siruk-web source 2026-09-30); send `measure_type` explicitly, since nothing pre-fills it. OPEN: whether poop-bag packs
(`4 × 20 bags`, today a `size` value) should move to `count` content
(`content 20, pack_count 4`).

## Variant axes

**Size, colour, volume** (volume = the net content above) — these override the food shelf test in
`reference/product-rules.md`, which splits on colour. One collar in six sizes
and five colours is ONE product with 30 options: that is how Trixie sells it,
and 131 duplicates created by the other reading were folded away on 2026-09-12.
Every variant carries `size` 28 (letter size, or the bowl capacity string
"0.25 l/ø 12 cm") and `color-family` 15 (both options — only option values and
the net content tell variants apart); `scripts/plan-trixie.py` sets both
from the page spec and attaches a row to the live product on the same
trixie.de page (`existing_id`), and `scripts/backfill-variant-axes.py` fills
the axis on older single variants afterwards. Trixie's palette needs the finer
values Aqua / Blush / Sage where royal blue + aqua or fuchsia + blush would
otherwise share one family inside a product
(2026-09-12 merge).

Keep the **full** measurement in the variant label ("XS–S, 22–35 cm/10 mm,
black") and put only the letter size on `size` — the label is what the shopper
reads, the attribute is what builds the selector. Every variant needs a value
on every axis the product uses, or the ones without it vanish from the dropdown
(`reference/admin-api.md`; rule 9a — `siruk_payload.py` refuses a new variant
that breaks it). Litter volumes are net content now (above), not the old
`product-weight` values 190 / 191.

Before creating an accessory, check for siblings already in the catalogue:
`scripts/find-product.sh "<line name>"`, and `scripts/find-duplicate-products.py`
to sweep the whole catalogue.

## Pricing

`price` = hafo's row for **that** article code (the pack price), `cost_price`
= CSV price (`reference/pricing.md`); the server computes any per-litre rate.
One hafo lookup per variant.

## Notes

Candidates for their own type later: Litter & Litter Boxes, Bowls & Feeders, Collars & Leashes, Beds, Carriers.
