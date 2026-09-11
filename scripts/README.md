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

| Script | What it does |
|---|---|
| `api.sh METHOD PATH [payload.json\|-]` | ad-hoc call — the escape hatch (`api.sh GET '/products?search=brit'`) |
| `ids.sh` | live brands / category tree / families / attributes ids. Trust this over ids written in docs |
| `refresh-attributes.sh` | regenerates `reference/attribute-values.json` (the closed menu). Atomic write |
| `fetch-logo.sh <url\|file…>` | **before create-brand** — downloads logo candidates, rejects svg/html/favicons (<160px), flags <400px as low-res, prints local paths so you can **Read (look at) the image** before uploading it. `MIN_PX=` / `HARD_MIN=` move the bars |
| `create-brand.sh "<Name>" [logo file\|url\|mediaId] [slug]` | creates a missing brand: refuses on an exact/near duplicate, uploads the logo, POSTs `{name,slug,image,meta}`, reads it back and prints the logo url. `FORCE=1` overrides the near-match guard, `KEEP_ALPHA=1` keeps logo transparency, `NO_LOGO=1` is required to create a brand with no image |
| `find-product.sh <text>` | **run before creating anything** — does the product already exist? |
| `show-product.sh <id> [--json]` | variant summary, or the full re-postable body |
| `create-product.sh <payload.json>` | validates required fields, **refuses a variant priced at or below its cost** (`ALLOW_BELOW_COST=1` only on the user's say-so), warns if a similar product exists (`FORCE=1` to override), POSTs, reads back |
| `add-variant.sh <id> <variant.json>` | GET → append → safety-check (incl. the price-vs-cost guard) → PUT → read back |
| `set-translation.py <id> <ru\|hy> <translation.json>` | stores a product's Russian/Armenian name, meta and variant texts per locale; copies every single-language field from `en`, verifies `en` untouched. `SIRUK_LANG=ru api.sh GET …` reads a locale |
| `create-category.py <spec.json> [--dry-run]` | creates categories from a spec list, idempotently (dedupes on parent+name). Each entry `{parent, name, slug, meta_title}`; `parent` is an id or a path already in the file (`"Dog > Supplies"`), so a parent and its leaves go in one run. **Only on an explicit user ask.** Add the ru/hy pair to `translate-categories.py` afterwards |
| `translate-categories.py [--dry-run]` | ru/hy names for every category from its built-in table |
| `translate-brands.py [--dry-run]` | ru/hy for every brand (Latin name in all locales, translated meta) |
| `backfill-translations.py [--only id,…] [--dry-run]` | ru/hy for every product from `reference/translations.json` (names, recurring bullet phrases, paragraphs) via `set-translation.py` |
| `verify-translations.py` | **after every import** — audits ru/hy coverage of all products, categories and brands; exit 1 if anything is English-only |
| `translate-attributes.py [--dry-run] [--probe-only] [--verify-only]` | ru/hy for every attribute name, value label and family name from `reference/translations-attributes.json` (17 + 629 + 5); probes a throwaway attribute first and refuses if English would be overwritten; ends with a read-back of all three locales. **Run after adding attribute values** (add their ru/hy pair to the JSON first) |
| `_build-attr-translations*.py` | the source tables that generate `reference/translations-attributes.json`; extend them when values are added |
| `sync-attributes.py [--dry-run]` | syncs the vocabulary to `reference/chewy-attributes.json` (creates, renames, families, filter flags; never deletes) |
| `restore-toy-size.py` | one-off: put `toy-size` back on toy variants from their labels |
| `check-hafo-prices.py [--apply] [--only id,…]` | compares every Siruk variant's sale price with its hafo row (+ `/product/change` cross-check) → `runs/<date>/price-check.csv`; `--apply` fixes unflagged mismatches |
| `hafo-lookup.py --code <art> [--name …]` | **the primary source of a sale price** — hafo.am row for our article code (`reference/pricing.md`, `reference/hafo.md`) |
| `zoovet-lookup.py --search "<ru text>" [--brand <slug>]`, `--url <page>`, `--brand <slug>`, `--brands` | zoovet.am: unwatermarked brand packshots (the original behind the thumbnail), a second AMD price, stock and a Russian description. It has **no article code** — its `ME-…` number collides with brand articles — so every hit is `confirmed: false` until confirmed by hand (`reference/zoovet.md`, CLAUDE.md rules 2b / 7b) |
| `rename-product.sh <id> "<name>" [slug]` | rename without touching variants (product names must not contain the brand — the storefront prints it separately) |
| `set-variant.sh <id> <sku> '<json patch>'` | patch one existing variant in place (deep-merges, so `attribute_value_ids` merges key-by-key) |
| `trixie-image.sh <art> [--first]` | every official gallery image for a Trixie article, packshot first (page-based; probes the CDN for `PHO_PRO_CLIP`/`PHO_PAC_CLIP` whenever the page lists no packshot, and as the fallback when there is no page). When trixie.de yields no packshot or fewer than three files it also asks **trixie.es** and merges those in behind them — `TRIXIE_ES=0` skips it, `TRIXIE_ES=always` asks every time |
| `trixie-es.py --images <art>` / `--article <art>` | the Spanish TRIXIE shop: articles trixie.de has dropped, 1500×1500 files, the English name and the on-page `Ref.` that confirms the article. Only files carrying **our** article are returned; a trailing-1 vendor form (`35031` → article `3503`) is reported on stderr as a candidate, never used silently. Cache: `.siruk-cache/trixie-es.json` |
| `trixie-shop-index.py [--cached] [--lookup <art>]` | **trixie.shop**, Trixie's own Shopify store (approved fallback, 2026-09-11): pulls the whole catalogue in 12 requests and indexes it by article number. Variant `sku` is the article and the files keep Trixie's names, so a hit is self-verifying; it also carries the family files the CDN probe cannot guess (`PHO_PRO_CLIP_SilverReflect-12222-1`). Drops `created-with-AI` renders. Index: `.siruk-cache/trixie-shop-art-images.json` |
| `trixiecz-index.py --sitemap` / `--sweep [--from N --to N]` / `--lookup <art>` | **trixiecz.cz**, the official Czech distributor (approved fallback, 2026-09-11) — the route to discontinued articles. `--sitemap` walks the two product sitemaps; `--sweep` walks the numeric ids (`/en/a_z<id>/`, live = 301, dead = 404), which is what reaches the clearance stock the sitemap omits. Reads `data-code`, `data-ean` and the English `<h1>`; normalises images to the 570×570 rendition. Index: `.siruk-cache/trixiecz-index.json` |
| `add-all-images.py [--only id,…] [--dry-run]` | backfill: uploads every gallery image for each Trixie variant and sets the full `images` list in gallery order, packshot first (resumable) |
| `feature-image.py [--apply] [--sheet] [--only id,…] [--out dir]` | **feature-image audit** (CLAUDE.md rule 7): classifies every variant image by its stored filename, reorders so a clean product shot leads (`--apply` PUTs), writes `feature-images.csv` + `needs-packshot.csv` and, with `--sheet`, an HTML contact sheet of every first image to check by eye |
| `upload-media.sh <file\|url> [dir]` | downloads (browser UA) if given a URL, sanitises the filename, uploads multipart, **checks the file is really readable**, prints the media id. URL→id results are cached in `.siruk-cache/media-cache.json`, so re-running a row never re-uploads the same image (delete that file to force fresh uploads) |
| `verify-media.sh [--fix] [product-id…]` | checks every image of every product (or just the listed ones) actually resolves; `--fix` re-uploads from the recorded source url and relinks. Run it after every import |
| `verify-media.sh --brands` | the same for brand logos, plus the case a product sweep can't see: **several brands pointing at one media** |
| `set-brand-logo.sh <brand-id> <file\|url\|mediaId>` | replaces an existing brand's logo, keeping name/slug/meta. Refuses an image another brand already uses (`FORCE=1` overrides) and verifies the new url resolves |
| `rasterize-svg.sh <file.svg> [width] [out.png]` | renders an SVG logo to a tight PNG with headless Chrome. The media library can't serve SVG, and Bewital (Belcando/Leonardo/Bewi) and Agras (Schesir/Stuzzy) publish only SVG. `qlmanage` is not a substitute — it pads or clips |
| `pace.sh [product\|api\|media\|show]` | `show` prints the effective pacing/retry settings; `product` is the breather to call between two CSV rows |
| `regroup-schesir.py [--apply] [--only <name>]` | replays the corrected `plan-schesir.py` grouping onto the live catalogue: moves variants onto the product holding most of the range's SKUs, renames only what a merge invalidated, deletes the emptied products. Dry-run by default; `--apply` backs every touched product up to `.siruk-cache/schesir-regroup-backup.json` first |

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
`GET` and refuses to PUT unless:

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
- **422 on product create** → missing `name`/`slug`/`category_ids`, or a variant
  without `sku`/`price`/`pricing_type:"fixed"`.
- **"sale price at or below cost"** → the variant's `price` is not hafo's row
  for that SKU (or was invented). Re-run `hafo-lookup.py`; never override
  without the user.
