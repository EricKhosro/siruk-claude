---
name: glovo-export
description: Fill Glovo's "Pelican Partners" product template (sku, barcode, Armenian title, image link, description, price, availability, sections) from the live Siruk catalogue on api.siruk.am — one row per variant, each image a 500×500 square hosted on ImgBB (the video's postimages.org refuses scripts). Use when the user asks to fill / update / regenerate the Glovo xlsx, list Siruk on Glovo, or hands over the Pelican Partners template.
---

# Glovo product template (Pelican Partners)

Glovo onboards a store from one Excel: `reference/glovo/Pelican-Partners-Template.xlsx`
(sheet "Partner Template Product Creati", headers in row 1, Armenian help in
row 2, **data from row 3**). How to fill it comes from Glovo's Armenian video
(2026-10-21), summarised in `reference/glovo/README.md` — read it once.

**One row per VARIANT, never per product.** A product with 3 variants is 3 rows.

## Run

```bash
.venv-img/bin/python scripts/glovo-export.py --from-export --upload  # → final/glovo/siruk-glovo-products.xlsx
```

(Windows: `.venv-img/Scripts/python`.) `--from-export` reads the whole catalogue
in Armenian from one `GET /products/export?lang=hy&format=json` (siruk-web
2026-10-27, ~15 s) through `scripts/catalogue_export.py`, which rebuilds each
variant's attribute values (id, role, label) from the export's options text and
fetches the hy category tree. 2026-10-27: field for field identical to the
per-product dumps on all 1,644 variants (`catalogue_export.py --lang hy --check`).

Without `--from-export` (the old way, ~1 h per language):

```bash
scripts/dump-products.py --refresh --fast            # en, ~1040 products, read-only
scripts/dump-products.py --lang hy --refresh --fast  # hy texts for title/description
SIRUK_LANG=hy scripts/api.sh GET "/categories?per_page=500" > .siruk-cache/glovo-categories-hy.json
.venv-img/bin/python scripts/glovo-export.py --upload
```

`--limit N` / `--ids …` for a test run, `--out` for another file.

**Images.** The video uploads each photo to postimages.org and pastes its
Direct link. postimages refuses scripted uploads (2026-10-26: 403 "Automated
uploads are not allowed via the website. Please use the official API"), and
the free account has no API key. Never get around that with browser
automation, stealth tools (Scrapling) or extra accounts. We use **ImgBB**
instead, which does the same job through an official API made for scripts:

- the key is in `.imgbb-key` (gitignored; the user's imgbb.com account, key from
  api.imgbb.com);
- `--upload` makes each variant's first image a white-padded **500×500** JPG (the
  template asks for a square, ideally 500×500), uploads it with no expiry,
  and writes `data.url` (`https://i.ibb.co/<id>/siruk-m<media id>.jpg`) into
  column D;
- each photo is uploaded once: `.siruk-cache/glovo/imgbb.json` keeps media id →
  link, so a re-run uploads only new photos (~1 s per upload, with a back-off on
  errors);
- **ImgBB has an undocumented upload cap.** On 2026-10-26 it answered "Rate limit
  reached." after ~1,030 uploads in ~50 min. The script then stops uploading,
  writes the sheet with what it has, and exits 3. Re-run `--upload` later: it
  continues from the cache (a retry loop every 15 min works). ImgBB told the
  user by phone (2026-10-26) that a second key is fine for this, so
  `.imgbb-key` holds one key per line and the script moves to the next key
  when one hits the cap. Add a key only with the user's say-so;
- without `--upload`, column D gets the original api.siruk.am url (not square)
  and the row goes on the problems CSV.

## Columns (what `scripts/glovo-export.py` writes)

| Col | Header | Value |
|---|---|---|
| A | sku (mandatory) | variant `sku` (≤64 chars; `-KG` / `-100G` loose variants keep theirs) |
| B | BARCODE | variant `barcode` when it is 8, 13 or 14 digits; a 12-digit UPC-A (Acana) gets a leading 0 (its EAN-13 form, Glovo file only); a 5-digit scale PLU (`-KG`, `-100G`) is left empty |
| C | Product Title (mandatory) | Armenian, the video's pattern `<what it is> «Brand» <name>, <options>, <size>` — e.g. `Չոր կեր շների համար «Acana» Classics Red Meat, Տավարի միս, 9.7 կգ`. Built from the hy product name, hy option labels (flavour, colour, toy size) and the size in Armenian units (կգ, գ, մլ, լ, հատ, սմ). Brand stays Latin inside «». |
| D | Image link (mandatory) | the variant's **first** image (the packshot), on a white 500×500 square, ImgBB direct link `https://i.ibb.co/<id>/siruk-m<media id>.jpg` |
| E | Description | the variant's hy "about this item", plain text, ≤300 chars at a sentence end |
| F | Price (mandatory) | variant `price` in AMD; decimals with a dot, never a comma |
| G | Availability | `1` in stock and purchasable, else `0` |
| H, I, J | Section 1–3 | the product's category leaves in Armenian with the pet, e.g. `Չոր կեր շների համար`; a dog+cat product gets one section per tree |

Left out: discontinued products, variants with no price, and the variants on
`state/glovo-exclude.csv`. Siruk can discontinue only a whole product, so a
single variant that is off sale goes on that list (sku, variant id, product id,
reason). 2026-10-27: 4 never-received Royal Canin pouches from
`final/not-received-review-2026-10-27.xlsx`. Take a row off the list when the
variant arrives. All of these are listed in `<out>-problems.csv`, together with
variants that have no image or a failed upload.

## After a run

- Open the xlsx and spot-check ~10 titles across food, treats and accessories.
- Every column-D link must open a 500×500 picture (`i.ibb.co/...jpg`); spot-check a few with curl + PIL.
- Send the user the xlsx and the problems CSV; give the row count and how many
  rows still need an image or a price.
