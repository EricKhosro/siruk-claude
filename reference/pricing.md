# Pricing policy

Price is the most sensitive field in the catalogue. A wrong price looks like
real data the moment it is saved. These rules are absolute.

## The two numbers

| Field | Source | Never |
|---|---|---|
| `cost_price` | **the CSV**. Any price column the CSV has is what *we pay*: `Buy Price (AMD)`, `Unit H/S Cost`, `R/Price`, a bare `Price`. | a brand-site price, a hafo price |
| `price` — always the **pack** price (catalog model, 2026-09-29) | **hafo.am**, the row in `product_additional_information[]` whose SKU is our article code. Only when hafo has none: a **confirmed** zoovet.am price, then the sibling fallback (both below). | anything computed, guessed, copied from a similar product, or read off a brand site |

If the CSV has both a cost and a *filled* sale-price column (a re-import of
`no-hafo-price.csv` the user completed by hand), the user's figure is the sale
price and hafo is only a cross-check (confirmed 2026-09-10). An empty
sale-price column means "fetch from hafo", never "fill it in yourself".

**Exception: the user names the sale-price column up front for the run.**
When the user's own instructions state that a specific column *is* the
selling price (e.g. "column X is our sale price"), write that column straight
to `price` for every row that has it and skip the whole
hafo → zoovet → sibling lookup chain for pricing on those rows entirely. This
only applies when stated up front for that column in that run — absent that
statement the CSV price is cost as usual and the full hafo-first chain runs.
The column still never doubles as `cost_price` unless the user also says so.
A vendor sheet's `R/Price` (suggested retail) is **not** a sale price: always
check hafo first, and if a sheet carries `R/Price` for rows hafo cannot price,
**ask the user** before using it (user rule 2026-09-10).

## The register — the price of record since 2026-09-16

