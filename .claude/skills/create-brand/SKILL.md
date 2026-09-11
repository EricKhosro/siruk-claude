---
name: create-brand
description: Create a missing brand in the Siruk admin panel — find the brand's real official logo, look at it, upload it to the media library, and create the brand with it. Use when a product import hits a brand that isn't in admin yet, or when the user asks to add/create a brand.
argument-hint: [brand name] [optional logo url]
---

Create the brand in the Siruk admin. Brand (and optional logo URL):

$ARGUMENTS

Two fields only: **name** and **logo**. Everything else (slug, meta) is derived.
Read `CLAUDE.md` for credentials and `reference/brand-sites.md` for the
brand→official-site map.

The whole difficulty of this skill is the logo. A brand is a shared reference —
its image renders next to every product of that brand — so the bar is *this is
demonstrably that brand's logo*, not *this is an image that came from a
plausible URL*. *(A previous run created brands with images that were never
looked at; Stuzzy still carries the Schesir/Agras logo as a placeholder.)*

Write via the admin JSON API using `scripts/create-brand.sh`. The UI form
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

3. **Find candidate logos** — the brand's *official wordmark/emblem*, in this
   order. Collect **2–3 candidate URLs**, don't stop at the first hit:
   - **The brand's own press kit / media / downloads page** — best source, they
     publish print-resolution files. Try the brand map in `reference/brand-sites.md` first,
     else `WebSearch` for `"<brand>" press kit logo download` and
     `"<brand>" official site`, and use only the manufacturer's domain.
   - **The brand's homepage header** — `WebFetch` the page, or with
     chrome-devtools pull the images in **one `evaluate_script`** (never
     `take_snapshot`, brand pages are huge):

     ```js
     [...document.images].map(i => ({src: i.currentSrc || i.src, w: i.naturalWidth,
       h: i.naturalHeight, alt: i.alt, cls: i.className}))
       .filter(i => /logo|brand|header/i.test(i.src + i.alt + i.cls))
       .concat([{src: document.querySelector('meta[property="og:image"]')?.content, og: true}])
     ```
   - **Wikipedia / Wikimedia Commons** for the brand (use the file page's
     full-resolution PNG, not the thumbnail).
   - Last: an image search for `"<brand>" logo png official`, and only if you can
     trace the result back to an official page.

   Watch for the trap that produced the bad images: a search result, a CDN path
   or an `og:image` that belongs to the **parent group, the distributor, a
   sibling brand, or a product pack** — Schesir/Stuzzy (both Agras Delic) and
   Belcando/Leonardo (both Bewital) are exactly the pairs that get swapped.

4. **Screen them, then LOOK at them** — this step is not optional and cannot be
   satisfied by reasoning about the URL.

   ```sh
   scripts/fetch-logo.sh '<url1>' '<url2>' '<url3>'
   ```

   It downloads each candidate, rejects SVGs (the media library can't serve
   them), HTML error pages and favicon-sized crops (<160 px), flags anything
   under 400 px as `LOW-RES`, and prints the local paths of the survivors.
   Nothing is uploaded.

   **SVG-only brand?** Don't settle for the ~120 px header bitmap — render the
   official vector: `scripts/rasterize-svg.sh <logo.svg> 1200`. That is how
   Belcando, Leonardo, Schesir and Stuzzy got 1200 px logos on 2026-08-13
   (Bewital and Agras publish nothing else). Two traps seen there:
   - the site's PNG is often the **white** version for a dark header — it
     disappears on white. Check what you rendered actually has ink in it.
   - Acana and Orijen embed the logo as **inline `<svg>`** in the page HTML
     (`class="AcanaLogo"` / `"OrijenLogo"`); extract the element, add the
     `inkscape:`/`sodipodi:` namespace declarations if it came from Inkscape, and
     hide a black background path (`path.OrijenLogo--background{display:none}`)
     before rendering.

   A `LOW-RES` verdict is not a failure — most brand sites ship a ~250×70 header
   logo, which is what Brit does. Spend one more search on a bigger version (the
   press kit, the `@2x`/full-size upload of the same file, Wikimedia); if there
   isn't one, use it and say so in the report.

   **Then open each surviving path with the Read tool and actually look at the
   image.** Confirm, by eye:
   - it is a **logo** (wordmark/emblem) — not a product packshot, not a photo,
     not a banner, not an "award"/retailer badge, not a screenshot;
   - the text in it reads as **this brand's name** — if you cannot read the
     brand's name or recognise its emblem in the picture, it is not the logo;
   - it is the brand, not its parent group or distributor;
   - it is complete and clean: uncropped, no watermark, no surrounding page
     furniture, transparent or plain background.

   Fail any of these → discard it and go back to step 3. **Never generate, draw
   or approximate a logo.** If nothing acceptable exists, create the brand with
   `NO_LOGO=1` and flag it for the user (the API accepts a null image; the UI
   marks it required, so someone has to fill it in later).

5. **Create** — pass the file you looked at, not the URL you guessed:

   ```sh
   scripts/create-brand.sh "<Brand Name>" .siruk-cache/logos/<the-one-you-chose>.png
   ```

   It uploads via `upload-media.sh` (which sanitises the filename and verifies
   the stored file is actually readable), derives `slug` (kebab-case name) and
   `meta`, POSTs `{name, slug, image, meta}` and prints the new id.
   - Transparency: the default flattens alpha onto **white**, because the
     storefront composites transparent images on black and a dark wordmark would
     vanish. Pass `KEEP_ALPHA=1` only if the user wants the logo transparent.
   - A different slug: third argument. A different meta description: `META_DESC=…`.
6. **Verify & hand back** — the script re-reads the brand from
   `GET /brands?forProducts=true` and prints the logo's storage URL. Confirm the
   URL resolves (`scripts/verify-media.sh` covers products; for a brand, fetching
   the printed URL is enough) — a media id is not proof the file exists.
   Report the **brand id** (that's the `brand_id` the caller needs), the logo
   source URL and the media id.
6b. **Translate it** — `scripts/translate-brands.py` writes `ru`/`hy` for
   every brand (Latin name in all locales, translated meta); run it after the
   create so the new brand is not English-only.
7. **Record it** — append the brand to the brand id list in
   `reference/admin-api.md` (and the quick ids in `CLAUDE.md`), and to the
   brand→official-site table in `reference/brand-sites.md` if you learned the
   official domain. If this ran inside an import, note in `runs/<date>-report.md`
   that the brand was created (name, id, logo source) rather than flagged as
   missing.

## Fallback (UI)

Only if the API create fails in a way the error doesn't explain: open
`https://demo-api.siruk.am/admin/catalog/brands/create`, `fill_form` the name
(slug usually auto-fills), attach the logo from the media library or with
`upload_file`, save, then read the id back via
`scripts/api.sh GET '/brands?forProducts=true'`. The logo rules above apply
unchanged — the image still has to be one you looked at.

## Safety

- One brand per real brand — never create a duplicate or a second spelling.
- Never rename, re-image or delete an existing brand here; this skill only adds.
  An existing brand with a wrong logo is a separate, explicit request — and then
  the tool is `scripts/set-brand-logo.sh <id> <file>`, never a hand-written PUT.
- Never point two brands at one media. That is what made every brand render the
  same picture until 2026-08-13; `scripts/verify-media.sh --brands` now catches
  it, and `set-brand-logo.sh` refuses it.
- Distributors are not brands: the CSV's `Brand / Vendor` is `Brand / local
  distributor` — create the **brand** (part before the `/`), never the
  distributor.
- Demo environment only. If `SIRUK_API` points elsewhere, stop and confirm.
