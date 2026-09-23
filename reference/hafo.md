# hafo.am — identity and price lookup

hafo.am is the Armenian distributor behind most of our invoices. Its catalogue
is keyed by **the same article codes our supplier sheets use**, so a code
lookup turns a bare code into a brand, a real product identity and a retail
price. Use it **first**, before any brand site. Use it for **identity and price
only** — never for images, names or descriptions (it has no English; its ENG
switch is a Google Translate widget, and `meta_keywords` is the most English it
offers).

Its images are watermarked placeholders (CLAUDE.md rule 7a). The second
Armenian shop, **zoovet.am**, is not: `reference/zoovet.md` covers it — clean
photos and a fallback price, at the cost of having no article code, so every
hit there has to be confirmed by hand.

## The API (found 2026-09-09)

```
GET https://hafo.am/products/filter?search=<q>&page=1&order_by=order-desc
    &min_price=0&max_price=200000&animal=&brand=&weight=&age=&type=&is_new=false
```

Laravel paginator (`{current_page,data[],total,last_page,…}`, 40/page). Items
carry `title`, `content` (HTML), `image_main_url`, `price`, `wholesale_price`,
`slug`, `meta_*`, `product_maker` and `product_additional_information[]`.

**`search` matches the SKU**, so an article-code lookup is exact and
language-independent. It also matches the Armenian `title` and the per-row
`name`, which is how a **codeless** register row is identified (CLAUDE.md
rule 6, 2026-09-17): `scripts/identify-by-name.py` searches the register
name, lists every `product_additional_information[]` row of every hit with
its `sku`, `name`, `price` and `wholesale_price`, and the row is taken only
when brand + line + flavour + pack all match (cost equality is confirming
evidence, not a requirement — the PM's cost can lag hafo's).

## `product_additional_information[]` is the real record

One hafo listing covers every size/flavour of a product. Each is a row in this
array with its own `sku`, `name` (size in it), `price`, `wholesale_price`,
`qty_in_stock`, `kg_price` and `barcode` (EAN-13). The top-level `price` is
just the cheapest row. Everything we price comes from **our** row.
`barcode` is the join key to brand shops that expose EANs (monge.shop's
PrestaShop `reference`), which gives an official image with no name matching.

## How the storefront itself prices a variant (seen in the browser, 2026-09-10)

Product pages are `https://hafo.am/products/<slug>` (`/product/<slug>` 404s).
The page renders `<select name="product_data_id">` whose **option values are
the `product_additional_information[].id` row ids** and whose text is the
article SKU; the price line `<span class="real-price">` shows the selected
row. Picking another option fires

```
POST https://hafo.am/product/change
color-id=<row id>&image-color=<row.image_color_name>&product_id=<listing id>
headers: x-csrf-token: <urldecoded XSRF-TOKEN cookie>, x-requested-with: XMLHttpRequest
→ [{"sku","price","wholesale_price","kg_price","unique_price","in_stock","image"}]
```

Without the CSRF header it 302s; any GET of hafo.am sets the cookie. The
returned `price` is **the same number as the row's `price` in the listing
API** — so `/products/filter` rows are the storefront price, no page scraping
needed. The description text often carries a hand-typed price table that is
**stale** (3275Tx: table 3100, page and API 2750) — never read prices from it.
Discount markers exist (`listing.discount`, `max_discount`, row
`discount_price`, `unique_price`); none was set on our products, so the
formula is unknown — `scripts/check-hafo-prices.py` flags them instead of
guessing.

**`search` is a substring match on the SKU**, so search with the bare number
(`4020` finds `TX 040201`; `4020Tx` finds nothing) and match the row with the
`Tx` form (the zero-pad tolerance in `sku_matches` needs it). Match on the
row's `sku`/`article` only — hafo's internal `code` ("02812") collides with
unrelated products. Listings whose `product_maker` is empty slip past a brand
filter; the reliable tie-break is **row `wholesale_price` == our invoice
cost**.

## Use the script, not curl

```bash
scripts/hafo-lookup.py --code 41116Tx --name "<armenian name>"        # one row, JSON
scripts/hafo-lookup.py --csv csv/products.csv --limit 10 --out .siruk-cache/hafo.json
```

Result fields that matter: `confirmed` (true only on an article-code match),
`brand`, `title`, `variant` (our row), `price`, `wholesale_price`,
`price_source` (`"variant"` | `"UNRESOLVED"`), `candidates` (name-search hits,
never trusted).

## SKU formats per brand (all normalised by the script)

