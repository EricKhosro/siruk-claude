# Siruk PetShop — Product Import Automation

Goal: given a CSV of product names, find each product on **its brand's official
website**, extract its data (title, images, description, variants, etc.), and
create the product in the Siruk admin panel. This project is the
investigation/POC for the Jira task "Investigate AI Automation for Admin Panel
Data Filling".

> Data source changed from Chewy → brand official sites. Chewy is blocked by
> Kasada anti-bot (HTTP 429, no content) AND is a poor match for this catalog's
> European brands. See `INVESTIGATION.md`. Brand sites are richer, legal, and
> mostly not bot-protected.

## Environments & credentials

- Admin panel (demo): `https://demo-api.siruk.am/admin/login`
  - email: `dev@conceptstudio.club`
  - password: `C6iA7HLmHU00v/0`
  - This is a demo environment. For production, request a dedicated service
    account with catalog-only permissions instead of a personal login.
- Product create page: `https://demo-api.siruk.am/admin/catalog/products/create`
- Source: the **brand's official website** (see brand→site map below). Pick the
  site from the row's `Brand / Vendor`, search/browse to the matching product,
  extract from the product page. **Read-only**: never add to cart, never create
  an account, never interact with checkout.

### Brand → official site map

Resolve the site from the CSV `Brand / Vendor` (the part before `/` is the
brand; the part after is the local distributor — ignore it for sourcing).

| Brand | Official site | Search approach |
|---|---|---|
| Brit | `https://brit-petfood.com` | Site search or Products menu; also `brit-petfood.com/en/` |
| Royal Canin | `https://www.royalcanin.com` | Country picker → product finder; `/us/` catalog is richest |
| Farmina | `https://www.farmina.com` | Product catalog (N&D, Matisse, Ecopet lines) |
| Belcando | `https://www.belcando.de` (EN: `/en/`) | Bewital Petfood; product finder |
| Leonardo | `https://www.leonardo-catfood.com` | Bewital; same group as Belcando |
| Canvit | `https://www.canvit.com` (EN: `/en/`) | Supplements catalog |
| Schesir | `https://www.schesir.com` | Agras Delic; cat/dog wet lines |
| Stuzzy | `https://www.stuzzy.com` | Agras Delic; same group as Schesir |

If a brand isn't in this map, do a web search for `"<brand>" official site` and
use the manufacturer domain (not a retailer/marketplace). Record any new brand
site back into this table.

Fallback when the official site lacks a product page, a search UI, or blocks
automation: try (1) the local distributor's catalog, (2) a general web/image
search for the exact product to gather title/description/image, and flag the row
as "sourced from fallback" in the report. Never fabricate specs or ingredients —
leave a field empty rather than guess.

## Two integration paths

### 1. Backend API (preferred — token-efficient)

The admin SPA talks to a Laravel JSON API at `https://demo-api.siruk.am/api/admin/*`.

**Use `scripts/` — do not re-type curl/jq pipelines inline.** Bash + curl + jq,
committed and debuggable, documented in `scripts/README.md`:

| Script | Use |
|---|---|
| `scripts/api.sh METHOD PATH [payload.json\|-]` | any ad-hoc call |
| `scripts/ids.sh` | live brands / categories / families / attributes ids (trust over the list below) |
| `scripts/refresh-attributes.sh` | regenerate `reference/attribute-values.json` |
| `scripts/find-product.sh <text>` | **before every create** — does it exist already? |
| `scripts/show-product.sh <id> [--json]` | variant summary / full re-postable body |
| `scripts/create-product.sh <payload.json>` | validate → POST → verify |
| `scripts/add-variant.sh <id> <variant.json>` | GET → append → guard → PUT → verify |
| `scripts/upload-media.sh <file\|url> [dir]` | download w/ browser UA, upload, print media id |

Token lives in `.siruk-token` (repo root, gitignored) so it survives reboots —
capture it once from the SPA console (`scripts/README.md` has the steps). Scripts
read `SIRUK_TOKEN` env first, then that file. Working files/diffs land in
`.siruk-cache/` (gitignored).

