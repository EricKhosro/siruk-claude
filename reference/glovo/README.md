# Glovo — Pelican Partners product template

`Pelican-Partners-Template.xlsx` is Glovo's blank onboarding sheet (as received
2026-10-21). `/glovo-export` (`scripts/glovo-export.py`) fills it from the live
catalogue.

## What Glovo's video shows (Armenian, 2:39, recorded 2026-04-26)

The video fills one example row (Coca-Cola 0.5 l) column by column, starting on
row 3 (row 1 headers, row 2 the Armenian help text):

1. **sku** — any internal code (example `1`); max 64 characters.
2. **BARCODE** — the 8/13/14-digit barcode (example `12345678`). Optional, but
   Glovo asks for it.
3. **Product Title** — Armenian: product kind, brand in «», quantity:
   `Գազավորված ըմպելիք «Կոկա Կոլա» 0.5լ`. The help text: the title must tell
   the customer what they are buying — brand, product name, short
   description and quantity.
4. **Image link** — open postimages.org (link in the row-2 help), keep
   *Do not resize my image* and *No expiration*, *Choose images*, pick the
   product photo, and when "Upload completed!" shows, copy the **Direct link**
   (`https://i.postimg.cc/9FNbP6wT/Coca-Cola-0-5l-New-01.jpg`) — not the
   short `postimg.cc/...` page link — into the cell. Several images may be
   comma-separated. The help asks for a square image, ideally 500×500 px.
5. **Description** — only info not already in the title
   (`Զովացուցիչ ըմպելիք «Կոկա Կոլա» կլասիկ`).
6. **Price** — a number, decimals with a dot (`500.99`, never `500,99`); example `350`.
7. **Availability** — `1` available, `0` not (only when there is no
   stock/price integration).
8. **Section 1** (2, 3 optional) — the store section the product sits in, as
   on the Glovo app (`Գազավորված ըմպելիքներ`).

The audio was not transcribed (no speech-to-text on the Mac); the steps above
are read off the screen.

## What we do differently: ImgBB instead of postimages (2026-10-26)

postimages.org blocks scripted uploads on its website and gives free accounts
no API key, so `/glovo-export` hosts the images on **ImgBB** (api.imgbb.com,
the official API, key in `.imgbb-key`). Each image is padded to exactly
500×500 before upload. The links are permanent direct links like the video's.
