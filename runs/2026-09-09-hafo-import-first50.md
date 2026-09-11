# 2026-09-09 — hafo-first workflow + first 50 rows imported

New sourcing step in front of the brand sites, and the first 50 rows of
`csv/products.csv` imported to the demo admin.

## The hafo.am API

hafo.am is a Laravel marketplace; its product grid is a Vue app fed by:

```
GET https://hafo.am/products/filter?search=<q>&page=1&order_by=order-desc
    &min_price=0&max_price=200000&animal=&brand=&weight=&age=&type=&is_new=false
```

Standard Laravel paginator, 40/page. Items carry `title`, `content` (HTML),
`image_main_url`, `price`, `wholesale_price`, `slug`, `meta_*`, `product_maker`
and `product_additional_information[].sku`.

**`search` matches the SKU**, and hafo's SKUs are the same article codes our
supplier invoices use — so a code lookup is exact and language-independent.
Wrapped in `scripts/hafo-lookup.py`.

### Three things that cost time, now handled in the script

1. **SKU formats differ per brand.** Trixie is `41116Tx` (our exact format) *but
   also* `TX 040201` — a prefix, a zero pad and a trailing variant digit, so our
   `4020Tx` is hafo's `TX 040201`. Monge is `MG 013147` with a **non-breaking
   space**. Comparing raw strings silently misses, and the lookup then falls
   through to a name search that returns *a different flavour of the same line* —
   `013117` (chicken & turkey) came back as the pork one. Normalise to
   alphanumerics, allow an alphabetic prefix, and tolerate the zero-pad.
2. **A name hit is a candidate, not a match.** Marked `confirmed: false` with a
   `candidates` list. Searching `4 ԹԱԹ` for a jelly pouch returns the brand's dry
   dog food.
3. **hafo has no English.** Its ENG switch is a Google Translate widget; the
   database is Armenian only. `meta_keywords` carries hand-written English terms
   and is the best it offers. English names here were composed from the confirmed
   identity plus the brand sites.

## Lookup results — 50 rows

| | rows |
|---|---|
| confirmed by article code | 43 |
| name-guess only (not trusted) | 3 — `142535`, `40211Tx`, `40570Tx` |
| not on hafo at all | 4 — `300617`, `300657`, `40187Tx`, `61001K` |

## Pricing

Sale prices are **hafo's retail prices** for the 43 confirmed rows. Its markup
over our cost is tight and consistent — median ×1.364, range ×1.19–1.60, one mild
outlier — so the figures are sane retail numbers rather than noise.

For the 5 imported rows hafo could not price, the sale price is
`cost × 1.364` rounded to the nearest 50 and is flagged below. **These 5 are the
only invented numbers in the batch:**
`300617` 465 · `300657` 465 · `40187Tx` 3950 · `40211Tx` 3500 · `40570Tx` 10400

## Imported

**39 products / 48 variants**, ids **160–198**. All 42 image references verified
readable (`scripts/verify-media.sh`).

Rows were grouped into products by the project's variant rules — pack size,
flavour and texture stay as variants; lifestage, sterilised/adult and species
split into separate products. So 48 invoice rows became 39 products, e.g. the
three Grill Sterilised cat pouches (chicken/veal/trout) are one product.

### Brands created
`16 Ok-Lock` · `17 Club 4 Paws` · `18 Gemon` · `19 Simba` — each with a verified
official logo (ok-lock.pet, club4paws.com, monge.it/en/our-brands). Gemon and
Simba logos are low-res because that is all monge.it publishes.

## Open items

1. **2 rows not imported**, both needing brand research before a brand can be
   created with a real logo: `03623K` (Интеко litter mat) and `61001K` (DOGMAN
   litter mat). Say the word and I will research both and add them.
2. **6 variants have no image** — the 3 name-guess rows and 3 hafo misses:
   `142535`, `300617`, `300657`, `40187Tx`, `40211Tx`, `40570Tx`. The Trixie ones
   can be filled from trixie.de by `itemNo`; the rest need the brand site.
3. **Vocabulary wanted but missing** (nothing was created — per the standing rule):
   flavour values **Veal** and **Trout** (Monge Grill Sterilised cat pouches), and
   a **litre** unit for `product-weight` (cat litter is sold in 5 l / 8 l / 11 l).
   Because of the missing flavours, product 170 and the two Simba multipacks and
   both litter products carry **no variant attributes at all** rather than
   invented ones.
4. **Two transcription corrections from hafo**, both on SKU-confirmed matches:
   `012767` is hake/merluzzo, not the word I read from the scan; `301097` is
   herring (`տառեխ`), which I had read as beef (`տավարի`).
5. `40181Tx` and `40187Tx` differ only by colour and hood. Colour has no attribute
   in our system, so they are separate products.
