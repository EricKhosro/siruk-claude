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
2c. **The PM's register is the price of record** (2026-09-16) —
   `csv/Product.numbers` outranks hafo/zoovet; a register price at/below cost
   or a typo-level jump (≥ 2.5× cost **and** ≥ 2× current) is held, not
   written. The register has no article codes — recovery chain and full
   policy: `reference/pricing.md` → "The register".
3. **Each variant gets its own hafo price** — never the top-level listing
   price (the cheapest size only). Only `price_source: "variant"` may be
   written; unpriced variants go to the CSV individually.
4. **Re-check after any import** — `scripts/check-hafo-prices.py` for
   hafo-priced rows (`--apply` fixes unflagged rows only); a row priced from
   zoovet or nemo needs its own recheck against that source, not hafo — per
   row with `zoovet-lookup.py` / `nemo-lookup.py --url`, no batch script yet; see `reference/pricing.md` → "Recheck gap".
5. **Sale price must beat cost** — at or below our CSV cost means the wrong
   row (or an invented price), stop and check by hand. The write scripts
   refuse such a variant (`ALLOW_BELOW_COST=1` only on the user's explicit
   say-so).
6. **Identity from the article code when the row has one; by name only when
   it has none** (2026-09-17). A codeless row (the PM's register) is
   identified in order — hafo by name → zoovet.am or nemo.am by name → web
   search — stopping at the first source where **every axis matches** (brand,
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
   4lapy.ru → zoovet → hafo placeholder → web search → reverse-image search;
   petshop.ru for texts only) and every
   rung's confirmation rule: `reference/image-sources.md`. hafo's own photo is
   a **watermarked placeholder only** — last in the gallery, logged to
   `needs-image.csv` (rule 7a there); zoovet's is unwatermarked and finished
   once confirmed (rule 7b).
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
   **Sold loose** (a per-kg sale price on the row, 2026-09-30): the bag also
   gets a `sale_mode: "weight"` variant — `price` per kg, **minimum 1 kg, step
   1 kg** (`qty_min` = `qty_step` = 1000 g, user 2026-10-01), stock in grams
   (10 kg placeholder), cost = bag cost ÷ bag kg, SKU `<bag sku>-KG`. Detail:
   `reference/pricing.md` → loose sale.
8b. **Every product has a product type** (the admin's name for the API's
   attribute family; 2026-09-23, reworked 2026-09-30). Before an import,
   once the batch's product data is gathered, the `attribute-manager` agent
   is fed that data and creates or extends whatever product types the batch
   needs — we decide roles and flags logically, the PM edits later — then
   `scripts/product-types.py --check` must pass on every payload before the
   first write. Suppliers are out of scope for now.
8c. **The product type decides the attributes** (2026-09-29). Per attribute
   it sets `role` — `option` (what the customer picks: a selector axis, one
   value per variant) or `attribute` (specs and filters) — plus
   `is_required`, `is_filterable` (category filters come from this, not the
   attribute) and `show_on_product_card`. The API refuses a value outside the
   type or a second value on an option. Live: `reference/product-types.json`
   (`scripts/product-types.py --dump`).
9. **Search before create.** `scripts/find-product.sh` first; an existing
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
10. **Write only through `scripts/`** — every product/variant body is built
   by `scripts/siruk_payload.py` (it mirrors the admin form's
   `toVariantPayload`). Never hand-write a `PUT /products` body (it replaces
   the whole variants array). Never trust an unverified media id.
10a. **Stock is a ledger** (2026-09-29). A new variant sends `initial_stock`
   (CSV Qty 1 → placeholder 10); an existing variant's stock changes only
   through `/stock/variants/<id>` (set / receive / write-off, with a note),
   never the product PUT. `reference/admin-api.md` → "Stock".
11. **Brand sites are read-only.** No cart, no accounts, no forms. Extract
   with `evaluate_script`, don't `take_snapshot` product pages.
12. **Weights are metric (kg/g), never lbs.** Name never contains the brand;
   slug does. Don't turn a volume (litres) into a weight.
13. **Everything translatable ships in `en`, `ru` and `hy`** — create in
   `en`, then PUT each other locale (`scripts/set-translation.py` and the
   `translate-*.py` scripts). Variant labels stay single-language English.
   **Report translation status only from `scripts/verify-translations.py` /
   `translate-attributes.py --verify-only` output, never from what was
   sent.** Full per-resource rules and API quirks: `reference/admin-api.md`
   → "Translations".

## Environments
- Admin (demo): `https://demo-api.siruk.am/admin/login` —
  `dev@conceptstudio.club` / `C6iA7HLmHU00v/0`. Production needs a dedicated
  catalog-only service account (not yet requested).
- API: `https://demo-api.siruk.am/api/admin/*`, `Authorization: Bearer <JWT>`
  (cookies alone fail). Token in `.siruk-token` (gitignored, ~1 year). Check
  with `scripts/api.sh GET /account`; re-capture per `scripts/README.md` on 401.
- Pacing / retries / image verification: `config.json` (read on every call).
- Working files: `.siruk-cache/` (gitignored). Run scratch: `runs/<date>/`
  (clear once closed). **What outlives a run lives in `state/`** — the one
  open-items worklist, the register's code mappings and hand overrides, info
  sources (`state/README.md`).

## The pipeline (one row at a time, verified before the next)

1. `scripts/api.sh GET /account` → 200. `scripts/ids.sh` for live ids.
2. Load `reference/attribute-values.json` (refresh with
   `scripts/refresh-attributes.sh` if the user edited attributes).
3. **hafo** — `scripts/hafo-lookup.py --code <code> --name "<name>"`
   (`reference/hafo.md`). Need `confirmed: true` **and** `price_source:
   "variant"`. Confirmed but no price → try zoovet / nemo by name (rule 2b,
   `scripts/zoovet-lookup.py`, `scripts/nemo-lookup.py`), then the sibling
   fallback, then
   `no-hafo-price.csv`. Not confirmed → `not-found.csv`. **A row with no
   code at all** (the register) goes through `scripts/identify-by-name.py`
   first — hafo by name, then nemo/zoovet (its `shop_candidates`), then a web
   search, every axis matching
   (rule 6) — and continues with the code that recovers; the register price
   (rule 2c) then outranks hafo's.
4. **Brand site** — resolve from the brand hafo returned
   (`reference/brand-sites.md`), find the product page, extract title, images,
   description, composition, feeding guide, spec text. Nothing there? the
   brand's other country domains, then the **barcode lookup**
   (`scripts/barcode-lookup.py --code <code>`, then WebSearch `"<ean>"`;
   `reference/image-sources.md` → "Barcode lookup" — also whenever the
   identity is in doubt), then 4lapy.ru by EAN
   (`scripts/4lapy-lookup.py`), then zoovet / petshop.ru confirmed by hand
   (`reference/image-sources.md` → "Fallback sites"). New
   brand → research the official site, add it to the table, `/create-brand`.
5. **Product type + attributes** — once the whole batch is gathered, feed
   it to the `attribute-manager` agent to create/extend product types (rule
   8b); then per row: closed menu, evidence quote per pick, only attributes
   of the row's product type, our definitions (`reference/data-tables.md`)
   beat the brand's wording. `scripts/product-types.py --check` on all
   payloads before step 7.
6. **Group / exists?** — `reference/product-rules.md` for product-vs-variant,
   Name/slug/label, categories. `scripts/find-product.sh` before writing.
7. **Write** — `scripts/upload-media.sh <file> products/<brand-slug>/<type>`
   per image (all gallery images; Trixie: `scripts/trixie-image.sh <art>`
   lists them all, .de plus the .es shop), then
   `scripts/create-product.sh` or `scripts/add-variant.sh`. Payload shape:
   the docstring of `scripts/siruk_payload.py` (`price` = hafo pack price,
   size in `measure_type`/`content`/`pack_count`, `initial_stock`,
   `attribute_values` by attribute id or code).
8. **Translate** — write `.siruk-cache/tr-<id>-ru.json` and `-hy.json`
   (name + per-SKU texts; the hafo Armenian `title` is a good source for
   the `hy` name) and run `scripts/set-translation.py` for each.
9. **Verify** — `scripts/show-product.sh <id>`; `scripts/verify-media.sh` at
   the end of the run. `scripts/pace.sh product` between rows.
10. **Report** — `runs/<date>/report.md` + the two CSVs (`reference/pricing.md`
   has their columns). List "wanted but missing" vocabulary as questions.
   Then fold what is still open into `state/open-items.csv` and anything a
   later run reads back into `state/` — never leave it only in `runs/`.

## Reference docs

| Doc | When |
|---|---|
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

`/add-products <csv>` imports; `/create-brand <name>` adds a brand with a
verified official logo; `/manage-attributes` edits the vocabulary (never deletes
without an explicit ask). Big attribute batches → the `attribute-manager` agent.
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
Pharmacy 50 {51–58}, Litter 59 {60–65}, Supplies 66 {67, 79}, Trees 80 {81}.
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
