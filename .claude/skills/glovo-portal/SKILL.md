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
5. **Bring ArmSoft's Glovo prices (price type 02) up to date** (2026-11-09).
   The shop rings up a Glovo order with the buyer "000008 Glovo", whose
   contract uses price type 02, so ArmSoft must hold the same prices as Glovo:
   `glovo-portal.py dump`, `siruk export --format json -o runs/<date>/siruk-export.json`,
   a fresh ArmSoft price export (`armsoft-app` → Export → Prices), then
   `uv run --no-sync --with openpyxl python scripts/armsoft-glovo-prices.py <prices.xlsx> --siruk runs/<date>/siruk-export.json --date <yyyy-mm-dd> --out final/armsoft-<date>/glovo-prices-02.xml`
   and import the XML (`armsoft-app` → "Glovo price type 02"). Read the CSV
   it writes next to the XML: its notes (ArmSoft 01 ≠ Siruk) go to the user.

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

**After every posted warehouse receipt** (user 2026-11-09; office and shop alike): run
the check above with `--on-codes <the receipt's ArmSoft codes>`. It switches on only
what that delivery restocked, plus off anything sold out since the last run.
Something switched off by hand elsewhere stays off. Office: show the user the two
lists and apply on their yes. Shop: `/receive-invoices` → 5b. A run after till sales
alone (no receipt) is the plain check with no `--on…`.

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

- **New products** (our variants not on Glovo; `prices` lists them): Glovo's
  review via `createProductsRequest` (`reference/glovo/portal.md` → "Adding NEW
  products through the API"). Use `scripts/glovo-add-products.py <sheet.xlsx>
  --brand <Brand> --category <vendor cat id> [--also SKU:cat]`. The script is a dry
  run until `--apply`. Its `--out` writes the exact request plus a readable copy for
  the user, and it refuses any title not in **Zoovet's pattern** (brand first,
  Latin, no «», `glovo-titles.py` `check()`). Titles follow `glovo-export` → column C.
  Price = 50 ֏ under Zoovet's Glovo price (§2). Show the user the request file and
  get a yes before `--apply`. Example: YOKO × 12, 2026-11-09.
  **Route:** the script sends `createSimpleProductBatch`, the portal's own Add Product call.
  Every row needs the hy title in column C **and** the English title in column M; Armenia
  requires both. Afterwards, check that the products show under Store Management →
  Actions Overview → Added Products. The old `createProductsRequest` cases never reached
  Glovo's reviewers (2026-11-12).
  Since 2026-11-12, adding missing goods is pre-approved: every product we sell belongs on Glovo,
  so don't ask per batch.
  - Mixed brands go in one sheet, with column K for the brand and L for the categories.
  - Send `--batch N/11` with a gap between calls; a `VENDOR_RATE_LIMITED` refusal files nothing.
  - The script drops padded scale codes (`0000…`) from the barcode.
  - A good whose EAN is already in Glovo's master catalogue goes in with column B empty.
    **Never link it** ("Use this product"): the title and photo get locked.
  - Find what is missing with an "in ArmSoft stock but not on Glovo" check, not from the sheet.
    The onboarding silently dropped 39 rows (`reference/glovo/portal.md` → 2026-11-12).
  - **After sending, review what Glovo did** (user 2026-11-12). Glovo's team accepts or
    rejects the cases by hand, within hours. Re-run this until no case is "In progress":
    `uv run --no-sync --with openpyxl python scripts/glovo-add-products.py <every sheet sent> --review`
    It lists:
    - rows not live (with the case status);
    - a twin under a zero-stripped SKU that isn't ours;
    - a price or category set that isn't ours;
    - a changed hy title;
    - an en title where a number or species is wrong.
    Then:
    1. `--review --apply` restores our price and categories. This is pre-approved, like the add.
    2. A rejected row with no twin lands in `glovo-retry-<date>.xlsx` next to its sheet. Find
       out why first (a Glovo-made copy under another SKU or name, the photo, the title), fix
       it, then send that sheet.
    3. A "FAILURE" on a product that is live is a copy Glovo's staff made by hand. Fix its price
       and categories; don't resend it.
    4. Titles go through the guards: brand first (`glovo-titles.py` two-step rename, with
       `original`). Removing wrong words and reordering pass. Adding a variety, flavour, size or
       line word ('mini', 'bone') never does: that goes on a list for Glovo support.
    5. A wrong product Glovo's staff created (not one of our SKUs): `glovo-portal.py set-active
       <sku> --off --apply`, then `glovo-portal.py delete <sku>` (dry run). Delete it with
       `--apply` only on the user's yes, because a delete is permanent.
    Finally, add the new SKUs and prices to `final/glovo/siruk-glovo-products.xlsx`, so
    `prices` knows them.
- Titles / descriptions show read-only in the portal drawer. `ProductUpdate`
  takes `titles` / `descriptions`, but it is untested.
- Orders (bot-protected), promotions, opening times, store pause.

Learned something new? Add a dated line to `reference/glovo/portal.md`.
