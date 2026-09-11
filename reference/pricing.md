# Pricing policy

Price is the most sensitive field in the catalogue. A wrong price looks like
real data the moment it is saved. These rules are absolute.

## The two numbers

| Field | Source | Never |
|---|---|---|
| `cost_price` | **the CSV**. Any price column the CSV has is what *we pay*: `Buy Price (AMD)`, `Unit H/S Cost`, `R/Price`, a bare `Price`. | a brand-site price, a hafo price |
| `price` (or `price_per_kg` × `weight`) | **hafo.am**, the row in `product_additional_information[]` whose SKU is our article code. Only when hafo has none: a **confirmed** zoovet.am price, then the sibling fallback (both below). | anything computed, guessed, copied from a similar product, or read off a brand site |

If the CSV has both a cost and a *filled* sale-price column (a re-import of
`no-hafo-price.csv` the user completed by hand), the user's figure is the sale
price and hafo is only a cross-check (confirmed 2026-09-10). An empty
sale-price column means "fetch from hafo", never "fill it in yourself".
A vendor sheet's `R/Price` (suggested retail) is **not** a sale price: always
check hafo first, and if a sheet carries `R/Price` for rows hafo cannot price,
**ask the user** before using it (user rule 2026-09-10).

## Getting the sale price

```bash
scripts/hafo-lookup.py --code 41116Tx --name "<armenian name>"
```

Read three fields of the result:

- `confirmed` — `true` only on an article-code match. A name-search hit is a
  candidate and never carries a usable price.
- `price_source` — `"variant"` means the price came from our own row in
  `product_additional_information[]`. `"UNRESOLVED"` means the listing was found
  but our row was not, and the script returns **no price at all**. Do not
  substitute the top-level listing `price`: it is the cheapest size in the
  listing (the knotted-rope listing: top-level 400 for 15 cm while the 60 cm
  row is 2750 — 31 toys went live under-priced that way, 5 below cost).
- `wholesale_price` on that row — should equal our CSV cost for the same code
  (`3274Tx` → 1215, `3275Tx` → 1715). A mismatch means the wrong row; stop.

## Multi-variant products

A product with several variants (sizes, flavours, textures) needs **one hafo
lookup per variant**, each by its own article code, each priced from its own
row. Never copy one variant's price to its siblings, and never price a whole
product from a single listing figure. **Create only the variants that have a
hafo price**; each unpriced variant goes to `no-hafo-price.csv` on its own row
and is added later as a variant when the user returns a price (user decision
2026-09-10). Say in the report which product it belongs to.

## Second price source: zoovet.am (user rule 2026-09-11)

The user added zoovet.am as a second Armenian source — *"you can use it for
finding prices also"*. It does **not** displace hafo: hafo's row is matched by
our article code and its `wholesale_price` cross-checks against our cost, and
zoovet has no article code at all (`reference/zoovet.md`). It is the first
fallback when hafo cannot price a row.

The order, once `hafo-lookup.py` returns no usable price:

```
1. hafo row for our article        price_source: "variant"      ← primary
2. zoovet.am, identity CONFIRMED   (the checks in reference/zoovet.md)
3. sibling-price fallback          (below — same product, same cost)
4. none of those → no-hafo-price.csv, the row is not imported
```

A zoovet price may be used only when **all** of these hold:

1. hafo has no price for the code (`not on hafo` or `UNRESOLVED`);
2. the zoovet product is **confirmed** to be our article — the article number
   read off the pack in its full-size photo, or brand + line + flavour + pack
   size all matching with the pack artwork matching the brand site. An
   unconfirmed candidate is not a price, it is a note for the CSV;
3. the price beats our CSV cost (rule 5 applies to every source). A zoovet
   price at or below cost means the wrong product — treat it as no price.

Log every one in `runs/<date>/zoovet-priced.csv` and say so in the report:

```
Article Code,Brand,Product (admin id),Variant,Buy Price (AMD),Sale Price (AMD),zoovet url,zoovet name (ru),How identity was confirmed,Why hafo had no price,Date
```