- Auth: `Authorization: Bearer <JWT>` — **cookies alone do NOT authenticate the
  API**. The SPA stores the token in `localStorage.access_token` as JSON:
  `{"token":"eyJ..."}`. Tokens are long-lived (~1 year exp).
  To get a token without the browser, capture it once from the logged-in SPA
  (`JSON.parse(localStorage.access_token).token`) or ask backend team for the
  login endpoint / a personal access token.
- Endpoints observed (all `GET` verified working, JSON `{"data":[...]}`):
  - `GET /api/admin/categories?forProducts=true`
  - `GET /api/admin/brands?forProducts=true`
  - `GET /api/admin/attributes?forProducts=true`
  - `GET /api/admin/attribute-families?forProducts=true`
  - `GET /api/admin/medias?acceptTypes=...&directory=` (media library)
  - `GET /api/admin/account`, `GET /api/admin/roles`
- **Media upload** (verified): `POST /api/admin/medias`, `multipart/form-data`,
  two parts: `file` (binary, with filename) and `fileInfo` (JSON string:
  `{"filename","caption","alt","dimensions":"WxH","directory":""}`). Returns
  `{"data":{"id",...}}`. Use the returned `id` as the media reference elsewhere.
  From the browser use `fetch` with a `FormData` (don't set content-type). A
  JSON body or a missing `fileInfo` part → 500 "Attempt to read property filename
  on null". `directory` "" = root.
- ⚠️ **Product images must be opaque — never upload a transparent PNG.** The
  storefront gallery composites transparency onto a **black** backdrop, so a
  brand's transparent packshot renders on black (found 2026-08-12 on the Brit
  import; Royal Canin was unaffected only because its packshots are JPEGs).
  `scripts/upload-media.sh` now detects an alpha channel and flattens it onto
  white via `sips -s format jpeg` before uploading (`KEEP_ALPHA=1` opts out —
  use it for brand logos that should stay transparent). Brand PNGs are the norm,
  so this applies to most sites. *Dev question:* should the storefront composite
  transparent images on white instead of black?
- **Brand create** (verified): `POST /api/admin/brands` JSON
  `{name, slug, image:<mediaId>, meta:{title,description}}`. Required: name, slug
  (image optional at API level, though the UI marks it required). Returns id.
  Don't hand-roll it — `scripts/create-brand.sh "<Name>" <logo url|file>` dedupes
  against the live list, uploads the logo and verifies; the `/create-brand` skill
  covers finding a proper official logo first.
- **Category create** (verified): `POST /api/admin/categories` JSON
  `{parent_id:<id|null>, name, slug, description, quick_links:[], meta:{...}}`.
  Required: name, slug.
- **Product create** (verified): `POST /api/admin/products` JSON. Required
  top-level: `name`, `slug`, `category_ids` (array). Also send `brand_id`,
  `attribute_family_id` (nullable), `is_best_seller`, `is_on_sale`, `variants`.
  Variants may be `[]` (product saves), but each variant present requires `sku`
  plus a pricing shape (see **Pricing type** below). Full variant shape (from an existing
  product):
  `{name, about_this_item(HTML), ingredient_information(HTML),
    feeding_instructions(HTML), pricing_type:"fixed", sku, price(int AMD),
    price_per_kg, min_allowed_price, cost_price(int AMD), compare_at_price,
    weight, is_default:true, stock(int), vendor_stock:bool, sort_order:0,
    images:[mediaId,...], attribute_value_ids:{<code>:<valueId>}}`.
  Prices are integers in AMD (e.g. 26500). `images` are media ids (upload first).
  `weight` is **kilograms** — all weights in this project are metric,
  kilogram-based, never lbs/oz (convert US sources: `lb x 0.4536`).
