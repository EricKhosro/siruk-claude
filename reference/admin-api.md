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

## The catalog model (live on demo since 2026-09-29)

Source of truth: siruk-web `docs/catalog-model.md` and `docs/inventory-model.md`
(`git -C ~/Documents/Projects/siruk-web show origin/main:docs/<file>`). The
admin form's own body builder is `backend/resources/js/catalog/products/variantPayload.js`;
ours is `scripts/siruk_payload.py`, which mirrors it — every writer goes through it.
The 2026-09-25 interim model (`unit` / `net_quantity`, derived `product-weight`)
and the 2026-08-12 one (`pricing_type` fixed/per_kg, `price_per_kg`, `weight`)
are both gone; notes that mention them are history.

## Product create — `POST /products`

Required: `name`, `slug`, `brand_id`, **`attribute_family_id`** (the product
type — required now), `category_ids[]` (an **array, often more than one id**;
see "Multiple categories per product" in `reference/product-rules.md`),
`variants[]` (≥ 1, exactly one `is_default`). Optional: `is_best_seller`,
`is_on_sale`, `is_discontinued`, `show_unit_price`. Variant:

```
{sku (unique catalogue-wide), name (label, single-language),
 about_this_item / ingredient_information / feeding_instructions (HTML),
 price (AMD, > 0, multiple of 10 — the PACK price; for sale_mode weight the price per kg),
 cost_price, compare_at_price (> price), min_allowed_price,
 sale_mode: "pack" | "weight",
 measure_type: "mass" | "volume" | "count" | null,   # pack only; required with content
 content: number (g / ml / pcs; ≤ 3 decimals, whole for count),  # one item
 pack_count: int ≥ 1 (12 for "12 × 85 g"),
 qty_max (per-order cap), qty_min/qty_step (weight only, grams),
 initial_stock, initial_stock_warehouse_id, initial_stock_unit_cost   # NEW variants only
 track_inventory, out_of_stock_policy (deny|backorder|dropship), backorder_lead_days,
 low_stock_threshold, reorder_point, reorder_qty,
 is_default, sort_order, images: [mediaId…],
 attribute_values: {"<attribute id>": [valueId, …]} }
```

**Refused (422, `prohibited`)**: `unit`, `net_quantity`, `item_content`
(server-derived from `content`), `stock`, `vendor_stock`, `min_quantity`,
`quantity_step`, `max_quantity`, `attribute_value_ids`, `options`, and
`initial_stock*` on an existing variant; `qty_min`/`qty_step` on a pack
variant. `pricing_type`/`price_per_kg`/`weight` are not accepted fields any more.

Read-only on GET (never send back — `to_variant_payload` strips them):
`item_content` (mg/µl), `size_label` ("1.25 kg"), `unit_price` +
`formatted_unit_price` ("1,680 ֏/kg"), `available_quantity`, `stock_levels[]`,
`stock_status`, `is_purchasable`, `last_cost_*`, `stock_unit_locked`,
`delete_locked`, `attribute_value_labels`. `suppliers[]` is writable but we
never send it (an absent key leaves the rows alone; suppliers are out of scope).

`DELETE /products/<id>` → 204. **Archiving a variant** (2026-10-07): a variant
with stock history or orders now carries `will_archive: true` — leaving it out
of the product PUT moves it to the form's "Archived variants" (restorable)
instead of deleting it; any `stock_to_write_off` on hand is written off. Still
build the body with `siruk_payload.put_body` and drop the variant from it
(`runs/2026-10-07-archive-rc-cases/archive.py` did the 22 RC cases).
`delete_locked` + `delete_blockers` mark a variant that can't go even so.

### Size (net content)

`measure_type` + `content` + `pack_count` on the variant; the server stores
`item_content` in mg / µl / pcs and `net_content = item_content × pack_count`,
builds the label ("12 × 85 g", "0.4 ml", "10 pcs") and the rate
(`UnitPriceResolver`: per kg / 100 g / L / 100 ml by the type's
`unit_price_basis`, else the smallest-pack rule; hidden for `count`, when
`show_unit_price` is off, or when the rate equals the price). The product
type's `measure_type` pre-fills new variants; a variant may differ (a
supplement's tablets are `count` while the type is `volume`). The type's
measure can only change once no variant holds a size in another measure.
Total content cap: 100 kg / 100 L / 100,000 pcs. `sale_mode: weight` (loose
food, price per kg, `qty_step`/`qty_min` in grams) has no content; none
exists yet.

### Variants and attributes

- `attribute_values` is keyed by **attribute id**; each list holds value ids.
  `siruk_payload.py` also takes attribute codes and converts them.
- The product type decides everything: an attribute outside the product's
  type is refused; an `option`-role attribute holds at most one value per
  variant (exactly one if `is_required`); an `attribute`-role one holds one
  unless its `input_type` is `multiselect`; required attributes must be set.
  Switching a product's type is refused while its variants hold values the
  new type lacks.
