# Wiring in the two approved fallback image sources — 2026-09-11

The PM approved `trixie.shop` and `trixiecz.cz` (including the id sweep) after
the evaluation in `image-source-candidates.md`. This is what was built and what
it changed.

## What was built

| | |
|---|---|
| `config.json` → `images.sources` | the ordered chain, with what each source may be keyed on: **brand site → trixie.shop → trixiecz.cz → confirmed zoovet → hafo placeholder**. `require_article_key: true`, `min_pixels: 500` |
| `scripts/trixie-shop-index.py` | pulls Trixie's own Shopify catalogue (12 requests) and indexes it by article number |
| `scripts/trixiecz-index.py` | `--sitemap` and `--sweep` (numeric ids) for the Czech distributor |
| `scripts/enrich-images.py` | reads the chain from config, ranks the two new sources between the brand shots and hafo, and now **drops a watermarked placeholder as soon as a real photo exists** for that variant |
| `CLAUDE.md` rule 7c, `reference/brand-sites.md`, `scripts/README.md`, `reference/script-guide.md` | the rule, the per-site notes and the script entries |

## What the indexes hold

| Source | Articles indexed | Notes |
|---|---|---|
| trixie.shop | **5,285** with images (4,936 lead with a `PHO_PRO_CLIP` packshot) | 2,864 products, 12 requests, ~1 min |
| trixiecz.cz — sitemap | 2,433 | 4,771 pages |
| trixiecz.cz — **id sweep** `z1…z18000` | **4,687** (4,639 with images) | ~40 min, 30 chunks; ids 12022–12700 are a real gap in their id space, confirmed by hand |

The sweep nearly doubled the Czech index, exactly as the 400-id sample
predicted, and it is what reaches the discontinued stock: the sitemap lists
neither 35510 (Hippo, latex, 15 cm) nor 35856 (Unicorn, plush, 28 cm), and both
are on the site with clean packshots.

## Two things the sweep taught us about trixiecz.cz

1. **The gallery URLs on a product page are relative**, and the only absolute
   one is the 1200×630 social crop. A first pass that scraped absolute URLs
   therefore collected one padded square per product and nothing else.
2. **`_0` is the original.** The renditions are
   `/data/tmp/<size>/<last digit of image id>/<image id>_<size>.jpg`; `_0` is
   what the lightbox links to (1000–1920 px), `_3` a 570×570 square. The first
   uploads took `_3`; the indexer now takes `_0` and `enrich-images.py` drops a
   `_3` upload when the same variant gets the original.

Both are fixed in `scripts/trixiecz-index.py` (the scrape is scoped to
`<div class="product-gallery">` and takes the `data-rel="gallery"` hrefs), and
`--reparse` re-reads the pages already indexed after a change like this.

## What changed in the catalogue

The chain now ranks **1,046 trixie.shop** and **842 trixiecz.cz** pictures into
the image plan, and `enrich-images.py` drops a watermarked placeholder the
moment a real photo exists for that variant.

Applied so far (55 products — every product that carried a placeholder or had
no picture at all):

| | |
|---|---|
| Variants whose watermarked placeholder was replaced by a real photo | **16** (27 placeholder images removed) |
| Of the 24 rows on `needs-image.csv` | **17 now carry a real photo**, 7 do not |
| Still watermarked, whole catalogue | **22** variants → `needs-image.after-fallbacks.csv` |
| Media verified on those products | 105 references, 101 media, **0 broken** |

The 22 that remain, and why:

- **4 Monge** — Gran Bontà 400 g / 1,230 g cans. Not on monge.it in any locale,
  not on monge.shop; the only shops that stock them show carton photos. Ask the
  distributor.
- **3 Trixie** — 2411 (Comb with Rotating Pins), 33360 (Dumbbell with Soft
  Ends), 3435 (Football Ball, ø 6 cm). Gone from trixie.de, its CDN, trixie.es,
  trixie.shop and trixiecz.cz — the whole chain.
- **15 Trixie** from the later blocked-no-category batch — the bowls (25141–25245),
  the leads (200720, 201320) and the BE NORDIC bandana collars (17321–17335).
  These were imported after the worklist was written and have never been run
  against the chain by hand; the bandana collars' only picture is hafo's photo of
  a dog wearing one, which is a placeholder twice over (watermarked *and* a
  lifestyle shot).

Feature images were checked by eye on the contact sheet
(`runs/2026-09-11/fallback-audit/feature-sheet.html`): every trixiecz photo that
now leads a gallery is a clean product shot on white, and the only watermarked
leaders left are the 22 above.

## Left to run

Two things are queued rather than done, because **a second session is running
`scripts/import-plan.py` against the same admin** and two writers on one product
clobber each other (a PUT replaces the whole variants array):

1. **Upgrade the remaining 50 priority products** from the 570 px square to the
   original: 5 of the 55 were re-applied before I stopped.
2. **Gallery enrichment for the other ~416 products** — 289 variants stand to
   gain about 1,280 further pictures from the two new sources.

Both are the same command, and it is resumable:

```bash
SIRUK_CONFIG=$PWD/.siruk-cache/config-fast-media.json \
  python3 scripts/enrich-images.py --apply
```

(`.siruk-cache/config-fast-media.json` is a copy of `config.json` with shorter
media waits, made for this backfill — the project default is untouched. At the
default pacing the backfill runs about 2.5× slower.)

Afterwards: `scripts/verify-media.sh <ids>`, `scripts/feature-image.py --sheet`,
and regenerate `needs-image.csv` with `scripts/_write-run-csvs.py 2026-09-11
small-plan.json`.
