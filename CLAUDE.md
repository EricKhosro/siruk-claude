# Siruk PetShop — product import automation

Turn a supplier CSV into products in the Siruk admin. Per row: identify the
product (hafo.am, by article code) → get its **sale price from hafo** → get
name / images / description from the **brand's official site** → write it via
the admin JSON API. Read this file fully; open a `reference/` doc only when the
step you are on needs it.

## Hard rules — read before every run

Full detail, thresholds, evidence and scripts for every rule below live in
`reference/`; this list is the compact index, not the whole policy — open the
linked doc before you rely on a number from memory.

1. **CSV price is our COST, never the sale price — unless the user names a
   sale-price column up front for the run.** Sale price comes from hafo.am
   for the exact article code, never from arithmetic. If the user states a
   specific column is the selling price for that run, write it straight
   through and skip the price-lookup chain (2, 2a, 2b) for those rows
   entirely. Full exception wording, sanity checks: `reference/pricing.md`.
2. **Never invent a sale price** — no markup, no rounding, no brand-site
   price. A row hafo can't price is not imported: `runs/<date>/no-hafo-price.csv`,
   empty, for the user. Exceptions: the user fills it in, a confirmed
   **zoovet.am or nemo.am** price — both searched **by product name**, since
   neither carries our article code (2b) — or the sibling fallback (2a).
   `reference/pricing.md`.
2a. **Sibling-price fallback** (2026-09-10): a same-cost variant of an
   already hafo-priced sibling takes that sibling's price; differing
   sibling prices block it. Logged in `sibling-priced.csv`. Full rule:
   `reference/pricing.md` → "Sibling-price fallback".
2b. **zoovet.am and nemo.am are the second/third price sources** (zoovet:
   2026-09-11) — name search, only for a hand-confirmed identity, only if it
   beats cost. Neither outranks the other; try either. Order: hafo →
   confirmed zoovet/nemo → sibling → `no-hafo-price.csv`. `reference/zoovet.md`,
   `reference/pricing.md`.
