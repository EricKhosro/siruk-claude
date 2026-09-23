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
| 4 Images | `scripts/upload-media.sh <url-or-file> products/<brand-slug>/<type>/` per gallery image | prints a verified-readable media id; URL→id is cached, so re-running a row never re-uploads. Always pass the directory — `banners/…` for non-product images |
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
to its own backup for a product a previous run already deleted. `--run
runs/<date>` points it at another run folder (plan, backups, state).

**Food, treats and pharmacy siblings** (2026-09-16) fail step 1 — the brand
gives every flavour its own page and the flavour sits inside the product Name,
so neither the page signal nor the stripped-name signal joins them. Those groups
are decided by hand, with the evidence written down:

| Step | Command | Notes |
|---|---|---|
| 1 Decide | `runs/<date>/variant-groups.json` | one entry per group: ids, the line name, ru/hy names, `why`, and per SKU the new label + the attribute labels to set (`flavor`, `product-weight`, `pet-weight-range`, `size`, `color-family`) |
| 2 Plan | `scripts/plan-variant-merge.py --run runs/<date>` | resolves the groups against `.siruk-cache/catalogue-snapshot.json`, refuses two variants that would share an attribute combination, lists the labels the menu lacks, writes `merge-plan.json` + `merge-plan.md` in the same shape `merge-products.py` reads |
| 3 Vocabulary | add ru/hy to `reference/translations-attributes.json` → `scripts/add-attribute-values.py <code> --apply` → `scripts/translate-attribute-values.py <new ids>` | the targeted translator writes only the new values (the full `translate-attributes.py` is ~1,700 PUTs) |
| 4 Merge | `scripts/merge-products.py --dry-run --run runs/<date>`, then for real | as above |
| 5 Snapshot | `scripts/catalogue-snapshot.py --ids <all group ids>` | re-reads the survivors and drops the deleted ones — minutes, not the hour a `--refresh` takes |
| 6 Axes | `scripts/backfill-variant-axes.py [--apply]` | rule 9a: every variant of a multi-variant product gets the axis its siblings carry, read off its label; lists what still collides |

## 2c. Importing a toys CSV

Still the live path for a batch of toys, not a one-off — re-run whenever there
is a new toys CSV.

