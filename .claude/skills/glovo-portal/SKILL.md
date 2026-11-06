---
name: glovo-portal
description: Manage Siruk's live store on Glovo through the Glovo Partner portal (portal.glovoapp.com, Delivery Hero's partner portal) — read the catalogue, push prices from the Glovo sheet, switch products on/off (Glovo has no stock quantities), restore SKUs that lost their leading zeros. Uses the portal's catalogue GraphQL API with the token from the built-in browser, where the user signs in. Use when the user asks to update prices / availability on Glovo, check what is on Glovo, take a product off Glovo, or work in the Glovo portal. Building the Pelican sheet itself is /glovo-export.
---

# Glovo Partner portal

Read `reference/glovo/portal.md` first: vendor ids, the API, the token, the
SKU zero-stripping trap, what is bot-protected. This skill is the procedure.

**Writes are live on Glovo the moment they run.** Every write command is a
dry run until `--apply`. Show the user the dry run and get a yes before `--apply`.

## 0. Token

1. `python3 scripts/glovo-portal.py whoami`. It prints the e-mail, the vendor,
   minutes left and the product count. "expired" / "no .glovo-token" → step 2.
2. Open the portal in the **built-in browser**:
   `mcp__Claude_Browser__preview_start` with `url: https://portal.glovoapp.com/`.
   If `get_page_text` shows "Log in", call `tabs_context`. If the pane is hidden,
   ask the user to press Cmd+Shift+B. Then ask them to sign in (two-step: e-mailed
   code). **Never type the password.**
3. Signed in: read the cookies in the page with
   `mcp__Claude_Browser__javascript_tool`:
   ```js
   const ck=Object.fromEntries(document.cookie.split('; ').map(c=>{const i=c.indexOf('=');return [c.slice(0,i),decodeURIComponent(c.slice(i+1))]}));
   JSON.stringify({access_token:ck.accessToken, refresh_token:ck.refreshToken, device_token:ck.deviceToken,
     vendor:'GV_AM;982410', platform_vendor_id:'982410', global_entity_id:'GV_AM', saved:new Date().toISOString()})
   ```
   Write the result to `.glovo-token` with `umask 077` (gitignored). Never echo it in chat.
   Never call the refresh endpoint from a script; the browser refreshes itself.
4. A "Press & hold" / "Before we continue" box is PerimeterX's human check.
   **Never solve it.** Ask the user to do it in the pane.

## 1. Read

- `glovo-portal.py dump` → `.siruk-cache/glovo/portal-products.json` (all products, ~15 s).
- `glovo-portal.py find <sku|text>`, `glovo-portal.py categories [--locale hy|en]`.

## 2. Prices

Prices of record for Glovo = column F of `final/glovo/siruk-glovo-products.xlsx`,
filled by `scripts/glovo-prices-into-sheet.py`:
- base = column N of `final/siruk-source-of-truth.xlsx` (the Yandex price,
  `scripts/yandex-prices-into-sot.py`; rules in `reference/yandex/README.md`);
- **every product Zoovet also sells on Glovo goes just under Zoovet's Glovo price**
  (rounded down to 50 ֏ below it), Royal Canin included (user 2026-11-06). The checked
  matches are in `state/glovo-zoovet-matches.csv`. A row is never priced at a loss, and a
  Zoovet per-kg / per-piece price (under 40% of ours) is not compared.

0. Whenever the source of truth or Zoovet's prices may have moved:
   `uv run --no-sync --with openpyxl python scripts/glovo-prices-into-sheet.py harvest`
   (Zoovet's open branch, ~5 min), then `… fill` (dry run), then `… fill --write`.
   "CAN'T BEAT Zoovet at a profit" rows → tell the user. New Zoovet products aren't
   matched automatically: re-check matches (brand + size candidates, every axis equal,
   as on 2026-11-06) and add the rows to the state CSV.
1. `glovo-portal.py prices` (dry run): count, first 15 changes, skipped rows, our
   SKUs not on Glovo.
2. Skipped rows: a jump over ±40 % is refused (a wrong match or a wrong Glovo
   price). Check each with `find`. Only on the user's say-so:
   `set-price <sku> <price> --force --apply`.
3. On the user's yes: `glovo-portal.py prices --apply` (about 0.4 s per product,
   ~10 min for the whole catalogue; run it in the background). Log:
   `runs/<date>/glovo-prices.csv`.