2c. **No rival price → recommend, never set** (user, 2026-10-12). When none of
   hafo / zoovet / nemo sells the exact item and the sibling rule (2a) doesn't
   apply, `scripts/recommend-price.py` lists comparables: same brand, same
   animal, same product type, closest leaf and size, priced from a rival.
   It suggests our cost × their median price/cost ratio, with the unit-price
   method beside it as a cross-check. The list goes to the user as an Excel;
   only an approved price is written (source: "user-approved
   recommendation"). Order: hafo → zoovet/nemo → sibling → recommendation →
   `no-hafo-price.csv`. `reference/pricing.md` → "Price recommendations".
3. **Each variant gets its own hafo price** — never the top-level listing
   price (the cheapest size only). Only `price_source: "variant"` may be
   written; unpriced variants go to the CSV individually.
4. **Re-check after any import** — `siruk recheck-prices` for
   hafo-priced rows (`--apply` fixes unflagged rows only); a row priced from
   zoovet or nemo needs its own recheck against that source, not hafo — per
   row with `zoovet-lookup.py` / `nemo-lookup.py --url`, no batch script yet; see `reference/pricing.md` → "Recheck gap".
5. **Sale price must beat cost** — at or below our CSV cost means the wrong
   row (or an invented price), stop and check by hand. The write scripts
   refuse such a variant (`ALLOW_BELOW_COST=1` only on the user's explicit
   say-so).
6. **Identity from the article code when the row has one; by name only when
   it has none** (2026-09-17). A codeless row (the PM's register) is
   identified in order — the whole hafo catalogue matched locally (exact
   name + cost; hafo's search misses rows) → hafo by name → zoovet.am or
   nemo.am by name → web search, **every query also in the brand's
   Latin/Russian/Ukrainian spelling** (`reference/name-aliases.json`) — stopping at the first source where **every axis matches** (brand,
   line, lifestage, flavour, pack, +size/colour for accessories). Full order,
   logging files and the CSV `Brand`-column caveat: `reference/hafo.md` →
   "Identifying a row with no article code".
7. **Media, English name and description come from the brand's official
   site** (`reference/brand-sites.md`), including its other-country domains.
   Upload the **whole gallery**, verified readable, ordered packshot → pack →
   lifestyle → group shot; the **first image must be a clean product shot**
   (no animal/hand/scene/group) or it goes to `needs-packshot.csv`. **No
   product ships with an empty gallery** (2026-09-23; `ALLOW_NO_IMAGE=1` is
   the rare hand override) and every upload goes in a media-library folder
   — `products/<brand-slug>/<type>/`, `logos/`, `categories/`, or `banners/`
   (page-top banners only) — never the root. The full
   fallback ladder (country TLDs → **barcode lookup** (2026-09-25: hafo's
   confirmed EAN → `scripts/barcode-lookup.py` + a web search for the EAN;
   identity from two EAN pages, content only from pages printing our EAN) →
   trixie.shop/trixiecz → EAN-keyed shops incl.
   4lapy.ru → zoovet → web search → reverse-image search → **Google search +
   Google Lens in a headed browser** (2026-10-01; the `/google-lens` skill →
   `scripts/google-lens.py` since 2026-10-02: Scrapling drives a visible real
   Chrome with a persistent profile; a CAPTCHA goes to the user, never solved
   by us) → hafo placeholder, only when all of that misses;
   petshop.ru for texts only) and every
   rung's confirmation rule: `reference/image-sources.md`.
   **Texts with no official page** (2026-10-02): after the fallback sites,
   Google search + the result pages opened in the same headed browser
   (`google-lens.py` `page` jobs) — keyed by our EAN/article, or by name with
   every axis matching on two pages — and **hafo's Armenian text last**
   (cleaned → `hy`, translated to `en`/`ru`, row on `needs-text.csv`).
   `reference/image-sources.md` → "Texts when the brand has no page".
   hafo's own photo is a **watermarked placeholder only** — last in the gallery, logged to
   `needs-image.csv` (rule 7a there); zoovet's is unwatermarked and finished
   once confirmed (rule 7b).
   **Each pack size has its own gallery** (2026-10-01): a variant's first
   image must show **that** size (a 14 kg bag never shows the 2 kg bag —
   product 1176 did), sourced from that size's own article/EAN; no
   size-specific photo → the closest same-line photo goes on
   `needs-image.csv` with the reason "other size". A by-weight variant
   reuses its bag's gallery. `reference/image-sources.md` → "One gallery per
   size".
   **A product belongs to every category that fits** — `category_ids` is an
   array, leaves only (parents roll up on their own), never drop a category
   an existing product already has. Dual-species and vet-diet second-leaf
   conventions, and what to do when no matching leaf exists: `reference/product-rules.md`
   → "Multiple categories per product".
8. **Never fabricate specs.** Empty field beats a guess. Attribute values
   only from the closed menu `reference/attribute-values.json`, evidence
   quote per pick. Don't create attributes, values or categories without an
   explicit ask — except product types and which attributes they carry (8b).
   One value per option per variant. The product-type skill says which attributes a row
   gets.
8a. **Pack size is the variant's net content, never an attribute**
   (catalog model, 2026-09-29) — `measure_type` (`mass`/`volume`/`count`) +
   `content` (g / ml / pcs, up to 3 decimals: a 0.4 ml pipette) +
   `pack_count` (12 for "12 × 85 g"). `price` is always the **pack** price;
   the server makes the size label and the per-kg / per-100 ml rate. The
   `product-weight` attribute and `pricing_type`/`price_per_kg`/`weight` are
   gone. A sized product type refuses a variant with no content unless
   `ALLOW_NO_SIZE=1` (a chew measured in cm, a collar). A physical size (toy
   S/M/L, collar length, bowl 0.2 L) is an option attribute, not content.
   Supplements: tablets/pipettes/collars `count`, liquids/pastes ml/g (user,
   2026-09-30). Spec: siruk-web `docs/catalog-model.md` §2, §4.
   **Sold loose** (a per-kg sale price on the row): **every bag gets a "1 kg"
   PACK variant** — `sale_mode: "pack"`, `measure_type: mass`, `content`
   1000, `price` = the per-kg price, cost = bag cost ÷ bag kg, stock 10, SKU
   `<bag sku>-KG`, label "1 kg", same attributes, texts (en/ru/hy) and gallery
   as its bag, placed right after it. **Never `sale_mode: "weight"`** — the
   PM paused by-weight sale on 2026-10-01 until its UI is tested; the 84
   by-weight variants were deleted by the developers that day. A bag with no
   per-kg price gets no 1 kg variant — never derive one. **Treats sold
   loose get a "100 g" variant instead** (user 2026-10-15: nobody buys 1 kg
   of a ~1.3 kg treat bag) — SKU `<bag sku>-100G`, `content` 100, price =
   the user-approved per-100 g price, cost = bag cost ÷ (bag g / 100), PLU
   barcode; ArmSoft/scale keep it per kg (303 price = 10 × the 100 g price).
   Detail: `reference/pricing.md` → loose sale.
   **Multipacks: ask about single sale** (user 2026-10-19). Any variant with
   `pack_count` > 1 ("10 × 5 g" sticks, "4 × 15 g" purée, "6 pcs / 60 g")
   → ask the user whether the single unit is sold too; never decide alone.
   On a yes: a variant on the same product, label "<flavour>, 1 × 5 g", SKU
   `<pack sku>-1`, content one unit, price = a rival's single-unit price
   (zoovet lists "1 шт, 5 г"; never pack price ÷ N; none → recommendation,
   rule 2c), cost = pack cost ÷ N, its own single-unit photo, stock 10.
   ArmSoft gives the good a piece unit (as Felix: 001 + case unit).
8b. **Every product has a product type** (the admin's name for the API's
   attribute family; 2026-09-23, reworked 2026-09-30). Before an import,
   once the batch's product data is gathered, the `attribute-manager` agent
   is fed that data and creates or extends whatever product types the batch
   needs — we decide roles and flags logically, the PM edits later — then
   `scripts/product-types.py --check` must pass on every payload before the
   first write (`siruk check` does the same). Suppliers are out of scope for now.
8c. **The product type decides the attributes** (2026-09-29). Per attribute
   it sets `role` — `option` (what the customer picks: a selector axis, one
   value per variant) or `attribute` (specs and filters) — plus
   `is_required`, `is_filterable` (category filters come from this, not the
   attribute) and `show_on_product_card`. The API refuses a value outside the
   type or a second value on an option. Live: `reference/product-types.json`
   (`scripts/product-types.py --dump`).
9. **Search before create.** `find_products` / `siruk find` first; an existing
   product gets the row as a variant, never a second product. Variant axes
   are the net content plus the product type's `option`-role attributes
   (flavour, texture, colour, toy size…) — nothing else tells variants apart. **A flavour, dose band or colour
   inside a product Name is the symptom of a mis-split product.** Full
   evidence rules and the merge procedure (131 duplicates folded on
   2026-09-12, 55 more on 2026-09-16): `reference/product-rules.md` →
   "Sibling products".
9a. **A product with two or more variants needs every option attribute it
   uses set on every variant**, and no two variants may share the same
   options + size — a missing value makes that tile row vanish, a duplicate
   makes a variant unreachable (product 874 hid half its stock this way; 480
   still has one). `scripts/siruk_payload.py` refuses both before writing;
   `scripts/backfill-variant-axes.py` after any merge. Full detail:
   `reference/admin-api.md` → "Variants and attributes".
10. **Write only through `siruk` (or `scripts/`)** — every product/variant
   body is built by `siruk/payload.py` (`scripts/siruk_payload.py` is its
   shim), which mirrors the admin form's `toVariantPayload`. Never hand-write a `PUT /products` body (it replaces
   the whole variants array). Never trust an unverified media id.
10a. **Stock is a ledger** (2026-09-29). A new variant sends `initial_stock`
   **10 on every variant, whatever the CSV Qty says** (user 2026-10-01); an existing variant's stock changes only
   through `/stock/variants/<id>` (set / receive / write-off, with a note),
   never the product PUT. `reference/admin-api.md` → "Stock".
10b. **Every variant carries its codes** (siruk-web 2026-10-09, user
   2026-10-12): `barcode` = the pack's EAN, or the **5-digit scale PLU** on a
   1 kg loose variant (`<bag sku>-KG`); `accounting_code` = the **ArmSoft good
   code** (a bag and its 1 kg share one); `price_source_url` = the hafo /
   zoovet / nemo page the sale price came from (empty for a register-file
   price). Import-only fields: the admin form never sends them, and a PUT that
   leaves them out keeps them. `siruk_payload.check_codes` validates them;
   `scripts/backfill-variant-codes.py` fills the live catalogue.
   `reference/admin-api.md` → "Variant codes".
11. **Brand sites are read-only.** No cart, no accounts, no forms. Extract
   with `evaluate_script`, don't `take_snapshot` product pages.
12. **Weights are metric (kg/g), never lbs.** Name never contains the brand;
   slug does. **Name never contains the pack size either** (user 2026-10-01)
   — the storefront prints "Brand Name, <size label>", so "Wild Coast, 9.7 kg"
   shows the size twice; the size lives only in the variant (content + label).
   An accessory's physical dimensions are not pack size. `validate-card.py`
   fails a name ending in kg/g/ml. Don't turn a volume (litres) into a weight.
13. **Everything translatable ships in `en`, `ru` and `hy`** — create in
   `en`, then PUT each other locale (`scripts/set-translation.py` and the
   `translate-*.py` scripts). Variant labels stay single-language English.
   **Report translation status only from `scripts/verify-translations.py` /
   `translate-attributes.py --verify-only` output, never from what was
   sent** (`siruk verify-translations` is the same audit). Full per-resource rules and API quirks: `reference/admin-api.md`
   → "Translations".
14. **Recommendations are computed from our data, never linked by hand**
   (siruk-web 2026-10-09). PDP "Related items" = same leaf + same product type
   → sibling leaf → same brand, ranked by price per kg/l/pc; the cart's
   "goes well with" = bought-together pairs → the category's
   `complement_category_ids` (`reference/complement-categories.json`,
   `scripts/set-complements.py`) → same pet, categories not in the cart. So a
   wrong leaf, a missing product type, a missing `content` or a mis-split
   product now breaks other products' rails too. `merch_boost`, category
   pins and the complement map belong to the PM — an import never sends them
   (`siruk_payload` refuses). **All Breeds / All Lifestages are universal**
   (they match every filter value), so never tag them next to a specific
   size/age. Audit: `scripts/audit-recommendation-data.py`. Algorithms:
   `CLAUDE.local.md`, `reference/admin-api.md` → "Recommendations".

## Environments
- Admin (production): `https://api.siruk.am/admin/login` —
  `dev@conceptstudio.club` / `C6iA7HLmHU00v/0` (the demo host is gone).
  Claude never types the password: the user logs in in the chrome-devtools
  window, then the token is read from `localStorage.access_token`.
- API: `https://api.siruk.am/api/admin/*` (the `scripts/lib.sh` default),
  `Authorization: Bearer <JWT>` (cookies alone fail). Token in `.siruk-token`
  (gitignored). Check with `scripts/api.sh GET /account`; re-capture per
  `scripts/README.md` on 401.
- Pacing / retries / image verification: `config.json` (read on every call).
- A batch's source of truth: `batches/<batch>/` (invoices, `batch.xlsx`,
  `products.csv`; committed).
- **`knowledge/`** (2026-10-23): what we learned — resolved blockers, what each
  ArmSoft document is, cost checks against hafo's wholesale, how each kind of
  good is set up. Read the area's file before ArmSoft / invoice / cost work;
  add a dated bullet the moment a blocker lifts or a fact is learned
  (`knowledge/README.md`).
- Working files: `.siruk-cache/` (gitignored). Run scratch: `runs/<date>/`
  (clear once closed). **What outlives a run lives in `state/`** — the one
  open-items worklist, the register's code mappings and hand overrides, info
  sources (`state/README.md`).

## `siruk` CLI, TUI and MCP server (2026-10-26)

One Python package (`siruk/`) owns the API client and the write rules; three
faces share it. `scripts/siruk_payload.py` is now a shim over `siruk/payload.py`,
so the scripts and these tools enforce the same rules.

**Use `siruk` first** (user, 2026-10-27). For every job it covers, call the
`siruk` MCP tool (reads; writes as a dry run, show the diff, `confirm: true`
on the user's yes) or the CLI, not the script. The scripts stay as the
fallback: for jobs `siruk` has no command for, when the MCP server is not
loaded, or when a `siruk` command fails in a way a script doesn't. A skill or
doc that still names a script means its `siruk` equivalent from this table:

| Job | MCP tool | CLI | Fallback script |
|---|---|---|---|
| token / API check | `account_status` | `siruk doctor` | `api.sh GET /account` |
| live ids | `list_reference` | `siruk ids [brands\|categories\|types\|attributes]` | `ids.sh` |
| refresh the menus | — | `siruk refresh` | `refresh-attributes.sh` + `product-types.py --dump` |
| search before create | `find_products` | `siruk find <text>` | `find-product.sh` |
| show a product | `get_product` | `siruk show <id> [--lang]` | `show-product.sh` |
| validate payloads | `validate_payload` | `siruk check <payload…>` | `product-types.py --check` |
| create one product | `create_product` | `siruk create <payload>` | `create-product.sh` |
| create many new products | `bulk_create_products` (≤ 25) | `siruk bulk-create <payloads…>` | `bulk-create.py` |
| add a variant | `add_variant` | `siruk add-variant <id> <variant>` | `add-variant.sh` |
| patch a variant | `update_variant` | `siruk set-variant <id> <sku> <patch>` | `set-variant.sh` |
| rename | `rename_product` | `siruk rename <id> <name> [--slug]` | `rename-product.sh` |
| ru / hy translation | `set_translation`, `get_translation` | `siruk translate <id> ru\|hy <file>` | `set-translation.py` |
| translation audit (rule 13) | `verify_translations` (≤ 50 ids) | `siruk verify-translations` | `verify-translations.py` |
| media upload | `upload_media` | `siruk media upload <file\|url> --folder <folder>` | `upload-media.sh` |
| media check | — | `siruk media check <ids…>` | `verify-media.sh` |
| stock | `stock_movements`, `stock_receive` / `_write_off` / `_set` | `siruk stock show\|receive\|write-off\|set <vid> …` | `api.sh /stock/variants/…` |
| hafo / zoovet / nemo price | `hafo_lookup`, `zoovet_search`, `nemo_search` | `siruk price hafo --code X --name "…"` / `price zoovet\|nemo --search "…"` | `hafo-lookup.py`, `zoovet-lookup.py`, `nemo-lookup.py` |
| hafo recheck (rule 4) | `hafo_price_recheck`, `apply_hafo_prices` (≤ 50 ids) | `siruk recheck-prices [--apply]` | `check-hafo-prices.py` |
| whole-catalogue read / audit | `export_catalogue`, `catalogue_audit`, `save_catalogue_export` | `siruk export [--audit]` | `dump-products.py` (still needed for attribute ids / GET shape) |
| pacing between rows | — (the client paces itself) | `siruk pace product` | `pace.sh product` |
| any other endpoint | — (no raw API in the MCP) | `siruk api METHOD PATH [body]` | `api.sh` |

Everything else (hafo identify-by-name, barcode / 4lapy / Trixie image
lookups, google-lens, translate-*.py, backfills, ArmSoft, Glovo, scale) stays
a script.

- **CLI** — `uv run siruk <command>` (or `python -m siruk` with no install for
  the stdlib commands): `doctor`, `find`, `show`, `ids`, `refresh`, `check`,
  `create`, `add-variant`, `set-variant`, `rename`, `translate`, `stock`,
  `media upload`, `price hafo|zoovet|nemo`, `api`, `pace`, and the batch /
  end-of-run jobs `bulk-create`, `verify-translations` (rule 13) and
  `recheck-prices` (rule 4; `--apply` asks per product). `siruk export`
  saves the admin's catalogue export (one row per variant, xlsx/json/csv,
  `--lang`, `--since`, `--search`); `siruk export --audit` runs the
  catalogue-wide checks on it (below cost, missing codes / images / size,
  duplicate barcodes and SKUs) in one call. Every write takes
  `--dry-run` (prints the diff) and reads back after writing; the guards are
  the env vars above or `--allow-below-cost` / `--allow-no-image` / `--force`,
  only on the user's say-so. Exit 1 = refused by a rule, 2 = API error.
- **TUI** — `uv run siruk tui`: search, product + variants (margin, red below
  cost), variant/stock/hafo tabs; `e` edit variant, `t` translate, `s` stock,
  `n` rename, `h` hafo price. Every write shows its diff and asks first.
- **MCP** — `siruk` in `.mcp.json` / `opencode.jsonc` (`uv run siruk-mcp`):
  read tools plus guarded writes that are **dry runs unless `confirm: true`**.
  No deletes, no raw API, no below-cost / no-image override (CLI only).
  `export_catalogue` (paged, compact fields by default), `catalogue_audit`
  and `save_catalogue_export` read the export.
  `verify_translations` / `hafo_price_recheck` take ≤ 50 product ids,
  `bulk_create_products` ≤ 25 payloads; full-catalogue sweeps are CLI jobs.
- `scripts/verify-translations.py`, `check-hafo-prices.py` and `bulk-create.py`
  are thin wrappers over `siruk/verify.py`, `pricecheck.py` and `bulk.py` (same
  arguments and output).
- Same token (`.siruk-token`), `config.json` pacing and `.siruk-cache/.pace-*`
  state as `scripts/api.sh`. Tests: `uv run --group dev pytest` (offline).

## The pipeline (one row at a time, verified before the next)

0. **Invoices → the batch Excel** (user, 2026-10-14). A new batch starts from
   its invoices (any language, any headers): `/invoice-intake` transcribes
   each one, checks it against its printed total, and builds
   `batches/<batch>/batch.xlsx`, **the batch's source of truth**, plus the
   `products.csv` the import reads. Cost = unit price incl. VAT. A foreign
   currency needs the user's rate. Questions in the sheet → stop for the
   user; none → straight on. Corrections go back into the xlsx.
   `reference/invoice-intake.md`.
1. `account_status` / `siruk doctor` → 200 (fallback `scripts/api.sh GET /account`).
   `list_reference` / `siruk ids` for live ids.
2. Load `reference/attribute-values.json` (refresh with `siruk refresh` if
   the user edited attributes).
3. **hafo** — `hafo_lookup` / `siruk price hafo --code <code> --name "<name>"`
   (same JSON as `scripts/hafo-lookup.py`; `reference/hafo.md`). Need `confirmed: true` **and** `price_source:
   "variant"`. Confirmed but no price → try zoovet / nemo by name (rule 2b,
   `scripts/zoovet-lookup.py`, `scripts/nemo-lookup.py`), then the sibling
   fallback, then
   `no-hafo-price.csv`. (`zoovet_search` / `nemo_search`, or
   `siruk price zoovet|nemo --search "<name>"`.) Not confirmed → `not-found.csv`. **A row with no
   code at all** (the register) goes through `scripts/identify-by-name.py`
   first — hafo by name, then nemo/zoovet (its `shop_candidates`), then a web
   search, every axis matching
   (rule 6) — and continues with the code that recovers.
4. **Brand site** — resolve from the brand hafo returned
   (`reference/brand-sites.md`), find the product page, extract title, images,
   description, composition, feeding guide, spec text. Nothing there? the
   brand's other country domains, then the **barcode lookup**
   (`scripts/barcode-lookup.py --code <code>`, then WebSearch `"<ean>"`;
   `reference/image-sources.md` → "Barcode lookup" — also whenever the
   identity is in doubt), then 4lapy.ru by EAN
   (`scripts/4lapy-lookup.py`), then zoovet / petshop.ru confirmed by hand
   (`reference/image-sources.md` → "Fallback sites"), then **Google search
   with the result pages read in the headed browser** (`google-lens.py`
   `search` + `page` jobs), then **hafo's own text** as the last resort
   (→ `needs-text.csv`; "Texts when the brand has no page"). New
   brand → research the official site, add it to the table, `/create-brand`.
5. **Product type + attributes** — once the whole batch is gathered, feed
   it to the `attribute-manager` agent to create/extend product types (rule
   8b); then per row: closed menu, evidence quote per pick, only attributes
   of the row's product type, our definitions (`reference/data-tables.md`)
   beat the brand's wording. `validate_payload` / `siruk check <payloads…>`
   on all payloads before step 7.
6. **Group / exists?** — `reference/product-rules.md` for product-vs-variant,
   Name/slug/label, categories. `find_products` / `siruk find` before writing.
7. **Write** — `upload_media` / `siruk media upload <file> --folder
   products/<brand-slug>/<type>` per image (all gallery images; Trixie: `scripts/trixie-image.sh <art>`
   lists them all, .de plus the .es shop), then
   `create_product` / `siruk create` or `add_variant` / `siruk add-variant`
   — or, for a batch of **new** products, `bulk_create_products` /
   `siruk bulk-create <payloads…>`
   (`POST /products/bulk`, en/ru/hy in the same call, so step 8 is already
   done; `reference/admin-api.md` → "Bulk create"). Payload shape:
   the docstring of `siruk/payload.py` (`price` = hafo pack price,
   size in `measure_type`/`content`/`pack_count`, `initial_stock`,
   `attribute_values` by attribute id or code, and the rule-10b codes:
   `barcode`, `accounting_code`, `price_source_url`).
8. **Translate** — write `.siruk-cache/tr-<id>-ru.json` and `-hy.json`
   (name + per-SKU texts; the hafo Armenian `title` is a good source for
   the `hy` name) and run `set_translation` / `siruk translate <id> ru|hy
   <file>` for each.
9. **Verify** — `get_product` / `siruk show <id>`; `siruk media check` (or
   `scripts/verify-media.sh`) at the end of the run; `siruk export --audit`
   for the catalogue-wide checks. `siruk pace product` between rows (the MCP
   tools pace themselves).
10. **Report** — `runs/<date>/report.md` + the two CSVs (`reference/pricing.md`
   has their columns). List "wanted but missing" vocabulary as questions.
   Then fold what is still open into `state/open-items.csv` and anything a
   later run reads back into `state/` — never leave it only in `runs/`.

## Reference docs

| Doc | When |
|---|---|
| `reference/invoice-intake.md` | step 0: reading invoices into the batch Excel — header names in hy/ru/en, the JSON shape, VAT/currency/case rules |
| `reference/pricing.md` | anything touching `price` or `cost_price` — the full policy, cross-checks and the two output CSVs |
| `reference/hafo.md` | the hafo API, SKU formats per brand, what the lookup script returns |
| `reference/image-sources.md` | every place a product photo can come from, in rule-7 order — the brand sites, the distributors, the EAN-keyed shops and the web-search last resort |
| `reference/zoovet.md` | zoovet.am — unwatermarked photos, a second price, the `ME-…` code trap and how to confirm a candidate |
| `reference/brand-sites.md` | brand → official site, per-site extraction notes, image sourcing (Trixie CDN, Schesir JSON, Monge caveats) |
| `reference/admin-api.md` | endpoints, payload shapes, pricing types, media rules, known API quirks, **live ids** (brands, categories, families, attributes) |
| `reference/product-rules.md` | Name / slug / label rules, product vs variant, category map, admin form field map, storefront behaviour |
| `reference/csv-formats.md` | the input CSV shapes (starter list, vendor sheets, invoice extract) and how to decode vendor strings |
| `reference/data-tables.md` | our attribute definitions (lifestage etc.), brand wording → our values, pricing-type table |
| `reference/attribute-redesign.md` | the attribute spec (pre-2026-09-29; product types now: siruk-web `docs/catalog-model.md` §3) |
| `reference/script-guide.md` | **which script, when** — by job: session start, per-row pipeline, end-of-run checks, translations, media, brands, prices, one-offs |
| `scripts/README.md` | every script, `config.json`, debugging |
| `state/README.md` | the files that outlive a run, and how to re-run the register audit |
| `PLAN.md`, `INVESTIGATION.md` | roadmap; why Chewy was dropped (Kasada anti-bot) |

## Skills

`/invoice-intake <invoices>` builds a batch's source-of-truth Excel from its invoices (step 0) and hands it to `/add-products`; `/add-products <csv>` imports; `/create-brand <name>` adds a brand with a
verified official logo; `/manage-attributes` edits the vocabulary (never deletes
without an explicit ask); `/google-lens` runs Google search + Lens for a photo
(image rung 9c, mandatory before a hafo placeholder); `/armsoft-sync <export.xml>`
compares a fresh ArmSoft goods export with Siruk and builds the import files
(new goods, barcode/unit updates, prices); `armsoft-app` drives the ArmSoft
desktop program itself with computer use (export goods + prices, add barcodes;
2026-10-23). **ArmSoft hard rules** (user, 2026-10-23: name < 50 chars for the HDM,
price / selling unit / barcodes / code match Siruk, bag coefficient = bag kg,
VAT off, per-kg goods: main unit kg + Քաշային): `/armsoft-sync` → "Hard rules".
`/glovo-export` fills Glovo's Pelican Partners xlsx from the live catalogue, one
row per variant (`reference/glovo/README.md`). Big attribute batches → the `attribute-manager` agent.
**One spec skill per product type** — `toys`, `dry-food`, `wet-food`, `treats`,
`supplements`, `grooming`, `accessories` (`.claude/skills/<type>/SKILL.md`) —
says which categories that type gets and how to pick its values and size;
which attributes exist, their roles and flags come from the live product
type (`reference/product-types.json`), which wins on any disagreement. `/add-products` reads the row's type skill before filling attributes;
`/manage-attributes` builds vocabulary from it. `toys` is complete (Chewy
layout); the others are templates for the user to fill.

## Quick ids (demo — `scripts/ids.sh` is the truth; full category tree,
brand list, family list and attribute-value ids: `reference/admin-api.md`)

