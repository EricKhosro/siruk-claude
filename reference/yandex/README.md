# Yandex Eda — Retailer cabinet (ЛК Ритейлера / Picker App admin)

Explored 2026-11-02 (admin version 1.206.2). Siruk sells on Yandex Eda
(Armenia) through the retailer cabinet at `https://pickerapp.eda.yandex.ru/pa/`.

## Account

| What | Value |
|---|---|
| User | 37540, role **Manager**, "Eric" (+374 41 518808) |
| Chain (network / brand) | **Siruk Pet Shop**, `brand_slug` = `siruk_pet_shop_shop`, `network_id` = **13258**, brand id 312237 |
| Store | store id **2360618** (`/pa/stores/view?id=2360618`), **`place_id` = 3315164** — Hovhannes Badalyan St 13/4, entrance 1, Yerevan |
| Brand settings | `department: "other"` (not grocery / flowers), `is_catalog_enabled: true`, **`is_partner_types_enabled: false`** → the form uses the **v2** product endpoints and the partner-type / ОКПД2 / ТН ВЭД fields do not apply |

## Sign-in and session

- Sign-in is **Yandex ID** (passport.yandex.ru). Claude never types the
  password: the user signs in **in the Claude desktop app's built-in
  browser** (the browser pane). Its profile is persistent, so the session
  cookies stay for later sessions until Yandex expires them.
- Yandex's `Session_id` cookies are httpOnly — they can't be read or
  copied out. So **every API call runs inside the browser pane**
  (`mcp__Claude_Browser__javascript_tool` on a `pickerapp.eda.yandex.ru` tab),
  where `fetch` carries the cookies by itself.
- Every write needs the header `X-CSRF-Token`: `GET
  /v1/pickerapp/csrf-token-generator` → `{"sk": "<token>",
  "max-age-seconds": N}`. Fetch a fresh one per batch.
- Logged out? The page redirects to `passport.yandex.ru/...origin=pikerka_dc`.
  Ask the user to sign in again in the pane.

## Sections (top menu)

Statistics `/pa/analytics` · Pickers `/pa/pickers` · **Catalog**
`/pa/catalog/edit?id=siruk_pet_shop_shop` · Schedules `/pa/schedules` ·
Shops `/pa/stores` · Orders `/pa/orders` · Feedback `/pa/feedback` · More →
Users. Help: `https://yandex.ru/support/retail/ru/admin/about`.

The catalogue page has a store filter ("All stores" = the whole network, or
one store), a status filter, a category tree on the left (`+` adds a
category, `⋮` adds a subcategory, renames or deletes), the product list
(status toggle, photo, name, weight, price, `⋮` → details / edit / delete),
and the **Export** (XLSX) and **Import** (CSV) buttons at the top.

## Catalogue model

- **Network catalogue** (categories + products) is shared by every store.
  Per store: price, discount, availability.
- **No variants.** Every pack size / flavour / colour is its own card. The
  pet-shop rules forbid choice-in-one-card ("Не указывайте в одной карточке
  варианты товара на выбор"). One Siruk variant = one Yandex product.
- New products get `moderation_info.status: "required"`. Yandex moderates
  each card before it shows in the app (Каталог → Модерация товаров).
- Categories: free-form tree we create (`parent_id` for subcategories).
  Today there is one category, **"Կեր"** (`de76cdfd-049a-480f-9735-ef1960d8f504`),
  empty since the test product "Կեր կեր" was deleted on 2026-11-02.

## JSON API (all `POST` unless noted; snake_case keys; base `https://pickerapp.eda.yandex.ru`)

| Job | Call |
|---|---|
| CSRF token | `GET /v1/pickerapp/csrf-token-generator` |
| Brand settings | `GET /admin/v1/brands/settings?brand_slug=siruk_pet_shop_shop&language=en` |
| Category tree | `/admin/v2/menu-catalog/categories/list?brand_slug=…&locale=en` body `{}` |
| Create category | `/admin/v2/menu-catalog/category/create?brand_slug=…` body `{"name": "...", "parent_id": "<uuid>"?}` → `{category_id}` |
| Rename / delete category | `/admin/v1/menu-catalog/category/update`, `/category/delete` |
| Products in a category | `/admin/v2/menu-catalog/products/list?brand_slug=…&limit=20&offset=0&locale=en` body `{"category_id": "…"}` (also `name_part`, `moderation_status`, `is_available`) |
| Products in a store | `/admin/v2/menu-catalog/place/products/list?place_id=3315164&limit=…&offset=…&locale=en` |
| Product detail | `/admin/v2/menu-catalog/product/detail-info?brand_slug=…&product_id=<uuid>&locale=en` body `{}` |
| **Upload image** | `/admin/v1/menu-catalog/image/upload?network_id=13258`, multipart field **`image`** → `{"image_url": "https://avatars.mds.yandex.net/get-eda/…/orig"}` |
| **Create product** | `/admin/v2/menu-catalog/product/create?brand_slug=siruk_pet_shop_shop` (body below) |
| Update product | `/admin/v2/menu-catalog/product/update?brand_slug=…&product_id=<uuid>` (same body) |
| Delete products (network) | `/admin/v1/menu-catalog/products/delete?network_id=13258` body `{"products_ids": ["<uuid>"]}` → 204 (verified 2026-11-02) |
| Delete in one store | `/admin/v1/menu-catalog/place/products/delete?place_id=…` body `{"products_ids": […]}` |
| Store price / availability | `/admin/v1/menu-catalog/place/products/update-or-create?place_id=…`, `/place/product/set-availability?place_id=…` body `{"product_id", "is_available"}` |
| CSV import (network) | `/admin/v1/menu-catalog/import?network_id=13258`, `Content-Type: text/csv` |
| Export | `/admin/v1/menu-catalog/export?network_id=13258` → XLSX; store: `/place/products/export?place_id=…` |
| Discounts file | `/admin/v1/menu-catalog/discounts-import?network_id=…` (XLSX) |
| Moderation | `/admin/v1/brand/products/moderation/…` (preview / list / export) |

The JS client lives in `yastatic.net/s3/pickerapp-admin/<ver>/ru/next/_next/static/chunks/18552-*.js`
(class with `endpoint="/admin/v1/menu-catalog"`); the form payload builder
is in chunk `872-*.js` (`eZ=async e=>{…}`). Re-read them if a call starts
failing after a Yandex release.

### Product body (what the admin form sends, snake_case)

```json
{
  "name": "Сухой корм для кошек Brand Line с курицей 2 кг",
  "category_id": "<uuid>",
  "place_ids": [3315164],
  "place_ids_to_add": [3315164],
  "images": [{"url": "<image_url from image/upload>"}],
  "measure": {"value": "2", "unit": "KGRM"},
  "places_prices": [{"place_id": 3315164, "price": {"value": "12500"}}],
  "description": "…",
  "vendor_name": "Brand",
  "vendor_country": "<country>",
  "barcodes": [{"value": "4607013973725"}],
  "package_quantity": 12,
  "adult": false
}
```

- `measure.unit`: **`GRM` | `KGRM` | `MLT` | `LT`** only. No piece unit. Item
  type in the form: "Piece product" (default; no quantum) or by-weight
  (`measure.quantum` = the portion size).
- Optional: `places_discounts`, `description` (≤ 2400 chars),
  `vendor_name`, `vendor_country`, `barcodes`, `package_quantity` (pieces per
  pack). Required: name, category, store, measure, price, **at least one
  photo**.

## Yandex's rules (summary; source: `support/retail/ru/catalog/requirements`)

**Names** — in **Russian**. Order: product type → brand (+ sub-brand) →
line/series → distinguishing traits (flavour, colour, size, audience) →
weight / volume / pieces. No CAPS (only brand acronyms), no quotes, no
extra punctuation, no unclear abbreviations, no ad or superlative words
(акция, хит, новинка, лучший …). Say the flavour directly ("ягненок", not
"вкус ягненок"). Multipack: count in the name ("85 г х 28 шт").
Pet-shop example: «Влажный корм для собак Cesar Ягненок в сырном соусе 85 г х 28 шт».
**The pack size goes in the name here** (opposite of Siruk rule 12).

**Description** — Russian, starts with a capital, no CAPS, no links, no ad
words. Composition, use, country, storage, nutrition may go in.

**Barcode** — the maker's 13-digit EAN. Never an internal code (so no PLU
from a 1 kg loose variant).

