---
name: toys
description: Product-type spec for TOYS — which categories, attribute family, attributes and values a toy gets, its variant axes, and how to source them. Read by /add-products for every toy row and by /manage-attributes when building or extending the toy vocabulary. Use when importing, re-attributing or reviewing dog/cat toys.
---

# Toys — product-type spec

Replicates Chewy's toy filters (user decision 2026-09-10): **Breed Size,
Color Family, Toy Feature, Material**, plus a hidden **Toy Size** as the
variant axis. Skipped on purpose: Collection, Made In. One value per attribute
per variant — the API rejects arrays (verified 2026-09-10), so pick the single
most prominent feature / material / colour.

The full value lists live in `reference/chewy-attributes.json` (the file
`scripts/sync-attributes.py` applies to the admin) and, once synced, in the
closed menu `reference/attribute-values.json`. Pick only from the menu.

## Where a toy is filed

Family **5 Toys**. Category = the **leaf** under Toys, chosen from the
`toy-type` value (never the parent 15/16):

| toy-type | Dog leaf | Cat leaf |
|---|---|---|
| Plush | 17 Plush | 23 Mice & Animals (flag if not an animal shape) |
| Latex & Rubber | 18 Latex & Rubber | 24 Balls if a ball, else flag |
| Rope & Tug | 19 Rope & Tug | flag (no cat leaf) |
| Ball / Fetch & Retrieve | 20 Fetch & Retrieve | 24 Balls |
| Chew & Dental | 21 Chew & Dental | flag |
| Activity & Intelligence | 22 Activity & Intelligence | 26 Activity & Intelligence |
| Catnip | — | 25 Catnip |
| Mouse & Animal | — | 23 Mice & Animals |

`toy-type` (11) stays as the internal attribute that drives this table even
though Chewy shows it as a category, not a filter.

## Attributes

| Attribute | id | Values | How to fill |
|---|---|---|---|
| `breed-size` | 4 | Chewy's 6 | only when the page states a size/breed claim ("for small dogs", "XS"); a length range with no claim → empty |
| `color-family` | 15 | Chewy's 24 (Multi … Navy, Color Varies, Glow In The Dark) | from the page text or the packshot you looked at; 2+ colours → **Multi**; Trixie "assorted colours" (random shipment) → **Color Varies**. A colour that differs per article code is a variant axis |
| `toy-feature` | 13 | Chewy's 30 (Squeaky, Tough Chewer, Exercise, Training, Dental, Teething, Outdoor, Water Toy, Crinkle, Bouncy, Stuffing-Free, Variety Pack, Durable, Electronic, Glowing & Light-Up, Puzzle Toy, Battery Operated, Replacement, Herding, Catnip, Floats, Nylon, TPR, Natural, Spring, Waterproof, Animal & Figure, App-Controlled, Scented, Scratcher) + our 5 extras (Massages Gums, Mint Flavour, Shock Absorber, With Bell, With Rope) | the feature the page leads with, with a quote. Trixie wording → Chewy value: "squeaker" → Squeaky; "floats" → Floats; "glow" → Glowing & Light-Up; "for teeth cleaning / dental care" → Dental; "with catnip" → Catnip; "robust / strong chewers" → Tough Chewer; "intelligence / strategy game" → Puzzle Toy; "water" → Water Toy |
| `material` | 12 | Chewy's 46 + our 3 extras (Plush, Cotton/Polyester, Paper Cord) | the material the page prints (Trixie prints one on almost every toy). **You may create a value** for a material not in the menu — see below |
| `toy-size` | 16 (hidden from filters) | "<n> cm", 42 values | from the label/page dimension ("22 cm", "ø 6 cm"). Create a missing size with `/manage-attributes` in the same "<n> cm" form. **Not shown in the storefront sidebar** (`isFilterable: false`) — it exists only so size variants stay distinct |
| `lifestage` | 3 | Nursing, Puppy, Kitten, Adult, Senior, All Lifestages | only on an explicit claim ("puppy toy", "for kittens") |

Every non-empty pick needs a quote from the page. Empty beats a guess.

### Material — create values, but never a synonym

The brand's word goes into the menu only if no existing value means the same
thing. Map the page wording through this table first, and extend the table
when you add a value:

| Page says | Use |
|---|---|
| plush, plushy, soft, fleece, cuddly fabric | Plush (or Fleece / Faux Fur when the page says exactly that) |
| polyester, fabric, textile, cloth, nylon fabric | Polyester / Synthetic Fabric — pick the one the page names; "fabric" with no fibre → Synthetic Fabric |
| cotton, cotton rope, rope | Cotton, or Rope when it is a rope toy |
| natural rubber, rubber | Rubber |
| TPR, thermoplastic rubber, TPE | Thermoplastic Rubber |
| latex | Latex |
| plastic, PP, ABS | Plastic (Polypropylene only if the page says PP) |
| vinyl, PVC | Vinyl / PVC |
| wood, wooden | Wood; bamboo → Bamboo |
| paper cord | Paper Cord; cardboard, paper → Cardboard / Paper |
| sisal, jute, seagrass, natural fibre | Jute, or Plant Material |
| foam, EVA | Foam |

A genuinely new material → check the menu for a neighbour, create it **once**
with `/manage-attributes`, named in the same style, and list it under "values
created" in the run report. Never two values a shopper would read as the same.

## Variant axes

**Size (cm) and colour.** Same toy in 22 / 28 / 40 cm = one product, three
variants, each with its own `toy-size`; same toy in blue / red = one product
with `color-family` per variant. The label carries every varying axis
("28 cm", "Red 15 cm"). Each variant must end up with a distinct attribute
combination or the API rejects it.

## Pricing, sourcing, naming

- `pricing_type: "fixed"`, `price` = hafo's row for **that** article code,
  `cost_price` = CSV price (`reference/pricing.md`). One lookup per variant.
- Trixie: **all** gallery images via `scripts/trixie-image.sh <art no>` (one
  URL per line, packshot first — upload every line into `variant.images`;
  `scripts/add-all-images.py` backfills existing products), copy from
  `scripts/trixie-product.py`; `material` is the bullet almost every Trixie toy
  page prints (`reference/brand-sites.md`).
- Name = the toy without brand ("Playing Rope", "Hedgehog Ball"); slug =
  `trixie-playing-rope`. Metric only.
