# 2026-09-09 — hafo workflow, corrected

Supersedes `runs/2026-09-09-hafo-import-first50.md`. Two corrections applied
after review:

1. **Images must come from the brand's official site, not hafo.** hafo is the
   identity lookup only — it tells us what a code is, which brand it belongs to
   and what it retails for, so we know *which official site to go to*.
2. **No invented prices.** Rows hafo cannot price go to a CSV, not into the
   catalogue with a markup formula.

## What changed on the demo site

- **All 33 hafo images removed** from the imported products.
- **9 official images attached**, each verified:
  - TRIXIE `4020Tx`, `40121Tx`, `40397Tx`, `42404Tx` — from `cdn.trixie.de`,
    keyed by the article number. Self-verifying: the article number is printed
    on the pack in the photo returned (checked `4020` = Simple'n'Clean
    Silikatstreu Granulat 8,0 l, Art.-Nr. 4020).
  - MONGE `011257`, `011407`, `011477`, `012067`, `012087` — from
    `monge.it`, where the image filename names the same line, flavour and pack
    (e.g. `Extra-Small-Puppy-and-Junior-Rich-in-Chicken_800g_…`).
- **6 invented-price rows pulled out of the catalogue**: products 162, 173, 192,
  193, 195 deleted, and variant `300617` removed from product 172. (For the
  record, my earlier report said those Gemon prices were 465; they were 450.)

**Now live: 34 products / 42 variants**, all priced from hafo, all images
verified readable.

## The two CSVs

| File | Rows | |
|---|---|---|
| `no-hafo-price.csv` | 6 | Fully identified — brand, official site, product name, variant, buy price — but hafo had no retail price. **Not imported.** `Sale Price (AMD)` is empty for you to fill. |
| `not-found.csv` | 2 | Could not be resolved at all. `03623K` (Интеко) and `61001K` (DOGMAN) litter mats — neither brand is in hafo's brand list and neither has a confirmed official site. **Not imported.** |

## The honest gap: 33 variants still have no image

Official-site images could only be resolved for 9 of 42 variants.

- **TRIXIE is solved** — `scripts/trixie-image.sh` resolves an exact image from
  the article number. The 2 remaining Trixie gaps (`40261Tx`, `40181Tx`) have no
  asset under any probed CDN path and are not in trixie.de's search index.
- **Monge is the problem.** monge.it's English catalogue covers only ~756 of its
  products, and its wet-food pouches in particular are largely absent. Matching
  by name across all ~2,079 sitemap URLs produced confident-looking **wrong**
  answers — the Fruit dog pouch matched a GIFT treat bar, the Gemon wet pouches
  matched Gemon kibble, and several wet pouches matched dry-food pages. I threw
  those out rather than ship them.

Remaining by brand: Monge 23, Simba 4, Trixie 2, Ok-Lock 2, Gemon 2.
Full list: `.siruk-cache/needs-official-image.csv`.

To close this properly one of these is needed, and it is a decision for you:
- a Monge product feed or EAN→product mapping from the distributor, which would
  make Monge as exact as Trixie; or
- accept hand-matching the ~23 Monge products against monge.it; or
- accept the storefront running without images on those until the brand supplies
  a feed.

## Also updated

`CLAUDE.md` now states that hafo is identity/price only, that no row may be
priced by formula, that no image may come from a fuzzy name match, documents the
TRIXIE CDN pattern, and specifies the two per-run CSVs.