- **Trixie**: `41116Tx` (our exact format) *and* `TX 040201` — a `TX ` prefix,
  a zero pad and a trailing variant digit around the article number. Our
  `4020Tx` is hafo's `TX 040201`; `40261Tx` is `TX 040261`. This tolerance is
  applied only to codes that carry the `Tx` suffix — on a bare numeric code it
  produced a false positive (`15266` chicken treat vs `TX 152661` leash).
- **Monge**: `MG 013147` with a **non-breaking space** (`\xa0`). Raw string
  comparison silently fails and the fallback name search then returns a
  different flavour of the same line.
- **Others** (SMART, Eco-Premium, Gemon…): the bare code, `1101213`, `48905E`.

## What a hit means

- Article-code match → `confirmed: true`. Trustworthy identity; price from the
  matched row.
- Name-search hit → `confirmed: false` + `candidates`. Searching `4 ԹԱԹ` for a
  jelly pouch returns the brand's dry dog food. Needs a human; the row goes to
  `not-found.csv` unless the user resolves it.
- Nothing → `not-found.csv`.

## The CSV `Brand` column is derived — don't trust it blindly

`csv/products.csv` carries `Brand Source`. `article-code suffix 'Tx'` is
reliable; `description` is not. Of 812 Trixie-labelled rows, the 12 without a
`Tx`/`TXN` suffix were 11 other brands (7 confirmed 8in1 — `TASTIES`,
`PRO DENTAL`) and one real Trixie row. The authoritative test is membership in
the brand's own catalogue (`scripts/trixie-catalogue.py --lookup <code>`).
Excluded rows go to `not-found.csv` for re-resolution.

## hafo's Armenian flavour word can be wrong — verify identity by EAN

Seen 2026-09-10 on Simba: hafo titles 009157/009177 "թռչնամսով" (poultry) —
the EAN (`barcodes[]`, 8009470009157) is Simba *Chunks with Wild Game*
(`selvaggina`); 009097 "ձկան" (fish) is *Chunkies with Tuna*. The article
code and EAN are reliable, the title's flavour is a translation. When the
brand site has no EAN join, a web search for the bare EAN plus the brand
returns retailer listings that name the flavour; the brand's own spec sheet
then confirms it.

## Identifying a row with no article code at all (rule 6, 2026-09-17)

**With a code, the code is the identity** — a name hit can never override it:
a hafo name-search hit is a candidate (`confirmed: false`), never a match, and
a code that resolves to a different product than the name says is a
stop-and-check, not a coin toss. (This reverses the earlier "identity only
from the code" rule — a codeless row still needs identifying, below.)

**Without a code** (the PM's register, `csv/Product.numbers`, prints none —
140 rows had no recoverable code on 2026-09-16) identify the row by name, in
this order, stopping at the first source that confirms it:

1. **hafo** — search the Armenian name; a hit whose
   `product_additional_information[]` row has our exact brand + line + flavour
   + pack — and, when it lists one, a `wholesale_price` matching our cost as a
   tie-break among candidates — is the article, and its `sku` becomes the
   row's code.
2. **zoovet.am or nemo.am** — Russian/Armenian name search, either order;
   neither carries a manufacturer article code, so a hit is a candidate until
   confirmed the same way: brand + line + flavour + pack all matching, or the
   article read off the pack in a full-size photo where one is printed.
   `reference/zoovet.md` has zoovet's specific confirmation tests (including
   its `ME-…` code-collision trap); nemo.am has no documented quirks yet —
   confirm it on the same brand/line/flavour/pack basis until one turns up.
3. **web search** — Google/Bing; the brand's own page or an EAN-keyed shop for
   the same brand + line + flavour + pack.

**"Same product" means every axis matches** — brand, line, lifestage/function,
flavour, pack size, and for accessories size and colour. A hit that matches
only the line, or only the pack, or a same-cost flavour sibling, is refused
and the row goes to `runs/<date>/not-found.csv` with the nearest candidate
named.

Every name-identified row is logged in `state/register/identified-by-name.csv`
(register row, name, source, hit url, code found, evidence) and the recovered
code goes into `state/register/match-overrides.json` so the register chain
(`reference/pricing.md` → "The register") treats it as a coded row from then
on. `scripts/identify-by-name.py` drives the search and writes both files.

## When hafo names a brand we don't have

Research the official site (manufacturer domain, not a marketplace), add a row
to `reference/brand-sites.md`, then `/create-brand`. Do this once, so later runs
skip the research.
