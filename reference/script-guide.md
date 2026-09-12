# Script guide — when and how to call each script

Organised by the job you are doing, not alphabetically. Every command is run
from the repo root. Bash scripts print `HTTP <code> <METHOD> <PATH>` to stderr
and JSON to stdout. Python scripts default to a dry run where they say so;
nothing with `--apply` or without `--dry-run` writes until you ask.

Two rules sit behind every script here: **the sale price comes from hafo.am**
(`hafo-lookup.py`) — or, when hafo has none, from a confirmed zoovet.am match
or the sibling fallback, never from arithmetic — and **`PUT /products` replaces
the whole variants array**, so product writes go only through the scripts that
rebuild the body from a fresh GET. `scripts/README.md` has the token setup, `config.json` knobs
and the debugging notes; this guide is the "which one, and when".

## 1. Start of every session

| When | Command | What you get |
|---|---|---|
| First thing | `scripts/api.sh GET /account` | `HTTP 200` means the token works. 401 → re-capture the token (`scripts/README.md`) |
| Before using any id | `scripts/ids.sh` | live brands, category tree, families, attributes. Trust it over any id in a note |
| Before filling attributes | `scripts/refresh-attributes.sh` | rewrites `reference/attribute-values.json`, the closed menu. Run it whenever someone edited attributes in the admin |
| Curious about pacing | `scripts/pace.sh show` | the effective delay / retry settings from `config.json` |

## 2. Importing one CSV row (the pipeline)

Run these in order, one row at a time, and verify before the next row.

| Step | Command | When / notes |
|---|---|---|
| 1 Identity + price | `scripts/hafo-lookup.py --code <article> --name "<csv name>"` | **Always first.** Need `confirmed: true` and `price_source: "variant"`. Confirmed but unpriced → try `scripts/zoovet-lookup.py` (rule 2b) and the sibling fallback, else `runs/<date>/no-hafo-price.csv`; not confirmed → `not-found.csv` |
| 2 Brand site | see section 8 | title, gallery, description from the official site (`reference/brand-sites.md`) |
| 3 Exists already? | `scripts/find-product.sh "<name words>"` | **Before creating anything.** A hit means the row becomes a variant of that product |
| 4 Images | `scripts/upload-media.sh <url-or-file>` per gallery image | prints a verified-readable media id; URL→id is cached, so re-running a row never re-uploads |
| 5a New product | `scripts/create-product.sh payload.json` | validates, refuses a variant priced at or below cost, warns on a similar product (`FORCE=1` to override), POSTs, reads back |
| 5b Extra variant | `scripts/add-variant.sh <product-id> variant.json` | GET → append → safety check → PUT → read back. Never hand-write the PUT |
| 6 Translate | `scripts/set-translation.py <id> ru .siruk-cache/tr-<id>-ru.json` then the same with `hy` | name + per-SKU texts per locale; copies every single-language field from `en` and verifies `en` is untouched |
| 7 Check | `scripts/show-product.sh <id>` | variant summary; `--json` gives the full body |
| 8 Breathe | `scripts/pace.sh product` | the between-rows pause; keeps the WAF happy |

**End of every run**

| Command | Why |
|---|---|
| `scripts/verify-media.sh` | every image of every product actually resolves; `--fix` re-uploads dead ones from the cached source url |
| `scripts/feature-image.py` | is the first image a clean product shot? `--apply` reorders, `--sheet` renders a contact sheet to look at |
| `scripts/check-hafo-prices.py` | every variant's sale price against its hafo row → `runs/<date>/price-check.csv`; `--apply` fixes unflagged mismatches only |
| `scripts/verify-translations.py` | ru/hy coverage of products, categories, brands; exit 1 if anything is English-only |
| `scripts/find-duplicate-products.py [--refresh]` | sibling rows imported as separate products — one collar sold as 22. Cross-checks trixie.de + trixie.shop against the names; writes `.siruk-cache/dedup/groups.json` and a review list |
| `scripts/translate-attributes.py --verify-only` | attribute names, value labels and family names read back in all three locales |

