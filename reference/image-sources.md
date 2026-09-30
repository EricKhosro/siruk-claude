# Where a product photo may come from

CLAUDE.md rule 7 in one page: the ladder, what each rung is keyed to, and the
script that reaches it. **A source may only be used when the match is keyed to
the article number or to the EAN that resolves to it** — never to a name — and
the picture is looked at before it is attached. Feature image = a clean shot of
the product alone (rule 7).

| # | Source | Keyed by | Script | Notes |
|---|---|---|---|---|
| 1 | the brand's own site + CDN | file name carries the article | `trixie-image.sh`, `monge-it-page.py`, `neoterica-fetch.py` | the only rung that is automatically finished quality |
| 2 | the brand's country domains | same | `trixie-es.py` (wired into `trixie-image.sh`) | keeps articles the main site dropped |
| 2b | **barcode lookup** (added 2026-09-25) | our EAN, from hafo's confirmed listing | `barcode-lookup.py --code <art>`, then WebSearch `"<ean>"` | run it the moment rungs 1–2 have nothing: it says **what the product is** and **which pages print our EAN** — identity, name, texts and photo leads for every brand. Rules: "Barcode lookup" below |
| 3 | trixie.shop (Trixie's Shopify) | `variant.sku` + Trixie file names | `trixie-shop-index.py` | reaches the group files the CDN probe cannot guess |
| 4 | trixiecz.cz (official CZ distributor) | the page's `Kód` (+ EAN) | `trixiecz-index.py --sweep` | 4,697 articles, incl. discontinued; photos 570–1920 px |
| 5 | tiierisch.de (German shop, Shopify) | `variant.sku` = article, `variant.barcode` = EAN | `tiierisch-index.py` | 5,223 Trixie articles; images are linked to the variant |
| 5b | **4lapy.ru** (Russian chain, added 2026-09-23) | the **barcode printed on each pack-size offer** = the EAN | `4lapy-lookup.py --search … --ean …` | every brand, not just Trixie; per-offer gallery + Russian description / composition / feeding guide |
| 6 | zoovet.am | nothing — confirm by hand | `zoovet-lookup.py` | unwatermarked, but see `reference/zoovet.md` |
| 7 | carrefour-es picture bucket | the EAN, in the url | `ean-image-lookup.py` | `…/catalog/pictures/original/<ean>_1.jpg`, up to 5 files, 1500 px |
| 8 | hornung-baushop.de | the EAN, in the file name | `ean-image-lookup.py` | `napf-nahrungsaufnahme-4047974251416-hornung-baushop.jpg` |
| 9 | a general web / image search | the article or EAN in the file name or page url | `image-search.py`, `web-image-lookup.py` | rule 7d, last resort |
| 9b | **reverse image search on the hafo photo** | hafo is keyed to the article, so its own picture is | Yandex, in the browser | rule 7e — see below |
| 10 | hafo.am | the article in the file name | `enrich-images.py` | **watermarked placeholder**: last in the gallery, and the variant goes on `needs-image.csv` (rule 7a) |

`config.json` → `images.sources` is the machine-readable copy of this list.

## Fallback sites for name, description and photos (user list, 2026-09-23)

For when the brand's official site (and its country domains) has nothing for
the product. Each was checked on 2026-09-23 for access, robots.txt and what
it keys on — that decides what it may be used for:

| Site | Use for | Keyed by | How | Status |
|---|---|---|---|---|
| **4lapy.ru** | photos **and** texts | the manufacturer **barcode on every pack-size offer** — a hit on our EAN is confirmed | `scripts/4lapy-lookup.py` (product sitemap index, ≈39k urls; the site's `/search/` is robots-disallowed and not used) | in the chain, rung 5b |
| **zoovet.am** | photos, texts, a price (rule 2b) | nothing — confirm by hand | `scripts/zoovet-lookup.py` | in the chain already (rung 6, `reference/zoovet.md`) |
| **petshop.ru** | **texts only** (name, description, composition), after confirming identity by hand (brand + line + flavour + pack) | nothing — its `Артикул` is the shop's own number, and no EAN is printed | open the product page **without** its `?oid=` suffix (robots.txt disallows every query URL); reach it from `https://www.petshop.ru/sitemap/products.xml` | text fallback only — never a photo source (rule 7: unkeyed) |
| **petfood.ru** | — | — | its product pages exist only as `…/?oid=<n>` urls and robots.txt disallows `/*?*`; the path without the query 404s | **not usable** as of 2026-09-23 |
| **zoozavr.ru** | — | — | DDoS-Guard answers 418 to every request | **not usable** (a bot wall is not something we work around) |

Texts from these sites are **Russian**. They serve as evidence for attribute
picks, as the source of the `ru` translation, and — translated — as the
English copy only when no English source exists; say which site the copy came
from in the run report. Their prices are RUB retail and are never a sale
price (rule 2).

## Barcode lookup (user rule 2026-09-25)

**Why it exists.** On 2026-09-25, 11 rows hafo had already identified (code,
price and barcode all known) were still not on the site, because the brand's
own site had no page for the pack: discontinued (flexi New Comfort, 8in1 Pro
Digest), renamed (8in1 Excel → Vitality) or a market-specific article
(Beaphar 12625). A plain web search for the barcode named every one of the 6
we tested, through shops that print it. Two rows the 2026-09-23 run had
parked were settled by the barcode alone: DL711836 *is* Dog Fest "Rabbit Ears
with Chicken for Puppies 90 g" (the run had rejected that page as a different
product), and 074322 SexControl is a Neoterica product (Rolf Club's maker).

**When.** For every row with a code, as soon as the brand site and its country
domains (rungs 1–2) have no page for our exact pack — and any time the
identity itself is in doubt (flavour, recipe, size). It does not replace
rungs 3–5b for Trixie photos; it runs alongside them and before anything
unkeyed (zoovet, petshop.ru, name-based web search).

**Steps.**
1. `scripts/barcode-lookup.py --code <art> --name "<row name>"`. The barcode
   counts **only** if hafo confirms the code *and* the barcode belongs to the
   variant whose own sku / article is our code — the script enforces both and
   validates the check digit. It also answers from the EAN caches we already
   have (4lapy.ru, monge.it, hornung/carrefour) and from UPCitemdb / Open Pet
   Food Facts. No barcode → this rung is skipped, never guessed.
2. WebSearch the EAN in quotes: `"4048422108634"`. Read the result titles.
3. **Identity** is confirmed when **two independent pages** that show our
   EAN agree on brand + line + flavour/recipe + pack, and agree with hafo's
   own name for the row. A disagreement (a different flavour, another pack
   size) stops the row — log it, don't pick one.
4. **Content** may then come from a page that **prints our exact EAN** on the
   page itself (title, spec table, url or image file name) — the result
   snippet alone is evidence for identity, never a source to copy from:
   - English name: from an EAN-keyed page in English; else translate an
     EAN-keyed page's title. Our Name rules (`reference/product-rules.md`) still
     apply.
   - Description, composition, feeding guide: from EAN-keyed pages; texts in
     another language are translated, and Russian texts also feed `ru`.
   - Photos: from EAN-keyed pages, looked at before upload ("Keyed is
     necessary, not sufficient" below), unwatermarked, clean packshot first.
     Open Pet Food Facts photos are CC-BY-SA — evidence only.
5. **Only open pages we are allowed to read.** Sites with a bot wall or a
   robots.txt that shuts us out stay closed, even when the search lists them —
   see "Sites already tested and turned down" (rozetka.com.ua is Cloudflare,
   pets24.ee disallows AI crawlers). Their search-result title can still count
   toward identity (step 3).
6. **Log** every row this rung touched in `runs/<date>/barcode-sourced.csv`:
   `Article Code, EAN, Identity pages, Name from, Text from, Images from,
   Notes`. The run report names these rows as "barcode lookup", like any other
   fallback.

**Sources tested 2026-09-25**, on 9 barcodes of stuck rows:

| Source | Result |
|---|---|
| web search for `"<ean>"` | 6 / 6 identified, with shop pages carrying photos and texts |
| UPCitemdb trial API | 1 / 6 (throttles bursts: `TOO_FAST`; 100 lookups a day) |
| Open Pet Food Facts / Open Food Facts / Open Products Facts | 0 / 9 |
| barcodelookup.com | 403 bot wall; its API is a paid subscription — not used |
| listex.info search, barcodes.olegon.ru | no usable direct lookup (404 / redirect) |

## No product ships with an empty gallery (user rule 2026-09-23)

`scripts/create-product.sh` and `scripts/add-variant.sh` both refuse a
payload with no images anywhere on the product unless `ALLOW_NO_IMAGE=1` is
set by hand. If every rung of this ladder genuinely comes up empty, that is
rare enough to stop and ask, not to force through the override by default.

## Media library uploads go in a folder (user rule 2026-09-23)

`scripts/upload-media.sh <file> <directory>` takes the media API's
`directory` field — pass it on every call during an import, don't leave it to
the default. Layout (user, 2026-09-23):

| Folder | What |
|---|---|
| `products/<brand-slug>/<product-type>/` | product images, e.g. `products/trixie/toys` ("Products / Trixie / Toys") |
| `logos/` | brand logos (`create-brand.sh` / `set-brand-logo.sh` default here) |
| `categories/` | category tiles (the square 500–600 px images on category pages) |
| `banners/` | page-top banners only — free-shipping strip, landing-page and blog banners |

Brand slug is the brand's admin slug, product type the attribute family code =
the skill name (`dry-food`, `wet-food`, `treats`, `toys`, `supplements`,
`grooming`, `accessories`, `litter`). `upload-media.sh` refuses anything outside
this layout and creates the folder record first (`scripts/media-folder.py`);
`scripts/organize-media.py` re-files existing media (run 2026-09-23 filed the
whole catalogue). The root keeps only the team's site content (About us icons,
blog tiles, illustrations) and the pre-rebuild photos no live product uses.

## Why the hafo placeholder is attached at all, not dropped

PM decision, 2026-09-11 — reversing a "drop them" instruction given earlier
the same day: the watermarked hafo photo is still attached (last in the
gallery) when nothing else has a picture, because the PM uses it to recognise
the product and replace it by hand. That is what `needs-image.csv` is a
worklist for.

## Trixie numbering, learned the hard way

- **Two GS1 prefixes are in live use.** `4011905…` is the old one and `4047974…`
  the newer; both appear on current articles (3435 → 4011905034355, but 25141 →
  4047974251416), and some lines sit on a third, `4053032…` (CityStyle). Always
  try both computable forms before concluding an article has no barcode.
- **The barcode is not a formula.** 3435 → 4011905**034355** (article padded to
  five) but 2345 → 4011905**234519** (article plus a pack digit). Compute it to
  *search* with; never reject a page whose own `Kód`/`sku` matches the article
  because the EAN came out different — the page's own key wins.
- **Six- and seven-digit codes are article + colour.** `2007`+`20`, `19716`+`01`,
  `20272`+`0`. Colour 20 is *orchidee*, 25 *flieder*, 16 *grafit*, 01 *schwarz*,
  11 *fuchsia*. A sibling colour's photo is **a different product** — it may not
  be attached (2026-09-12: 200721 *violett* was rejected for our 200720
  *orchidee*).
- **A trailing vendor digit exists too**: 29411 → Trixie article 2941, 35031 →
  3503. Never accept a trim automatically; confirm it on a page that prints both.

## Keyed is necessary, not sufficient

2026-09-12, article 041537 (Gran Bontà Bocconi con **Carne** 400 g): a shop page
printed our own barcode 8009470041539 and its title said *carne*, but the photo
on it was the **Manzo** (beef) can. The number got us to the right page; only
looking at the picture caught that the picture was wrong. Every hit is looked at
on a contact sheet (`scripts/contact-sheet.py` + headless Chrome) before it is written.

## Reverse-image search — the strongest of the last resorts

hafo's photo is watermarked but it is a photo *of our article* (hafo is keyed to
the article code). Feeding that image to a reverse-image search therefore finds
the same photograph, unwatermarked, wherever else it is published — and the
identity still traces back to the article, not to a name. This is the user's own
method and it is **rule 7e**.

    https://yandex.com/images/search?rpt=imageview&url=<the hafo image url>

Drive it in the browser (Google Lens answers automation with a CAPTCHA, which we
never solve). Read two blocks:

- **"In other sizes"** — Yandex's own claim that these are the *same* image.
  Careful: it will also fold in a sibling size whose photo looks alike
  (202816's list included wildberries' 202916).
- **"Sites"** — the pages, whose titles often spell out the full spec
  (`Trixie CityStyle / 1971901 XS-S, черный`), and sometimes the file name
  carries our article outright.

Accept only when the candidate is **the same photograph** — put it beside the
hafo original on a contact sheet and look at the pose, lighting and crop.

On 2026-09-12 this closed 7 of the 9 remaining placeholders:

| article | what it found | evidence |
|---|---|---|
| 25180 | `248287_PHO_PRO_CLIP_25180-1.jpg` on chihuahua-shop.com, 2000×1381 | Trixie's own file name |
| 202720 | `PHO_PRO_CLIP_Premium-202720-202920-1` on lapka.rs | Trixie's own file name |
| 1971901 | `citystylecollar1971901_trixie…` on 21vek.by, 1600×838 | article in the file name |
| 19021 | junai.nl, 2000×910 | same photo; Yandex Market names it "Active Comfort белый со стразами XS–S: 20–24 см х 12 мм" |
| 202816 | czv.kz, 500×500 | same photo; page spec is exactly ours |
| 041537 | reginatofratelli.it, `…boccgr400-carne…` | file names line, flavour and pack |
| 041787 | emmezootecnici.com, 1150×1508 | page names line, flavour and pack |

**It also caught a bad hafo photo.** hafo's picture for 041787 (Gran Bontà Chef,
415 g) is the **1230 g** can — the tall one, with the same artwork. The 415 g can
is visibly shorter. When a found image disagrees with the row's pack size, check
what the row says before believing either picture.

