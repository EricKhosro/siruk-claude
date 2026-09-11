# zoovet.am — second Armenian source: clean photos and a second price

Added 2026-09-11 on the user's instruction: *"zoovet.am can be our source of
truth just like hafo.am, and it doesn't have a watermark in its images, so if
you don't find the picture search here also, you can use it for finding prices
also."*

zoovet.am is an Armenian OpenCart shop, Russian-language, 212 brands — **18 of
our 19** (everything except Ok-Lock). It gives three things hafo cannot:

| | zoovet | hafo |
|---|---|---|
| photos | the brand's own packshot, **no watermark**, 700–1500 px | every image stamped with a repeating "Hafo" watermark |
| price | a second Armenian retail price in AMD, plus stock | the primary price |
| text | a Russian name + description (useful for the `ru` locale) | Armenian title only |

And one thing it cannot do at all, which decides how it may be used:

> **zoovet has no brand article code.** Its `Артикул: ME-00008447` is an
> internal sequential code, and those digits **collide with brand article
> numbers**: searching `3503` (Trixie's Longies) returns a *Monge* bag whose
> zoovet code happens to be `ME-00003503`. Never search zoovet by an article
> code and never treat a numeric hit as identity.

So a zoovet hit is a **candidate**, exactly like a hafo name-search hit —
`scripts/zoovet-lookup.py` always returns `confirmed: false`. CLAUDE.md rule 6
(identity only from the article code) and rule 7 (never attach an image from a
fuzzy name match) still hold. Confirming a candidate is the step below.

## Confirming a candidate

One of these, and the evidence goes in the report:

1. **The article printed on the pack.** Trixie and most European brands print
   it: `Art.-Nr. 42703`, `#31501`. Open the **full-size** image (not the
   thumbnail) and read it. This is as good as a CDN filename match.
2. **Brand + line + flavour + pack size all match the row**, and the pack
   artwork matches the brand site's photo of the same product. Use this only
   when the pack carries no readable number.

Refuse the match when anything in the Russian name contradicts the row: zoovet
"Туалет **Carlo серый** для кошек, 37 x 15 x 47 см" is **not** our "Classic
Litter Tray, 37 × 15 × 47 cm, **mint green/white**" — same size, different
product. A colour, a line name or a pack size that disagrees is a different
article, not a translation artefact.

## The endpoints

```bash
scripts/zoovet-lookup.py --search "шампунь сухой 450"        # candidates
scripts/zoovet-lookup.py --search "шампунь" --brand trixie   # inside one brand
scripts/zoovet-lookup.py --brand trixie                      # whole brand list
scripts/zoovet-lookup.py --url https://zoovet.am/…           # full detail
scripts/zoovet-lookup.py --brands                            # brand → slug
```

Under the hood (plain HTML, no API, no auth):

- search `https://zoovet.am/search/?search=<q>&description=true&limit=100`
  (`index.php?route=product/search` 301s to it). The query is **Russian** —
  search the Russian words for the thing (`шампунь`, `туалет`, `лакомство`),
  the pack size and the brand.
- brand listing `https://zoovet.am/<slug>?limit=100&page=N` — the reliable way
  to work a brand: fetch it once (cached in `.siruk-cache/zoovet-<slug>.json`)
  and match our rows against the list offline. Trixie has 339 products there.
- product page: `product-title`, `sku` (`ME-…`), `price`, stock, the gallery,
  `attr-item__k`/`attr-item__v` spec rows and a Russian description.

**Images: take the original, not the thumbnail.** The page links
`/image/cache/catalog/<path>-800x800.png`; dropping `cache/` and the `-800x800`
suffix gives `/image/catalog/<path>.png`, which is the file the shop was given —
716 px to 1500 px, the brand's own packshot, no watermark. The lookup script
already returns the original.

## What zoovet is used for, and where it ranks

**Images** — after the brand's own site (CLAUDE.md rule 7) and **before** a
hafo placeholder (rule 7a). A confirmed zoovet photo is a real photo: it does
not go last in the gallery and it does not put the variant on
`needs-image.csv`. Note the source in the report all the same, because it is a
retailer's copy rather than the brand's own CDN.

Ordering when several sources have the article:

```
brand official site (incl. the country TLDs — reference/brand-sites.md)
  → zoovet.am original (confirmed)
    → hafo.am watermarked placeholder (last in the gallery, needs-image.csv)
```

**Price** — hafo stays primary (`reference/pricing.md`); zoovet is the first
fallback when hafo has no price for the article. The rules, the log file and
the disagreement check are in `reference/pricing.md` ("Second price source").

**Russian text** — the description is a retailer's copy, usually a translation
of the brand's own bullets. Fine as raw material for the `ru` locale, never a
source of specs or attribute values (rule 8: evidence comes from the brand
site).

## Coverage — what it will and will not rescue

zoovet carries food, treats, toys, grooming, litter and pharmacy. It does
**not** carry most Trixie hardware: of the 161 unpriced Trixie rows in
`runs/2026-09-11/no-hafo-price.csv` (mostly leads, harnesses and collars), its
Trixie range of 339 products has no harness at all and no "Berto" litter box.
Expect it to rescue snacks, shampoos, toys and litter, not accessories.

## Brand → slug

`scripts/zoovet-lookup.py --brands` prints the live table. Ours:

| Brand | slug | Brand | slug |
|---|---|---|---|
| Acana | `acana` | Leonardo | `leonardo` |
| Belcando | `belcando` | Monge | `monge` |
| Bewi Cat | `bewi-cat` | Orijen | `orijen` |
| Bewi Dog | `bewi-dog` | Royal Canin | `royal-canin` |
| Brit | `brit` | Schesir | `schesir` |
| Canvit | `canvit` | Simba | `simba` |
| Club 4 Paws | `club4paws` | Stuzzy | `stuzzy` |
| Dogland | `dogland` | Trixie | `trixie` |
| Farmina | `farmina` | Ok-Lock | *not listed* |
| Gemon | `gemon` | | |

Also present and useful for brands we may add: 8in1, Beaphar, Comfy,
Eco-Premium, Flexi, Inspector, Iv San Bernard, Mr.Fresh, Rolf Club.

## House rules

Read-only, like every brand site: no cart, no account, no form (CLAUDE.md rule
11). Pace requests (the lookup script sleeps between pages) and cache brand
lists rather than re-crawling.
