# Product rules — naming, grouping, categories, admin form

## Name, slug, label

- **Name never contains the brand** — the storefront prints the brand before
  it ("Royal Canin Mini" would render twice). Strip `RC `/brand prefixes. Name
  = line + breed size + lifestage (+ pack weight/flavour/texture only while the
  product has a single variant).
- **Slug** = kebab-case of brand + Name (`royal-canin-mini`); slugs are global.
- **Variant label** = only the axes that vary, and every axis that varies:
  "8 kg", "Gravy 12 x 85 g", "Tuna 85 g". Metric only.
- **SKU** = the article code (`Կոդ` minus `W-`), else `BRAND-SLUG-LIFESTAGE-WEIGHT`.
- Rename a product that outgrew a single variant with
  `scripts/rename-product.sh` and move the weight into the labels.

## Product vs variant — the shelf test

Variants are the same pack with a different option printed on it. **Variant
axes: pack size (the net content, CLAUDE.md 8a), flavour, texture**
(gravy/jelly/loaf/mousse) — flavour and texture being the product type's
`option`-role attributes (`reference/product-types.json`). Everything
that redesigns the pack splits products: **lifestage, breed size, food form,
special diet, health feature**, colour. RC Mini Puppy 8 kg and Mini Adult 8 kg
are two products; Sterilised in gravy + in jelly is one product with two
variants. Unclear → separate products + flag. Full reasoning in
`reference/data-tables.md` §2.

**Those axes are the FOOD axes.** A product type's own skill overrides them,
within the options its live type defines: `accessories` adds **size, colour
and volume**, so one collar in six sizes and five colours is one product with
30 options, not 30 products. Same for `grooming` (size, scent). Colour only
splits a *food* pack. Only option-role values plus the net content tell
variants apart — a spec-role value never does.

Grouping lessons (2026-08-13, the Schesir regroup):
- Never let a variant axis into a grouping key (pack weight/texture in the key
  made 81 products of 70).
- An unknown field must not discriminate — fold rows with unknown species/
  container into the one group agreeing on every known field.
- Parser residue is not identity (`POLLO&UOVO` unsplit landed in the key).

Only the rows in the CSV become variants — never add pack sizes/flavours the
brand site lists but the CSV lacks (no price).

## Existing product?

`scripts/find-product.sh "<line name>"` (then brand name), `show-product.sh`
on hits. Same product only if brand, line, lifestage, breed size, form, diet
and health claims all match. Then `scripts/add-variant.sh`; else
`scripts/create-product.sh`. Procedure details: `data-tables.md` → "Adding a
variant to a product that already exists".

## Category map (CSV `Category` → admin id)

Dry food—Dogs → 3 · Wet food—Dogs → 4 · Dry food—Cats → 10 · Wet food—Cats →
11 · Treats → the **leaf** under 6 (dog) or 14 (cat), chosen by treat form —
see the table in the `treats` skill (dog: 7 Bones/Bully Sticks & Naturals,
82 Soft & Chewy, 83 Dental, 84 Biscuits & Cookies, 85 Long-Lasting Chews,
86 Jerky, 87 Freeze-Dried & Dehydrated, 88 Lickable; cat: 89 Crunchy,
90 Lickable, 91 Soft & Chewy, 92 Dental, 93 Catnip, 94 Cat Grass) ·
Vitamins & supplements → **43**
(dog) / **52** (cat), the other Health & Pharmacy leaves by purpose (42–49 /
51–58, see `reference/admin-api.md`) · Cat litter → the leaf under 59 by type
(60 Clumping, 61 Scented, 62 Unscented, 63 Natural, 64 Lightweight, 65
Crystal — silica gel = Crystal, plant-based clumping = Clumping unless the
pack says "natural") · litter trays, scoops, mats → 67. Veterinary dog diets
also → 5. Toys → the **leaf** under
15 (dog: 17 Plush, 18 Latex & Rubber, 19 Rope & Tug, 20 Fetch & Retrieve,
21 Chew & Dental, 22 Activity & Intelligence) or 16 (cat: 23 Mice & Animals,
24 Balls, 25 Catnip, 26 Activity & Intelligence), chosen by `toy-type` (table
in the `toys` skill). Grooming → the leaf under 27 (dog) or 34 (cat): Brushes
& Combs, Shampoos & Conditioners, Grooming Tools, Paw & Nail Care, Ear Care,
Skin Care (28–33 / 35–40). Products always go in a leaf, never a parent.

