# Brand → official site, and how to extract from each

Resolve the brand from hafo (`reference/hafo.md`) or from the CSV
`Brand / Vendor` (the part before `/` is the brand; after it is the local
distributor — ignore for sourcing). Sites are **read-only**: never add to cart,
create an account or touch checkout. Ignore every price on a brand site.

Not in the table → web-search `"<brand>" official site`, use the manufacturer
domain (never a retailer/marketplace), and **add the row here**.

**This table grows from every run, not just new brands.** When a brand *is*
already listed but its site has nothing for a given article (discontinued,
dropped from the catalogue, region-locked) and a web search turns up a site
that actually works for it — another country TLD, a distributor, an
EAN-keyed shop — don't just use it for that one row and move on: add it to
that brand's **Notes** column (or a new row) so the next run doesn't repeat
the same search. A finding stays session-only only when it's a one-off,
unkeyed, low-confidence hit that isn't worth trusting again (rule 7d) — log
those in the run report instead, not here.

| Brand | Official site | Notes |
|---|---|---|
| Brit | `https://www.krmivo-brit.cz` | `brit-petfood.com` redirects here (VAFO's shop). Sitemap `…/out/sitemaps/ArticleEntity/cz.xml.gz` → 572 product pages, slugs are English names |
| Royal Canin | `https://www.royalcanin.com` | JS-rendered, 403s to curl — **browser only**. Listing `/uk/cats/products/retail-products?page=N` (15/page), slugs end in the product id |
| Farmina | `https://www.farmina.com` | N&D, Matisse, Ecopet lines |
| Belcando | `https://www.belcando.com` (`.de` redirects) | Bewital; Shopware. Sitemap slugs carry the pack size (`belcando-adult-gf-poultry-12.5-kg`) |
| Leonardo | `https://www.leonardo-catfood.com` | Bewital; same Shopware setup and slug pattern as Belcando |
| Canvit | `https://www.canvit.com` (EN `/en/`) | Supplements; sitemap is a stub — browser |
| Schesir | `https://www.schesir.com` | Agras Delic. **Shopify — JSON API, never scrape pages** (below) |
| Stuzzy | `https://www.stuzzy.it` (EN `/en/`) | Agras Delic (`.com` is not the brand). WordPress, no product post type — products live on category pages (below) |
| Monge, Gemon, Simba, Lechat, Special Dog | `https://www.monge.it` (EN `/en/`) | One site for the whole group (Monge, BWILD, Grill, Fresh, Fruit, Gran Bonta, Monoprotein, VET, GIFT + Gemon/Simba/Lechat/Special Dog). Product pages `/en/product/<slug>/`. **English catalogue is partial** — see image caveat below; **the EAN is in the image filenames** (`…_8009470012345.jpg`) — index every page by EAN (`ean2mit`) and join on hafo `barcodes`; `monge.shop` (PrestaShop) also keys `reference` = EAN |
| Trixie | `https://www.trixie.de` (EN `/en/`), then `https://www.trixie.es` | Fetch `/en/search` **once** and parse it (below). Images by article number via `scripts/trixie-image.sh`, which falls back to the Spanish shop for articles .de has dropped or under-illustrated (country-TLD section below) |
| SMART / OK-LOCK | `https://ok-lock.pet` | Plant-based clumping litter ("SMART litter"). Russian only |
| Club 4 Paws (`4 ԹԱԹ`) | `https://club4paws.com` | Kormotech (Ukraine). Vendor sheets and hafo write it `4 ԹԱԹ` |
| Rolf Club, Inspector, Gelmintal, Insectal, Cliny, Mr. Fresh, SexControl | `https://neoterica.ru` | One Neoterica site (Russian only) for all its lines. Product pages `/products/<slug>`; the **article code is in the image filenames** (`…_077982.jpg`) — key by it, then hand-map the rest from the line's listing page (`/catalog/<line>`) or the site search. Description = the Russian text after the last occurrence of the name, up to "ИМЕЮТСЯ ПРОТИВОПОКАЗАНИЯ" / "Купить у Партнеров". SexControl is its own line on the site but invoiced/hafo-named as Rolf Club |
| Comfy | `https://comfypet.pl` | Aquael's pet-accessory brand. WordPress/WooCommerce; images keyed by article code in the filename. The sitemap carries `%produkty-category%` placeholder URLs — filter them |
| Iv San Bernard | `https://isbusa.com` (US distributor mirror), `https://ivsanbernardcanada.ca` for the logo | `ivsanbernard.it` sits behind a CAPTCHA — not scrapeable. isbusa.com has the lines (Traditional, Protective Shield, Atami) with an English name and description but **only group shots of the sizes** (no single-bottle packshot → `needs-packshot.csv`). The DIY perfume line has no page anywhere reachable |
| Acana, Orijen | `https://emea.acana.com/en/` and `https://emea.orijenpetfoods.com/en/` (the **EMEA** hosts, not `www.acana.com`/`www.orijenpetfoods.com`, which serve the North-American catalogue under different recipe names) | Champion Petfoods; Salesforce Commerce Cloud. Sitemap `…/en/sitemap_0.xml`; product slugs are `eu-aca-<recipe>` / `eu-ori-ns-ori-<recipe>`. The **JSON-LD `Product` block carries `name` and an HTML `description`** — use it, the flattened page text is full of nav noise. Composition sits in `<div id="section2">` under `<h2>Composition</h2>`, analytical constituents under `<h2>Analytical Constituents</h2>`, feeding in `<div id="section3">`. Images are `/dw/image/v2/…master-catalog/…` with **spaces in the filename** (encode before fetching; add `?sw=1200` for full size) — filenames name the recipe, the view (`Front Right` / `Back`) and a pack size. **One packshot per recipe regardless of pack size** — an 11.4 kg bag is shown by the 6 kg photo and no other size renders (404). Two filename traps seen 2026-09-11: the Adult Small Breed front shot is named `…Light & Fit…` (the photo itself is correct — look before dropping it), and the Ranchlands page carries a `…Wild Prairie Features…` graphic that belongs to another recipe (drop it). EU recipe names differ from US ones: Singles are `Yorkshire Pork` / `Grass-fed Lamb` / `Free-Run Duck` here, `Pork & Squash` / `Lamb & Apple` / `Duck & Pear` in the US catalogue |
| Beaphar | `https://www.beaphar.com` (EN `/en-gb/`) | Product pages `/en-gb/product/<slug>`; gallery + description + composition in the HTML |
| 8in1 | `https://www.8in1.eu/en` | Laroy Group's brand. Product pages `/en/products/<slug>`, sizes as `/en/products/dental-bones/L`. **Prints no article number** — the join is hafo (which is keyed to the article) naming the same line, flavour and pack, then the pack photo itself printing the weight. Its own photos are `/fileadmin/_processed_/…csm_TH<nnnnn>_<size>_<hash>.png` (1000 px): `_9649` is the flat front packshot (the feature image), `_9652` a 3/4 pack, `_14255` another angle, and `csm_TR<nnnnn>_9632` the bare treat on white. Everything under `/fileadmin/pictures/8in1_*_Category_*` is a menu banner — drop it. Reader: `scripts/8in1-page.py`. **EAN prefix `4048422…`** |
| Mooor, KorMell, Justin | `https://rupetfood.ru` (producer, АО «Лемниската»); Justin also `https://justin-petfood.ru` | Three brands of one Russian producer — **EAN prefix `4620213…` for all three**, which is what proves they are separate brands and not one brand spelled three ways. Corporate sites only: brand logos yes, **per-article packshots no**, and justin-petfood.ru's "Justin" assets are all packshots rather than a wordmark. Justin's logo is white-on-transparent — keep the alpha (`KEEP_ALPHA=1`), the storefront composites on black. Photos for these articles come from hafo |
| Myau (`Мяу!`) | `https://miau.ua` | Kormotech's Ukrainian economy cat line — **a separate brand from Club 4 Paws** (brand 17), both Kormotech, which hafo confirms by listing `МЯУ` and `Club4Paws` as distinct brand values. The site is a **single-page app**: every path returns the same shell, so there is no per-article page and no packshot to key on. The logo is there though: `/frontAssets/assets/img/logo-red.svg` (render it, don't take the bitmap). **EAN prefix `4820269…`** |
| Versele-Laga (brand 36, 2026-09-17) | `https://www.versele.com/en/vl` | Belgian litter (eXtreme Compact, Senegal, Silica); GS1 `5410340…`, our codes end `V`. Packshots are literally `<EAN>pack.ashx` — EAN-keyed. Rebranded "Versele" in 2025; packs still say Versele-Laga |
| Mnyams / Мнямс (37) | `https://mnyams.ru` | Russian cat treats; GS1 `4610011…` (older articles) / `4620202…` (current). Our `5488xx` codes are the current articles while hafo carries the older EANs — two pillow flavours changed between generations, check the pack |
| Derevenskie Lakomstva / Деревенские лакомства (38) | `https://derlak.ru` | dog jerky made in China for ООО ТК Адресник, GS1 `6921959…` / `6921499…`; pages print the article |
| flexi (39) | `https://flexi.de/en/` | retractable leads, GS1 `4000498…`; flexi-world.com is now parked. Pages print no article — identity rests on hafo naming line + size + colour |
| Eco-Premium / ЭКО-Премиум (40) | `https://xn----jtbjfmbjjj7a9g.xn--p1ai/` | Russian clumping wood litter, GS1 `4631155…`, codes end `E`; one generic page, photos show only the Green bag |
| Kaskad / Каскад (41) | `https://www.kaskad-pet.ru` | Russian leather collars, GS1 `4605350…`, codes end `K`; pages print the article |
| Pchelodar / Пчелодар = АО «Агробиопром» (42) | `https://agrobioprom.ru` | veterinary drops (Дезацид форте, Отидез форте), codes end `PCHL`; only the corporate logo exists, so the brand carries no image |
| Beaphar — codes | `https://www.beaphar.cz` | **our Beaphar article numbers are the Czech-market SKUs**: beaphar.cz prints the SKU in the spec table and names the gallery file after it; the UK/NL sites sell the same lines under other articles/EANs (usable as English text only). beaphar.ru (importer) prints `Артикул` too |

