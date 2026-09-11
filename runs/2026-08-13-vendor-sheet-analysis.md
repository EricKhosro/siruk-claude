# 2026-08-13 — Vendor sheets: analysis, brand setup, two catalogue fixes

Source: `csv/Vendors_Siruk - *.csv` (5 sheets)
Status: **groundwork complete, product import not yet started** — see "Where this
stands" at the bottom.

## The workbook

Five sheets, five different column layouts. **Sheet names do not describe their
contents** — only sheet 3 is Royal Canin.

| Sheet | Rows | Priced | Actually contains |
|---|---|---|---|
| Royal Canin 1 | 256 | 194 | Schesir 191, Stuzzy 65 |
| Royal Canin 2 | 168 | 164 | Belcando 58, Leonardo 66, Bewi Dog 20, Bewi Cat 7, Mastercraft 10, Dogland 2, Hausmarke 1 |
| Royal Canin 3 | 181 | 176 | Royal Canin (brand implied, never written in a row) |
| Joly food | 117 | 117 | Brit |
| Joly Vitamins | 26 | 26 | Canvit |
| **Total** | **748** | **677** | 71 blank-price rows skipped per user decision |

Normalized by `scripts/normalize-vendor-csv.py` → `.siruk-cache/vendor-rows.json`.

### Number formats (all verified against hand-checked values)

- `  21,500 ` comma-thousands with padding
- `20.900 դր` — **Joly food uses a DOT as the thousands separator** (= 20,900 AMD)
- `5,800 դր` — Joly Vitamins uses a comma
- `6,100 դ r` — a typo in the Canvit sheet, handled
- `-` / blank = not stocked

### Price semantics differ per sheet

- **Sheet 1** `R/Price` = **one retail unit**; the leading `12X`/`6X`/`8X6X` is the
  vendor case pack and is stripped. Proof: lamb `6X1,5KG` at 6500 ÷ 1.5 kg = 4333
  ≈ the sheet's own `PRICE/KG` of 4400.
- **Sheet 3** `Վաճառքի Գին` = **the retail multipack box as sold**. Verified
  against the live catalogue: products 54 and 34 already carry 8600 for 12×85g
  and product 22 carries 9800 for 10×140g — exactly the sheet's numbers.

## Brands

### Created ✅

| id | Brand | Logo | Source |
|---|---|---|---|
| 13 | Bewi Dog | 1200×1200, verified | `bewidog-logo-rahmen.svg` (Bewital), rasterized |
| 14 | Bewi Cat | 1200×1200, verified | `bewicat-logo-rahmen.svg` (Bewital), rasterized |
| 15 | Dogland | 300×100, verified, **low-res** | `dogland-nutrition.de` header |

All three logo media re-fetched afterwards and confirmed HTTP 200.

Two logo traps avoided:
- Dogland's header `logo.png` carries `alt="BEWI DOG® Logo"` — the sibling-brand
  trap CLAUDE.md warns about. The image itself is the correct DOGLAND wordmark.
- **bewi-cat.de's own logo SVG is white** (`fill:#FFFFFF`, for a dark header).
  Flattened onto white it renders as a blank square. The Bewital "rahmen"
  version (red panel, white mark) was used instead.
- Dogland's "rahmen" SVG rasterizes washed-out, so the crisp low-res header
  wordmark was preferred. Replace if a better one turns up.

### Not created — they are not brands ⚠️

- **Mastercraft** is **`BELCANDO® MASTERCRAFT`**, a Belcando line by Bewital. All
  10 rows map to Belcando URLs (`belcando-mastercraft-fresh-beef-10-kg`;
  toppings → `belcando-mastercraft-toppings-*-12-x-100-g`). Creating a separate
  brand would have split Belcando's catalogue. **File under Belcando (id 2).**
- **Hausmarke** is German for "house brand" — an unbranded generic distributed by
  Bewital, made by OLEWO. 1 row (`Hausmarke Croc 20 Kg`, 22500). No brand
  identity and no logo exists. **Needs a user decision.**

