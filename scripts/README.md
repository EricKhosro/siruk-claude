# scripts/ — Siruk admin API helpers

Plain bash + `curl` + `jq` (all preinstalled on macOS). No Python, no deps.
Every script sources `lib.sh`, prints `HTTP <code> <METHOD> <PATH>` to **stderr**
and JSON to **stdout**, so you can pipe or redirect any of them.

## Token (do this once; it survives reboots)

The API needs `Authorization: Bearer <JWT>` — cookies alone don't authenticate.
Log in to the admin (`https://demo-api.siruk.am/admin/login`, creds in
`CLAUDE.md`), then in the browser console:

```js
JSON.parse(localStorage.access_token).token
```

Paste it into `.siruk-token` in the repo root (gitignored, never committed):

```sh
pbpaste > .siruk-token     # or: echo 'eyJ...' > .siruk-token
scripts/api.sh GET /account   # verify → HTTP 200
```

Tokens last ~1 year. `SIRUK_TOKEN=eyJ... scripts/…` overrides the file;
`SIRUK_API=…` points the scripts at a different environment.

## The scripts

**Which one, and when → `reference/script-guide.md`** (organised by job: session start, the per-row pipeline, translations, media, brands, prices, one-offs). The table below is the per-script reference.

**Catalog model (backend change 2026-09-29).** Pack size is the variant's net
content (`measure_type` / `content` / `pack_count`), `price` is always the pack
price, stock is a ledger (`initial_stock` on new variants only), variant
attributes are `attribute_values` keyed by attribute id, and every product has
a product type (the API's attribute family) that decides which attributes it
may carry and their role. **Every writer builds its product/variant body
through `siruk_payload.py`** (CLAUDE.md rule 10). Scripts are being converted
as of 2026-09-30; a script whose code still sends `pricing_type`,
`price_per_kg`, `weight`, `product-weight`, `attribute_value_ids` or `stock`
will be refused by the API (or by `siruk_payload.py`) — read its docstring
before running it.

| Script | What it does |
|---|---|
| `api.sh METHOD PATH [payload.json\|-]` | ad-hoc call — the escape hatch (`api.sh GET '/products?search=brit'`) |
| `ids.sh` | live brands / category tree / product types (families) / attributes ids. Trust this over ids written in docs |
| `siruk_payload.py put-body <get.json> [<new-variant.json>] [--patch-sku SKU --patch JSON [--replace-attrs]]` \| `post-body <payload.json>` | **the one place that builds product/variant bodies** (new 2026-09-29), mirroring the admin form's `toVariantPayload`; also a library for the Python writers. Strips server-only fields from a GET, converts mechanical legacy input (`attribute_value_ids` → `attribute_values`, `stock` → `initial_stock`, attribute codes → ids) and refuses the rest (`pricing_type: per_kg`, `weight`, `unit`, `net_quantity`, `product-weight`). Checks every variant against the **live** product type: attribute outside the type, two values on an option, required attribute missing, price not a positive multiple of 10, a sized type's new variant with no content (`ALLOW_NO_SIZE=1` downgrades that to a warning), an option set on some variants but not all (rule 9a), two variants with the same options + size, not exactly one default. Prints the body, or exits 1 with the reasons. The docstring is the new-variant shape |
| `product-types.py --dump` \| `--check <payload.json…>` | product types (new 2026-09-30). `--dump` writes the live types — measure, sale mode, and per attribute role / required / filterable / on-card — to `reference/product-types.json` and prints a table. `--check` runs create-product payloads through `siruk_payload.py` without writing; run it on the whole batch after the `attribute-manager` agent has created/extended the types and before the first write (CLAUDE.md 8b); exit 1 if any fails |
| `refresh-attributes.sh` | regenerates `reference/attribute-values.json` (the closed menu). Atomic write |
| `fetch-logo.sh <url\|file…>` | **before create-brand** — downloads logo candidates, rejects svg/html/favicons (<160px), flags <400px as low-res, prints local paths so you can **Read (look at) the image** before uploading it. `MIN_PX=` / `HARD_MIN=` move the bars |
| `create-brand.sh "<Name>" [logo file\|url\|mediaId] [slug]` | creates a missing brand: refuses on an exact/near duplicate, uploads the logo, POSTs `{name,slug,image,meta}`, reads it back and prints the logo url. `FORCE=1` overrides the near-match guard, `KEEP_ALPHA=1` keeps logo transparency, `NO_LOGO=1` is required to create a brand with no image |
| `prepare-run.py <csv> --run runs/<date>` | batch import step 1 — every deterministic decision per row (price chain, guards, route, pack size, brand, live?) → `rows.jsonl` + `batches.json` + `not-found.csv` + `holds.csv`, summary only on stdout |
| `card-import.py --run runs/<date> <code> [--payload|--write]` | phase C of `/add-products`: builds one card's create/add-variant body (size from the row's `pack` or the card's `size`, `initial_stock`, the loose `-KG` twin, the product type from `product-types-map.json`), checks it against the live type, and with `--write` uploads the gallery and writes through create-product.sh / add-variant.sh |
| `validate-card.py --run runs/<date> [codes…]` | checks worker cards (`reference/card-schema.md`) against the hard rules — closed menu, quotes present in the evidence, price vs cost, leaves, product type, gallery, net content (the row's `pack` or the card's `size`; a `product-weight` pick fails), brand-less name; exit 1 on any FAIL |
| `live-ids.py` | caches live brands / category tree / families in `.siruk-cache/live-ids.json` for the two above |
| `find-product.sh <text>` | **run before creating anything** — does the product already exist? |
| `fix-outgrown-names.py [--plan …] [--ids …] [--apply]` | renames a product that gained a sibling and still carries its first variant's label (or a plan's `rename_to`); re-cuts the ru/hy names or lists them for a hand-written one |
| `plan-variant-merge.py --run runs/<date>` | hand-decided sibling groups (`variant-groups.json`: flavour / dose-band / colour options that were imported as separate products) → `merge-plan.json` for `merge-products.py`; refuses attribute-combination collisions, lists missing vocabulary |
| `backfill-variant-axes.py [--ids …] [--apply]` | rule 9a: gives every variant of a multi-variant product the axis its siblings carry — the product type's option-role attributes (`size`, `color-family`, `flavor`, `pet-weight-range`, `toy-size`…) and the net content (`measure_type`/`content`), read off the label; reports what still collides |
| `register-price-sync.py --run state/register [--apply]` | re-prices every live variant to the register's `Վաճառքի գին` (rule 2c); SKIPs at-or-below-cost rows and typo-level jumps (SUSPECT) into `price-sync.csv` |
| `translate-attribute-values.py <id …>` | ru/hy for a few attribute values by id (after `add-attribute-values.py`), from `reference/translations-attributes.json`; reads en/ru/hy back |
| `catalogue-snapshot.py --ids <id …>` | re-reads only those products into the snapshot and drops the ones that 404 — after a merge or an import |
| `read-register.py` / `match-register.py --reg` / `register-status.py --run --overrides` / `register-audit.py --run` | the register chain (`reference/script-guide.md` §10c); `read-register.py` reads `csv/Product.numbers` directly |
| `show-product.sh <id> [--json]` | variant summary, or the full re-postable body |
| `create-product.sh <payload.json>` | validates required fields, **refuses a variant priced at or below its cost** (`ALLOW_BELOW_COST=1` only on the user's say-so), warns if a similar product exists (`FORCE=1` to override), builds the body with `siruk_payload.py post-body` (checked against the product type), POSTs, reads back. Payload shape in its header: `price` = pack price, `measure_type`/`content`/`pack_count`, `initial_stock`, `attribute_values` |
| `add-variant.sh <id> <variant.json>` | GET → append via `siruk_payload.py put-body` (checked against the product type) → safety-check (incl. the price-vs-cost guard) → PUT → read back. `variant.json` is one new variant in the catalog-model shape, no `id` |
| `set-translation.py <id> <ru\|hy> <translation.json>` | stores a product's Russian/Armenian name, meta and variant texts per locale; copies every single-language field from `en`, verifies `en` untouched. `SIRUK_LANG=ru api.sh GET …` reads a locale |
| `create-category.py <spec.json> [--dry-run]` | creates categories from a spec list, idempotently (dedupes on parent+name). Each entry `{parent, name, slug, meta_title}`; `parent` is an id or a path already in the file (`"Dog > Supplies"`), so a parent and its leaves go in one run. **Only on an explicit user ask.** Add the ru/hy pair to `translate-categories.py` afterwards |
| `translate-categories.py [--dry-run]` | ru/hy names for every category from its built-in table |
| `translate-brands.py [--dry-run]` | ru/hy for every brand (Latin name in all locales, translated meta) |
| `backfill-translations.py [--only id,…] [--dry-run]` | ru/hy for every product from `reference/translations.json` (names, recurring bullet phrases, paragraphs) via `set-translation.py` |
| `verify-translations.py` | **after every import** — audits ru/hy coverage of all products, categories and brands; exit 1 if anything is English-only |
| `translate-attributes.py [--dry-run] [--probe-only] [--verify-only]` | ru/hy for every attribute name, value label and family name from `reference/translations-attributes.json` (17 + 629 + 5); probes a throwaway attribute first and refuses if English would be overwritten; ends with a read-back of all three locales. **Run after adding attribute values** (add their ru/hy pair to the JSON first) |
| `_build-attr-translations*.py` | the source tables that generate `reference/translations-attributes.json`; extend them when values are added |
| `sync-attributes.py [--dry-run]` | syncs the vocabulary to `reference/chewy-attributes.json` (creates, renames, families, filter flags; never deletes). Its product-type step re-sends every existing row and appends new ones (`attributes`, 2026-09-30); batch product-type work before an import is the `attribute-manager` agent's |
| `restore-toy-size.py` | one-off: put `toy-size` back on toy variants from their labels |
| `check-hafo-prices.py [--apply] [--only id,…]` | compares every Siruk variant's sale price with its hafo row (+ `/product/change` cross-check) → `runs/<date>/price-check.csv`; `--apply` fixes unflagged mismatches |
| `hafo-lookup.py --code <art> [--name …]` | **the primary source of a sale price** — hafo.am row for our article code (`reference/pricing.md`, `reference/hafo.md`) |
| `barcode-lookup.py --code <art> [--name …]`, `--ean <ean>`, `--no-net` | the barcode rung (2026-09-25): reads our EAN from hafo only when hafo confirms the code and the barcode sits on the variant whose sku is ours (brand-prefix aware: `TX 236411` = 23641Tx, `AC 5301112` = AC5301112; check digit validated), then answers from the local EAN caches, UPCitemdb (≥12 s apart) and Open Pet Food Facts, and prints the `"<ean>"` web search to run next. Every hit is a lead — rules in `reference/image-sources.md` → "Barcode lookup" |
| `4lapy-lookup.py --search "<words>" [--ean <ean>]`, `--url <page>`, `--reindex` | 4lapy.ru: finds products through the product sitemap (its `/search/` is robots-disallowed), then reads every pack-size offer — barcode, gallery, Russian description / composition / feeding. An offer whose barcode equals `--ean` is `confirmed: true`; a slug match alone is a candidate. RUB prices are never used |
| `zoovet-lookup.py --search "<ru text>" [--brand <slug>]`, `--url <page>`, `--brand <slug>`, `--brands` | zoovet.am: unwatermarked brand packshots (the original behind the thumbnail), a second AMD price, stock and a Russian description. It has **no article code** — its `ME-…` number collides with brand articles — so every hit is `confirmed: false` until confirmed by hand (`reference/zoovet.md`, CLAUDE.md rules 2b / 7b) |
| `nemo-lookup.py --search "<text>" [--brand <slug>]`, `--url <page>`, `--brand <slug>` | nemo.am (nopCommerce): AMD price, stock, manufacturer, description, one image. No manufacturer article code anywhere on the platform, so every hit is `confirmed: false` until confirmed by hand the same way as zoovet — brand+line+flavour+pack, pack photo matching (`reference/pricing.md`, CLAUDE.md rule 2b) |
| `tiierisch-index.py [--brand TRIXIE]`, `--lookup <art>` | indexes tiierisch.de (Shopify) → `{article: {ean, title, variant, images, family}}`. `sku` is the Trixie article and `barcode` the EAN, and Shopify says which image belongs to which variant, so a colour never inherits its sibling's photo. 5,223 Trixie articles — the widest fallback we have (rule 7d) |
| `ean-image-lookup.py <ean> […]` | a photo **by barcode**: hornung-baushop.de (EAN in the file name) plus the carrefour-es picture bucket, which is addressed by the EAN directly (`…/original/<ean>_1.jpg`, no search) |
| `image-search.py --article <a> [--ean …] [--brand …] [--name …] [--sheet]` | the rule 7d image search: Bing Images on the EAN and on the article, every hit classified `keyed-file` / `keyed-page` / `name-only`; only keyed hits are downloaded, measured and sheeted. A name-only hit is reported, never used |
| `web-image-lookup.py --article <a> [--ean …] <url>…` | the other half of rule 7d: takes pages **you** found and reports which of our keys each one actually prints, then pulls its images. A page that prints none of them is refused in the output |
| `gap-images.py --worklist … --out … [--web] [--only …] [--sheet]` | walks the whole ladder for every variant with no usable photo (brand site → trixie.shop → trixiecz → tiierisch → monge → `--web`: EAN shops, then image search), downloads everything with its provenance and renders one contact sheet |
| `hafo-audit.py [--csv runs/<date>/hafo-images.csv]` | every variant in the catalogue still showing a hafo photo — by the url it was uploaded from **and** by hafo's own file-name shapes (a bare upload timestamp, or timestamp + article), which is what catches the ones the caches lost |
| `apply-gap-images.py <found.json>… [--only …] [--dry-run]` | uploads the reviewed images and sets `variant.images` in gallery order (one PUT per product, rebuilt from a fresh GET); drops any hafo placeholder the variant still carried |
| `contact-sheet.py <out.html> <found.json>…` \| `--dir <folder>` | contact sheet with the thumbnails inlined as data: URIs — headless Chrome will not load `file://` images from a `file://` page, so a sheet that references them shows nothing |
| `rename-product.sh <id> "<name>" [slug]` | rename without touching variants (product names must not contain the brand — the storefront prints it separately) |
| `set-variant.sh <id> <sku> '<json patch>'` | patch one existing variant in place; `attribute_values` (by attribute id or code) merge attribute-by-attribute, `REPLACE_ATTRS=1` replaces the whole map. Body rebuilt from a fresh GET through `siruk_payload.py`. Stock is not patchable here — `/stock/variants/<id>` (CLAUDE.md 10a) |
| `backfill-product-weight.py`, `make-perkg-twin.py` | **retired 2026-09-29, moving to `scripts/archive/`**: the first put the `product-weight` attribute on every variant (rule 8a of 2026-09-14), the second added a per-kilo `per_kg` twin variant for the register's `Kg` column. The attribute and the `per_kg` pricing type are gone — pack size is net content now |
| `trixie-image.sh <art> [--first]` | every official gallery image for a Trixie article, packshot first (page-based; probes the CDN for `PHO_PRO_CLIP`/`PHO_PAC_CLIP` whenever the page lists no packshot, and as the fallback when there is no page). When trixie.de yields no packshot or fewer than three files it also asks **trixie.es** and merges those in behind them — `TRIXIE_ES=0` skips it, `TRIXIE_ES=always` asks every time |
| `trixie-es.py --images <art>` / `--article <art>` | the Spanish TRIXIE shop: articles trixie.de has dropped, 1500×1500 files, the English name and the on-page `Ref.` that confirms the article. Only files carrying **our** article are returned; a trailing-1 vendor form (`35031` → article `3503`) is reported on stderr as a candidate, never used silently. Cache: `.siruk-cache/trixie-es.json` |
| `trixie-shop-index.py [--cached] [--lookup <art>]` | **trixie.shop**, Trixie's own Shopify store (approved fallback, 2026-09-11): pulls the whole catalogue in 12 requests and indexes it by article number. Variant `sku` is the article and the files keep Trixie's names, so a hit is self-verifying; it also carries the family files the CDN probe cannot guess (`PHO_PRO_CLIP_SilverReflect-12222-1`). Drops `created-with-AI` renders. Index: `.siruk-cache/trixie-shop-art-images.json` |
| `trixiecz-index.py --sitemap` / `--sweep [--from N --to N]` / `--lookup <art>` | **trixiecz.cz**, the official Czech distributor (approved fallback, 2026-09-11) — the route to discontinued articles. `--sitemap` walks the two product sitemaps; `--sweep` walks the numeric ids (`/en/a_z<id>/`, live = 301, dead = 404), which is what reaches the clearance stock the sitemap omits. Reads `data-code`, `data-ean` and the English `<h1>`; normalises images to the 570×570 rendition. Index: `.siruk-cache/trixiecz-index.json` |
| `add-all-images.py [--only id,…] [--dry-run]` | backfill: uploads every gallery image for each Trixie variant and sets the full `images` list in gallery order, packshot first (resumable) |
| `feature-image.py [--apply] [--sheet] [--only id,…] [--out dir]` | **feature-image audit** (CLAUDE.md rule 7): classifies every variant image by its stored filename, reorders so a clean product shot leads (`--apply` PUTs), writes `feature-images.csv` + `needs-packshot.csv` and, with `--sheet`, an HTML contact sheet of every first image to check by eye |
| `media-folder.py <path>` \| `--list` | makes sure a media-library folder chain exists (`POST /media-folders {name, parentId}`, as the admin does); named after the brand / product type ("Products / Royal Canin / Dry Food"); `--list` prints the tree. `upload-media.sh` calls it |
| `organize-media.py [--apply] [--only <dir>]` | re-files every product image into `products/<brand-slug>/<type>/`, logos into `logos/`, category tiles into `categories/` via the bulk `POST /medias-move`; dry run by default, idempotent. Reads `.siruk-cache/catalogue-snapshot.json`. Log in `runs/<date>/media-reorg/` |
| `upload-media.sh <file\|url> [dir]` | downloads (browser UA) if given a URL, sanitises the filename, uploads multipart, **checks the file is really readable**, prints the media id. URL→id results are cached in `.siruk-cache/media-cache.json`, so re-running a row never re-uploads the same image (delete that file to force fresh uploads) |
| `verify-media.sh [--fix] [product-id…]` | checks every image of every product (or just the listed ones) actually resolves; `--fix` re-uploads from the recorded source url and relinks. Run it after every import |
| `verify-media.sh --brands` | the same for brand logos, plus the case a product sweep can't see: **several brands pointing at one media** |
| `set-brand-logo.sh <brand-id> <file\|url\|mediaId>` | replaces an existing brand's logo, keeping name/slug/meta. Refuses an image another brand already uses (`FORCE=1` overrides) and verifies the new url resolves |
| `rasterize-svg.sh <file.svg> [width] [out.png]` | renders an SVG logo to a tight PNG with headless Chrome. The media library can't serve SVG, and Bewital (Belcando/Leonardo/Bewi) and Agras (Schesir/Stuzzy) publish only SVG. `qlmanage` is not a substitute — it pads or clips |
| `pace.sh [product\|api\|media\|show]` | `show` prints the effective pacing/retry settings; `product` is the breather to call between two CSV rows |

## Pacing, retries and the image check — `config.json`

Everything in `scripts/` reads `config.json` in the repo root on every call, so
editing it takes effect immediately — no restart, nothing to re-source.
All times are **seconds** (decimals fine); `0` turns a knob off.

```jsonc
"request": { "delay_seconds": 0.6,    // minimum gap between two API calls
             "jitter_seconds": 0.3,   // random extra, so calls aren't metronomic
             "chunk_size": 15,        // after this many calls…
             "chunk_pause_seconds": 5,//  …take a longer breather
             "idle_reset_seconds": 120, "timeout_seconds": 60,
             "connect_timeout_seconds": 15 },
"retry":   { "attempts": 4, "backoff_seconds": 2, "backoff_factor": 2,
             "max_backoff_seconds": 30,
             "retry_on_status": [408,425,429,500,502,503,504],
             "retry_on_network_error": true },
"media":   { "delay_seconds": 2, "chunk_size": 5, "chunk_pause_seconds": 15,
             "max_pixels": 2000,
             "verify": { "enabled": true, ... } },   // see below
"product": { "pause_seconds": 3 }                    // between two CSV rows
```

The gap is measured from the *previous request*, and the counter lives in
`.siruk-cache/.pace-<channel>` — so pacing holds **across separate script
invocations** (an import run is one script call per row), and resets itself
after `idle_reset_seconds` of quiet. Uploads are paced separately (and harder)
from plain API calls.

`scripts/pace.sh show` prints what the scripts are actually running with.
`scripts/pace.sh product` is the between-rows breather for an import loop.

Env vars beat the file for one-off overrides: `SIRUK_DELAY`, `SIRUK_CHUNK_SIZE`,
`SIRUK_CHUNK_PAUSE`, `SIRUK_MEDIA_DELAY`, `SIRUK_RETRIES`, `MAX_PX`,
`SIRUK_CONFIG=/path/to/other.json`, and `SIRUK_NO_PACE=1` to skip all waiting
for a single ad-hoc call.

### Dead images: always verify an upload

`POST /medias` can return **201 with a media id whose file is not readable** —
the record exists, `GET /medias/<id>` works, and every storage url 404s. The
product then saves happily with a dead image (found 2026-08-13 on product 71).

Known cause: **a `%` or a space in the filename.** A source url like
`…_HEALTH%201.png` yields the filename `…_HEALTH%201.png`, which is served back
inside a url, decoded once more, and no longer matches anything on disk.
`upload-media.sh` now percent-decodes and slugifies the filename to
`[A-Za-z0-9._-]` before uploading, and afterwards fetches the media record and
GETs its url. A media that never becomes readable is deleted and re-uploaded
(`media.verify.upload_attempts`), and the script fails loudly rather than
handing back a dead id. Cached URL→id hits are re-checked too, so a bad id
can't be reused. `KEEP_ALPHA=1` and the checks are independent.

`scripts/verify-media.sh` sweeps products that already exist; `--fix` re-uploads
from the source url in `.siruk-cache/media-cache.json` and relinks the variant.
Run it after every import.

Note what a "media" is: **one upload creates three rows** — the original,
`<name>-adminThumbnail` and `<name>-<hash>` (the webp the storefront serves).
`GET /medias/<id>.url` always returns the admin thumbnail, so the webp — the url
a customer's browser actually requests — is checked separately
(`media_webp_status` in `lib.sh`, used by `--brands`).

### Media ids are recycled

Deleting a media frees its id for a later upload. Media 61 was the Schesir logo
on 2026-08-12; the next day the same id was a Royal Canin packshot, so every
brand referencing 61 silently changed picture. **Never delete a media something
still points at** (the record carries `isUsed`), and re-check any id written down
in an older note before trusting it.

## The one dangerous call

`PUT /products/<id>` **replaces the entire variants array**. A variant missing
from the payload is deleted — silently (HTTP 200) if it wasn't the default, or
422 if it was. That's why `add-variant.sh` always rebuilds the body from a fresh
`GET` (through `siruk_payload.py`) and refuses to PUT unless:

- the variant count grew by exactly 1,
- every pre-existing variant id is still in the payload,
- exactly one variant is `is_default`.

Never hand-write a PUT body.

## Debugging

`add-variant.sh` keeps its working files in `.siruk-cache/` (gitignored):
`product-<id>-before.json`, `-put.json`, `-after.json`. Diff before/after to see
exactly what the API did. Downloaded images land there too.

Common failures:

- **401/403** → token expired, or the WAF blocked the User-Agent. The demo WAF
  403s `Python-urllib`; curl's default UA is fine.
- **500 "Attempt to read property filename on null"** (media upload) → the
  `fileInfo` part is missing or was sent as a JSON body instead of a form part.
- **422 on product create** → missing `name`/`slug`/`category_ids`/
  `attribute_family_id`, a variant without `sku`/`price`, or a field the
  catalog model refuses (`prohibited`: `pricing_type`/`price_per_kg`/`weight`,
  `unit`, `net_quantity`, `stock`, `attribute_value_ids`, `initial_stock` on an
  existing variant — `reference/admin-api.md` → "Product create").
  `siruk_payload.py` catches most of these before the request.
- **"… is not part of product type …" / "… is required by the product type"**
  (`siruk_payload.py`) → the row's type lacks that attribute or needs one the
  row doesn't fill: extend the type with the `attribute-manager` agent
  (CLAUDE.md 8b), don't drop the check.
- **"sale price at or below cost"** → the variant's `price` is not hafo's row
  for that SKU (or was invented). Re-run `hafo-lookup.py`; never override
  without the user.

## Keeping this folder clean

`scripts/archive/` holds one-off run scripts whose job is finished — a driver
hardcoded to one date/brand/batch (`_run-import-2026-09-11.sh`,
`plan-small.py`) that nothing else calls and that a fresh CSV wouldn't reuse.
Moved there with `git mv`, never deleted, so the history stays. They resolve
the project root from their own path, so an archived script must be moved
back into `scripts/` before it will run. When a run
script's job is done, archive it in the same session rather than leaving it
at the top level — that's what let 30 of these pile up before the
2026-09-23 cleanup. A script belongs in the main folder, not archive, if
anything still calls it by name (grep `reference/script-guide.md`, `CLAUDE.md`,
`.claude/skills/*/SKILL.md`) or if it's general-purpose enough for the next
brand/run to reuse as-is.