| Step | Command | Notes |
|---|---|---|
| 1 Plan | `scripts/plan-toys.py [--out .siruk-cache/toy-plan.json]` | CSV row + hafo price + trixie.de page → create payload; `toy-type` from Trixie's own breadcrumb, `material`/`toy-feature` from page bullets, `lifestage` only when the breadcrumb or name says puppy/kitten — anything without evidence is left unset and reported |
| 2 Import | `scripts/import-toys.py [--limit N] [--dry-run]` | resolves each variant's image (`trixie-image.sh`), uploads it, checks for an existing product by slug, POSTs and reads back; resumable via a state file |

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
| Build the attribute table | `scripts/archive/_build-attr-translations.py`, then `archive/_build-attr-translations-2.py` (archived; move back into `scripts/` before running — their `ROOT` is one level up) | only when extending the vocabulary in bulk; they regenerate the JSON from their inline tables and list what is still untranslated |
| Composition / analytical / additive lines | `scripts/translate-composition.py --check strings.json` (or `import` and call `tr(text, "ru"\|"hy")`) | rule-based ru/hy, term by term, for the formulaic Trixie/Monge lines; unrecognised terms are reported, never guessed |
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
| put the pack weight on every variant that prints one | `scripts/backfill-product-weight.py [--create-values] [--apply] [--families all]` | CLAUDE.md rule 8a. Reads the weight (numeric field → variant label → product name), refuses a dose band / length / bare count, and fills a product **all-or-none** so no variant drops out of the pack-size dropdown. Audit first, then `--create-values` (writes ru/hy into `reference/translations-attributes.json` — run `translate-attributes.py` after), then `--apply` |
| give a product its attribute family | `scripts/set-attribute-family.py --dry-run` then `--apply [--only id,…]` | a product with `attribute_family_id: null` serves no attribute facets at all on the storefront; sets the family from the leaf category (Grooming/Accessories/Litter — the families that didn't exist until 2026-09-15). Rebuilds from a fresh GET, refuses to write if a variant would be lost |

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
| find every variant still showing a hafo photo | `scripts/hafo-audit.py [--csv runs/<date>/hafo-images.csv]` | rule 7a: catches watermarked placeholders the caches lost too, by matching the hafo CDN url or hafo's own file-name patterns. Feeds `needs-image.csv` |
| collect every source's images for a run's products | `scripts/enrich-images.py --build` then `--apply [--only id,…] [--limit N] [--dry-run]` | the reusable fallback ladder (brand packshot → pack → detail/set → trixiecz → in-use → lifestyle → group/drawing → hafo last), ranked and keyed to the article per `config.json` → `images.sources` |
| walk the fallback ladder for variants with no usable photo | `scripts/gap-images.py --worklist .siruk-cache/image-worklist.json --out runs/<date>/found [--sheet] [--only id,…]` | brand → trixie.shop → trixiecz.cz → tiierisch.de → monge → web search, downloaded with provenance and rendered to a contact sheet — nothing is attached before it's looked at (rule 7) |
| attach reviewed gap images | `scripts/apply-gap-images.py runs/<date>/found/found.json […] [--dry-run] [--only id,…]` | uploads each `found.json` entry in gallery order (index 0 = feature image, already vetted from the contact sheet) and PUTs one rebuilt product per id; drops any hafo placeholder the real photo replaces |
| last-resort keyed image search | `scripts/find-article-image.py <article> […]` | Trixie only: zoo4you.de, gundogstore.eu, miscota.com — pages that print the article in the URL/markup. Prints candidates; nothing uploaded until you've looked at the file (rule 7) |

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
| Trixie (internal) | `scripts/trixie-parse.py --url "<page>"` / `--urls list.json --out out.json` | parses a page already cached by `trixie-product.py` into name, breadcrumb, species, gallery order, bullets, prose, per-article variant table, composition/analytical/additives |
| Trixie (internal) | `scripts/trixie-gallery.py <article…>` / `--batch articles.json` | every official gallery image for an article, ranked packshot first, from the cached page plus a CDN probe — the logic `trixie-image.sh` calls |
| Trixie (internal) | `scripts/trixie-cdn-sweep.py <article…>` / `--plan plan.json [--refresh]` | probes the trixie.de CDN directly for every `PHO_*`/`GRA_*` shot of an article, not just the ones a product page happens to list — needed since one page often covers a whole product family |
| any brand, by EAN | `scripts/4lapy-lookup.py --search "<brand line words>" --ean <ean>` (or `--url <page>`) | 4lapy.ru: each pack-size offer prints its barcode, so an EAN hit is **confirmed**; per-offer photos + Russian description, composition, feeding. `--reindex` refreshes the sitemap cache |
| any brand | `scripts/zoovet-lookup.py --search "<russian text>" [--brand <slug>]` | zoovet.am candidates: unwatermarked photo, AMD price, stock, ru description. **Always `confirmed: false`** — confirm by hand (`reference/zoovet.md`) |
| any brand | `scripts/nemo-lookup.py --search "<text>" [--brand <slug>]` / `--url <page>` | nemo.am candidates: AMD price, stock, manufacturer, ru/hy description. No article code at all on the platform — **always `confirmed: false`**, confirm the same way as zoovet (brand+line+flavour+pack, pack photo matching) |
| Monge / Gemon / Simba | `scripts/monge-shop-lookup.py <ean…>` or `--from-hafo hafo.json --out map.json` | exact chain article → hafo barcode → monge.shop reference → image + EN name |
| Monge (fallback) | `scripts/monge-match.py urls.txt spec.json --out out.json` | scores sitemap slugs on keyword overlap; images only, never the name |
| Monge group (source) | `scripts/monge-it-crawl.py [--limit N] [--refresh]` | crawls all ~2,080 monge.it product pages (Monge, BWILD, Grill, Fresh, Gran Bontà, Gemon, Simba, Lechat, Special Dog, Leo's) and indexes them by the EAN in each pack photo's file name — `.siruk-cache/ean2mit.json`, feeds `plan-monge.py` |
| Monge group (source) | `scripts/monge-it-page.py --url <page>` / `--urls list.json --out pages.json` | one monge.it page → name, og:image + gallery, description, composition, analytical constituents, additives, feeding table |
| Monge group (source) | `scripts/monge-shop-page.py --url <page>` / `--from .siruk-cache/mongeshop-group.json --out pages.json` | one monge.shop (PrestaShop, `/gb/`) page → name, EAN reference, gallery, description + the "Produkt card" attribute table |
| Schesir | `scripts/plan-schesir.py` | uses the cached schesir.com catalogue in `.siruk-cache/sources/schesir.jsonl` |
| Rolf Club / Inspector / Gelmintal era | `scripts/neoterica-fetch.py --brands rolfclub-3d,inspector,... --out .siruk-cache/neoterica/pages.json` | live scraper for neoterica.ru brand listings and product pages: name, 544×600 images, description, composition, instructions |

Other brands: extract from the page with the browser (`reference/brand-sites.md`).

## 9. Prices

| When | Command |
|---|---|
| Pricing a row | `scripts/hafo-lookup.py --code <article> [--name …]` — the primary source of a sale price |
| Pricing a whole CSV at once | `scripts/hafo-batch.py csv/products.csv .siruk-cache/hafo-all.json` — resumable, keyed by article code; calls `hafo-lookup.py` per row and writes progress every 10 |
| hafo has no price | `scripts/zoovet-lookup.py --search …` or `scripts/nemo-lookup.py --search …` — either order, usable only once the identity is confirmed by hand; then the sibling fallback; then `no-hafo-price.csv` (`reference/pricing.md`) |
| After any import, or when asked | `scripts/check-hafo-prices.py [--apply] [--only id,…]` — hafo cross-check; **the register outranks it** since 2026-09-16. Covers hafo-priced rows only — recheck a zoovet/nemo-priced row by hand with `zoovet-lookup.py --url`/`nemo-lookup.py --url` (`reference/pricing.md` → "Recheck") |
| The PM's register (rule 2c) | `scripts/register-audit.py` → `scripts/register-price-sync.py --run state/register [--apply]` — every live variant whose price differs from `Վաճառքի գին` is re-priced; at-or-below-cost and typo-level jumps are written to `price-sync.csv` as SKIP / SUSPECT, never applied |
| Historical fix for toys priced from hafo's top-level price | `scripts/fix-toy-prices.py` — corrects only where hafo's wholesale price equals our cost, never at or below cost |

## 10. Preparing supplier data

| Input | Command | Output |
|---|---|---|
| The five vendor price sheets in `csv/` | `scripts/normalize-vendor-csv.py [csv-dir] [-o out.json]` | one canonical row list, `.siruk-cache/vendor-rows.json`; unpriced rows kept with `skip_reason` |
| Transcribed invoice lines | `scripts/verify-invoices.py [lines.csv]` | per-invoice check that line totals add up to the printed total |
| The invoice ledger | `scripts/build-product-catalogue.py` | one row per article code with brand, species, category → `csv/invoices/2026-09-products.csv` + a needs-review file |

## 10b. Auditing the whole CSV against what is live (2026-09-15)

Answering "what from this CSV is still not on the site?" — the 2026-09-15
sweep. Run them in this order.

| Step | Command | What you get |
|---|---|---|
| 1 Snapshot the catalogue | `scripts/catalogue-snapshot.py [--refresh]` | every product with its variants' SKUs → `.siruk-cache/catalogue-snapshot.json`. **Resumable** — a re-run only fetches products it does not already hold, so the incremental pass after an import is quick |
| 2 Diff | `scripts/csv-vs-live.py` | `runs/<date>/csv-vs-live.json` = `{live, missing}`. A row counts as live when its article code is a variant SKU; Trixie codes are matched with the `Tx`/`TXN` stripped, and also one trailing vendor digit removed **when the live variant's cost equals the row's buy price** (that is how `40261Tx` resolves to SKU `4026`) |
| 3 Re-point the planners | `scripts/refresh-planner-inputs.py --diff runs/<date>/csv-vs-live.json` | rewrites `.siruk-cache/todo-rows.json` and `live-catalogue.json` from today's reality, so `plan-trixie.py` / `plan-monge.py` / `plan-small.py` skip everything already live (originals backed up as `*.pre-2026-09-15`) |
| 4 Import | `scripts/import-plan.py <plan>.json` | as usual. **Run one plan at a time** — two concurrent imports starve each other on the paced API |
| 5 Translate a batch | `scripts/apply-translations.py <translations.json> <plan>.state.json` | writes ru + hy for every product in the plan; the translation file is keyed by **slug** → `{skus, ru:[name, html], hy:[name, html]}`, ids come from the plan state so no name search is needed |
| 6 Collect what was made | `scripts/write-run-report.py` | reads all created products back from the API → `runs/<date>/created.json`, and prints any variant priced at/below cost or without an image |
| 7 The ledger | `scripts/build-import-ledger.py --diff runs/<date>/csv-vs-live.json --out runs/<date>/import-ledger.csv` | one line per CSV row: name, code, imported, info source, price source, why not. Info sources are recovered from every run report's markdown tables, overridden by `runs/<date>/sources.json` |

Two readers written for this run, both keyed to the article, never to a name:

| Command | |
|---|---|
| `scripts/trixiecz-page.py <url>...` | one trixiecz.cz product page → the `Code:` it prints, its EAN, English name, description and the full-size images (kept only when Trixie's own file name carries the article, which is what filters out the category-menu icons) |
| `scripts/8in1-page.py <slug>...` | one 8in1.eu product page → name, pack sizes, bullets, description and the product's own `csm_TH…` photos (the `/fileadmin/pictures/8in1_*_Category_*` banners are dropped) |

`scripts/repair-media.py <product-id>... --ids <a,b,c>` re-uploads and relinks a
**known** list of broken media, for when `verify-media.sh --fix` would spend its
time walking a whole catalogue. Note it has never been exercised against a
genuinely broken media — the run it was written for turned out to be a false
alarm (see below), and `upload-media.sh` will return the cached id unchanged if
the media verifies fine.

> **Media checks must be paced.** An unpaced concurrent sweep of `/medias/<id>`
> makes the demo API return HTTP 500 and empty bodies, which looks exactly like
> the "media id whose file was never written" bug. On 2026-09-15 that produced a
> 14-media false alarm; all 78 resolved when checked serially. `verify-media.sh`
> prints nothing until it finishes — it is slow, not hung.

## 10c. The PM's register — the stock list with prices but no codes (2026-09-16)

`csv/Product.numbers` is the shop's own goods-on-hand list: Armenian name,
quantity, cost, **sale price** (`Վաճառքի գին`, the price of record — rule 2c)
and a `Kg` rate for bags also sold loose. It has no article codes, so the
codes are recovered first. Run in this order; every script takes `--run`.

| Step | Command | What you get |
|---|---|---|
| 1 Read | `scripts/read-register.py --csv state/register/register.csv` | the rows (Numbers via `numbers-parser`, or the `.xlsx` export with `--src`) |
| 2 Codes from the invoice CSV | `scripts/match-register.py --reg … --out state/register/register-match.json` | exact name, then fuzzy name + equal cost |
| 3 Codes from hafo | `scripts/hafo-by-name-cost.py --in … --out state/register/hafo-recovered.json` | hafo row name + wholesale == cost → sku (`--verify` confirms by code) |
| 4 Live or not | `scripts/register-status.py` | against the snapshot; `state/register/match-overrides.json` fixes a fuzzy hit that landed on a same-cost flavour sibling (4 on 2026-09-16 — diff the flavour words) |
| 5 Audit | `scripts/register-audit.py` | per row: exists, price verdict, per-kg twin, family → `register-audit.csv/json`, `register-ledger.csv` |
| 6 Re-price | `scripts/register-price-sync.py --run state/register [--apply]` | see §9 |
| 6b Rename | `scripts/fix-outgrown-names.py --plan … --ids … [--apply]` | a live single-variant product that took the row as a sibling loses the axis from its Name |
| 7 Import the rest | `state/register/register-todo-rows.json` (CSV-shaped rows built from the status file) + `TODO_ROWS=… REGISTER_STATUS=… scripts/plan-trixie.py` / `plan-monge.py` | the planners price from the register first and group Trixie accessories by page with `size` + `color-family`, attaching to the live product on the same page (`existing_id`) |

## 11. Batch imports and one-off repairs (history; do not re-run casually)

These were written for a specific batch. Each is dry-run by default and rebuilds PUT bodies from a fresh GET, but read the docstring before touching them again.

`plan-toys.py` / `import-toys.py` are **not** in this table — they remain the
live path for importing a toys CSV (plan from CSV + hafo + trixie.de, then
create; resumable) and are re-run whenever there is a toys batch to add, not
just history.

All of these except `plan-schesir.py` and `restore-toy-size.py` now live in
`scripts/archive/`.

| Script | What it was for |
|---|---|
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