## A brand has more than one site — check the country TLDs

A manufacturer's national shops are the **same official source** under another
domain, and they are not copies: each keeps its own product records and its own
picture files, so a country site routinely holds an article the main site has
dropped. Before falling back to a distributor photo, try them. For Trixie the
table is below; for any other brand, `<brand>.<cc>` is worth one HEAD request
before you give up on an article, and a live one gets a row in the table above.

## Finding a photo by EAN when every brand site fails (2026-09-11)

For ~60 articles neither trixie.de, its CDN, trixie.shop, trixie.es nor
trixiecz.cz has a picture. The EAN of **our own hafo row** unlocks most of them,
because some catalogues name the image file after the EAN — so the hit is keyed
to the article, not to a name (fallback level 2; flag the row):

- `scripts/ean-image-lookup.py` — searches **hornung-baushop.de** by EAN and
  keeps files whose name carries it (`napf-nahrungsaufnahme-4047974251416-…jpg`).
  The product slug comes back too, so the identification can be read in words.
  **Take a file that names one EAN, ours.** A multi-EAN file
  (`buerste-pflegen-4011905023540-4011905023564-4011905023533-…`) is a set photo
  and may show a sibling.
- **Carrefour ES** serves `…/catalog-pictures-carrefour-es/catalog/pictures/
  hd_510x_/<EAN>_<n>.jpg`. Probe `_1.._3` — a 404 means it is not carried, so the
  URL itself is the check.