Two searches that found nothing are worth recording so nobody repeats them:
**200720** (Premium lead, colour 20 = orchidee) and **041887** (Gran Bontà *le
Delizie dello Chef* Bocconi col Manzo, 1230 g). Both exist only as hafo's
watermarked shot.


## Sites already tested and turned down (2026-09-11)

Twenty-one candidate sites were tested for status codes, bot protection,
robots.txt and a live lookup of one of our own articles. trixie.shop and
trixiecz.cz passed (above). Don't re-test these unless something has changed:

| Site | Verdict |
|---|---|
| `pets24.ee` | **Has** our articles (article number in the page title) and answers 200 — but its robots.txt disallows `ClaudeBot`, `GPTBot`, `CCBot` … and signals `ai-train=no`. Excluded on policy, not on ability. |
| `idealo.de` | Akamai → 403 |
| `rozetka.com.ua`, `masterzoo.ua`, `brekz.nl`, `zoomalia.com` | Cloudflare challenge → 403 |
| `apetete.pl` | 403 |
| `zoozavr.ru` | DDoS-Guard → 418 (re-checked 2026-09-23: unchanged) |
| `petshop.ru` | 200, but robots.txt disallows every query URL (`Disallow: /*?`), which is the whole search. **2026-09-23:** product pages without the `?oid=` load, so it is now a *text-only* fallback (above) |
| `zooplus.de` / `bitiba.de` / `zoohit.cz` | No bot wall, but they expose **no manufacturer article number or EAN**, and they do not stock discontinued lines → fails rule 7 |
| `arcaplanet.it`, `zooplus.it`, `bauzaar.it`, `robinsonpetshop.it` | JS storefronts, no open catalogue API found (VTEX endpoint absent, search paths 404) |
| Amazon, eBay | Bot walls; seller-supplied photos of uncertain provenance |
| Open Pet Food Facts | Free API, no bot wall — but **no record** for our test EAN, and its photos are CC-BY-SA (attribution obligations) |
| `zoowilczek.pl` | Domain is parked/dead |