## Sourcing routes (all verified reachable)

| Brand | Route |
|---|---|
| Schesir | **Shopify JSON**, `…/products.json?limit=250&page=N` — 302 products in 6 requests. Rich content (composition / additives / feeding / storage) is in `<details class="cc-accordion-item">` blocks on the product page, **curl-fetchable, no browser** |
| Belcando + Mastercraft | Shopware sitemap; slugs carry pack size |
| Leonardo | same Shopware setup |
| Brit | `krmivo-brit.cz` sitemap → 572 product pages, English slugs |
| Stuzzy | WordPress, no product type; 7 category pages |
| Canvit | sitemap is a stub — browser needed |
| Royal Canin | **403 to curl, JS-rendered — browser only.** `/uk/cats/products/retail-products?page=N`, 15/page |
| Bewi Dog / Bewi Cat / Dogland | bewital sites, browser |

### ⚡ Schesir rows match by article code, not by name

Schesir image filenames embed the article code (`…/ITA_21142001_MAIN_….jpg`).
The sheet's `Կոդ` matches on the **first 7 digits** (trailing digit is a
country/pack marker: `21142003` → `ITA_21142001`). This resolves **100 of the
129** priced Schesir rows deterministically. The ~29 misses are ranges no longer
on the site (`Can Jelly 56x85g` tuna flavors, some dry bags).

## Fixes applied

### Product 99 — Tuna in Jelly 85g — repriced ✅

SKU `21123003` is the sheet's `SCHESIR C&B WET CAT TUNA IN JELLY CAN 12X85G`
(cost 730 / price 880). The product carried 680 / 820 — the numbers belonging to
the `SCH TONNO … JEL 12X85 NE` rows.

- `price` 820 → **880**, `cost_price` 680 → **730**

`PUT /products/99` → 200, built from a fresh GET. Variant id 113, images 675/678
and all attributes preserved.

### Product 100 — After Dark Chicken in Paté 80g — NOT renamed ⚠️ correction

I first flagged this as mislabeled, reasoning `AD` sat where `BABY` and `SILVER`
sit and therefore meant *Adult*. **That was wrong.** The Schesir `After Dark` tag
covers exactly 13 products, all 80 g:

| Site format | Flavors |
|---|---|
| in broth 80g can | Chicken, Quail Egg, Beef, Duck, Ham (5) |
| in paté 80g can | Chicken, Quail Egg, Beef, Duck (4) |
| in mousse 80g pouch | Chicken, Quail Egg, Beef, Duck (4) |

The sheet's `AD` rows match one-to-one, and the article-code index confirms it
independently (`21112003` → `chicken-in-broth-80g-in-can`, tagged After Dark).
80 g is unique to After Dark; Baby and Silver are 70 g. The existing name,
description, ingredients and images are all correct — **no change made**.

## Where this stands

Done: sheet normalization + verified parsing, brand creation, sourcing routes for
all 12 brands, the Schesir code-matching index, and the two catalogue fixes.

Not started: **the product import itself** (677 rows → an estimated 300–400
products). Remaining effort is dominated by per-brand content extractors and
roughly a thousand image upload+verify round trips, which is a multi-session job.

Suggested order — highest confidence first:
1. **Schesir** (129 rows, 100 code-matched, JSON + curl-fetchable content)
2. **Belcando + Mastercraft** (68 rows, slugs carry pack size)
3. **Leonardo** (66), **Brit** (117), **Canvit** (26)
4. **Royal Canin** (176) — slowest, browser-only
5. **Stuzzy** (65), **Bewi Dog/Cat + Dogland** (29)

## Open questions

1. **Hausmarke** (1 row) — file under Dogland, leave brandless, or skip?
2. Stuzzy's brand logo is still the Schesir/Agras placeholder, and **Leonardo
   (id 11) also shares that same placeholder media (61)** despite being a Bewital
   brand, not Agras. Both should be replaced.
3. No `Qty` column anywhere in this workbook — stock will default to 10.
