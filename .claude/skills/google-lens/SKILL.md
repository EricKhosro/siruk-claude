---
name: google-lens
description: Find a non-hafo product photo — and, when the brand has no product page, the description / composition / feeding text — with Google search, Google Images, Google Lens and the result pages opened in a headed real Chrome driven by Scrapling (scripts/google-lens.py). Rung 9c of the image ladder, mandatory before any variant is left with hafo's watermarked photo, and the last text rung before hafo's own Armenian text. Use during /add-products when the brand site, barcode lookup, 4lapy, zoovet and web search found no photo or no text, when replacing hafo images on live products, or when the user asks to Google / Lens a product.
argument-hint: [article code(s), a run's needs-image.csv, or a still-hafo-images.csv]
---

Find a real (non-hafo) photo for each variant given:

$ARGUMENTS

hafo's photo is a watermarked placeholder (CLAUDE.md rule 7a). Before a variant
may keep one, this skill must have run for it and the result must be logged
(`reference/image-sources.md` → "Google and Google Lens before hafo").

## The browser

- **Always `scripts/google-lens.py`**, run with `.venv-scrapling/bin/python`.
  It drives the installed Google Chrome **headed** (a window the user sees)
  through Scrapling's StealthySession (`real_chrome`, normal fingerprint) with a
  persistent profile in `.siruk-cache/google-profile`. Plain automation — the
  chrome-devtools MCP's fresh profile — got Google's reCAPTCHA on the first
  query (2026-10-02); this setup got none across the test batch.
- Setup, once: `python3 -m venv .venv-scrapling && .venv-scrapling/bin/pip install "scrapling[fetchers]"`.
- **A CAPTCHA is the user's.** The script prints
  `CAPTCHA: waiting for the user to clear it in the Chrome window` and keeps the
  window open (`--captcha-wait`, default 600 s). Run it with
  `run_in_background`, watch its output, and when that line appears **tell the
  user in chat** to clear it in the open Chrome window. Never click, solve or
  bypass a CAPTCHA; never turn on `solve_cloudflare`. The cleared cookie stays in
  the profile, so it rarely comes back.
- Pace: one window, queries in a batch with `--pause` (default 6 s) between
  them. No parallel Google sessions.
- Lens is fed by **uploading the file through the camera icon**:
  `lens.google.com/uploadbyurl` redirects to a URL Google answers 403 for.
  Pass the hafo image url (it is downloaded to `.siruk-cache/lens/`) or a local file.

## Per variant

1. Gather the keys: article code, the EAN(s) (hafo's `barcodes` in
   `.siruk-cache/hafo-all.json` or the run's `hafo.json`), hafo's image url, the
   brand + line + flavour + size in Latin script (and the Cyrillic spelling from
   `reference/name-aliases.json`).
2. Write a jobs file `runs/<date>/lens-jobs.json`, three jobs per variant:
   ```json
   [{"id": "041887", "kind": "search", "q": "\"8009470041881\""},
    {"id": "041887", "kind": "images", "q": "\"041887\" monge gran bonta"},
    {"id": "041887", "kind": "lens",   "q": "https://d1b3l6j8a0ngef.cloudfront.net/uploads/….jpg"}]
   ```
   Add a `search` for `"<article>" <brand>` when the EAN finds nothing.
3. Run it in the background:
   `.venv-scrapling/bin/python scripts/google-lens.py --jobs runs/<date>/lens-jobs.json --out runs/<date>/lens-results.json`
   (`--debug runs/<date>/lens-debug` saves a screenshot + html per page when a
   result looks empty).
4. Read the results. Lens's `results` are the **Exact matches** tab (the same
   photograph elsewhere, with its pixel size in `meta`); `visual` is the All tab.
   Skip hafo.am, siruk.am and pages whose title names a different flavour, line
   or size. Prefer the largest exact match from a shop or the brand itself.
5. Open the candidate page (curl / WebFetch; Scrapling's `StealthyFetcher` only
   when a plain request is refused) and take the **full-size** image url.
6. **Accept only** (rule 7d/7e):
   - our EAN or article on the page or in the image file name, **and** the
     picture shows this exact product and **this pack size / colour**; or
   - an Exact-matches hit that is **the same photograph** as hafo's: put both on
     a contact sheet (`scripts/contact-sheet.py`) and look at pose, light, crop.
   Then download it and **look at it**: clean, unwatermarked, product alone for a
   first image. A different size, flavour or colour is a reject, even when the
   page title looks right ("Keyed is necessary, not sufficient"). **Read the
   flavour/colour/size printed on the pack** — shops that print our EAN often show
   one stock photo for every flavour (2026-10-02: three Myau flavours all showed
   the beef bag). Before writing, run `scripts/variant-image-audit.py <product id>`
   and compare each sibling's first image side by side.
7. Upload with `scripts/upload-media.sh <url> products/<brand-slug>/<type>` and
   put it **first**; hafo's photo comes out of the gallery once a real one is
   in (or stays last only if the new one is not the same pack — log why).
8. Log every variant, found or not, in `runs/<date>/needs-image.csv` /
   the run's image log: query, what came back, accepted url or "nothing", so
   no later run repeats it. Fold still-open rows into `state/open-items.csv`.

## Texts (no official page)

Same browser, same jobs file. For every row whose brand site, barcode pages,
4lapy, zoovet/nemo and petshop.ru gave no description
(`reference/image-sources.md` → "Texts when the brand has no page"):

1. `search` jobs: `"<EAN>"`, `"<article>" <brand>`, and
   `<brand> <line> <flavour> <pack>` in Latin and in the Cyrillic spelling
   from `reference/name-aliases.json`.
2. From the results' `page` urls pick the distributor / importer / pet-shop
   pages (skip hafo.am, siruk.am and the turned-down sites) and run a second
   batch of `page` jobs:
   ```json
   [{"id": "041887", "kind": "page", "q": "https://shop.example/product/…",
     "keys": ["8009470041881", "041887"]}]
   ```
   Each returns title, h1, meta description, JSON-LD `Product`, the main text
   and `keys_found`. `error: "blocked"` = a bot wall: leave that page.
3. Accept a page when `keys_found` has our EAN/article, or when two
   independent pages match brand + line + flavour + lifestage + pack. Take the
   description / composition / feeding from it, stripped of prices and shop
   text; translate as usual (Russian originals feed `ru`).
4. Nothing acceptable → **hafo's own text** is the last fallback: the
   listing's `content_html` (price table and `Արտադրող` line removed) is the
   `hy` text, translated to `en`/`ru`; the row goes on
   `runs/<date>/needs-text.csv`.
5. Log every row in `runs/<date>/text-sources.csv` (queries, pages opened,
   accepted url or "hafo", keyed by, fields taken).

## Live products (replacing hafo photos)

Production writes go through the run's script pattern (dry run first, every
write read back): the variant's gallery = new image(s) first, other non-hafo
images kept, hafo removed. Re-run `scripts/hafo-audit.py` afterwards (with the
production `SIRUK_API` / `SIRUK_TOKEN_FILE`) and report what is still hafo and
why, with the queries tried.
