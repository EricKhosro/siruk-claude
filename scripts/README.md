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

| Script | What it does |
|---|---|
| `api.sh METHOD PATH [payload.json\|-]` | ad-hoc call — the escape hatch (`api.sh GET '/products?search=brit'`) |
| `ids.sh` | live brands / category tree / families / attributes ids. Trust this over ids written in docs |
| `refresh-attributes.sh` | regenerates `reference/attribute-values.json` (the closed menu). Atomic write |
| `create-brand.sh "<Name>" [logo file\|url\|mediaId] [slug]` | creates a missing brand: refuses on an exact/near duplicate, uploads the logo, POSTs `{name,slug,image,meta}`, reads it back. `FORCE=1` overrides the near-match guard, `KEEP_ALPHA=1` keeps logo transparency |
| `find-product.sh <text>` | **run before creating anything** — does the product already exist? |
| `show-product.sh <id> [--json]` | variant summary, or the full re-postable body |
| `create-product.sh <payload.json>` | validates required fields, warns if a similar product exists (`FORCE=1` to override), POSTs, reads back |
| `add-variant.sh <id> <variant.json>` | GET → append → safety-check → PUT → read back |
| `rename-product.sh <id> "<name>" [slug]` | rename without touching variants (product names must not contain the brand — the storefront prints it separately) |
| `set-variant.sh <id> <sku> '<json patch>'` | patch one existing variant in place (deep-merges, so `attribute_value_ids` merges key-by-key) |
| `upload-media.sh <file\|url> [dir]` | downloads (browser UA) if given a URL, uploads multipart, prints the media id. URL→id results are cached in `.siruk-cache/media-cache.json`, so re-running a row never re-uploads the same image (delete that file to force fresh uploads) |

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
