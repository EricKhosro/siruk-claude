---
name: create-brand
description: Create a missing brand in the Siruk admin panel — find the brand's official high-quality logo, upload it to the media library, and create the brand with it. Use when a product import hits a brand that isn't in admin yet, or when the user asks to add/create a brand.
argument-hint: [brand name] [optional logo url]
---

Create the brand in the Siruk admin. Brand (and optional logo URL):

$ARGUMENTS

Two fields only: **name** and **logo**. Everything else (slug, meta) is derived.
Read `CLAUDE.md` for credentials and the brand→official-site map.

Write via the admin JSON API using `scripts/create-brand.sh` — it dedupes,
uploads the logo, POSTs and reads the brand back. The UI form
(`https://demo-api.siruk.am/admin/catalog/brands/create`) is the fallback only.

## Steps

1. **Auth** — `scripts/api.sh GET /account`. On 401, re-capture the token per
   `scripts/README.md` (`.siruk-token`, lasts ~1 year).
2. **Does it exist already?** — `scripts/ids.sh` (or
   `scripts/api.sh GET '/brands?forProducts=true'`). An exact match (ignoring
   case/punctuation) means **use that id, create nothing**. A near-match is a
   judgment call the user makes, not you: "Brit" vs "Brit Care", "Monge" vs
   "Monge Superpremium" — stop and ask which one the product belongs to.
   `create-brand.sh` enforces both checks, so a run that dies on "brand already
   exists" is the answer, not an error to work around.
3. **Find the logo** — the brand's *official wordmark/emblem*, from its own site
   first (brand map in CLAUDE.md; else web-search `"<brand>" official site` and
   use the manufacturer domain):
   - Homepage header `<img>`, or a press/media-kit/downloads page (best source —
     they publish print-resolution files).
   - Then Wikipedia / Wikimedia Commons for the brand.
   - Then an image search for `"<brand>" logo png official`.

   Pull candidates with **one `evaluate_script`** (never `take_snapshot` — brand
   pages are huge):

   ```js
   [...document.images].map(i => ({src: i.currentSrc || i.src, w: i.naturalWidth,
     h: i.naturalHeight, alt: i.alt, cls: i.className}))
     .filter(i => /logo|brand|header/i.test(i.src + i.alt + i.cls))
     .concat([{src: document.querySelector('meta[property="og:image"]')?.content, og: true}])
   ```

   **Quality bar** — reject and keep looking if any of these fail:
   - ≥400 px on the long side (800–1600 is ideal); no favicons, no sprite slices.
   - The brand's real logo — not a product packshot, not a photo, not a
     retailer/marketplace badge, not fan art or a redesign.
   - Clean background (transparent or plain white), no watermark, not cropped.
   - Raster: PNG/JPEG/WebP. **SVG is not supported** by the media library — if
     the site only ships SVG, take the PNG the press kit offers, or an
     equivalent-resolution PNG from another official source.
   - **Never generate, draw or approximate a logo.** No acceptable image →
     create the brand without one and flag it for the user (the API accepts a
     null image; the UI marks it required, so it needs filling in later).
4. **Create** — `scripts/create-brand.sh "<Brand Name>" <logo url|file>`.
   It uploads the logo via `upload-media.sh`, derives `slug` (kebab-case name)
   and `meta`, POSTs `{name, slug, image, meta}` and prints the new id.
   - Transparency: the default flattens alpha onto **white**, because the
     storefront composites transparent images on black and a dark wordmark would
     vanish. Pass `KEEP_ALPHA=1` only if the user wants the logo transparent.
   - A different slug: third argument. A different meta description: `META_DESC=…`.
5. **Verify & hand back** — the script re-reads the brand from
   `GET /brands?forProducts=true`. Report the **brand id** (that's the
   `brand_id` the caller needs), the logo source URL and media id.
6. **Record it** — append the brand to the brand list in `CLAUDE.md`
   ("Reference data"), and to the brand→official-site table if you learned the
   official domain. If this ran inside an import, note in `runs/<date>-report.md`
   that the brand was created (name, id, logo source) rather than flagged as
   missing.

## Fallback (UI)

Only if the API create fails in a way the error doesn't explain: open
`https://demo-api.siruk.am/admin/catalog/brands/create`, `fill_form` the name
(slug usually auto-fills), attach the logo from the media library or with
`upload_file`, save, then read the id back via
`scripts/api.sh GET '/brands?forProducts=true'`.

## Safety

- One brand per real brand — never create a duplicate or a second spelling.
- Never rename, re-image or delete an existing brand here; this skill only adds.
- Distributors are not brands: the CSV's `Brand / Vendor` is `Brand / local
  distributor` — create the **brand** (part before the `/`), never the
  distributor.
- Demo environment only. If `SIRUK_API` points elsewhere, stop and confirm.