## 2b. Folding duplicate products back together

A row-by-row import makes one product per CSV row, so sibling rows become
sibling products. Three steps, and nothing is written until the plan reads right
(`reference/product-rules.md` → "Sibling products"):

| Step | Command | Notes |
|---|---|---|
| 1 Find them | `scripts/find-duplicate-products.py --refresh` | reads the whole catalogue, groups by trixie.de page / trixie.shop product / stripped name. `--refresh` re-reads the API (en + ru + hy) into `.siruk-cache/dedup/` |
| 2 Plan | `scripts/plan-product-merge.py` | picks the surviving product, its name, slug, categories and the **variant axis** each variant needs; writes `runs/<date>/merge-plan.json` and lists the attribute values the vocabulary still lacks |
| 2b Vocabulary | `scripts/sync-attributes.py --spec runs/<date>/attribute-spec.json` → `scripts/refresh-attributes.sh` → add ru/hy to `reference/translations-attributes.json` → `scripts/translate-attributes.py` | only on an explicit ask (rule 8) |
| 3 Merge | `scripts/merge-products.py --dry-run`, then for real | backs every product up in en/ru/hy, checks the whole body BEFORE deleting anything, DELETEs the absorbed products (SKUs are unique catalogue-wide), PUTs the survivor, re-writes ru/hy, and records `runs/<date>/variant-id-map.csv` |

`merge-products.py` is resumable (`runs/<date>/merge-state.json`) and falls back
to its own backup for a product a previous run already deleted.

## 3. Fixing a product that already exists

| I want to… | Command | Notes |
|---|---|---|
| see it | `scripts/show-product.sh <id> [--json]` | |
| change one variant field | `scripts/set-variant.sh <id> <sku> '{"price": 4200}'` | deep-merges, so `attribute_value_ids` merges key by key |
| add a variant | `scripts/add-variant.sh <id> variant.json` | |
| rename | `scripts/rename-product.sh <id> "<new name>" [slug]` | variants untouched; the name never contains the brand |
| anything else | `scripts/api.sh GET/PUT/DELETE /path [payload.json\|-]` | the escape hatch. Never a hand-written `PUT /products` body |
| fix / replace its images | section 6 | |

## 4. Translations (three languages everywhere)

Create in `en`, then write `ru` and `hy`. One locale per request.

| Resource | Command | When |
|---|---|---|
| One product | `scripts/set-translation.py <id> <ru\|hy> <file.json>` | right after create / add-variant (pipeline step 6). **List every sku** — one left out gets the English text written into that locale, wiping a translation that was already there |
| Many products | `scripts/backfill-translations.py [--only id,…] [--dry-run]` | after a batch import; uses the phrase tables in `reference/translations.json` |
| Categories | `scripts/create-category.py <spec.json>` | creating categories — only on an explicit user ask; `--dry-run` first |
| Categories | `scripts/translate-categories.py [--dry-run]` | after adding a category (add it to the table inside the script first) |
| Brands | `scripts/translate-brands.py [--dry-run]` | after `/create-brand` |
| Attributes, values, families | `scripts/translate-attributes.py [--dry-run\|--verify-only]` | after adding attribute values: add their ru/hy pair to `reference/translations-attributes.json`, then run. Probes a throwaway attribute first and refuses if English would be overwritten |
| Build the attribute table | `scripts/_build-attr-translations.py`, then `_build-attr-translations-2.py` | only when extending the vocabulary in bulk; they regenerate the JSON from their inline tables and list what is still untranslated |
| Audit | `scripts/verify-translations.py` | after every import. **Report status from this output, never from what was sent** |

Still English-only on the backend: product-variant labels. Keep them English.

Read a locale: `SIRUK_LANG=ru scripts/api.sh GET /products/<id>`.

## 5. Attribute vocabulary