- **Option signature**: sha1 of a variant's option-role value ids plus its
  size, unique per product. Two variants with the same options and size
  can't coexist (the second gets no signature and can't be selected on the
  storefront — product 480, audit 2026-09-30). Spec-role values never tell
  variants apart.
- The storefront selector is built by `VariantOptionsBuilder` from the
  content group plus every option-role attribute of the type that any
  variant uses; a group is *selectable* only if it really varies, otherwise
  it's a fixed tile. A variant missing a value for a selectable group makes
  that tile row vanish when it is selected — so an option used on one
  variant must be set on all (rule 9a; `siruk_payload.py` refuses a new
  variant that breaks this). Read what the shop sees:
  `GET https://demo-api.siruk.am/api/products/<id>` → `optionGroups` and each
  variant's `options`.

## Bulk create — `POST /products/bulk` (siruk-web 6af3eeb9, 2026-10-01)

`ProductController::bulkStore` → `ProductBulkCreateService`. **Not on demo yet**
(2026-10-01: `Cannot POST /api/admin/products/bulk`). Body `{"products": [<a POST
/products body>, …]}`, 1 to `catalog.bulk_create_max` (100) items. Over the cap or empty
→ 422 for the whole batch. Otherwise always **200**, one result per item, in order:

```
{"data": [{"index": 0, "status": "created", "id": 1234, "slug": "…"},
          {"index": 1, "status": "failed", "errors": {"variants.0.price": ["…"]}}],
 "summary": {"created": 1, "failed": 1}}
```

- Each item is validated by `ProductRequest` and saved on its own. A failed item
  leaves nothing behind and never blocks the others; an unexpected server error fails
  only that item (`{"product": ["The product could not be saved."]}`).
- A slug or SKU repeated **inside the batch** fails the later item ("duplicates item #n").
- **Translations inline**: product `name` and the variant texts (`about_this_item`,
  `ingredient_information`, `feeding_instructions`) may be `{"en","hy","ru"}` objects.
  `en` is required for the name, other keys are refused, and the name is ≤ 255 per
  locale. A plain string is stored in the request's `Content-Language` locale. So a
  bulk create needs no `set-translation.py` afterwards.
- Variant `images` attach to their variant, as in `POST /products`.
- Creates only. Adding a variant to a live product is still `add-variant.sh`.

Our writer: `scripts/bulk-create.py` (create-product.sh's pre-flight per item, chunked by
`config.json → bulk`, never auto-retried, read-back + `verify-translations.py`).

## Product types — `/attribute-families`

