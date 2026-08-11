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
- **Brand create** (verified): `POST /api/admin/brands` JSON
  `{name, slug, image:<mediaId>, meta:{title,description}}`. Required: name, slug
  (image optional at API level, though the UI marks it required). Returns id.
- **Category create** (verified): `POST /api/admin/categories` JSON
  `{parent_id:<id|null>, name, slug, description, quick_links:[], meta:{...}}`.
  Required: name, slug.
- **Product create** (verified): `POST /api/admin/products` JSON. Required
  top-level: `name`, `slug`, `category_ids` (array). Also send `brand_id`,
  `attribute_family_id` (nullable), `is_best_seller`, `is_on_sale`, `variants`.
  Variants may be `[]` (product saves), but each variant present requires
  `sku`, `pricing_type:"fixed"`, `price`. Full variant shape (from an existing
  product):
  `{name, about_this_item(HTML), ingredient_information(HTML),
    feeding_instructions(HTML), pricing_type:"fixed", sku, price(int AMD),
    price_per_kg, min_allowed_price, cost_price(int AMD), compare_at_price,
    weight, is_default:true, stock(int), vendor_stock:bool, sort_order:0,
    images:[mediaId,...], attribute_value_ids:{<code>:<valueId>}}`.
  Prices are integers in AMD (e.g. 26500). `images` are media ids (upload first).
  Attributes are OPTIONAL — omit `attribute_value_ids` to skip; to set them you
  need existing attribute-value ids (see `GET /api/admin/attribute-values`) or
  create values first. `DELETE /api/admin/products/<id>` → 204 to remove.
  Read: `GET /api/admin/products/<id>` returns `{data:{...variants[...]}}`.
- Images: source product image URLs are downloaded (curl) and uploaded to the
  media library via the media endpoint above, then referenced by media id.
- **Auth note:** the API needs `Authorization: Bearer <JWT>`; cookies alone fail.
  From the logged-in SPA: `JSON.parse(localStorage.access_token).token`. All the
  create work above was driven from the browser console via `fetch` with that
  header — no UI form-filling needed once payloads are known.
- **WAF note:** the demo WAF returns 403 for the default `Python-urllib`
  User-Agent. curl's default UA is fine; Python scripts must set a UA header.
- **Attribute-value create** (verified 2026-08-11): `POST /api/admin/attribute-values`
  JSON `{attribute_id, value, label}` → `{data:{id,...}}`. **Attribute create**
  (verified): `POST /api/admin/attributes` JSON `{code, name}` → defaults
  `isVariant/isFilterable: true`. Use only on explicit user request — the user
  curates the vocabulary by hand (see Attributes note below).