**Supplies / Cleaning & Potty** (created 2026-09-11, Chewy menu) — collars,
leads, harnesses, ID tags → **69** dog / **79** cat · bowls, travel bottles,
place mats → **70** · beds and cooling mats → **71** · clothing, dog socks →
**72** · car seat covers, carriers → **73** · muzzles, behaviour-correction
sprays (anti-chew, anti-soiling) → **74** · nappies, diapers, protective pants
and their pads → **76** · poop bags, dispensers, scoops → **77** · odour and
stain removers, lint rollers, textile brushes → **78** · scratching boards and
cardboards → **81**. Cat behaviour and odour sprays go to **67** (Litter Boxes
& Accessories) — the Cat menu has no Cleaning or Training node (user call,
2026-09-11). **13 Accessories is not a product category** (`forProducts`
omits it); a row landing there is a bug, not a fallback.

## Sibling products — finding them after the fact (2026-09-12)

An import that walks a CSV row by row makes one product per row, and sibling
rows become sibling *products*: `Premium Collar, S, 25–40 cm/15 mm, fuchsia`
and `Premium Collar, S–M, 30–45 cm/15 mm, black` were 22 separate products
where Trixie sells one collar. 131 such duplicates were folded away on
2026-09-12.

`scripts/find-duplicate-products.py` re-runs the detection. Three signals, the
first two authoritative **both ways** — they merge and they split:

| Signal | What it is |
|---|---|
| **trixie.de** | the article codes sit on the same official product page (`trixie-product.py` parses its whole variant table) |
| **trixie.shop** | the article codes are options of the same Shopify product — reaches discontinued lines the .de catalogue dropped |
| **name** | identical product name once the variant label is stripped, same brand, same categories — only where no official signal contradicts it |

The splitting half is what keeps look-alikes apart: three **Stainless Steel
Bowl** lines (24851–55 heavy weight, 25071–74 non-slip, 25271–73 varnished),
six **Soft Brush** lines, and `Dog Socks XL/black` (19526), a different product
from the grey 19500–19503. A name group spanning several official products
never merges, and a member with no official key of its own goes to the review
list. `SPLIT_OFF` in the script holds the hand-checked exceptions with their
evidence.

**A merged product needs a variant axis.** The storefront builds the selector
from the net content plus the type's **option** attributes, not from the
variant label — verified on product 874, whose second variant carried no
`flavor` and was simply unreachable. So before merging, every variant needs a
different size or a value on an option that varies across the group (and that
option on every variant — rule 9a). `scripts/plan-product-merge.py` works that
out and names the vocabulary it still needs; `scripts/merge-products.py`
refuses to write a product where two variants share an attribute combination
(it builds its bodies through `siruk_payload.py`, which also refuses two
variants with the same options + size).

Accessory axes (created 2026-09-12): **`size` 28** — letter sizes (XXS–XS …
XL) for collars, harnesses, leads and apparel, measurement strings
("0.45 l/ø 19 cm", "9 × 15 cm") for bowls, brushes and packs. **`pet-weight-range`
27** — the dose band on antiparasitic drops and tablets (1–4 kg …). Colour
rides on `color-family`. Whether each is an option and filterable is set per
product type now (`reference/product-types.json`), not on the attribute. The full measurement stays in the variant label, so
"XS–S, 22–35 cm/10 mm, black" still reads in full on the product page.

**The second sweep (2026-09-16) was about food, treats and pharmacy**, which
the three signals above cannot see: the brand gives every flavour its own page
(so the page signal *splits* them) and the flavour sits inside the product
Name (so the stripped-name signal never joins them). "Barbecue Ribs with Duck"
+ "…with Chicken", five Monge Gift Sticks recipes, Trixie Premio Stripes in
five flavours, Rolf Club / Inspector / Insectal / Gelmintal antiparasitics in
their dose bands and a litter tray in two colours — 36 products from 91,
decided by hand, one evidence line per group
(`scripts/plan-variant-merge.py` reads a `variant-groups.json` of that shape). The tell-tale is **an axis value in the
Name**: flavour, dose band, pack, colour. Kept apart on purpose: lines that
differ by lifestage or health function (Gift Sticks Adult vs Puppy & Junior,
Filled & Crunchy Hairball vs Sterilised), by packaging (85 g pouch vs 100 g
tray vs 400 g can), by sex-specific formulation (SexControl for male vs female
cats) and by species-specific pack ("Spray for Dogs" vs "for Cats").

**Merging deletes before it writes.** SKUs are unique catalogue-wide, so the
surviving product cannot claim a sku another product still holds; the absorbed
products are DELETEd first, which is why `merge-products.py` backs every one of
them up (en/ru/hy) before it touches anything.

## Multiple categories per product (verified 2026-09-12)

`category_ids` is an **array** and the admin's Categories field is a
multi-select tree (`ant-select-multiple ant-tree-select`) — a product may sit
on several shelves at once. A two-id `PUT` reads back with both ids, and 29
products (572, 606, 668/669, 715–718, 730–736, 755–794) were already filed
this way; the big Trixie / Monge / toy / treat imports each wrote a single id,
which is what needs fixing.