- **Pricing type** (verified 2026-08-12) — `pricing_type` accepts exactly
  **`fixed`** or **`per_kg`**; anything else 422s ("The selected
  variants.N.pricing_type is invalid"):
  - **`fixed`** — sold by the unit (pouch, can, multipack, tin): send `price`
    (int AMD). What we did before.
  - **`per_kg`** — **sold by weight** (dry kibble in a bag; admin form: Pricing
    type = "priced by weight", Rate per Kg, Pack weight): send
    `price_per_kg` + `weight` (kg). **`price` is IGNORED and stored as 0**, so the
    rate has to reproduce the pack price: `price_per_kg = CSV price / weight`.
    Only **2 decimals** are stored (4666.666… → 4666.67), which keeps the
    recomputed pack price within a few hundredths of an AMD.
  - On a `per_kg` variant **do not set the `product-weight` attribute** — the
    admin derives the weight from Pack weight (user rule 2026-08-12).
    ⚠️ Exception forced by the API: if a product's variants differ *only* by pack
    size, dropping `product-weight` makes their attribute combinations identical
    and the API refuses the second variant — keep it there and flag it (see the
    dev question in `reference/data-tables.md` table 4).
  **Each variant needs a unique `attribute_value_ids` combination** — the API
  rejects two variants with identical attributes ("This attribute combination is
  already used in variant N"), so every variant axis you use must be backed by an
  attribute value that actually differs (verified 2026-08-12).
  Attributes are OPTIONAL — omit `attribute_value_ids` to skip; to set them you
  need existing attribute-value ids (see `GET /api/admin/attribute-values`) or
  create values first. `DELETE /api/admin/products/<id>` → 204 to remove.
  Read: `GET /api/admin/products/<id>` returns `{data:{...variants[...]}}`.
- **Product search** (verified 2026-08-12): `GET /api/admin/products?search=<text>`
  matches product names (`{"data":[...]}`, paginated). Other query names
  (`q`, `keyword`, `name`, `filter[name]`) are **silently ignored** and return
  everything — only `search` filters. Empty catalog → `{"data":[]}`.
- **Product update / add a variant** (verified 2026-08-12):
  `PUT /api/admin/products/<id>` (PATCH behaves the same) with the same JSON
  shape as create. `GET /api/admin/products/<id>` returns a directly re-postable
  body whose variants each carry an `id`; append the new variant (no `id`) to
  that array and PUT it back → 200, existing variant ids preserved.
  ⚠️ **PUT replaces the whole variants array**: a variant omitted from the
  payload is deleted (200, silent) — or 422 if the omitted one was
  `is_default`. Always build the PUT body from a fresh GET.
  **Before creating any product, `search` for it first** — if it exists, add the
  row as a variant instead of creating a second product (rules in
  `reference/data-tables.md` → "Adding a variant to a product that already
  exists").
- Images: source product image URLs are downloaded (curl) and uploaded to the
  media library via the media endpoint above, then referenced by media id.
- **Auth note:** the API needs `Authorization: Bearer <JWT>`; cookies alone fail.
  From the logged-in SPA: `JSON.parse(localStorage.access_token).token`, saved to
  `.siruk-token` in the repo root (gitignored) — capture it once, not per
  session. Verify with `scripts/api.sh GET /account`. No UI form-filling is
  needed once payloads are known.
- **WAF note:** the demo WAF returns 403 for the default `Python-urllib`
  User-Agent. curl's default UA is fine; Python scripts must set a UA header.
- **Attribute-value create** (verified 2026-08-11): `POST /api/admin/attribute-values`
  JSON `{attribute_id, value, label}` → `{data:{id,...}}`. **Attribute create**
  (verified): `POST /api/admin/attributes` JSON `{code, name}` → defaults
  `isVariant/isFilterable: true`. **Attribute rename** (verified 2026-08-12):
  `PUT /api/admin/attributes/<id>` JSON `{code, name}` → renames in place;
  value ids, labels and family membership survive, and each value's derived
  `name` ("size: 85 g") re-derives from the new code. Use only on explicit user
  request — the user curates the vocabulary by hand (see Attributes note below).
- **Media delete** (verified 2026-08-12): `DELETE /api/admin/medias/<id>` → 200.
- **Refreshing the attribute menu** after the user edits values in the admin:
  `./scripts/refresh-attributes.sh` (atomic write — a failed fetch leaves the
  existing menu intact).

### ⚠️ BLOCKER: Chewy anti-bot (found 2026-08-10)

Chewy is behind **Kasada** bot protection. Every request from the
chrome-devtools MCP browser (search and direct `/dp/` product URLs alike)
returns **HTTP 429** and a challenge page (`KPSDK`/`ips.js`, `x-kpsdk-*`
headers); the real page body never renders (`document.body.innerText` empty).
Cause: the MCP drives an automation-flagged Chrome (`navigator.webdriver` ===
true, `--enable-automation`), which Kasada detects and blocks. Reloading, direct
product URLs, and waiting for the challenge to resolve all fail.

Chewy has **no public product API**. Options to unblock (need user decision):
1. Feed product data from another source (manufacturer sites, a data export,
   or user-provided data) instead of Chewy.
2. Use a stealth/anti-detect browser + residential proxies (real engineering
   effort, ongoing maintenance, and check Chewy ToS/legal before scraping).
3. A commercial scraping API that returns structured product data.
The admin-side API integration below is unaffected and ready.

### 2. Browser automation (fallback / POC)

Use chrome-devtools MCP (configured in `.mcp.json`, persistent profile so the
admin login survives between sessions—if launch fails with "browser already
running", kill the stale instance:
`pkill -f 'chrome-devtools-mcp/chrome-profile'`).

Token-efficiency rules for the browser path:
- Brand product pages are large. Never `take_snapshot` a source product page.
  Use `evaluate_script` to pull exactly the fields needed (see the
  `add-products` skill for the extraction script).
- On the admin side prefer `fill_form` (one call, many fields) over single fills.
- Screenshots only to show the user a final result, never for navigation.

## Admin product form — field map

Form at `/admin/catalog/products/create` (language switcher "En" top-left; Save button top-right):

| Admin field | Required | Source on brand site |
|---|---|---|
| Name | yes | Product title **without the brand** — the storefront prints the brand before the name, so "Royal Canin Mini" would render twice. Strip the brand/`RC ` prefix from the CSV name. Keep the CSV pack weight (e.g. "8kg") only while the product has a single variant |
| Slug | yes | kebab-case of **brand + Name** (`royal-canin-mini`) — slugs are global, so they keep the brand even though the Name does not |
| Categories (multi-select) | yes | From CSV `Category` → map to tree below (Dog/Cat + Dry/Wet/Treat/etc.) |
| Brand (select) | yes | CSV `Brand / Vendor` (must exist in admin — see list) |
| Attribute Family (select) | no | Pick matching family or leave empty |
| Variant: SKU | no→yes | Brand product/article code if shown, else `BRAND-SLUG-LIFESTAGE-WEIGHT` |
| Variant: Label | no | The varying axes only — flavor / texture / pack weight, e.g. "8 kg", "Gravy 12 x 85 g", "Tuna 85 g". **Weights metric (kg/g), never lbs** |
| Variant: Pricing type | yes | **"priced by weight"** for dry kibble sold by the kilo → fill Rate per Kg + Pack weight; **fixed** for anything bought as a unit (pouch/can/multipack/tin) |
| Variant: Price | yes (fixed only) | CSV `Sale Price (AMD)` |
| Variant: Rate per Kg + Pack weight | yes (priced by weight) | Pack weight from the CSV name; Rate per Kg = CSV `Sale Price (AMD)` ÷ pack weight |
| Variant: Cost price | no | CSV `Buy Price (AMD)` |
| Variant: Min price | no | Leave 0 unless CSV/Notes say otherwise |
| Variant: Stock | yes | CSV `Qty` (default `10` if empty) |
| Variant: Vendor stock / Default variant (switches) | no | First variant → Default variant ON |
| Variant images | yes | Brand product-page gallery images (jpeg/png/webp/avif/gif) |
| Variant attributes (selects; current set: **Product Weight** (`product-weight` — pack weight; never call this "Size"), Food Form, Lifestage, Breed Size, Flavor, Special Diet, Health Feature, Food Texture, Packaging Type — see `reference/attribute-redesign.md`) | no | Brand page specs / product attributes; only values from the menu, skip if no match. Translate brand wording using `reference/data-tables.md` (our definitions win over the brand's) |
| About this item (rich text) | no | Brand product description / benefits |
| Ingredient information (rich text) | no | Brand "Composition"/"Ingredients" section |
| Feeding instructions (rich text) | no | Brand "Feeding guide"/"Recommended daily amount" |
| Status flags: Best Seller / On Sale / Rx Required / Bundle / Discontinued | no | Rx Required if it's a veterinary/prescription diet; rest OFF unless CSV/Notes say |
| SEO Meta Title (≤60) / Meta Description (≤160) / Meta Image (1200x630) | no | Truncate name / first description sentence |

One CSV row = one product with one variant (the pack weight named in the row).
Add extra variants ("Add variant") when the CSV has several rows for the same
product differing only in **pack weight, flavor or texture**. Do NOT pull in
other pack weights/flavors the brand site lists but the CSV doesn't (no AMD
price).

**Always check whether the product already exists before creating it.**
`GET /api/admin/products?search=<line name>`; if there's a match, the row is a
new **variant** of it — GET the product, append the variant, `PUT` the full
variants array back (see the Product update note above and "Adding a variant to
a product that already exists" in `reference/data-tables.md`). Never create a
second product for something that belongs as a variant.

**Is it a variant or a new product?** See "Product vs variant" in
`reference/data-tables.md`. Short version — **the shelf test**: variants are the
same pack with a different option printed on it. **Variant axes: pack weight,
flavor, texture** (gravy/jelly/loaf/mousse). Everything that redesigns the pack
splits products: **lifestage, breed size, food form, special diet, health
feature** — so RC Mini Puppy 8kg and Mini Adult 8kg are two products, exactly as
Chewy lists them, while Sterilised in gravy + in jelly is one product with two
variants. The Name carries line + breed size + lifestage (+ pack weight/flavor/
texture while only one exists); labels carry the varying axes. Each variant needs
a **unique attribute combination** — the API rejects duplicates, so a flavor or
texture variant must have that attribute set. Unclear → separate products + flag
it. **The Name never contains the brand** (storefront shows it separately); the
slug does. **All weights are metric, kilogram-based — never lbs.**

## Reference data (demo env, re-fetched 2026-08-12 after the rebuild — refresh via API when stale)

⚠️ The wipe/rebuild **renumbered brands and categories**. Any id in a note or
report written before 2026-08-12 is wrong; use these.

- Categories (id: name): 1 Dog → {2 Food → [3 Dry Food, 4 Wet Food, 5 Health
  Condition], 6 Treat → [7 Dog Bones, Bully Sticks & Chews]}; 8 Cat → {9 Food
  → [10 Dry Food, 11 Wet Food]}; top-level 12 Vitamins & Supplements,
  13 Accessories (flat, matching the CSV Category column; restructure/nest under
  Dog/Cat later if desired).
- CSV category → admin id map: Dry food—Dogs→3, Wet food—Dogs→4,
  Dry food—Cats→10, Wet food—Cats→11, Treats—Dogs→6,
  Vitamins & supplements→12, Accessories→13.
- Brands: 1 Acana, 2 Belcando, 3 Brit, 4 Canvit, 5 Monge, 6 Orijen,
  7 Royal Canin, 8 Trixie, 9 Farmina, 10 Schesir, 11 Leonardo, 12 Stuzzy
  (the last 4 added for this CSV; Stuzzy currently reuses the Schesir/
  Agras-group logo as a placeholder — replace with a real Stuzzy logo).
- Attribute families: 1 Dry Food, 2 Wet Food, 3 Treats, 4 Supplements
  (contents in `reference/attribute-redesign.md`; all pre-wipe brand-named
  families are gone).
- **Our definitions of attribute concepts** (how Siruk understands Lifestage
  etc., and how to translate a brand site's wording/age bands into it) live in
  `reference/data-tables.md`. Consult it whenever filling those attributes —
  our definitions override the brand's. New tables get added there.
- Attributes/values/families: **rebuild done** (2026-08-11/12, per the
  2026-08-11 meeting decision). The live set is 9 attributes (ids 1–9), ~153
  values, 4 families, spec in `reference/attribute-redesign.md`; the pickable
  menu is `reference/attribute-values.json` (regenerate with the command above
  whenever the user edits attributes in the admin). Old ids in any
  notes/reports written before 2026-08-12 predate the wipe — do not use them.
  Do not create attributes/values via API without an explicit ask; the import
  reports "wanted but missing" values instead (see the add-products skill).
- **Attribute naming:** `product-weight` / "Product Weight" is the pack weight
  (renamed from `size`/"Size" on 2026-08-12 — Royal Canin's "Size" means breed
  size, so the word is banned for pack weight). Never name an attribute after a
  brand's word for it; translate via table 3 of `reference/data-tables.md`.
  **Open dev question:** can `special-diet`/`health-feature` hold multiple
  values per variant? (Chewy-style multi-tag filtering depends on it.)

If a product's **brand** doesn't exist in admin, create it with the
`/create-brand` skill (official logo → media library → `POST /brands`) and use
the returned id; note the creation in the run report. If its **category** doesn't
exist: do NOT invent one — flag it in the run report and skip that field or ask
the user.

## Input CSV

Columns: `#`, `Product Name`, `Brand / Vendor`, `Category`, `Buy Price (AMD)`,
`Sale Price (AMD)`, `Margin %`, `Qty`, `Total Cost (AMD)`, `Total (USD)`,
`Priority`, `Notes`. Headers may contain quoted newlines.

Mapping (CSV always wins over brand-site data):
- Product Name → brand-site search term + admin Name
- Brand / Vendor → Brand select + which official site to source from
- Category → admin Categories
- Buy Price (AMD) → variant Cost price
- Sale Price (AMD) → variant Price (prices are AMD; ignore any price on brand site)
- Qty → variant Stock
- Priority → import order (highest priority first)
- Notes → free-text hints (e.g. which pack weight/flavor variant to pick)
- Margin %, Total Cost (AMD), Total (USD) → ignore (derived)

The brand's official site supplies the rest: images, description/benefits,
composition/ingredients, feeding guide, spec attributes, product/article code.

**Known gaps in this CSV** (flag in the report, don't invent):
- Brands: all CSV brands now exist (Farmina, Schesir, Stuzzy and Leonardo were
  added 2026-08-12). Any brand still missing → `/create-brand`, don't skip the
  field. Stuzzy's logo is still the Schesir/Agras placeholder.
- CSV categories `Vitamins & supplements` and `Accessories` have no matching
  admin category (tree is only Dog/Cat → Food/Treat). Ask user where to file
  these or to add categories.

## Workflow

Attribute/value/family creation: use the `/manage-attributes` skill (or the
`attribute-manager` agent for big batches, e.g. the post-wipe rebuild from
`reference/attribute-redesign.md`). Missing brand: use the `/create-brand
<brand name>` skill (official logo → media library → brand). Product import: use
the `/add-products <csv path>` skill. Summary: get token → load the
attribute menu (`reference/attribute-values.json`) → for each CSV row: resolve
brand → official site (brand map above) → find the product on that site →
extract fields with one `evaluate_script` → **fill variant attributes from the
page text** (closed menu, evidence quotes, no guessing — rules in the skill) →
**`search` the catalog: exists → `PUT` the row on as a new variant; doesn't
exist → `POST` a new product** (categories from the CSV map +
`attribute_value_ids`) → verify via GET → next row. Write `runs/<date>-report.md`: per-product status,
attributes set/blank, flagged candidates, and "wanted but missing" vocabulary
questions for the user. Build roadmap and phase status live in `PLAN.md`.