4. Re-run `prices`. It should say 0 changes.

One product: `set-price <sku> <price> [--apply]`. A subset: `prices --sku a b c`.

## 3. Availability (Glovo's only "stock")

Glovo keeps no quantities: `active` true/false per product. When something
sells out or comes back:
`glovo-portal.py set-active <sku…> --off|--on --note "<why>" [--apply]` →
`runs/<date>/glovo-availability.csv`. Never switch the whole catalogue off/on
without an explicit ask (the store would vanish from Glovo).

**From ArmSoft stock** (user, 2026-11-06 — "count the sealed and unsealed stock"):
1. ArmSoft turnover export (`/armsoft-app` → "Stock / turnover"), saved as
   `Scale/armsoft-turnover-<date>.xlsx`; the latest goods XML for bag sizes.
2. `uv run --no-sync --with openpyxl python scripts/glovo-portal.py stock
   Scale/armsoft-turnover-<date>.xlsx Scale/armsoft-export-<date>.xml
   --out final/glovo/glovo-availability-<date>.xlsx` (dry run). Rule: a bag needs
   a **sealed** bag (stock ≥ bag kg); its `-KG` / `-100G` variant needs 1 kg /
   100 g of open + sealed stock; everything else needs 1. Matched on the Siruk
   variant's `accounting_code`; zero-stripped Glovo SKUs handled.
3. Show the user the list, then `--apply`. It refuses to switch off over 25 % of
   the store without `--force` (a broken export, not a sell-out).
4. "off on Glovo but in stock": someone switched it off by hand — ask, don't
   `--on` by default (2026-11-06 both were ArmSoft stock errors → write-off).
5. Re-run the dry run: it should say 0 to switch off.

## 4. SKUs that lost their zeros

Onboarding went through Excel, so `011137` became `11137` on Glovo (202
products). Matching handles it (zero-stripped SKU, collisions settled by the Siruk
name), but `fix-skus` renames them back so they match exactly:
`glovo-portal.py fix-skus` (dry run) → user's yes → `--apply` →
`runs/<date>/glovo-skus.csv`. Run it before the first big price push. A
collision it can't settle is printed and left alone.

## 5. Armenian titles (Zoovet-style pattern)

Pattern: `<Brand> <Line> <what it is> <flavour -ով> <for whom … համար>, <size>`
(`reference/glovo/portal.md` → naming, and → renaming rules).

1. Proposals: one JSON line per product in `.siruk-cache/glovo/names/out-*.jsonl`. They are
   written to `.siruk-cache/glovo/names/BRIEF.md` from the `in-*.jsonl` data (current
   title + Siruk en/hy data).
2. `python3 scripts/glovo-titles.py sheet` → `final/glovo/siruk-glovo-titles.xlsx`. It
   checks that the brand comes first, that no number is lost or added, the length,
   and which words were dropped or added.
3. The user reviews it: corrections in "Your correction", `y` in "Approve".
4. `glovo-titles.py apply` (dry run), then `--apply` on the user's yes. It renames in two steps
   per product (Glovo's anti-hijacking check), sending `original` each time. Log:
   `runs/<date>/glovo-titles.csv`. A HIJACKING refusal is logged; reword that row by hand.

## 6. Not scripted yet (do by hand in the portal, or explore first)

- **New products** (our variants not on Glovo; `prices` lists them): the portal's
  Add Products goes through Glovo's review (`createProductsRequest` /
  `createSimpleProductBatch`). Explore and document in `reference/glovo/portal.md`
  before scripting it.
- Titles / descriptions show read-only in the portal drawer. `ProductUpdate`
  takes `titles` / `descriptions`, but it is untested.
- Orders (bot-protected), promotions, opening times, store pause.

Learned something new? Add a dated line to `reference/glovo/portal.md`.