| I want to… | Command | Notes |
|---|---|---|
| refresh the closed menu | `scripts/refresh-attributes.sh` | after any attribute edit in the admin |
| add / rename attributes to match Chewy | `scripts/sync-attributes.py [--dry-run]` | driven by `reference/chewy-attributes.json`; creates, renames, sets families and filter flags, never deletes |
| translate them | `scripts/translate-attributes.py` | section 4 |
| put `toy-size` back on toys | `scripts/restore-toy-size.py [--dry-run] [--only id,…]` | one-off from 2026-09-10; safe to re-run, only touches variants missing the value |

Creating attributes and values by hand goes through `/manage-attributes` (or the `attribute-manager` agent), which uses `api.sh`.

## 6. Media

| I want to… | Command | Notes |
|---|---|---|
| upload one image | `scripts/upload-media.sh <file\|url> [dir]` | sanitises the filename, uploads, **checks it is readable**, prints the id. `KEEP_ALPHA=1` keeps transparency |
| check every product image | `scripts/verify-media.sh [--fix] [id…]` | after every import |
| check brand logos | `scripts/verify-media.sh --brands` | also catches two brands sharing one media id |
| backfill full Trixie galleries | `scripts/add-all-images.py [--only id,…] [--dry-run]` | uploads every gallery image per Trixie variant, packshot first; resumable |
| audit / fix the feature image | `scripts/feature-image.py [--apply] [--sheet] [--only id,…]` | CLAUDE.md rule 7. Writes `feature-images.csv` and `needs-packshot.csv` |
| replace hafo photos with official ones | `scripts/reimage-official.py [product-id…]` | clears variant images and re-attaches only official-source images from `.siruk-cache/official-map.json`; leaves unresolved ones empty on purpose |
| turn an SVG logo into PNG | `scripts/rasterize-svg.sh logo.svg [width] [out.png]` | the media library cannot serve SVG (Bewital and Agras brands ship only SVG) |

## 7. Brands

In order, for a brand the admin does not have yet:

1. `scripts/fetch-logo.sh <url…>` — downloads candidates, rejects favicons / SVG / HTML, flags low-res. **Look at the file it prints** before using it.
2. `scripts/rasterize-svg.sh` if the only good logo is SVG.
3. `scripts/create-brand.sh "<Name>" <logo file|url|mediaId> [slug]` — refuses near-duplicates (`FORCE=1`), uploads, creates, reads back. `NO_LOGO=1` is required to create without an image.
4. `scripts/translate-brands.py` — ru/hy for the new brand.
5. `scripts/verify-media.sh --brands`.

Swap a logo later: `scripts/set-brand-logo.sh <brand-id> <file|url|mediaId>` (refuses an image another brand uses).

## 8. Brand-site helpers (media, English name, description)

| Brand | Command | What it does |
|---|---|---|
| Trixie | `scripts/trixie-catalogue.py --build` once, then `--lookup <article…>` | local article → product-page index from trixie.de (~3,250 links) |
| Trixie | `scripts/trixie-product.py --url "<page>"` or `--urls list.json --out pages.json` | English name, bullets, description and **every sibling article** on the page |
| Trixie | `scripts/trixie-image.sh <article> [--first]` | every official gallery image for the article, packshot first — trixie.de plus, when that is thin, trixie.es (`TRIXIE_ES=0` skips, `=always` forces) |
| Trixie | `scripts/trixie-es.py --images <article>` / `--article <article>` | the Spanish shop: articles trixie.de has dropped, 1500×1500 files, English name and the `Ref.` confirmation |
| Trixie | `scripts/trixie-shop-index.py` | Trixie's own Shopify store: 5,285 article numbers, Trixie's own file names, whole catalogue in 12 requests |
| Trixie | `scripts/trixiecz-index.py --sweep` | the Czech distributor: discontinued articles, `Kód` + EAN on every page, English names. The id sweep is the one that reaches clearance stock |
| any brand | `scripts/zoovet-lookup.py --search "<russian text>" [--brand <slug>]` | zoovet.am candidates: unwatermarked photo, AMD price, stock, ru description. **Always `confirmed: false`** — confirm by hand (`reference/zoovet.md`) |
| Monge / Gemon / Simba | `scripts/monge-shop-lookup.py <ean…>` or `--from-hafo hafo.json --out map.json` | exact chain article → hafo barcode → monge.shop reference → image + EN name |
| Monge (fallback) | `scripts/monge-match.py urls.txt spec.json --out out.json` | scores sitemap slugs on keyword overlap; images only, never the name |
| Schesir | `scripts/plan-schesir.py` | uses the cached schesir.com catalogue in `.siruk-cache/sources/schesir.jsonl` |

