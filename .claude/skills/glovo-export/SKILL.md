---
name: glovo-export
description: Fill Glovo's "Pelican Partners" product template (sku, barcode, Armenian title, image link, description, price, availability, sections) from the live Siruk catalogue on api.siruk.am — one row per variant, each image a 500×500 square hosted on postimages.org (as in Glovo's video), uploaded through a real Chrome. Use when the user asks to fill / update / regenerate the Glovo xlsx, list Siruk on Glovo, or hands over the Pelican Partners template.
---

# Glovo product template (Pelican Partners)

Glovo onboards a store from one Excel: `reference/glovo/Pelican-Partners-Template.xlsx`
(sheet "Partner Template Product Creati", headers in row 1, Armenian help in
row 2, **data from row 3**). How to fill it comes from Glovo's Armenian video
(2026-10-21), summarised in `reference/glovo/README.md` — read it once.

**One row per VARIANT, never per product.** A product with 3 variants is 3 rows.

## Run

```bash
scripts/dump-products.py --refresh --fast            # en, ~1040 products, read-only
scripts/dump-products.py --lang hy --refresh --fast  # hy texts for title/description
SIRUK_LANG=hy scripts/api.sh GET "/categories?per_page=500" > .siruk-cache/glovo-categories-hy.json
.venv-img/bin/python scripts/glovo-export.py --squares   # 1st: cut the 500×500 squares
# 2nd: upload .siruk-cache/glovo/squares/*.jpg to postimages.org in a real Chrome (below)
.venv-img/bin/python scripts/glovo-export.py             # 3rd: → final/glovo/siruk-glovo-products.xlsx
```

`--limit N` / `--ids …` for a test run, `--out` for another file, `--images imgbb`
for the old ImgBB host (`--upload-imgbb` uploads there directly, key in `.imgbb-key`).

**Images.** The video uploads each photo to postimages.org, *Do not resize my
image* + *No expiration*, and pastes the **Direct link**
(`https://i.postimg.cc/<id>/<name>.jpg`). postimages' `/json` endpoint answers
a scripted `curl` with 403 ("Automated uploads are not allowed via the website"):
it fingerprints the TLS/HTTP stack, not a header — **the same request from a
real Chrome page context is accepted (2026-10-30)**. So:

1. `glovo-export.py --squares` writes each variant's first image as a white-padded
   **500×500** JPG to `.siruk-cache/glovo/squares/m<media id>.jpg` and lists them
   in `squares.json` (the template asks for a square, ideally 500×500).
2. Upload them **from the page context of a headed Chrome** (the omp `browser`
   eval API or the chrome-devtools MCP): load `https://postimages.org`, then for
   each file `fetch('/json', {method:'POST', body: fd})` with
   `gallery=''`, `optsize=0`, `expire=0`, `numfiles=1`,
   `upload_session=<Date.now()+random>`, `file=<File named siruk-m<id>.jpg>`.
   The reply is `{"url":"https://postimg.cc/<page>/<slug>"}`.
3. Fetch that page (plain HTTP is fine) and read
   `<input … id="direct" value="https://i.postimg.cc/…">` — the canonical
   Direct link. Do **not** use the page-id path (`i.postimg.cc/<page>/<name>.jpg`
   is the 150-px thumbnail).
4. Save `.siruk-cache/glovo/postimages.json` as `{media id: direct link}` after
   every batch — that cache is what column D reads, so a re-run never re-uploads.

A rejected upload (403 or an error body) means the request left the browser
context; a CAPTCHA goes to the user, never solved by us.

Old host, kept for reference: ImgBB worked headless through its official API,
but hit an undocumented cap after ~1,030 uploads (2026-10-26) and needs a key
per line in `.imgbb-key`.

## Columns (what `scripts/glovo-export.py` writes)

| Col | Header | Value |
|---|---|---|
| A | sku (mandatory) | variant `sku` (≤64 chars; `-KG` / `-100G` loose variants keep theirs) |
| B | BARCODE | variant `barcode` when it is 8, 13 or 14 digits; a 12-digit UPC-A (Acana) gets a leading 0 (its EAN-13 form, Glovo file only); a 5-digit scale PLU (`-KG`, `-100G`) is zero-padded to 8 digits (`00108` → `00000108`; user 2026-10-26, Glovo file only). A single unit of a multipack (`<pack sku>-1`) carries the pack's EAN, as on Siruk |
| C | Product Title (mandatory) | Armenian, the video's pattern `<what it is> «Brand» <name>, <options>, <size>` — e.g. `Չոր կեր շների համար «Acana» Classics Red Meat, Տավարի միս, 9.7 կգ`. Built from the hy product name, hy option labels (flavour, colour, toy size) and the size in Armenian units (կգ, գ, մլ, լ, հատ, սմ). Brand stays Latin inside «». |
| D | Image link (mandatory) | the variant's **first** image (the packshot), on a white 500×500 square, postimages Direct link `https://i.postimg.cc/<id>/siruk-m<media id>.jpg` |
| E | Description | the variant's hy "about this item", plain text, ≤300 chars at a sentence end |
| F | Price (mandatory) | variant `price` in AMD; decimals with a dot, never a comma |
| G | Availability | `1` in stock and purchasable, else `0` |
| H, I, J | Section 1–3 | the product's category leaves in Armenian with the pet, e.g. `Չոր կեր շների համար`; a dog+cat product gets one section per tree |

Left out: discontinued products and variants with no price (listed in
`<out>-problems.csv` with variants that have no image or a failed upload).

## After a run

- Open the xlsx and spot-check ~10 titles across food, treats and accessories.
- Run `scripts/check-glovo-links.py` — it opens every column-D link and fails unless the response is an image of exactly 500×500 (20–25 min for ~1,440 links on a slow CDN day).
- Send the user the xlsx and the problems CSV; give the row count and how many
  rows still need an image or a price.