The PM's register `csv/Product.numbers` ("Ապրանքների մնացորդներ") now carries
`Վաճառքի գին` on every row, and the user's rule is that **our price must match
that column**. So the order is: register → hafo (cross-check, and the price
where the register is blank) → confirmed zoovet → sibling fallback. Two
guards stay: a register price at or below the row's cost is not written (rule
5; 69 rows on 2026-09-16 had the cost typed in the sale column) and a jump of
≥ 2.5× cost **and** ≥ 2× the current price is held as SUSPECT (a 150 g paté
at 9,600; a 85 g pouch at 8,300). `scripts/register-price-sync.py` applies the
rest and logs everything in `runs/<date>/price-sync.csv`. Where a `Kg` rate is
given the bag is also sold loose; the per-kilo twin variant that used to carry
it (`make-perkg-twin.py`) is retired with the `per_kg` pricing type
(2026-09-29).
Loose sale (user rules 2026-09-30, 2026-10-01): a per-kg sale price (the register's `Kg` column, a price list's `Վաճառքի Գին կիլոգրամով`) gives **every bag a "1 kg" pack variant**: `sale_mode: "pack"`, `measure_type: "mass"`, `content: 1000`, `pack_count: 1`, `price` = the per-kg price, `cost_price` = bag cost ÷ bag kg, `initial_stock` 10, SKU `<bag sku>-KG`, label "1 kg", same attributes, texts (en/ru/hy) and photos as the bag, sorted right after it. A bag with no per-kg price of its own gets none — never derive one from the bag price. **`sale_mode: "weight"` is not used** (PM, 2026-10-01: the by-weight UI is untested). History: on 2026-10-01 production briefly had 84 by-weight variants (`runs/2026-10-01-fix/weight.py`); the PM had them deleted by the developers (the API can't delete a variant with stock history) and the 1 kg pack variants restored (`add-1kg.py`). For wet food a small per-unit price (750 next to a 12 × 85 g pack) is not per kg (it is below cost per kg) but the price of one pouch → a 1 × 85 g pack variant.

**The register has no article codes** — recover them with this chain:
`scripts/read-register.py` → `scripts/match-register.py` →
`scripts/hafo-by-name-cost.py` → `scripts/register-status.py` →
`scripts/register-audit.py`. A fuzzy name match can land on a same-cost
flavour sibling instead of the right row — diff the flavour words and put the
fix in `state/register/match-overrides.json`, which the chain reads back on the
next pass.

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
- `wholesale_price` on that row is a useful tie-break when a name search
  returns several candidates (it's often close to our cost) — but it is not a
  validation gate: don't reject or stop on a hafo row because its
  `wholesale_price` differs from our CSV cost. The only price check that
  blocks a write is rule 5 below (sale price vs. our own cost).

## Multi-variant products

A product with several variants (sizes, flavours, textures) needs **one hafo
lookup per variant**, each by its own article code, each priced from its own
row. Never copy one variant's price to its siblings, and never price a whole
product from a single listing figure. **Create only the variants that have a
hafo price**; each unpriced variant goes to `no-hafo-price.csv` on its own row
and is added later as a variant when the user returns a price (user decision
2026-09-10). Say in the report which product it belongs to.

## Second and third price sources: zoovet.am and nemo.am

The user added zoovet.am (2026-09-11) and nemo.am as further Armenian
sources — searched **by product name**, since neither carries our article
code. Neither displaces hafo: hafo's row is matched by our article code, and
is always tried first. zoovet/nemo are the fallback when hafo cannot price a
row.

The order, once `hafo-lookup.py` returns no usable price:

```
1. hafo row for our article           price_source: "variant"      ← primary
2. zoovet.am or nemo.am, identity CONFIRMED (checks below / reference/zoovet.md)
3. sibling-price fallback             (below — same product, same cost)
4. none of those → no-hafo-price.csv, the row is not imported
```

Try either zoovet or nemo first — neither outranks the other — and use
whichever confirms. A zoovet/nemo price may be used only when **all** of
these hold:

1. hafo has no price for the code (`not on hafo` or `UNRESOLVED`);
2. the product is **confirmed** to be our article — the article number read
   off the pack in a full-size photo, or brand + line + flavour + pack size
   all matching with the pack artwork matching the brand site. An unconfirmed
   candidate is not a price, it is a note for the CSV. zoovet's specific
   confirmation tests (including its `ME-…` code-collision trap) are in
   `reference/zoovet.md`; nemo has no documented quirks yet — confirm it the
   same way until one turns up;
3. the price beats our CSV cost (rule 5 applies to every source). A price at
   or below cost means the wrong product — treat it as no price.

Log zoovet hits in `runs/<date>/zoovet-priced.csv` and nemo hits in
`runs/<date>/nemo-priced.csv`, same columns, and say so in the report:

```
Article Code,Brand,Product (admin id),Variant,Buy Price (AMD),Sale Price (AMD),Source url,Source name (ru/hy),How identity was confirmed,Why hafo had no price,Date
```

When hafo **does** price the row, hafo wins and zoovet/nemo are only a sanity
check: if either differs from hafo by more than ~25 %, say so in the report
(one line, with both numbers) rather than switching — a big gap usually means
one of them is a different pack size. Unconfirmed candidates for a row that
ends up in `no-hafo-price.csv` go in its `Why no price` text ("zoovet/nemo
candidate <url> at <price>, identity unconfirmed"), so the user can accept
the number in one look.

**Recheck: zoovet/nemo-priced rows aren't covered by `check-hafo-prices.py`.**
That script only re-verifies rows priced from hafo. For a zoovet- or
nemo-priced row, re-run `scripts/zoovet-lookup.py --url <the product's url>`
or `scripts/nemo-lookup.py --url <the product's url>` by hand and compare its
`price` to what's live — there is no batch/scheduled version of this yet
(one row at a time, no `--apply`). Say in the run report which rows were
zoovet/nemo-priced so they're not silently skipped by the periodic hafo-only
check.

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

- `price > cost_price` — both per pack. At or below cost → do not write,
  report it. The scripts enforce this
  (`ALLOW_BELOW_COST=1` overrides only on the user's explicit say-so). This is
  the only price check that blocks a write — `wholesale_price` is a tie-break
  signal during identification (above), never a reason to stop on its own.
- A price that is wildly off hafo's usual markup (its retail is typically
  ×1.2–1.6 over our cost) deserves a second look, not a silent import.

## Periodic check against hafo

`scripts/check-hafo-prices.py` walks every Siruk variant, finds its hafo row
(bare-number search, `Tx`-form match, brand filter, wholesale==cost
tie-break), re-asks `/product/change` for that row as the storefront would,
and writes `runs/<date>/price-check.csv` (siruk price, hafo price, hafo
wholesale, cost, stock, flags, status). `--apply` PUTs the hafo price onto
mismatching variants that carry no flag (discount markers, change≠listing,
price≤cost block the auto-fix; wholesale≠cost stopped being a flag on
2026-09-23 — the `hafo wholesale` column still shows it). First run 2026-09-10:
133/135 matched, 1 fixed (litter 8 l 6000→9250), 1 tie broken by cost.

## Pack price and the per-kg rate (catalog model, 2026-09-29)

`price` is always what one pack costs the shopper — hafo's figure for that
article, unchanged, for a 15 kg bag as for an 85 g pouch. The size lives in
`measure_type` / `content` / `pack_count` (CLAUDE.md 8a), and the server
derives the "֏/kg" or "֏/100 ml" rate from price ÷ net content — never send a
rate. `pricing_type`, `price_per_kg` and `weight` are gone, and with them the
old "rate = hafo price ÷ pack kg" arithmetic. The vendor sheets' `PRICE/KG`
column is the vendor's rounded figure: never a price of ours (at most a hint
that the row is a dry-food bag).

## The two CSVs every run writes

Both live in `runs/<date>/` and their rows are **deliberately not imported**
(further files list rows that *were* imported through a fallback:
`sibling-priced.csv` for the sibling rule, `zoovet-priced.csv` /
`nemo-priced.csv` for a confirmed zoovet / nemo price).

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
- `wrong row` — the hafo row found is priced at or below our cost (rule 5),
  or (Trixie) belongs to another brand;
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
  `scripts/archive/fix-toy-prices.py`; the per-row rule above is the result.
- 2026-08-12 → 2026-09-29 (history): dry kibble was `per_kg`, priced by a
  2-decimal rate × weight that had to reproduce hafo's pack price exactly. The
  catalog model stores the pack price and computes the rate instead.