When hafo **does** price the row, hafo wins and zoovet is only a sanity check:
if the two differ by more than ~25 %, say so in the report (one line, with both
numbers) rather than switching — a big gap usually means one of them is a
different pack size. Unconfirmed zoovet candidates for a row that ends up in
`no-hafo-price.csv` go in its `Why no price` text ("zoovet candidate <url> at
<price>, identity unconfirmed"), so the user can accept the number in one look.

## Sibling-price fallback (user rule 2026-09-10)

The one way a row hafo cannot price still gets imported. All three must hold:

1. hafo has **no price for that code** — either no listing matches the code
   (`not on hafo`) or the listing exists but has no row for our code
   (`price_source: "UNRESOLVED"`, `on hafo, size missing`).
2. The row is a **variant of a product that already has a hafo-priced
   variant** — created in an earlier run or earlier in this one. Same product
   by the shelf test (`reference/product-rules.md`): same brand, line,
   lifestage, breed size, food form, diet and health claims; only flavour,
   texture or pack differ.
3. The two rows have the **same CSV buy price**. Pack weight does not have to
   match (user decision 2026-09-10) — equal cost is the test; in practice it
   is almost always a flavour or texture sibling of the same pack.

Then the unpriced variant takes the sibling's hafo sale price, `cost_price`
stays the CSV figure, and the sale-price-beats-cost check still applies.

Not applied — the row goes to `no-hafo-price.csv` as usual — when:
- there is **no** priced sibling with the same cost;
- same-cost siblings carry **different** hafo prices (say Beef 600 and Lamb
  650): ambiguous, `Why no price` = `sibling prices differ`, list both
  candidates in the `Why no price` text so the user can pick;
- the "sibling" is a different product (different lifestage, breed size,
  form, diet, health claim) — that is not a sibling.

Record each fallback in `runs/<date>/sibling-priced.csv`:

```
Article Code,Brand,Product (admin id),Variant,Buy Price (AMD),Sale Price (AMD),Priced from (sibling code),Sibling hafo price,Why hafo had no price,Date
```

and say so in the report. `scripts/check-hafo-prices.py` reports such a
variant as `sibling match` when it is not on hafo but a same-product variant
with the same cost is, and that sibling's hafo price equals the variant's
price; it is flagged like any other mismatch when the sibling's price moved.

Worked example (2026-09-10): Simba Paté Adult 150 g — beef & peas 009257 is
on hafo at 480 (cost 355); chicken & liver 009267 is not on hafo, cost 355 →
imported at 480 as a second flavour variant of product 326.

## Sanity checks before any write

- `price > cost_price` (or `price_per_kg × weight > cost_price`). At or below
  cost → do not write, report it. The scripts enforce this
  (`ALLOW_BELOW_COST=1` overrides only on the user's explicit say-so).
- hafo `wholesale_price` == CSV cost for the same code, when both exist.
- A price that is wildly off hafo's usual markup (its retail is typically
  ×1.2–1.6 over our cost) deserves a second look, not a silent import.

## Periodic check against hafo

`scripts/check-hafo-prices.py` walks every Siruk variant, finds its hafo row
(bare-number search, `Tx`-form match, brand filter, wholesale==cost
tie-break), re-asks `/product/change` for that row as the storefront would,
and writes `runs/<date>/price-check.csv` (siruk price, hafo price, hafo
wholesale, cost, stock, flags, status). `--apply` PUTs the hafo price onto
mismatching variants that carry no flag (discount markers, wholesale≠cost,
change≠listing, price≤cost all block the auto-fix). First run 2026-09-10:
133/135 matched, 1 fixed (litter 8 l 6000→9250), 1 tie broken by cost.

## `per_kg` products

Dry kibble sold by the kilo uses `pricing_type: "per_kg"` with
`price_per_kg = hafo price ÷ pack weight (kg)` and `weight`. The API ignores
`price` on such variants and recomputes the pack price as rate × weight (2
decimals stored). Details in `reference/admin-api.md` and table 4 of
`reference/data-tables.md`. The vendor sheets' `PRICE/KG` column is only a
marker that the row is per-kg; it is the vendor's rounded figure, not our rate.

## The two CSVs every run writes

Both live in `runs/<date>/` and their rows are **deliberately not imported**
(two further files list rows that *were* imported through a fallback:
`sibling-priced.csv` for the sibling rule, `zoovet-priced.csv` for a confirmed
zoovet price).

`no-hafo-price.csv` — fully identified, but hafo had no price for that exact
code:

```
Article Code,Brand,Official Site,Proposed Product Name,Proposed Variant,Buy Price (AMD),Sale Price (AMD),Qty,Species,Invoice Name (as printed),Why no price,Status
```

`Sale Price (AMD)` stays empty for the user. When they return it filled, import
those rows with their figure. `Why no price` is one of:
- `not on hafo` — no listing matched the article code at all;
- `on hafo, size missing` — hafo lists the product but has no row for our
  size/pack (`price_source: "UNRESOLVED"`); name the hafo listing so the user
  can check;
- `wrong row` — the row found fails the wholesale-vs-cost check;
- `sibling prices differ` — the sibling-price fallback would apply but the
  same-cost siblings have different hafo prices; the candidates are named.

Add the zoovet candidate to that text whenever there is one
(`zoovet candidate <url> at <price>, identity unconfirmed`); when zoovet had
nothing either, say `not on hafo or zoovet` so nobody re-searches it by hand.

`not-found.csv` — could not be identified: no article-code match on hafo and
no confirmed brand / official site. Carries the raw invoice line so it can be
researched by hand.

## Why these rules exist (history)

- 2026-09-09: five rows were priced `cost × 1.364` and imported; all were pulled
  out again. No markup formula, ever.
- 2026-09-09: 31 toy variants priced from hafo's top-level listing price, 5 of
  them below our cost (60 cm rope at 400 against 1715 cost). Fixed by
  `scripts/fix-toy-prices.py`; the per-row rule above is the result.
- 2026-08-12: the storefront shows a "֏/kg" rate only on `per_kg` variants, so
  the rate must reproduce the pack price exactly.
