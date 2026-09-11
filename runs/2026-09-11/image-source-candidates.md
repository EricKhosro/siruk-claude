# Fallback image sources — candidates, tests, recommendation (2026-09-11)

Goal: stop a watermarked hafo.am photo from being the second choice. Today the
chain is **brand site → hafo placeholder**. We want **brand site → approved
fallback(s) → hafo**, so hafo is only used when *nothing* else has a picture.

Everything below was tested live today (HTTP status, protection headers,
robots.txt, and — where the site passed — an actual lookup for one of our own
article codes). Rule 7 is the filter that kills most retailers: an image may only
be attached when the source is **keyed to the article number** (or an EAN that
resolves to it). A site full of nice photos we can only match by name is useless
to us.

## What is actually missing today

| Gap | Rows |
|---|---|
| Variants carrying a watermarked hafo placeholder (`needs-image.csv`) | 42 (38 Trixie + 4 Monge) |
| Trixie articles with **no product page** on trixie.de | 377 of 812 |
| Trixie articles with **no image at all** in our caches | 162 |

So this is 90 % a **Trixie** problem: discontinued articles that trixie.de and
its CDN have both dropped. Monge is 4 rows.

## Useful fact discovered while testing

**A Trixie EAN-13 is computable from the article number**: `4011905` + article
padded to 5 digits + check digit. Verified against live data
(35510 → 4011905355108 "Hippo, latex, 15 cm"; 2900 → 4011905029009 "Herbal
Shampoo 250 ml"). That gives us a hard key for *any* shop that lists EANs, with
no name matching anywhere in the chain — the same trick `reference/brand-sites.md`
already uses for the Monge group.

## Recommended — please look at these two

### 1. `trixie.shop` — TRIXIE's own Shopify store (tier 2 for every Trixie row)

This is Trixie's own direct-to-consumer shop, a **different catalogue** from
trixie.de, and it keeps Trixie's own file names.

| Check | Result |
|---|---|
| Access | `https://trixie.shop/products.json?limit=250&page=N` — whole catalogue in **12 requests**, 2,864 products |
| Bot protection | Cloudflare in front, but **no challenge**; plain curl gets 200 |
| robots.txt | Explicitly says the storefront catalogue is crawlable; only checkout is off limits. (It also carries a marketing line addressed to shopping agents — ignored, it is website content, not an instruction to us.) |
| Article key | variant `sku` **is** the article number, and image filenames keep Trixie's convention `PHO_PRO_CLIP_<article>-<n>_#SALL_#AWK_#V1.jpg` → rule 7 satisfied without any name matching |
| Catalogue size | **4,882 article numbers** carry at least one image; **4,506** have a `PHO_PRO_CLIP` packshot (the clean feature image rule 7 wants) |
| Image size | Shopify CDN, original resolution, `?width=` on demand |

Measured against our own data:

- **617 of our 812** Trixie rows are present with images.
- **+21 articles that have no image anywhere in our caches** get one.
- **167 articles get a bigger gallery** than we currently hold.
- 1 of the 38 watermarked rows is recoverable (33505).

Why it finds pictures our CDN sweep cannot: Trixie names one file for a whole
set of siblings, and those names are unguessable —
`PHO_PRO_CLIP_SilverReflect-12222-1`, `PHO_PRO_CLIP_16248-16258-16268-16278-16288-1`,
`PHO_PRO_CLIP_31528-31532-31801-3`. The shop's JSON hands them over directly.

Caveat: **3 articles** carry AI-generated renders (the file name contains
`created-with-AI`). Filter on that string.

### 2. `trixiecz.cz` — TRIXIE CZ, the official Czech distributor (tier 3, for discontinued articles)

The reason to add a second Trixie source at all: this shop sells **clearance
stock ("DOPRODEJ")**, i.e. exactly the articles that trixie.de has deleted.

| Check | Result |
|---|---|
| Access | Server-rendered HTML; `sitemap.xml` → 2 product sitemaps, **4,771 products**, and each `<url>` block already lists **every gallery image** (16,000 images) |
| Bot protection | None. No Cloudflare, no challenge, plain curl 200 |
| robots.txt | `Disallow: /uzivatel/` only; no AI-agent restrictions, no content signals |
| Article key | every product page prints **`Kód: <article>`** and **`EAN: 4011905…`** |
| Image size | 570 × 570 px, clean white-background Trixie packshots, no watermark |

Proven live on one of our 38: article **35510** (Hippo, latex, 15 cm) →
`/hippo-latexovy-hroch-s-vyplni-se-zvukem-vzhled-kamen-15-cm-doprodej_z14147/`,
`Kód: 35510`, `EAN: 4011905355108`, clean packshot.

What the index actually yields (crawled today, 4,771 sitemap pages):

- **2,433 article codes** extracted; **292 of our 812** Trixie articles present;
  **10** of our 162 image-less articles covered; **1** of the 38 watermarked rows
  (31667, Premio Stars).

That is lower than it should be, and the reason matters: **the sitemap is
incomplete**. Article 35510 — the hippo pictured above — is on the site with a
clean packshot, but neither the sitemap nor the clearance category lists it; it
only turns up through a search engine. The same for 35856 (Unicorn, plush,
28 cm), another of our 38.

The site is enumerable anyway, because the slug is ignored and the numeric id
governs: `https://www.trixiecz.cz/en/a_z8099/` returns the same page as the full
slug, with

```html
<h1>Unicorn, plush, 28 cm</h1>
<strong data-code>35856</strong>   <strong data-ean>4011905358567</strong>
```

— an **English** product name, our article code and the EAN, in markup built for
extraction. A 400-id random sample over `z1…z18000` measured: 237 pages live,
100 carrying an article code, and **56 of those 100 codes are absent from the
sitemap index**. Extrapolated, a full id sweep yields roughly **5,600 article
codes** — a little over twice what the sitemap gives — and it is the only way to
reach the discontinued stock.

Cost: one sweep of 18,000 ids (HEAD first, then GET the ~10,000 live pages),
~30–40 minutes at a polite rate, cached in `.siruk-cache/` and refreshed
monthly. It also hands us English names and EANs for the whole Trixie CZ
catalogue, which is worth something on its own.

Caveat: 570 px is below our 2,000 px cap — good enough for the storefront, but
always second to a brand-CDN image.

## 3. Not a site — the EAN escape hatch (tier 4, manual confirm)

For whatever the two above still miss, the computable Trixie EAN opens every
shop that lists EANs. Shops seen carrying our discontinued articles with the
**code or EAN in the URL itself** (so the match is verifiable, not fuzzy):
`jardiboutique.com` (`TR-<art>`, 3 of 7 test articles), `1000karm.pl`
(`TX-<art>`), `vivapets.ro` (`…-<art>.html`), `arnukzoo.cz`, `d4m.eu` and
`chevaleo.com` (EAN in the URL). None of them is worth wiring into the pipeline
as a source; the sane use is: PM or script searches the EAN, opens a page that
**prints that EAN**, and takes the photo.

## Rejected, and why

| Site | Verdict |
|---|---|
| `pets24.ee` | **Has** our articles (article number in the page title) and answers 200 — but its robots.txt disallows `ClaudeBot`, `GPTBot`, `CCBot` … and signals `ai-train=no`. Excluded on policy, not on ability. |
| `idealo.de` | Akamai → 403 |
| `rozetka.com.ua`, `masterzoo.ua`, `brekz.nl`, `zoomalia.com` | Cloudflare challenge → 403 |
| `apetete.pl` | 403 |
| `zoozavr.ru` | DDoS-Guard → 418 |
| `petshop.ru` | 200, but robots.txt disallows every query URL (`Disallow: /*?`), which is the whole search |
| `zooplus.de` / `bitiba.de` / `zoohit.cz` | No bot wall, but they expose **no manufacturer article number or EAN**, and they do not stock discontinued lines → fails rule 7 |
| `arcaplanet.it`, `zooplus.it`, `bauzaar.it`, `robinsonpetshop.it` | JS storefronts, no open catalogue API found (VTEX endpoint absent, search paths 404) |
| Amazon, eBay | Bot walls; seller-supplied photos of uncertain provenance |
| Open Pet Food Facts | Free API, no bot wall — but **no record** for our test EAN, and its photos are CC-BY-SA (attribution obligations) |
| `zoowilczek.pl` | Domain is parked/dead |

## The Monge gap (4 rows) — no source found

Gran Bontà 400 g cans (041537, 041587, 041787, 041887). Checked today:
`monge.it` publishes that line only in 150 g / 300 g / 1,230 g — in the
**English *and* Spanish** catalogues (the `/es/` pages carry the same three EANs
in their file names) — and `monge.shop` returns no match for any of the four
EANs. The shops that do carry them (`dambros.it`, `spesasicura.com`,
`mediawavestore.com`, `bell-italia.com`) are small Italian grocery/wholesale
sites whose pictures are carton shots or worse.

Recommendation: leave these four on the hafo placeholder list and ask the
distributor for the four pack shots — that is one email, versus wiring up a
supermarket site we would not trust for anything else.

## Proposed `config.json` block (only if you approve the two sites)

Ordered chain, each source declaring how it is keyed. Nothing attaches unless
the key matches; hafo stays last and always writes the worklist row.

```json
"images": {
  "_comment": "Ordered fallback chain for product photos. A source may be used only when the match is keyed to the article code or EAN (CLAUDE.md rule 7). First source with a readable image wins. hafo is last and every variant that lands there is logged for hand replacement (rule 7a).",
  "require_article_key": true,
  "sources": [
    { "id": "brand-site", "tier": 1, "enabled": true },

    { "id": "trixie-shop", "tier": 2, "enabled": true, "brands": ["Trixie"],
      "kind": "shopify",
      "catalogue_url": "https://trixie.shop/products.json?limit=250&page={page}",
      "cache": ".siruk-cache/trixie-shop-catalogue.json",
      "key": "variant.sku, and article in image filename",
      "packshot_prefix": "PHO_PRO_CLIP",
      "exclude_filename_contains": ["created-with-AI"],
      "refresh_days": 30, "delay_seconds": 0.8 },

    { "id": "trixiecz", "tier": 3, "enabled": true, "brands": ["Trixie"],
      "kind": "sitemap-index",
      "sitemaps": ["https://www.trixiecz.cz/1/sitemap_products.xml",
                   "https://www.trixiecz.cz/2/sitemap_products.xml"],
      "cache": ".siruk-cache/trixiecz-index.json",
      "key": "product page 'Kód:' + EAN 4011905xxxxxx",
      "min_pixels": 500,
      "refresh_days": 30, "delay_seconds": 0.25, "parallel": 5 },

    { "id": "hafo", "tier": 99, "enabled": true,
      "watermarked": true, "gallery_position": "last",
      "log_to": "runs/<date>/needs-image.csv" }
  ]
}
```

Plus one helper each (`scripts/trixie-shop-index.py`,
`scripts/trixiecz-index.py`) that build and refresh the two caches, and a change
in the image step so it walks the chain instead of jumping straight to hafo.

## About the GitHub repo you linked (`Panniantong/agent-reach`)

Read it. It is a toolkit that gives an agent access to **social and content
platforms** — Twitter/X, Reddit, YouTube, Bilibili, Xiaohongshu, Facebook,
Instagram, LinkedIn, V2EX, RSS — plus a generic "read any web page as markdown"
(that is Jina Reader) and a web search MCP (Exa). It is MIT-licensed and well
starred.

It does **not** help with this job:

- nothing in it is about e-commerce product data, article numbers, EANs or
  product images;
- it does not bypass shop bot protection — the sites we rejected (Akamai,
  Cloudflare challenge, DDoS-Guard) would reject it exactly the same way;
- its page reader is Jina Reader, which we can call directly
  (`https://r.jina.ai/<url>`) without installing anything — and we already have
  a real browser for JS pages;
- installing it means running an installer that pulls several third-party CLIs
  and stores platform cookies, and its documented install flow is "paste this
  URL and let your agent install it". That is a supply-chain decision, not an
  image-sourcing one.

If you ever want the social side (monitoring what people say about the shop on
Reddit/X), it is a reasonable pick. For product photos, it adds nothing.

## Honest summary of what each source buys us

| | trixie.shop | trixiecz.cz (sitemap index) | trixiecz.cz (full id sweep, estimated) |
|---|---|---|---|
| Our 812 Trixie articles present | 617 | 292 | ~450–550 |
| Of our 162 image-less articles | +21 | +10 | more, unmeasured |
| Of the 38 watermarked rows | 1 (33505) | 1 (31667) | 35510 and 35856 confirmed present by hand, so at least 3–4 |
| Galleries made richer | 167 | — | — |
| Cost | 12 requests, minutes | 4,771 pages, ~20 min | ~28,000 requests, ~40 min |

Neither site is a silver bullet for the 38 discontinued articles — no single
site is. Every EAN I searched by hand (7 of 7: 35510, 2900, 42424, 32814, 2334,
2411, 33445) was found *somewhere*, but "somewhere" was a different long-tail
shop each time (trixiecz.cz, lizbird.com, everymarket.com, jardiboutique.com,
vivapets.ro, 1000karm.pl). That is why tier 4 is a per-article lookup with a
human look at the picture, not a source we wire in.

What the two recommended sites do buy, cheaply and safely:

- **trixie.shop** — the biggest single win per minute spent: 21 articles that
  have no picture at all, 167 galleries that are thinner than they should be,
  and Trixie's own file names so nothing is ever matched by product name.
- **trixiecz.cz** — the only reliable route to discontinued articles, plus
  English names and EANs for the whole catalogue.