- **Refreshing the attribute menu** after the user edits values in the admin
  (TOKEN = the Bearer JWT):
  `curl -s -H "Authorization: Bearer $TOKEN" "https://demo-api.siruk.am/api/admin/attributes?forProducts=true" | python3 -c 'import json,sys; d=json.load(sys.stdin)["data"]; json.dump({a["code"]:{"attribute_id":a["id"],"name":a["name"],"values":{v["label"]:v["id"] for v in a.get("values",[])}} for a in d}, open("reference/attribute-values.json","w"), ensure_ascii=False, indent=2)'

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
| Name | yes | Product title (keep the CSV size, e.g. "8kg", in the name) |
| Slug | yes | kebab-case of Name (lowercase, strip punctuation) |
| Categories (multi-select) | yes | From CSV `Category` → map to tree below (Dog/Cat + Dry/Wet/Treat/etc.) |
| Brand (select) | yes | CSV `Brand / Vendor` (must exist in admin — see list) |
| Attribute Family (select) | no | Pick matching family or leave empty |
| Variant: SKU | no→yes | Brand product/article code if shown, else `BRAND-SLUG-SIZE` |
| Variant: Label | no | Size/flavor label, e.g. "8 kg" (from CSV product name) |
| Variant: Price | yes | CSV `Sale Price (AMD)` |
| Variant: Cost price | no | CSV `Buy Price (AMD)` |
| Variant: Price per KG / Min price | no | Leave 0 unless CSV/Notes say otherwise |
| Variant: Stock | yes | CSV `Qty` (default `10` if empty) |
| Variant: Vendor stock / Default variant (switches) | no | First variant → Default variant ON |
| Variant images | yes | Brand product-page gallery images (jpeg/png/webp/avif/gif) |
| Variant attributes (selects; post-rebuild set: Size, Food Form, Lifestage, Breed Size, Flavor, Special Diet, Health Feature, Food Texture, Packaging Type — see `reference/attribute-redesign.md`) | no | Brand page specs / product attributes; only values from the menu, skip if no match |
| About this item (rich text) | no | Brand product description / benefits |
| Ingredient information (rich text) | no | Brand "Composition"/"Ingredients" section |
| Feeding instructions (rich text) | no | Brand "Feeding guide"/"Recommended daily amount" |
| Status flags: Best Seller / On Sale / Rx Required / Bundle / Discontinued | no | Rx Required if it's a veterinary/prescription diet; rest OFF unless CSV/Notes say |
| SEO Meta Title (≤60) / Meta Description (≤160) / Meta Image (1200x630) | no | Truncate name / first description sentence |

One CSV row = one product with one variant (the pack size named in the row).
Only add extra variants ("Add variant") if the CSV has multiple rows for the
same product in different sizes — merge those into one product. Do NOT pull in
other sizes the brand site lists but the CSV doesn't (no AMD price for them).

## Reference data (demo env, fetched 2026-08-10 — refresh via API when stale)

- Categories (id: name): 2 Dog → {4 Food → [6 Dry Food, 7 Wet Food, 13 Health
  Condition], 11 Treat → [12 Dog Bones, Bully Sticks & Chews]}; 3 Cat → {5 Food
  → [8 Dry Food, 9 Wet Food]}
- Brands: 6 Acana, 8 Belcando, 4 Brit, 9 Canvit, 3 Monge, 5 Orijen,
  2 Royal Canin, 7 Trixie, **11 Farmina, 12 Schesir, 13 Leonardo, 14 Stuzzy**
  (last 4 added 2026-08-10 for this CSV; Stuzzy currently reuses the Schesir/
  Agras-group logo as a placeholder — replace with a real Stuzzy logo).
- Added top-level categories (2026-08-10): **14 Vitamins & Supplements,
  15 Accessories** (flat, matching the CSV Category column; restructure/nest
  under Dog/Cat later if desired). CSV category → admin id map:
  Dry food—Dogs→6, Wet food—Dogs→7, Dry food—Cats→8, Wet food—Cats→9,
  Treats—Dogs→11, Vitamins & supplements→14, Accessories→15.
- Attribute families: pre-wipe families (Royal/Monge/Orijen Dry Food, Wet
  Food) are being deleted; the 4 replacements (Dry Food, Wet Food, Treats,
  Supplements) are defined in `reference/attribute-redesign.md`.
- Attributes/values/families: **being rebuilt from scratch** (meeting decision
  2026-08-11): the senior dev wipes all existing attributes, values, and
  families; the replacement system (9 attributes, ~150 values, 4 families,
  full Chewy parity) is specified in `reference/attribute-redesign.md` and
  gets created via the `/manage-attributes` skill / `attribute-manager` agent
  once the DB is clean. Old ids in any notes/reports predate the wipe — do not
  use them. After the rebuild, regenerate `reference/attribute-values.json`
  (command below) — until then that file intentionally does not exist.
  Do not create attributes/values via API without an explicit ask; the import
  reports "wanted but missing" values instead (see the add-products skill).
  **Open dev question:** can `special-diet`/`health-feature` hold multiple
  values per variant? (Chewy-style multi-tag filtering depends on it.)

If a product's brand/category doesn't exist in admin: do NOT invent one —
flag it in the run report and skip that field or ask the user.

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
- Notes → free-text hints (e.g. which size/flavor variant to pick)
- Margin %, Total Cost (AMD), Total (USD) → ignore (derived)

The brand's official site supplies the rest: images, description/benefits,
composition/ingredients, feeding guide, spec attributes, product/article code.

**Known gaps in this CSV** (flag in the report, don't invent):
- Brands not in admin: Farmina, Schesir, Stuzzy, Leonardo. Only Brit, Royal
  Canin, Belcando, Canvit exist. Ask user to add missing brands first.
- CSV categories `Vitamins & supplements` and `Accessories` have no matching
  admin category (tree is only Dog/Cat → Food/Treat). Ask user where to file
  these or to add categories.

## Workflow

Attribute/value/family creation: use the `/manage-attributes` skill (or the
`attribute-manager` agent for big batches, e.g. the post-wipe rebuild from
`reference/attribute-redesign.md`). Product import: use the
`/add-products <csv path>` skill. Summary: get token → load the
attribute menu (`reference/attribute-values.json`) → for each CSV row: resolve
brand → official site (brand map above) → find the product on that site →
extract fields with one `evaluate_script` → **fill variant attributes from the
page text** (closed menu, evidence quotes, no guessing — rules in the skill) →
create product via the API (categories from the CSV map + `attribute_value_ids`)
→ verify via GET → next row. Write `runs/<date>-report.md`: per-product status,
attributes set/blank, flagged candidates, and "wanted but missing" vocabulary
questions for the user. Build roadmap and phase status live in `PLAN.md`.
