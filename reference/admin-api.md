# Siruk admin JSON API — endpoints, payloads, quirks, live ids

Base `https://demo-api.siruk.am/api/admin`. Header `Authorization: Bearer <JWT>`
— cookies alone do **not** authenticate. The SPA stores the token in
`localStorage.access_token` as `{"token":"eyJ…"}` (~1 year). Always send a real
User-Agent (the WAF 403s `Python-urllib`; curl's default is fine).
**Use `scripts/` for every call** (`scripts/README.md`); `scripts/api.sh METHOD
PATH [payload.json|-]` is the escape hatch.

## Reads (all `{"data":[…]}`)

`GET /categories?forProducts=true` · `/brands?forProducts=true` ·
`/attributes?forProducts=true` · `/attribute-values` ·
`/attribute-families?forProducts=true` · `/medias?acceptTypes=…&directory=` ·
`/account` · `/roles` · `/products/<id>` (directly re-postable body, variants
carry `id`).

**Product search**: `GET /products?search=<text>` matches names (paginated).
Any other query name (`q`, `keyword`, `name`, `filter[name]`) is silently
ignored and returns everything.

## Product create — `POST /products`

Required: `name`, `slug`, `category_ids[]` — an **array, and products often
need more than one id** (the admin field is a multi-select tree; see
"Multiple categories per product" in `reference/product-rules.md`). Also send `brand_id`,
`attribute_family_id` (nullable), `is_best_seller`, `is_on_sale`, `variants`.
Variant shape:

```
{name, about_this_item(HTML), ingredient_information(HTML), feeding_instructions(HTML),
 pricing_type:"fixed"|"per_kg", sku, price(int AMD), price_per_kg, min_allowed_price,
 cost_price(int AMD), compare_at_price, weight(kg), is_default, stock(int),
 vendor_stock:bool, sort_order:0, images:[mediaId…], attribute_value_ids:{<code>:<valueId>}}
```

`DELETE /products/<id>` → 204.

### Pricing type (verified 2026-08-12)

Exactly `fixed` or `per_kg`; anything else 422s.

- **`fixed`** — sold per unit (pouch, can, multipack, tin, toy): send `price`.
- **`per_kg`** — sold by weight (dry kibble bags; admin form "priced by
  weight", Rate per Kg + Pack weight): send `price_per_kg` + `weight` (kg).
  **`price` is ignored and stored as 0**, so `price_per_kg = sale price ÷
  weight`; only 2 decimals are stored (4666.666… → 4666.67, pack price within
  hundredths). The storefront shows the "֏/kg" rate **only** on `per_kg`
  variants — on a `fixed` variant `price_per_kg` is stored and never displayed.
- Set `product-weight` on a `per_kg` variant **too** (reversed 2026-09-14 —
  it used to say the opposite). The numeric `weight` field is a pricing input;
  the attribute is what the storefront facets and the pack-size dropdown read,
  and nothing derives one from the other (`data-tables.md` table 4).
- Volume goods (litter "5 l / 8 l") need a real kg `weight` before `per_kg`;
  the storefront hard-labels the rate "֏/kg". A weight derived from another
  pack of the identical product needs the user's explicit approval (done once,
  2026-09-09, 8 l = 3.6 kg → 5 l = 2.25 kg).

### Variants and attributes

- Every variant needs a **unique `attribute_value_ids` combination**; the API
  rejects duplicates ("This attribute combination is already used in variant
  N"). So a flavour/texture variant must have that attribute set.
- A product with **2+ variants must give each a distinguishing attribute**
  (found 2026-09-09, product 199): with empty `attribute_value_ids` everywhere,
  no selector renders and every `/dp/<id>` URL shows the default variant. The
  uniqueness guard does not fire on empty combinations (dev question).
- The selector is built **per attribute**, not from the variant label: the page
  renders one dropdown per attribute that any variant carries, listing that
  attribute's values across the variants. A value MISSING on one variant
  quietly drops it from that dropdown — product 874's second variant had no
  `flavor` and was unreachable (fixed 2026-09-12). On an informational
  attribute that is only cosmetic (713 shows "Ingredient: Chicken, Pork" plus
  "See available options"); on the **axis** it hides stock. So when merging
  sibling products, fill the axis on every variant
  (`scripts/plan-product-merge.py` does, and `merge-products.py` refuses to
  write a product whose variants share a combination).
- Attributes are optional only on a single-variant product.

## Translations — `en` / `ru` / `hy` (verified 2026-09-10)

Content locales are **`en`, `ru`, `hy`** (Armenian is `hy`, never `am`).
Reads: header `Content-Language: <lang>` (`SIRUK_LANG=ru scripts/api.sh GET …`).
Writes: a flat `"locale": "<lang>"` key in the JSON body; no header, no query
param, no nested `{en,ru,hy}` object. One write per locale.

| Resource | Per-locale fields | Single-language (last write wins for ALL locales) |
|---|---|---|
| product | `name`, variant `about_this_item`, `ingredient_information`, `feeding_instructions` (product SEO `meta` is **not exposed** by `/products` at all — sent keys are ignored, the record has none) | **variant `name` (label)**, `slug`, sku, prices, stock, images, `attribute_value_ids` |
| category | `name` | `slug` |
| attribute / attribute value | `name` / `label` (per-locale since the 2026-09-10 backend change; before that a `ru` PUT overwrote English) | `code`, `value`, flags, sort, image |
| brand | `name`, `meta.title/description` (verified 2026-09-10) | `slug`, `image` |
| attribute family | `name` (per-locale since 2026-09-10) | `code`, `sortOrder`, `attribute_ids` |
| media | none (`alt`/`caption` global) | |

**Create carries exactly one locale.** `POST` accepts `"locale":"ru"` but then
the record exists *only* in `ru` (English name empty); a nested
`{"name":{"en","ru","hy"}}` 422s ("must be a string") and a `translations[]`
array is ignored. So there is no create-time multi-language payload: create in
`en`, then one `PUT` per extra locale — which is what `set-translation.py`,
`translate-categories.py` and `translate-brands.py` do. For attributes,
values and families the `locale` key was ignored until 2026-09-10 (every
shape tried rewrote the single stored label; the admin UI's En/Ru/Hy
dropdown sends the same flat `locale` key and overwrote English too). The
backend now stores them per locale and `scripts/translate-attributes.py`
applied `reference/translations-attributes.json` (17 names, 629 labels, 5
family names; read-back in en/ru/hy: 0 mismatches). The script still probes
a throwaway attribute first and refuses on a regression. Bodies mirror the
admin UI: attribute `{locale, name, code, is_variant, is_filterable}`; value
`{locale, attribute_id, value, label, color_hex, sort_order, image}`; family
`{locale, name, code, sortOrder, attribute_ids}`.

**`set-translation.py` writes EVERY variant, so a sku left out of the file gets
the English text written into that locale** — it does not leave the stored
translation alone (found 2026-09-12: translating one variant of product 1016
overwrote the Armenian texts of the other two). On a product that already has
translations, put every sku in the file, taking the ones you are not changing
from a `SIRUK_LANG=<lang> scripts/api.sh GET /products/<id>` first.

Use `scripts/set-translation.py <id> <ru|hy> <translation.json>` for products
— it copies every single-language field from the `en` record, refuses a file
that touches them, PUTs with `locale`, and verifies both that the translation
landed and that `en` is unchanged. Categories:
`scripts/translate-categories.py` (table inside). The `ru`/`hy` PUT still
replaces the whole variants array, so it is built from a fresh `en` GET.
*Still single-language:* product-variant `name` (the variant selector
label). Attributes, values and families were made per-locale by the backend
on 2026-09-10.

## Product update — `PUT /products/<id>` (PATCH identical)

Same shape as create. **PUT replaces the whole variants array**: an omitted
variant is deleted silently (200), or 422 if it was the default. Build the body
from a fresh GET — `scripts/add-variant.sh` / `scripts/set-variant.sh` /
`scripts/rename-product.sh` do this; never hand-write one.

**`category_ids` is replaced wholesale like everything else** — a PUT that
sends one id on a product that had two silently drops the other. Build the
body from a fresh GET and extend the list (`scripts/multi-category.py`).

**SKUs are unique catalogue-wide.** Moving a variant between products: DELETE
the source *before* the target PUT claims the SKU (else 422 "SKU already in
use"). Back bodies up first; bucket writes by target product and write each
once.

## Media — `POST /medias`

`multipart/form-data`, parts `file` (binary with filename) and `fileInfo` (JSON
string `{"filename","caption","alt","dimensions":"WxH","directory":""}`) →
`{"data":{"id"}}`. JSON body or missing `fileInfo` → 500 "Attempt to read
property filename on null". `DELETE /medias/<id>` → 200.

- **201 + id does not mean the file exists.** A `%` or space in the filename
  yields a record whose storage URLs all 404 (product 71 / media 621).
  `scripts/upload-media.sh` slugifies to `[A-Za-z0-9._-]`, then GETs the URL
  before returning an id. Sweep with `scripts/verify-media.sh` after imports.
- **Transparent PNGs render on black** in the storefront gallery;
  `upload-media.sh` flattens onto white (`KEEP_ALPHA=1` for logos).
- **Media ids are recycled** after delete (id 61 went from the Schesir logo to
  a Royal Canin packshot). Never delete a media something uses (`isUsed`);
  re-verify ids from old notes.
- One upload creates three rows (original, `-adminThumbnail`, `-<hash>` webp);
  `GET /medias/<id>.url` is the thumbnail, the webp is checked separately.

## Brands / categories / attributes

- `POST /brands` `{name, slug, image:<mediaId>, meta:{title,description}}` —
  use `scripts/create-brand.sh` (dedupes, verifies logo).
  `scripts/set-brand-logo.sh` to change a logo (refuses another brand's image).
- `POST /categories` `{parent_id, name, slug, description, quick_links:[],
  meta}`. Slugs are parent-prefixed (`dog-treat`, `cat-treat`). Never create
  without an explicit ask — then use `scripts/create-category.py <spec.json>`
  (dedupes on parent+name, resolves `"parent": "Dog > Supplies"` paths, so a
  parent and its leaves go in one file). Add the ru/hy pair to
  `scripts/translate-categories.py` and run it afterwards.
- `POST /attributes` `{code, name}` (defaults isVariant/isFilterable true);
  `PUT /attributes/<id>` renames in place (values, family membership survive).
  `POST /attribute-values` `{attribute_id, value, label}`. Only on explicit
  user request — `/manage-attributes`.
- **Attribute-family writes use `attribute_ids`**, not `attributes`
  (`{name, code, sortOrder, attribute_ids:[…]}`); an `attributes` array is
  silently ignored and you get an empty family with 201.
- Refresh the pickable menu after the user edits values:
  `scripts/refresh-attributes.sh` → `reference/attribute-values.json`.

## Live reference ids (demo, after the 2026-08-12 rebuild; `scripts/ids.sh` wins)

**Categories** (live 2026-09-10): 1 Dog → {2 Food → [3 Dry Food, 4 Wet Food,
5 Health Condition], 6 Treat → [7 Dog Bones, Bully Sticks & Chews], 15 Toys →
[17 Plush, 18 Latex & Rubber, 19 Rope & Tug, 20 Fetch & Retrieve, 21 Chew &
Dental, 22 Activity & Intelligence]}; 8 Cat → {9 Food → [10 Dry Food, 11 Wet
Food], 14 Treat, 16 Toys → [23 Mice & Animals, 24 Balls, 25 Catnip, 26
Activity & Intelligence], 34 Grooming → [35 Brushes & Combs, 36 Shampoos &
Conditioners, 37 Grooming Tools, 38 Paw & Nail Care, 39 Ear Care, 40 Skin
Care]}; 13 Accessories (empty). Dog also has 27 Grooming →
[28 Brushes & Combs, 29 Shampoos & Conditioners, 30 Grooming Tools, 31 Paw &
Nail Care, 32 Ear Care, 33 Skin Care] (both Grooming trees mirror Chewy,
created 2026-09-10 on user approval).
**Health & Pharmacy** (Chewy menu, 2026-09-10): Dog 41 → [42 Flea & Tick,
43 Vitamins & Supplements, 44 Probiotics & Digestive Health, 45 Allergy & Itch
Relief, 46 Heartworm & Dewormers, 47 Pharmacy & Prescriptions, 48 Anxiety &
Calming Care, 49 Test Kits]; Cat 50 → [51 Flea & Tick, 52 Vitamins &
Supplements, 53 Probiotics & Digestive Health, 54 Allergy & Itch Relief,
55 Pharmacy & Prescriptions, 56 Anxiety & Calming Care, 57 Urinary Tract &
Kidneys, 58 Test Kits]. The flat **12 Vitamins & Supplements was deleted**
(empty) — supplements go in 43 / 52.
**Cat Litter** 59 → [60 Clumping, 61 Scented, 62 Unscented, 63 Natural,
64 Lightweight, 65 Crystal]; **Cat Supplies** 66 → [67 Litter Boxes &
Accessories, 79 Collars, Leashes & Harnesses]; **Cat Trees, Condos &
Scratchers** 80 → [81 Scratchers & Scratching Posts].
**Dog Supplies / Cleaning & Potty** (Chewy menu, created 2026-09-11 on user
approval to unblock 208 rows of the 2026-09-11 run):
Dog 68 Supplies → [69 Collars, Leashes & Harnesses, 70 Bowls & Feeders,
71 Beds, 72 Clothing & Accessories, 73 Carriers & Travel, 74 Training &
Behavior]; Dog 75 Cleaning & Potty → [76 Pee Pads & Diapers, 77 Poop Bags &
Scoopers, 78 Cleaners & Stain Removers]. Only the leaves those rows fill were
created — Chewy's empty ones (Crates/Pens & Gates, Tech & Smart Home, Vacuums
& Steam Cleaners, Cat Beds/Carriers/Bowls, Trees & Condos, Wall Shelves,
Window Perches) were deliberately left out. 13 Accessories is now empty but
kept (it is not a product category — `forProducts` omits it).
Every category has `ru`/`hy` names (`scripts/translate-categories.py`).
**Products are filed in a leaf**, never a parent (`scripts/archive/recategorize-toys.py`
re-filed the first toy import).

**Brands**: 1 Acana, 2 Belcando, 3 Brit, 4 Canvit, 5 Monge, 6 Orijen, 7
Royal Canin, 8 Trixie, 9 Farmina, 10 Schesir, 11 Leonardo, 12 Stuzzy, 13
Bewi Dog, 14 Bewi Cat, 15 Dogland, 16 Ok-Lock, 17 Club 4 Paws, 18 Gemon, 19
Simba, 20 Lechat, 21 Special Dog, 22 Rolf Club, 23 Inspector, 24 Gelmintal,
25 Insectal, 26 Cliny, 27 Mr. Fresh, 28 Comfy, 29 Iv San Bernard, 30
Beaphar, 31 8in1, 32 Mooor, 33 KorMell, 34 Justin, 35 Myau, **36 Versele-Laga,
37 Mnyams, 38 Derevenskie Lakomstva, 39 flexi, 40 Eco-Premium, 41 Kaskad,
42 Pchelodar** (added 2026-09-17, `reference/brand-sites.md` has the sites).

**Attribute families** (after the 2026-09-10 Chewy sync): 1 Dry Food
`[product-weight, flavor, breed-size, lifestage, special-diet, health-feature,
packaging, ingredient]`, 2 Wet Food `[product-weight, flavor, lifestage,
texture, special-diet, health-feature, packaging, ingredient]`, 3 Treats
`[product-weight, flavor, lifestage, special-diet, health-feature, breed-size,
packaging, ingredient]`, 4 Supplements `[food-form, product-weight, lifestage,
health-feature, packaging, product-form, active-ingredient, special-diet,
flavor, breed-size, material]`, 5 Toys `[toy-type, material, toy-feature,
color-family, lifestage, breed-size, toy-size]`, 7 Grooming `[size,
color-family, product-weight, material, breed-size, product-form,
active-ingredient, health-feature]`, 8 Accessories `[size, color-family,
material, product-weight, breed-size, pet-weight-range, product-form]`,
9 Litter `[product-weight, material, product-form, health-feature]` (read
live 2026-09-23; there is no family 6). A row whose
product-type skill names a family that isn't in this list yet must have it
created first, never left empty (rule 8b).

**Attributes** — the vocabulary now replicates Chewy's filters
(`reference/chewy-attributes.json`, applied by `scripts/sync-attributes.py`,
2026-09-10): 1 `product-weight` (pack weight, never "Size"; also volumes `5 l`
190 / `8 l` 191), 2 `food-form` (15), 3 `lifestage` (6, incl. Nursing),
4 `breed-size` (6), 5 `flavor` (76), 6 `special-diet` (45), 7 `health-feature`
(52), 8 `texture` (10, ours), 9 `packaging` (12), 11 `toy-type` (9, ours —
drives the toy leaf category), 12 `material` (49), 13 `toy-feature` (35),
15 `color-family` (24), **16 `toy-size`** (42, `isFilterable: false` — variant
axis only, hidden from the sidebar; set the flag with the snake_case key
`is_filterable` too or the PUT is a no-op), 17 `ingredient` (69),
18 `product-form` (35), 19 `active-ingredient` (107),
**27 `pet-weight-range`** (7, added 2026-09-12 — the dose band printed on
antiparasitic drops/tablets, `1–4 kg` … `10–25 kg`; filterable) and
**28 `size`** (59, added 2026-09-12 — the accessory variant axis: letter sizes
`XXS–XS` 702 … `XL` 713 for collars, harnesses, leads and apparel, and
measurement strings `0.45 l/ø 19 cm`, `9 × 15 cm`, `4 × 20 bags` for bowls,
brushes and packs; `isFilterable: false`, same call as `toy-size`, because the
value set is deliberately mixed). Values we had that Chewy
lacks were kept (Hypoallergenic, Monoprotein, Sterilised; Herring, Fish,
Seabass…; Plush, Paper Cord, Cotton/Polyester; Massages Gums, With Bell…).
Deleted 2026-09-10 on the user's ask: 10 `7015`/"test"; 14 (the first
`toy-size`) was deleted then recreated as 16 and restored onto every toy
variant from its label (`scripts/restore-toy-size.py`). `DELETE
/attributes/<id>` → 204; variants referencing it silently lose the key. **Multi-value is not supported**: `attribute_value_ids.<code>` must
be an integer — an array 422s (verified 2026-09-10). User decision: stay
single-valued for now.

**New values from the 2026-09-16 variant merge** (`scripts/plan-variant-merge.py`,
`reference/product-rules.md` → "Sibling products"): 9 antiparasitic dose
bands on `pet-weight-range` 27 (`up to 4 kg` … `40–60 kg`, ids 830–838),
collar lengths 40/65/75 cm on `size` 28 (839–841), flavour `Horse` on
`flavor` (842), colours Aqua / Blush / Sage on `color-family` (843–845 — Trixie's
palette needed them because royal blue/aqua and fuchsia/blush both mapped
onto plain Blue/Pink), bowl capacities on `size` (846–854) and toy sizes on
`toy-size` (855–859). All with ru/hy —
`scripts/translate-attribute-values.py <ids>` writes just the new ones,
`translate-attributes.py` rewrites everything.

## Open dev questions (for the backend team)

- media endpoint should reject/sanitise unservable filenames
- storefront should composite transparency on white, not black
- media ids should not be reusable
- multi-variant product with no distinguishing attributes should 422
- attribute-family endpoint should 422 an unknown/echoed key
- category listing renders one card per **variant**; collapse to product?
- importer-side: assert price vs cost before writing (we do this in scripts)