The admin calls them **Product types**; the API/DB keep "attribute family".
`GET /attribute-families[/<id>]` →
`{id, name, code, defaultSaleMode, measureType, unitPriceBasis,
lowStockThreshold, lowStockGrams, attributes:[{id, code, name, inputType,
role, isRequired, isFilterable, showOnProductCard, position}], guards}` —
`guards` (single GET) says what a change would run into per attribute.
Write: `POST` / `PUT` `{name, code, default_sale_mode, measure_type,
unit_price_basis, low_stock_threshold, low_stock_grams, attributes:[{id,
role: option|attribute, is_required, is_filterable, show_on_product_card}]}`.
**`attributes` replaces the whole set** (array order = position; a flag left
out keeps the row's saved value, a newly attached attribute starts from the
attribute's own default flags) — GET first, re-send every row. The old
`attribute_ids` key is ignored now. Refused: removing an attribute still in
use, promoting to `option` while a variant holds two values, requiring an
attribute some variant lacks, a demotion that makes variants identical, a
measure change while variants hold other-measure sizes. **Category filters
come from `is_filterable` on the types of the products in that category**
(a type belongs to products, not to categories). Live snapshot:
`reference/product-types.json` (`scripts/product-types.py --dump`); creating
and extending types before an import: the `attribute-manager` agent.

## Stock — a ledger (`StockService` is its only writer)

Tables: `warehouses` (seed `main`, id 1, type `own`), `stock_levels`
(on_hand, allocated per variant × warehouse; available = on_hand −
allocated), append-only `stock_movements`. Placing an order allocates;
DELIVERED ships (on_hand −); cancel releases.

- New variant: `initial_stock` (+ optional `initial_stock_warehouse_id`,
  `initial_stock_unit_cost`) on the product create/PUT → a `receipt`
  movement "Initial stock (product form)". Our placeholder (user 2026-10-01):
  **10 on every pack variant, 10000 g on a weight variant**, whatever the CSV
  Qty — production was levelled to that on 2026-10-01
  (`runs/2026-10-01-fix/stock.py`).
- **A variant with any stock history can't be deleted or switched pack ↔
  weight** (`delete_locked` / `stock_unit_locked`, computed: stock ≠ 0, any
  movement, order, cart …; `ProductRequest.php`). Setting stock to 0 never
  unlocks it. To retire one: stock → its allocation via `/stock/variants`,
  then archive it (leave it out of the PUT — see "Archiving a variant" above). Lowering `on_hand`
  under `allocated` is refused.
- Existing variant: never through the product PUT.
  `PUT /stock/variants/<v>` `{warehouse_id, on_hand, reason, note}` (set a
  count; reasons: correction, damaged, lost, found, expired, write_off),
  `POST /stock/variants/<v>/receive` `{warehouse_id, quantity, unit_cost?, note?}`,
  `POST /stock/variants/<v>/write-off` `{warehouse_id, quantity, reason, note}`,
  `GET /stock/variants/<v>/movements`. Screens: Inventory → Stock (also
  warehouses, suppliers, purchase orders, transfers, counts, reports — out
  of scope for imports).
- Per-variant policy fields on the product form: `track_inventory` (default
  true), `out_of_stock_policy` (default deny), `low_stock_threshold`,
  `reorder_point`, `reorder_qty`. Leave them at the defaults unless asked.

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

### Folders, listing, moving (found 2026-09-23)

The admin panel and its API are `/Users/conceptmacmini01/Documents/Projects/siruk-web`
(read `origin/main`): routes in `backend/routes/admin.php`, media in
`backend/app/Http/Controllers/Admin/Common/MediaController.php` +
`MediaFolderController`, screens in `backend/resources/js/`. Copy its calls, don't guess.

- **Folders are records**: `GET /media-folders` (tree, `{id,name,path,parentId,children}`),
  `POST /media-folders {name, parentId}` (server derives `path` from the name —
  "Royal Canin" under `null` → `royal-canin`), `PUT`/`DELETE /media-folders/<id>`
  (delete refuses a folder with files). An upload's `directory` with no folder
  record still stores the file, but the media library never shows it — use
  `scripts/media-folder.py`. Layout: `products/<brand-slug>/<type>/`, `logos/`,
  `categories/`, `banners/`. `PUT /media-folders/<id> {name, parentId}`
  re-parents a folder **and moves its files** (url changes with the path).
- **Listing**: `GET /medias?directory=<path>&acceptTypes=<types>` — direct
  children only (`''` = root). `acceptTypes` is **one comma-joined, url-encoded
  string** (`image%2Fjpeg%2Cimage%2Fpng…`, what `Api.serializeParams` sends).
  `acceptTypes[]=…` makes it an array and the backend 500s (and logs an error
  the devs see); leaving it out returns an empty `data`. Filters on the stored
  mime type, so a text/html record (an uploaded 404 page) never lists.
- **Move**: `POST /medias-move {ids:[…], directory}` → the moved records. Ids
  are kept, so product galleries follow; the original's url changes to
  `storage/<directory>/<file>` (old url 404s). The `-adminThumbnail` and webp
  rows stay in `thumbnails/` and `webp/`. `scripts/organize-media.py`.
  Also `medias-copy` (same body), `medias-crop`, `medias-replace`,
  `medias-change-dimensions`, `medias-download`.

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
- `POST /attributes` `{code, name, input_type (select|multiselect|boolean|number|text),
  unit?, is_filterable, show_on_product_card}` — the flags are only defaults
  for a new product-type row; `PUT /attributes/<id>` renames in place.
  `POST /attribute-values` `{attribute_id, value, label, sort_order?}` —
  `value` is the **code**, a slug `^[a-z0-9]+(?:-[a-z0-9]+)*$` unique within
  the attribute (20 old Toy Type / Material codes aren't, audit 2026-09-30).
  A value used by a variant can't be deleted. Only on explicit user request
  — `/manage-attributes` — except what a batch's product types need (8b).
- Product-type writes: see "Product types" above (`attributes:[{id, role, …}]`;
  `attribute_ids` is ignored).
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
**Bird / Small Animal** (created 2026-09-28 on user approval for the sirook.pdf
invoice): Bird 95 → [96 Food, 97 Treats & Supplements]; Small Animal 98 →
[99 Food, 100 Hay, 101 Treats, 102 Supplements & Salt Licks, 103 Bedding].
Bird/rodent food uses family 1 Dry Food, snacks 3 Treats, mineral/salt stones
4 Supplements, bedding 9 Litter. `create-category.py` takes `"parent": null`
for a new top-level pet.
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
42 Pchelodar** (added 2026-09-17, `reference/brand-sites.md` has the sites),
**43 Dogman, 44 Inteko** (added 2026-09-23; Inteko has no logo — no official site found).

**Attribute families** (after the 2026-09-10 Chewy sync): 1 Dry Food
`[product-weight, flavor, breed-size, lifestage, special-diet, health-feature,
packaging, ingredient]`, 2 Wet Food `[product-weight, flavor, lifestage,
texture, special-diet, health-feature, packaging, ingredient]`, 3 Treats
`[product-weight, flavor, lifestage, special-diet, health-feature, breed-size,
packaging, ingredient]`, 4 Supplements `[food-form, product-weight, lifestage,
health-feature, packaging, product-form, active-ingredient, special-diet,
flavor, breed-size, material, pet-weight-range]` (pet-weight-range added 2026-09-23 — 37 dewormer variants already carried it), 5 Toys `[toy-type, material, toy-feature,
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
