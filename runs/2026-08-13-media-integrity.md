# Dead product images — root cause, fix, and the new pacing config (2026-08-13)

**Reported:** a product image url on the storefront 404s, e.g.
`https://demo-api.siruk.am/storage/webp/18461_BCC_Dry_food_7STERILIZED_URINARY_HEALTH%201.jpg-6a7c617ed29e2.webp`
Suspected cause: the server buckling under back-to-back import requests.

## What it actually was

Not load. **The filename.**

The image came from `brit-petfood.com/…/18461_BCC_Dry_food_7STERILIZED_URINARY_HEALTH%201.png`,
where `%20` is a percent-encoded space. `upload-media.sh` took the url basename
verbatim, so the media record was created with a filename containing a literal
`%`. The api serves that filename back inside a url (`…HEALTH%201.jpg-…webp`),
which is decoded a second time on the way in — to a space — and no longer
matches anything on disk. Result: **`POST /medias` → 201 with a valid id whose
every storage url 404s.** `GET /medias/<id>` returns a perfectly normal record,
so nothing downstream noticed; the product saved with a dead image.

Reproduced deterministically:

| upload | filename sent | storage url |
|---|---|---|
| original (media 621) | `…_HEALTH%201.jpg` | 404 |
| re-upload (media 720) | `…_HEALTH%201.jpg` | 404 |
| re-upload (media 723) | `…_HEALTH%201.jpg` | 404 |
| same bytes, clean name (media 726) | `brit-sterilized-urinary-health.jpg` | **200** |

Three retries produced the *same* dead url — a crash would not be that
reproducible. Rate limiting was never the problem, but pacing is worth having
anyway (below), and the verification it enabled is what found this.

**For the dev team:** `POST /medias` should reject or sanitize a filename it
cannot serve back, instead of creating an unusable record and reporting success.

## Fixes shipped

1. **`scripts/upload-media.sh` sanitizes filenames** — percent-decodes, then
   slugifies to `[A-Za-z0-9._-]` (`…_HEALTH%201.jpg` → `…_HEALTH-1.jpg`). The
   human-readable caption/alt keeps the decoded name.
2. **Every upload is verified before its id is used** — after uploading, the
   script fetches the media record and GETs its storage url. A media that never
   becomes readable is deleted and re-uploaded; if it still fails the script
   errors out instead of returning a dead id. Cached url→id hits are re-checked
   too, so a bad id can't be silently reused.
3. **`scripts/verify-media.sh`** — sweeps existing products: every variant image
   → media record → storage url. `--fix` re-uploads from the recorded source url
   (or the copy in `.siruk-cache/`) and relinks the variant with a guarded PUT.
   Report lands in `.siruk-cache/media-check.json`. Run it after every import.
4. **`config.json`** — the requested pacing/retry knobs (next section).

## `config.json` — pacing, retries, verification

Repo root, committed, read on **every** script call, so an edit applies
immediately. All times in **seconds** (decimals fine), `0` turns a knob off.

| Knob | Default | What it does |
|---|---|---|
| `request.delay_seconds` | 0.6 | minimum gap between two API calls |
| `request.jitter_seconds` | 0.3 | random extra, so traffic isn't metronomic |
| `request.chunk_size` | 15 | after this many calls… |
| `request.chunk_pause_seconds` | 5 | …take a longer breather |
| `request.idle_reset_seconds` | 120 | quiet longer than this = new run, chunk counter resets |
| `request.timeout_seconds` / `connect_timeout_seconds` | 60 / 15 | curl timeouts |
| `retry.attempts` | 4 | attempts per request |
| `retry.backoff_seconds` / `backoff_factor` / `max_backoff_seconds` | 2 / 2 / 30 | exponential backoff |
| `retry.retry_on_status` | 408,425,429,500,502,503,504 | which statuses are worth repeating |
| `retry.retry_on_network_error` | true | retry timeouts/connection resets |
| `media.delay_seconds` / `chunk_size` / `chunk_pause_seconds` | 2 / 5 / 15 | uploads paced separately (they're the heavy calls) |
| `media.max_pixels` | 2000 | downscale before upload (the endpoint 500s on huge images) |
| `media.verify.*` | on, 2s wait, 3 checks, delete-broken, 2 uploads | the dead-image check above |
| `product.pause_seconds` | 3 | breather between two CSV rows — `scripts/pace.sh product` |

Pacing is measured from the previous request and the counter lives in
`.siruk-cache/.pace-<channel>`, so it holds **across separate script
invocations** (an import run is one script call per row), not just inside a loop.

`scripts/pace.sh show` prints the effective settings. One-off env overrides:
`SIRUK_DELAY`, `SIRUK_CHUNK_SIZE`, `SIRUK_CHUNK_PAUSE`, `SIRUK_MEDIA_DELAY`,
`SIRUK_RETRIES`, `MAX_PX`, `SIRUK_CONFIG=/path/other.json`, and
`SIRUK_NO_PACE=1` to skip all waiting for a single ad-hoc call.

## Catalog state

- **Product 71** (Brit Care Cat Grain-Free Sterilized Urinary Health 7kg):
  repaired — image re-uploaded as media 729 with a clean filename, relinked to
  variant 84, verified 200. Dead media records 621/720/723/726 deleted.
- **Full sweep of all 73 products: 153 image references, 149 distinct media,
  0 broken.** Product 71 was the only casualty — it was the only image whose
  source url carried a `%` escape. Report: `.siruk-cache/media-check.json`.
- Note: `.siruk-cache/media-cache.json` (source url → media id, used to avoid
  re-uploading the same image and by `verify-media.sh --fix` to find a source)
  was reset during the investigation. It now holds only the Brit re-upload.
  `--fix` falls back to matching the media's filename against the downloaded
  copies still in `.siruk-cache/`, so repairs are still possible; a future
  import will simply re-upload an image it has seen before instead of reusing it.