**Manufacturer** — brand / maker. Must match the name, description and
photo.

**Photos** — JPEG / JPG / PNG, **at least 800×600 px**, up to **25 MB**, up to
10 per card, first one = main. Sharp, the **whole product**, centred,
**front-facing**, **white (or transparent) background**, not cropped, not
tiny in the frame, not rotated. Closed package. Current package design.
**No watermarks of other brands** (hafo's watermarked photos are out), no ad
text, no stray objects. Pet shops: **no faces, hands or other body parts**,
no "Brand #1" claims, the photo matches the unit count sold. The form
checks: copyright OK, no alcohol / cigarettes, matches the name, fully
visible, no inscriptions.

**Not deliverable** (relevant to us): **veterinary pharmacy / medicines**
("Ветаптека" — allowed only for pet shops with a licence; vet supplies such
as bandages are fine), rodent poison (traps are fine), items bigger than the
courier bag **40×25×40 cm** (unless we deliver ourselves), glass / ceramic
without packaging, "assorted" choice items (flavour / gender) except toys
of one series.

**Classifier codes** (ТН ВЭД / ОКПД2, permits): Russian-law fields tied to
partner types, which are **off** for our network. Not sent.

## Rival shops on the storefront (price research)

The customer storefront `eats.yandex.com/en-am/retail/<slug>` has a public,
no-login API. `scripts/yandex-shop-scrape.py <slug>` reads a shop's whole
catalogue: `POST /api/v2/menu/goods` with `{slug, latitude, longitude,
maxDepth: 100}` gives the tree, and adding `category_uid` gives every item in
that category (without it, a category returns a 4-item preview). An empty
category answers 404.

Zoovet (`zoovetam`, place 2285402) on 2026-11-02:
- 1,607 items, Armenian category names, a pharmacy section (it sells vet
  medicines on Yandex).
- Item names end in its zoovet.am code ("#4335" = ME-00004335).
- Dry food is mostly sold loose, "1 кг".
- Its Yandex prices are a **median 1.20× our Siruk price** on confidently
  matched items.
- Customers pay a service fee of 6% (֏49–490). Delivery is free from ֏1,000.
- Matches and the price proposal: `scripts/yandex-price-compare.py` →
  agent/hand check (`<slug>-verdicts.json`) → `scripts/yandex-price-sheet.py`
  → `final/yandex/siruk-yandex-prices.xlsx`.

## Photos: reuse of the Glovo squares

`.siruk-cache/glovo/squares/` holds 1,452 white-padded squares made from
each variant's first Siruk image. Same method, wrong size: they are
**500×500**, below Yandex's 800×600 minimum. Rebuild them with
`scripts/glovo-export.py`'s `square_jpeg(raw, side=1000)` from the Siruk
originals (`.siruk-cache/glovo/media.json` has the dimensions). 209 originals
have a long side under 800 px (89 under 600). Those get upscaled to fill the
square and are flagged for a visual check, since Yandex rejects blurry or
pixelated photos.