**Parents roll up, so never add one.** The storefront `/dog/treat/` renders 48
product cards drawn from leaves 7 and 82–88 even though *nothing* is assigned
to category 6 — checked by finding products from three different leaves
(Bacon Pâté → 88, Bagels → 82, Barbecue Ribs → 85) on that one page. Filing a
product in a parent adds nothing and breaks the leaf rule.

**When a second leaf is right** — the conventions already in the catalogue:

| Case | Categories | Evidence to require |
|---|---|---|
| Dual species | the **mirror leaf in both trees**, or the nearest leaf that species actually has — 29+36 Shampoos, 30+37 Grooming Tools, 31+38 Paw & Nail, 32+39 Ear Care, 33+40 Skin Care, 42+51 Flea & Tick, 47+55 Pharmacy, 43+52 Vitamins, 69+79 Collars | the pack/brand page says "for dogs and cats" (or the invoice names both `շն` and `կատ`) |
| Dewormer for both species | 46 Heartworm & Dewormers **+** 55 Pharmacy & Prescriptions (Cat has **no** dewormer leaf, so 46 mirrors to 55) | the pack names both species |
| Veterinary diet | its food leaf (3/4/10/11) **+** 5 Health Condition | a stated clinical indication |

Checked 2026-09-12 so the table stays honest: 46 holds 12 dewormers, 55 holds
the cat ones, and 47 holds only the First Aid Kit and the SexControl tablets —
so "every dewormer also goes in 47" is **not** a convention here and must not
be applied. Where a species has no shelf at all (Cat has no Health Condition,
Bowls & Feeders, Beds, Clothing, Carriers or Cleaning & Potty node), report the
gap; creating a category needs an explicit ask (rule 8).

Add a leaf only on the product's own evidence — never a species the brand does
not claim (rule 8 still applies). And because `PUT /products` replaces the
whole record, always build the body from a fresh `GET` and **extend**
`category_ids`; `scripts/multi-category.py` does this and refuses to shrink a
product's category list.

Missing category → flag, never invent.

## Storefront behaviour worth knowing

- `/product/<slug>/dp/<id>` — `dp` is the **variant** id. Category listing
  shows one card per variant; `/api/search` one per product.
- Variant selector is built from the net content plus the product type's
  option-role attributes — see "Variants and attributes" in
  `reference/admin-api.md`.
- The unit price ("֏/kg", "֏/100 ml") is computed by the server from price ÷
  net content; hidden for `count`, when `show_unit_price` is off, or when it
  equals the price (catalog model, 2026-09-29).
- **The filter sidebar of a category comes from `is_filterable` on the product
  types of the products in that category**, ∩ the values those products
  actually use (catalog model, 2026-09-29; before that it was the family's
  attributes ∩ the attribute's own `isFilterable`, verified 2026-09-14 against
  the page's `availableAttributes`). So an attribute the type does not carry
  never facets, however many variants hold it, and an attribute with one value
  in use still renders as a one-option facet. Every product has a type now
  (rule 8b) — the old "no family, no facets" gap is closed.
- History (2026-09-14): the sidebar sorted a facet by the leading NUMBER of
  the label, ignoring unit and `sort_order` (`1.25 կգ, 1.3 կգ, 45 գ …`), which
  scrambled the mixed-unit `product-weight` list. Pack size is net content
  now; re-check the order if a mixed-unit option list (e.g. `size` 28)
  facets.

## Admin form field map (UI fallback only — `/admin/catalog/products/create`)

| Admin field | Required | Source |
|---|---|---|
| Name / Slug | yes | rules above |
| Categories | yes | map above |
| Brand | yes | must exist (else `/create-brand`) |
| Product type | yes | the row's product type — never left empty; the `attribute-manager` agent creates/extends it before the import (rule 8b) |
| Variant SKU | yes | article code |
| Variant Label | no | varying axes |
| Sale mode | yes | `pack` (the type's default); `weight` (loose, price per kg) is not used yet |
| Net content | per type | `measure_type` + content + pack count (rule 8a; the type skill says which measure) |
| Price | yes | **hafo sale price** for the pack |
| Cost price | no | CSV price |
| Min price | no | 0 |
| Initial stock | new variants | CSV qty (Qty 1 or empty → placeholder 10); an existing variant's stock changes only in Inventory → Stock (rule 10a) |
| Default variant | – | first variant ON |
| Variant images | yes | brand-site gallery, verified |
| Variant attributes | per type | only the product type's attributes (required ones must be set); closed menu, evidence, our definitions |
| About / Ingredients / Feeding (rich text) | no | brand description / composition / feeding guide |
| Flags | no | Rx Required for veterinary diets; rest off |
| SEO meta | no | truncate name (≤60) / first sentence (≤160) |

Browser path: chrome-devtools MCP (`.mcp.json`, persistent profile; on
"browser already running": `pkill -f 'chrome-devtools-mcp/chrome-profile'`).
Prefer `fill_form`; screenshots only for a final result.