Dog 1 → Food 2 {Dry 3, Wet 4, Health Condition 5}, Treat 6 (leaves 7, 82–88),
Toys 15 {17–22}, Grooming 27 {28–33}, Health & Pharmacy 41 {42–49}, Supplies
68 {69–74}, Cleaning & Potty 75 {76–78}. Cat 8 → Food 9 {Dry 10, Wet 11},
Treat 14 (leaves 89–94), Toys 16 {23–26}, Grooming 34 {35–40}, Health &
Pharmacy 50 {51–58}, Litter 59 {60–65}, Supplies 66 {67, 79, Beds 107 (2026-10-19)}, Trees 80 {81}.
Bird 95 → {Food 96, Treats & Supplements 97}; Small Animal 98 → {Food 99,
Hay 100, Treats 101, Supplements & Salt Licks 102, Bedding 103} (2026-09-28).
**Accessories 13 is not a product category** — never file a row there.
Products go in a **leaf**, never a parent. Which treat leaf a row gets is
decided by the table in the `treats` skill (`scripts/classify-treats.py`
re-files the whole catalogue). Product types (API: attribute families): 1 Dry Food, 2 Wet Food, 3 Treats,
4 Supplements, 5 Toys, 7 Grooming, 8 Accessories, 9 Litter — their live
attributes, roles and flags are in `reference/product-types.json`; type
skills say how to pick values.
Any id in a note written before 2026-08-12 predates the rebuild and is wrong.

## Running under OpenCode (2026-10-07)

`CLAUDE.md` and `AGENTS.md` are the same file — `AGENTS.md` is a symlink to
this one, so OpenCode (which loads `AGENTS.md` only) and Claude Code read
identical instructions. Skills stay in `.claude/skills/`; the `/` commands and
the `attribute-manager` agent live in `.opencode/` (see `.opencode/README.md`).

Two tool-name differences when the text below or a skill names a Claude tool:

- `Read` → `read`, `WebFetch` → `webfetch`, `WebSearch` → `websearch`.
- chrome-devtools MCP tools carry the server prefix:
  `evaluate_script` → `chrome-devtools_evaluate_script`, etc.
- A skill body shows `$ARGUMENTS` literally under OpenCode; read it as
  "the arguments for this run", which the `/`-command (or the user's message)
  supplies.