- **lumenet.hu is a trap**: `img/555/<EAN>/<EAN>.webp` returns 200 for *any*
  EAN, including invented ones. Never use it.

Two identity facts learned here:

- **Our vendor code is often Trixie's article plus a trailing digit** — 35031 is
  article 3503, 35061 is 3506, 35821 is 3582 — and the EAN proves it, since its
  item field carries our five digits (`4011905 35031 8`). hafo's row barcode is
  the safest form; where hafo has none, compute the check digit over each Trixie
  prefix (4011905, 4047974, 4053032) and let a 200 confirm the guess.
- **A family page names the whole set in one file**:
  `PHO_PRO_CLIP_25241-25242-25243-25244-25245-1`, and the line name can come
  first: `PHO_PRO_CLIP_SilverReflect-12214-12215-12216-1`. Match the article as a
  `-`/`_` delimited token, not as a substring.

Every recovered URL is kept in `reference/recovered-images.json`, which
`scripts/enrich-images.py` merges into its plan so a rebuild never drops them.

## hafo.am images are watermarked placeholders (PM decision, 2026-09-11)

Every photo hafo serves — `image_main_url`, the listing page, all of them — is
stamped with a repeating "Hafo" watermark across the whole frame. It cannot ship
to production, but it **is** attached when the brand site has no picture,
because the PM uses it to recognise the product and swap in a real photo by
hand. So:

- a hafo picture goes **last** in the gallery; a brand shot always leads;
- take only a file whose name carries **our** article (a listing spans sizes —
  40181's page also shows 40182), or the listing's own photo when the listing
  holds a single row and so can only depict our article;
- every variant carrying one goes into `runs/<date>/needs-image.csv`, which is
  the replacement worklist, and the report says these galleries are placeholders.

Texts when the brand site has none: 4lapy.ru (EAN-keyed), zoovet.am and
petshop.ru (both confirmed by hand; petshop.ru is text-only) — the full
fallback table with what each may be used for is in
`reference/image-sources.md` → "Fallback sites". petfood.ru and zoozavr.ru
were on the same list but cannot be used (robots.txt / bot wall).

A hafo photo is now the **third** choice, not the second: try the brand's
country TLDs (below) and then a confirmed zoovet.am original
(`reference/zoovet.md`) first — both are unwatermarked, so a variant sourced
from either is finished and does **not** go on `needs-image.csv`.

Discontinued Trixie articles are the usual case: gone from trixie.de and from
its CDN, and no sibling page carries them. Checked 2026-09-11 against
trixie.es: of the 38 Trixie variants then on the needs-image list, 16
have a page there with the article confirmed and 13 of those have article-keyed
photos — so that worklist should be re-run before anyone photographs anything.

## Image sourcing — the rule

Attach an image **only** when the source is keyed to the article number
(Trixie CDN, Schesir article code in the filename, an EAN join) or the filename
itself names the same line, flavour and pack. Never from a fuzzy name/slug
match: on monge.it that produced confident wrong answers (a Fruit dog pouch →
a GIFT treat bar, Gemon wet pouch → Gemon kibble, wet pouches → dry-food
pages). No image is better than a wrong one; list the gap for follow-up
(`.siruk-cache/needs-official-image.csv`).

Product images must be **opaque** — `scripts/upload-media.sh` flattens
transparent PNGs onto white (the storefront composites alpha onto black).
`KEEP_ALPHA=1` only for brand logos.

**Feature image = clean product shot.** `variant.images[0]` is the storefront
thumbnail and the big picture on the product page. It must show the product
alone (or in its own pack) on a plain background — no animal, no hand, no
scene, no group of siblings. The brand page's gallery order is not a
guarantee: Trixie pages often list `PHO_PRO_CAT/DOG` (animal playing with the
toy) first and sometimes omit the `PHO_PRO_CLIP` packshot that the CDN does
have (article 45558, 2026-09-10) — `scripts/trixie-image.sh` now probes the
CDN for the packshot whenever the page has none. For brands without a filename
convention, download the candidate and look at it. A lifestyle/group shot may
lead only when nothing clean exists; log those in
`runs/<date>/needs-packshot.csv`. `scripts/feature-image.py` audits and
reorders the whole catalogue and renders a contact sheet (`--sheet`) so every
feature image can be checked by eye in a few screenshots.

## Trixie

### The country TLDs (2026-09-11) — trixie.es has what trixie.de dropped

| Domain | What it is | Use it for |
|---|---|---|
| `trixie.de` | the head office site + `cdn.trixie.de`. `/en/`, `/de/`, `/fr` are languages of the same catalogue; `trixie.fr`, `trixie.at`, `trixie.ch` redirect here | primary: catalogue, product pages, CDN gallery |
| **`trixie.es`** | Grupo Trixder, Trixie's Spanish company. Its own ePages shop with its own copies of the official photos at **1500×1500** and an English locale | **the fallback** — it has a search by article and prints the article on the page |
| **`trixie.shop`** | Trixie's own Shopify store — a *different* catalogue from .de, 2,864 products / 5,285 article numbers, keeps Trixie's own file names | **approved fallback** (2026-09-11): whole catalogue in 12 requests, article = variant `sku` |
| **`trixiecz.cz`** | TRIXIE CZ, the official Czech distributor. Sells clearance ("DOPRODEJ") stock, so it still lists articles Trixie deleted | **approved fallback** (2026-09-11): `Kód` + EAN on every page, English locale, 570×570 photos |
| `trixie.it` | Italian site on the same CMS as .de (uses `cdn.trixie.de`, `?itemNo=`) | a regional catalogue if .es misses; not wired up |
| `trixiepet.com` | the US company, same CMS/CDN, US assortment | last resort; names are US-English |
| `trixie.se` | a Swedish wholesaler, different system, no Trixie CDN | not a source |
| `trixie.com` | **not Trixie** — an unrelated personal blog | never |

Why it matters: trixie.de drops a discontinued article from both the catalogue
and the CDN (149 of our articles have no page there), and even a live page
often keeps a single photo.

```
article 3503  Longies 18 cm   .de CDN 1 image (449×1200)   .es 3 images (1500²)
article 31501 Chew Bites 150g .de gone entirely            .es 4 images + EN name
```

Two article-keyed facts on a `.es` page, which is what makes it usable under
rule 7:

- the variations table — `<td data-title="ref">31501</td>`, printed as
  `Ref.31501` in search results. This is Trixie's own article → product
  mapping;
- the file names — `PHO_PRO_CLIP_<article>-<n>.jpg`, the same convention as the
  CDN, so a file is self-verifying (the article is printed on the pack).

```bash
scripts/trixie-es.py --images 31501     # URLs, packshot first
scripts/trixie-es.py --article 31501    # JSON: name, ref, spec, images
```

`scripts/trixie-image.sh` calls it automatically when .de yields no packshot or
fewer than three pictures, and merges the results behind the .de ones (same
file → the .de copy wins). `TRIXIE_ES=0` skips it, `TRIXIE_ES=always` asks for
every article; answers are cached in `.siruk-cache/trixie-es.json`.

Three traps, all seen on 2026-09-11:

- **a page can show a sibling's photo only** — article 24183's page carries
  `PHO_PRO_CLIP_24181-1.jpg` and nothing of ours. The scripts take only files
  whose name carries our article; don't take the rest by hand either.
- **the bullet text can be stale** — 31501's bullets read "with lamb" while the
  pack in its own photo reads "with parsley & peppermint". Take the images, the
  `ref` and the name; treat the bullets as unverified.
- **the page title is the family's, the `ref` row is ours** — the Chew Bites
  page is titled "150 g" but covers two flavours, and the Ring page is titled
  "ø 17 cm" while its `ref 33445` row says `medidas: ø 11 cm`, which is what our
  invoice says. Read the spec cells of **our** ref row (`data-title="medidas"`,
  `contenido_peso`, `capacidad`…) — `scripts/trixie-es.py` returns them as
  `spec` — and treat the title as a hint. If the ref row itself contradicts the
  invoice, the identity is not settled: flag the row, do not attach the photo.
- **a file named for our article can still show a sibling's pack** — on the
  31501 page `PHO_PRO_CLIP_31501-1` is the blue lamb pack while `PHO_PAC_CLIP`
  is the green parsley & peppermint one that our row is. The file name gets you
  to the right family, your eyes decide the flavour (rule 7's "look at it").

**Our sheets sometimes carry a vendor form of the article.** `35031` is Trixie
article `3503` with a trailing 1 — the same +1 hafo writes as `TX 040201` for
`4020`. `trixie-es.py` reports such a trim on stderr as a *candidate* ("trim
3503 is '4 Longies, latex, 18 cm'"); confirm it against the row's name and pack
size, then re-run with the real article. Never let an unconfirmed trim become
an image. (`00265Tx` → article `31501` shows the other case: a vendor code with
no arithmetic relation to the article at all — only the invoice text carried it.)

### The two approved fallbacks (PM, 2026-09-11)

Twenty-one candidate sites were tested — status codes, protection headers,
robots.txt and a live lookup of one of our own articles. Two passed and are now
in the chain (`config.json` → `images.sources`, CLAUDE.md rule 7c); the full
evaluation, including why zooplus, idealo, rozetka, pets24.ee and the rest were
turned down, is in `reference/image-sources.md` → "Sites already tested and turned down".

**`trixie.shop`** — Trixie's own Shopify storefront.

```bash
scripts/trixie-shop-index.py            # refresh (12 requests, ~1 min)
scripts/trixie-shop-index.py --lookup 12222
```

Cloudflare sits in front but never challenges, and robots.txt says the
storefront catalogue is crawlable. Variant `sku` **is** the article, and the
images keep Trixie's names, so they are self-verifying like the CDN's. It is
worth having because Trixie names one file for a whole family and those names
cannot be guessed by the CDN probe:
`PHO_PRO_CLIP_SilverReflect-12222-1`,
`PHO_PRO_CLIP_16248-16258-16268-16278-16288-1`,
`PHO_PRO_CLIP_31528-31532-31801-3`. Drop any file whose name contains
`created-with-AI` (Trixie has a few AI renders in the shop).
Index: `.siruk-cache/trixie-shop-art-images.json`.

**`trixiecz.cz`** — TRIXIE CZ, the official Czech distributor, and the only
reliable route to discontinued articles.

```bash
scripts/trixiecz-index.py --sitemap     # 4,771 products, images inside the XML
scripts/trixiecz-index.py --sweep       # ids z1…z18000 — the real index
scripts/trixiecz-index.py --lookup 35510
```

Every product page prints the key in extractable markup —
`<strong data-code>35856</strong>`, `<strong data-ean>4011905358567</strong>` —
next to an English `<h1>`, so identity never rests on a name.

Two facts the sweep taught us:

- **the sitemap is incomplete.** It omits most of the clearance stock: article
  35510 (Hippo, latex, 15 cm) is on the site with a clean packshot and in no
  sitemap. The clearance category (`/akce_k2057/akcni-zbozi-doprodej_k2399/`,
  341 products) does not list it either;
- **the slug is ignored, the id governs.** `/en/a_z8099/` serves the same page
  as the full slug — a live id answers `301` to its canonical URL, a dead one
  `404` — so the ids enumerate the whole shop. That is what `--sweep` walks.

Images are `/data/tmp/<size>/<last digit of id>/<id>_<size>.jpg`, the same photo
at several sizes: **`_0` is the original** the lightbox links to (1000–1920 px),
`_3` a 570×570 square, `_2` 250 px, `_1` a 50 px thumb, `_108` a 1200×630 social
crop. Two traps, both hit on 2026-09-11:

- the gallery URLs on the page are **relative**, and the only absolute one is the
  social crop — scraping absolute URLs gets you one padded square and nothing
  else;
- the page also carries cross-sell thumbnails, so the scrape has to be scoped to
  `<div class="product-gallery">` and take the `data-rel="gallery"` hrefs.

`trixiecz-index.py` does both and normalises to `_0`; `--reparse` re-reads the
pages already indexed after a change like this. The file names carry no article,
so the page's `Kód` is the key and the pictures rank 4 — under every brand shot,
over nothing but the hafo placeholder.

**When both miss**, a Trixie EAN is computable — `4011905` + article padded to 5
+ check digit (35510 → 4011905355108, verified) — so the article can be searched
for on the open web; accept a page only if it prints that EAN or that article
back. Expect a different long-tail shop each time (trixiecz.cz, lizbird.com,
everymarket.com, jardiboutique.com, vivapets.ro, 1000karm.pl), which is why this
last step is a hand lookup and not a wired-in source.

### The CDN holds more than the page shows (2026-09-11)

A product page is written for a whole family, so a single-article variant often
keeps one picture — and 149 of our articles have no page at all. Every file is
named `<PREFIX>_<article>-<n>_%23SALL_%23AWK_%23V1.jpg` under
`https://cdn.trixie.de/assets/img/1600mx1200m/`, so the gallery can be probed
directly: `scripts/trixie-cdn-sweep.py --plan <plan>` HEADs all prefixes
(`PHO_PRO_CLIP` packshot, `PHO_PAC_CLIP` pack, `PHO_PRO_DET_CLIP`,
`PHO_PRO_SET_CLIP`, `PHO_PRO_USE(_CLIP)`, `PHO_PRO_DOG/CAT(_CLIP)`, `PHO_PRO`,
`GRA_PRO`) × n = 1..26 with one parallel curl (~450 req/s) and caches the hits in
`.siruk-cache/trixie-cdn-gallery.json`. Two facts the probe taught us:

- **n does not start at 1 and is not contiguous** — article 3271 has only `-6`,
  22846 has `-17, -18, -19, -21, -23`.
- **One file can serve a whole set of siblings**: `PHO_PRO_CLIP_25026-25027-25028-1`.
  Those names cannot be guessed, so they still come from the product page; when
  an article has neither a page nor a single-article file (38 of ours), the
  sibling's page does **not** carry it either — checked for five, zero hits.


- `https://www.trixie.de/en/search` (~17 MB) embeds the **whole catalogue**:
  3,259 `href="/en/productworld/…?itemNo=<article>"` links whose slug is the
  English name. `?q=` does nothing (form fields have no `name`; filtering is
  client-side). Parse once into `article → {url, name}`
  (`scripts/trixie-catalogue.py`), then curl each product page (~100 KB,
  server-rendered) for description, variants and "Contents"
  (`scripts/trixie-product.py`). Sitemaps: `https://cms.trixie.de/en/sitemap.xml`.
- **Images are exact and there are several per article**:
  `scripts/trixie-image.sh <art no>` (our code minus `Tx`) reads the product
  page's gallery (found via the cached catalogue) and prints **every**
  1600mx1200m image whose file name carries the article — `PHO_PRO_CLIP`
  packshot first, then `PHO_PAC_CLIP`, lifestyle (`PHO_PRO_DOG/CAT`), group
  shots (`PHO_PRO_GROUP_CLIP_<a>-<b>…`) and `GRA_PRO` drawings — one URL per
  line; `--first` gives only the thumbnail. Articles without a catalogue page
  (litter 4020) fall back to a CDN probe that keeps every hit. Upload all of
  them (`scripts/add-all-images.py` backfills). The article number is printed
  on the pack in the photo, so a hit is self-verifying. trixie.de throttles
  bursts — cache results (`.siruk-cache/trixie-gallery-urls.json`).
- Litter is specced by volume ("Contents: 5 l / 8 l"), no kg. See the volume
  note in `reference/admin-api.md`.

## Schesir (Shopify)

```
curl -s -A "<browser UA>" "https://www.schesir.com/en/products.json?limit=250&page=N"
```

~6 requests → 302 products with `title`, `handle`, `body_html` (one-line
teaser only; bullets, composition and feeding guide are on the rendered page),
`images[]`, `variants[]`, `product_type`, `tags[]`. **`tags` carry the line**
(After Dark, Baby, Silver, Classic, Bio, Stix, Soup, Broth, Taste the World,
Born Carnivore, Monoprotein, Petit Cuisine, Snack…) plus species
(`Gatto`/`Cane`) and `Umido`/`Secco`. Single lookup:
`https://www.schesir.com/en/search/suggest.json?q=<text>&resources[type]=product`.

**Match by article code, not name**: image filenames embed it
(`…/ITA_21142001_MAIN_….jpg`) and the vendor `Կոդ` matches on the **first 7
digits** (sheet `21142003` → image `ITA_21142001`). That resolved 100 of 129
priced rows deterministically; the ~29 misses are ranges no longer on the site.

## Stuzzy (WordPress, no API)

Category pages map 1:1 onto the Italian line names in vendor sheets:
`/{cane,gatto}/umido/{bocconcini,sfilaccetti,pate,monoprotein}/` and
`/cane/secco/crocchette/`. Extract with `evaluate_script`.

## Monge group

`monge.it/en/` covers ~756 of the group's ~2,079 sitemap URLs; wet pouches are
largely missing. Match only where the filename names the same line, flavour and
pack (`Extra-Small-Puppy-and-Junior-Rich-in-Chicken_800g_…`). Otherwise leave
the image empty. `scripts/monge-match.py`, `scripts/monge-shop-lookup.py`
(monge.shop PrestaShop, joins on EAN from hafo) are the tools.
`scripts/monge-it-crawl.py` walks all three product sitemaps (~2,080 pages) and
indexes them by the EAN in the image file name → `.siruk-cache/ean2mit.json`.

**Join on the EAN of OUR hafo row, never on `barcodes`.** `barcodes` lists every
size in the listing, and a monge.it page shows every size of the family plus
site banners (ECVIM, Quality Award, UE). Taking any of them attached the 3 kg
bag to article 004097, which is the 800 g pack (found and fixed 2026-09-11;
`.siruk-cache/hafo-variant-barcode.json` holds the per-row barcode). A monge.it
file whose name carries no EAN names only the line and flavour — the bag artwork
is shared across sizes, so it is safe; one that carries a different EAN is not.

### Simba (verified 2026-09-10, 15 rows)

- **monge.it has Simba only in the Spanish catalogue** (`/es/producto/simba-…/`,
  41 URLs in `product-sitemap*.xml`; `/en/` has 3). The `/en/simba/` brand
  page 301s to a blog post. Page text is Spanish and the composition /
  feeding tabs are empty in the HTML — but every page links an **official
  English spec sheet PDF** (`Simba-dog-chunks-with-beef-ENG.pdf`,
  `Simba-cat-chunkies-with-…-EN.pdf`) with the English name, description,
  composition, analytical constituents, additives, instructions and the
  feeding table. Read the PDF (Read tool renders it), not the page.
- **One packshot per flavour** (`og:image`,
  `simba_cane_umido_bocconi_con_<flavour>.jpg` / `simba_gatto_umido_bocconcini_con_…`,
  427×625): the same can artwork serves 415 g and 1230 g, so both sizes share
  it. Clean packshots (the animal is printed on the label).
- **monge.shop has no Simba** — the EAN join returns nothing. Identity for
  flavours hafo names ambiguously came from a web search of the hafo EAN
  (`"8009470009157" Simba` → retailer listings naming the product); three
  rows were resolved that way (2026-09-10).
- Line names on the sheets: dog "Chunks with …" (pack "Bocconi Adult"), cat
  "Chunkies with …" ("Bocconcini Adult"), dog "Paté with …" ("Paté Adult",
  alutray 150 g / 300 g). Products 324 / 325 / 326.

## Brand logos

Every brand has its own verified official logo (media ids: Acana 1501,
Belcando 1504, Brit 1507, Canvit 1510, Monge 1513, Orijen 1516, Royal Canin
1519, Trixie 1522, Farmina 1525, Schesir 1528, Leonardo 1531, Stuzzy 1534;
16–19 added 2026-09-09). Brit / Canvit / Monge / Farmina / Gemon / Simba are
low-res because that is all the sites publish. Check with
`scripts/verify-media.sh --brands`; change with `scripts/set-brand-logo.sh`.
Bewital and Agras publish SVG only → `scripts/rasterize-svg.sh`. A logo URL
must be **looked at** before upload (`scripts/fetch-logo.sh`) — logo paths
routinely serve packshots, a sibling brand's mark (Schesir↔Stuzzy,
Belcando↔Leonardo) or placeholders.

## Fallback

If the official site lacks the product, has no search, or blocks automation, in
this order:

1. **the brand's other country sites** — same official source, different
   domain (Trixie: `trixie.es`, see above);
2. **zoovet.am** (`reference/zoovet.md`) — an Armenian shop whose photos are
   the brands' own, unwatermarked. Its identity has to be confirmed by hand
   (it has no article code), but a confirmed photo is a finished photo, not a
   placeholder;
3. **the EAN-keyed shops** — **`4lapy.ru`** for any brand (every pack-size
   offer prints the manufacturer barcode; photos + Russian description,
   composition, feeding — `scripts/4lapy-lookup.py`, added 2026-09-23),
   `tiierisch.de` (Shopify: `sku` = the article,
   `barcode` = the EAN, images tied to the right variant —
   `scripts/tiierisch-index.py`, 5,223 Trixie articles), the **carrefour-es**
   picture bucket and `hornung-baushop.de` (both `scripts/ean-image-lookup.py`);
4. **hafo.am** — text and identity freely, images only as the watermarked
   placeholder described above (`needs-image.csv`);
5. **a general web/image search** (CLAUDE.md rule 7d, user rule 2026-09-12) —
   `scripts/image-search.py` finds them, `scripts/web-image-lookup.py` checks a
   page you found by hand. A hit counts only when the **file name or the page
   url carries our article or EAN**; a name match is refused. Then look at the
   picture anyway: a page printing our own barcode has been seen carrying the
   wrong flavour's can.

The whole ladder, with what each rung is keyed to and the Trixie numbering traps
(two GS1 prefixes, the colour suffix, the trailing vendor digit), is in
`reference/image-sources.md`.

Flag the row "sourced from fallback" and name which one. Never fabricate specs.

## Chewy (dropped)

Chewy is behind Kasada anti-bot (HTTP 429 to automation-flagged Chrome) and has
no public API; it is also a poor match for this European catalogue. Details in
`INVESTIGATION.md`.
