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
axes: pack weight, flavour, texture** (gravy/jelly/loaf/mousse). Everything
that redesigns the pack splits products: **lifestage, breed size, food form,
special diet, health feature**, colour. RC Mini Puppy 8 kg and Mini Adult 8 kg
are two products; Sterilised in gravy + in jelly is one product with two
variants. Unclear → separate products + flag. Full reasoning in
`reference/data-tables.md` §2.

Grouping lessons (2026-08-13, `runs/2026-08-13-schesir-regroup.md`):
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
| Dual species | the **mirror leaf in both trees** — 29+36 Shampoos, 30+37 Grooming Tools, 31+38 Paw & Nail, 32+39 Ear Care, 33+40 Skin Care, 42+51 Flea & Tick, 47+55 Pharmacy, 43+52 Vitamins, 69+79 Collars | the pack/brand page says "for dogs and cats" (or the invoice names both `շն` and `կատ`) |
| Dewormer | 46 Heartworm & Dewormers **+** 47 Pharmacy & Prescriptions | it is an antiparasitic given orally |
| Veterinary diet | its food leaf (3/4/10/11) **+** 5 Health Condition | a stated clinical indication |

Add a leaf only on the product's own evidence — never a species the brand does
not claim (rule 8 still applies). And because `PUT /products` replaces the
whole record, always build the body from a fresh `GET` and **extend**
`category_ids`; `scripts/multi-category.py` does this and refuses to shrink a
product's category list.

Missing category → flag, never invent.

## Storefront behaviour worth knowing

- `/product/<slug>/dp/<id>` — `dp` is the **variant** id. Category listing
  shows one card per variant; `/api/search` one per product.
- Variant selector is built from variant attributes — see the multi-variant
  rule in `reference/admin-api.md`.
- Rate "֏/kg" shows only on `per_kg` variants.

## Admin form field map (UI fallback only — `/admin/catalog/products/create`)

| Admin field | Required | Source |
|---|---|---|
| Name / Slug | yes | rules above |
| Categories | yes | map above |
| Brand | yes | must exist (else `/create-brand`) |
| Attribute Family | no | matching family or empty |
| Variant SKU | yes | article code |
| Variant Label | no | varying axes |
| Pricing type | yes | "priced by weight" for dry kibble by the kilo; fixed otherwise |
| Price / Rate per Kg + Pack weight | yes | **hafo sale price** (rate = price ÷ kg) |
| Cost price | no | CSV price |
| Min price | no | 0 |
| Stock | yes | CSV qty (default 10) |
| Default variant | – | first variant ON |
| Variant images | yes | brand-site gallery, verified |
| Variant attributes | no | closed menu, evidence, our definitions |
| About / Ingredients / Feeding (rich text) | no | brand description / composition / feeding guide |
| Flags | no | Rx Required for veterinary diets; rest off |
| SEO meta | no | truncate name (≤60) / first sentence (≤160) |

Browser path: chrome-devtools MCP (`.mcp.json`, persistent profile; on
"browser already running": `pkill -f 'chrome-devtools-mcp/chrome-profile'`).
Prefer `fill_form`; screenshots only for a final result.