Other brands: extract from the page with the browser (`reference/brand-sites.md`).

## 9. Prices

| When | Command |
|---|---|
| Pricing a row | `scripts/hafo-lookup.py --code <article> [--name …]` — the primary source of a sale price |
| hafo has no price | `scripts/zoovet-lookup.py --search …` — usable only once the identity is confirmed by hand; then the sibling fallback; then `no-hafo-price.csv` (`reference/pricing.md`) |
| After any import, or when asked | `scripts/check-hafo-prices.py [--apply] [--only id,…]` |
| Historical fix for toys priced from hafo's top-level price | `scripts/fix-toy-prices.py` — corrects only where hafo's wholesale price equals our cost, never at or below cost |

## 10. Preparing supplier data

| Input | Command | Output |
|---|---|---|
| The five vendor price sheets in `csv/` | `scripts/normalize-vendor-csv.py [csv-dir] [-o out.json]` | one canonical row list, `.siruk-cache/vendor-rows.json`; unpriced rows kept with `skip_reason` |
| Transcribed invoice lines | `scripts/verify-invoices.py [lines.csv]` | per-invoice check that line totals add up to the printed total |
| The invoice ledger | `scripts/build-product-catalogue.py` | one row per article code with brand, species, category → `csv/invoices/2026-09-products.csv` + a needs-review file |

## 11. Batch imports and one-off repairs (history; do not re-run casually)

These were written for a specific batch. Each is dry-run by default and rebuilds PUT bodies from a fresh GET, but read the docstring before touching them again.

| Script | What it was for |
|---|---|
| `plan-toys.py` → `import-toys.py [--limit N] [--dry-run]` | the Trixie toy batch: plan from CSV + hafo + trixie.de, then create (resumable) |
| `plan-schesir.py` → `import-schesir.py [--dry-run] [--limit N] [--only name]` | the Schesir batch from the vendor sheet |
| `regroup-schesir.py [--apply]` | replayed the corrected grouping onto the live catalogue; backs up first |
| `fix-schesir-names.py [--apply]`, `fix-schesir-leftovers.py [--apply]` | name and grouping repairs after that import |
| `import-first10.py <plan.json>` | the first hafo-sourced batch |
| `recategorize-toys.py` | moved toys from the parent category into leaves |
| `fix-toy-prices.py`, `restore-toy-size.py` | see sections 9 and 5 |

## 12. Environment variables that change any script

| Variable | Effect |
|---|---|
| `SIRUK_LANG=ru` | read that locale (`Content-Language`) |
| `SIRUK_NO_PACE=1` | skip pacing for one ad-hoc call |
| `SIRUK_TOKEN=…` / `SIRUK_TOKEN_FILE=…` | token override |
| `SIRUK_API=…` | another environment (production needs its own service account) |
| `SIRUK_CONFIG=…`, `SIRUK_DELAY`, `SIRUK_CHUNK_SIZE`, `SIRUK_MEDIA_DELAY`, `SIRUK_RETRIES`, `MAX_PX` | pacing / retry / image-size overrides for one run |
| `TRIXIE_ES=0` / `TRIXIE_ES=always` | skip the trixie.es fallback in `trixie-image.sh`, or ask it for every article |
| `FORCE=1`, `ALLOW_BELOW_COST=1`, `NO_LOGO=1`, `KEEP_ALPHA=1` | per-script guards; only on the user's say-so |
