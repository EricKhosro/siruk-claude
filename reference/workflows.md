# Workflows — warehouse and catalogue recipes, start to finish

Fifteen recipes. Each is a short command sequence with the check after it. Read
`reference/ops.md` first: every `siruk ops` and `siruk admin` write is a dry run
until `--apply <code>`, the user sees the dry run before the apply, and exit 3
means check before repeating. A catalogue command (`siruk create`, `set-variant`, …)
writes unless `--dry-run`, so always dry-run it first. A good is named by its
SKU, barcode, accounting code or id; `<id>` below is a value the previous step
printed.

Roles per command: the `roles` column of `reference/siruk-cli.md`. A key acts
as one person, so that person's role has to be on the list.

## 1. Add a product end to end

New product in siruk, then into Ops, then its receipt name, then its stock.

```sh
siruk find "royal canin mini"
siruk create runs/<date>/p1.json --dry-run
siruk create runs/<date>/p1.json
siruk ops catalog sync
siruk ops goods show 387957
siruk ops goods set 387957 --fiscal-name "Royal Canin Mini 2 kg" --adg 2309.10
siruk ops goods show 387957
```

1. `find` first; never create a duplicate (CLAUDE.md rules). The payload's
   `price` is the website price; a `prices` dict adds the other types
   (`reference/admin-api.md` "Price types"). A new variant gets **no stock**:
   on a price-types server `initial_stock` is dropped with a warning.
2. `siruk create … --dry-run`, show the diff, then the real `create`.
   Check: `siruk show <product id>` lists every variant.
3. `ops catalog sync` pulls siruk's catalogue into Ops (a dry run, then
   `--apply <code>`). It is **manager-only**: a warehouse key cannot run it. Check: `siruk ops catalog status`, then `siruk ops goods
   show <sku>` finds the good.
4. `ops goods set`: the **fiscal name** (at most 50 characters, the HDM cuts
   longer) and the **ADG code** (digits and dots) are Ops-only and the till
   needs both. Check: `goods show` prints them.
5. Stock arrives by a receipt: recipe 3 (e-invoice) or 4 (paper invoice). The
   good is not sellable at the till until it has stock and a price.

## 2. Set a store or Glovo price, and its barcode or PLU

siruk owns every price. The price type's own code (`--barcode`) is siruk's; the
variant's main barcode and a loose good's PLU are Ops's (`siruk ops goods plu`).

```sh
siruk price-types
siruk prices show 874
siruk prices set 874 387957 --type store --price 2000 --barcode 20001
siruk prices set 874 387957 --type glovo --price 2300 --compare-at 2500
siruk prices set 874 387957 --type glovo --remove
siruk prices show 874
siruk ops catalog sync
siruk ops goods show 387957
```

1. `price-types` lists the codes (`website`, `store`, `glovo`, …). The
   website row is required and has no barcode of its own; it cannot be removed.
2. `prices set` is dry by default: show it, then repeat with `--apply <code>`.
   It reads the variant back. A price is above 0 and a multiple of 10;
   compare-at is above the price; a type's barcode is unique in the product
   and never equals a variant's main barcode.
3. Check: `prices show` lists each type's price and barcode. After a sync,
   `ops goods show` shows the Ops copy. The change reaches Glovo or the till
   only through their own sync.
4. `prices set` and every catalogue write refuse a price at or below cost, for
   any price type (rule 5); the override is `--allow-below-cost`, on the user's
   say-so only. A below-cost row of another type that the command leaves alone
   is a warning, not a refusal. A price that is not from the pricing rules
   (`reference/pricing.md`) is still wrong even when it is above cost.
5. To make a PLU the main barcode of a loose good: `siruk ops goods plu
   387957-KG 121` (irreversible: its EAN moves to the extra barcodes).

## 3. Receive a supplier e-invoice

The e-invoice is what arrived; receive it as invoiced (never from the order).

```sh
siruk ops einvoices pull --from 2026-11-01 --to 2026-11-15
siruk ops einvoices list --status new
siruk ops einvoices show A6840667000
siruk ops goods-links list
siruk ops einvoices match A6840667000 3 RC-MED-4KG 2pcs
siruk ops einvoices rematch A6840667000
siruk ops einvoices receive A6840667000 --location MAIN
siruk ops einvoices post A6840667000
siruk ops einvoices show A6840667000
siruk ops stock --location MAIN
```

1. `pull` is `real-world` (it uses the owner's saved tax-service login): the
   owner's yes, each time. Skip it when the invoice is already listed.
2. `list` / `show`: the lines, their matches, **blockers** and any receipt.
   Never receive an invoice twice, and never acknowledge a replacement invoice
   (never-list): tell the owner.
3. A line with no good: `goods-links list` shows goods made from invoice
   lines. Match each line to the good and the **base units it receives**
   (`2pcs` = two sealed bags of that pack). Two candidates or a guess is not a
   match: stop and ask.
4. `receive` makes the draft receipt; `--override` accepts the failed cost
   checks and is for the owner or a manager, on the user's yes to each
   check. Show the draft in plain words (supplier, invoice, each line,
   quantity, cost, total).
5. `post` is `irreversible`: stock goes in and the supplier is owed. Check:
   `einvoices show` says posted, and `goods show <sku>` has the new stock
   (a manager's key also has `ops history <good>`).
6. Also available, each on its own owner or manager yes: `einvoices link` to a
   purchase order, `settle` for an order already received, `not-stock` for
   services and supplies (no undo), `goods-links link` to merge an invoice-made
   good onto its siruk variant (stock moves, no way back; needs `--evidence`).

## 4. Receive a paper invoice (manual receipt)

```sh
siruk ops suppliers list
siruk ops docs new receipt --location shop --supplier "Pet House" --invoice AB123456 --lines runs/<date>/receipt.json
siruk ops docs show <id>
siruk ops docs lines <id> --lines runs/<date>/receipt.json
siruk ops docs post <id>
siruk ops history 387957 --from 2026-11-01
```

1. `runs/<date>/receipt.json` is `[{"variant": "RC-2KG", "quantity": 12,
   "unit_cost_amd": 1300}]`: one line per good; a quantity is base units or
   `2.5kg`; exactly one of `unit_cost_amd` or `amount_amd` per line. The sum
   of the lines has to equal the invoice total; say so if it is a few dram off.
2. `docs new receipt` needs `--supplier` and `--invoice`. It saves a **draft**
   (tier `draft`): check it with `docs show <id>`; fix with `docs lines <id>`
   (replaces every line) or `docs delete <id>`. Locations:
   `siruk ops locations list`.
3. `docs post <id>` is `irreversible`. The dry run prints stock now and after
   for each line; show it. A posted document never changes: a mistake is
   corrected by a new document.
4. Check: `goods show` shows the new stock; a manager's key also has
   `history <good>` (the receipt) and `ops stock` (the value).

## 5. Raise and receive a purchase order

```sh
siruk ops po create --line 8009470387958=6 --line 387967=12@1300
siruk ops po lines PO-0042 --line 387957=6 --line 387967=12
siruk ops po show PO-0042
siruk ops po sent PO-0042 --ref 2026-1187
siruk ops po receive PO-0042 --line 387957=4
siruk ops po not-received PO-0042 --line 387967
siruk ops po delivered PO-0042
siruk ops po show PO-0042
```

1. `po create` makes a **draft** (hafo unless `--supplier`); a line is
   `REF=QUANTITY[@UNIT_COST_AMD]`. `po lines` replaces every line of a draft.
   A web order's draft: `siruk ops po from-web-order <web order id>`.
2. **Placing the order with hafo is never done here** (never-list): the owner
   places it. When they have, `po sent --ref <hafo's number>` records it
   (`irreversible`; hafo's number is required).
3. `po receive` books what arrived into stock: one receipt per run, `--line
   REF=QUANTITY` or `--all`. Lines the supplier did not bring: `po
   not-received` (and `po reopen` takes them back). `po delivered` closes a
   placed order. Ops allows it with lines still open: those lines get no stock and
   web orders waiting on hafo that the order covered go back to "new". Receive
   the rest or mark it `not-received` first. `po cancel` only when nothing was
   received.
4. Check: `po show` lists, per line, what is received and still open and the
   receipts; `goods show <sku>` has the stock.

## 6. Write-off, count, transfer, open a bag

Each document is saved as a draft with `docs new`, then posted with
`docs post <id>`. Show the dry run of both. All four are `irreversible` once
posted.

```sh
siruk ops docs new write_off --location shop --reason damaged --note "torn bag" --lines '[{"variant": "387957", "quantity": 1}]'
siruk ops docs new count --location shop --lines '[{"variant": "387957", "counted": 9}]'
siruk ops docs new transfer --location MAIN --to-location shop --lines '[{"variant": "387957", "quantity": 6}]'
siruk ops docs post <id>
siruk ops open-bag shop 387957 2
siruk ops goods list 387957 --location shop
```

1. **Write-off**: `--reason` is `damaged`, `expired`, `lost` or `other`; lines
   take no cost (the ledger values them).
2. **Count**: `"counted"` is what is on the shelf, not a change; count each
   good once. Posting books the difference. A count of a few goods is
   normal; never count with a guess.
3. **Transfer**: `--location` is the source and `--to-location` the
   destination, and they differ. Both are shops or storerooms, never a
   supplier warehouse.
4. **Open a bag**: `siruk ops open-bag <location> <sealed bag> <how many>`
   moves their weight to the loose good in one step (a dry run shows the on-hand
   count it read). `--loose` only when the product has several loose goods.
   The on-hand count is part of the request id, so a second run after a
   successful opening opens **another** bag; it exits 1 only when Ops answers with
   an earlier opening and the count did not fall. `--tag` forces a repeat.
5. Check: `docs show <id>` says posted; `goods list` shows the new counts
   (a manager's key also has `ops history <good>`).

## 7. Reorder levels and the reorder list

```sh
siruk ops goods set 387957 --reorder-mode custom --reorder-point 4 --reorder-target 12 --low-stock-at 5000
siruk ops goods set 387957 --clear reorder-point
siruk ops goods show 387957
siruk ops reorder show --due
siruk ops reorder build
siruk ops reorder list
siruk ops reorder lines --set 387957=6 --drop 387967
siruk ops reorder accept
siruk ops reorder reject
```

`accept` and `reject` are alternatives: one or the other ends the list.

1. Levels are per good: `--reorder-mode` is `global` (the shop's default
   levels), `custom` (this good's own point and target, in pieces) or `never`;
   `--low-stock-at` is the low-stock level, in base units or `5kg`. Check:
   `goods show` prints them.
2. `reorder show --due` is every good at or below its point, as the rule sees
   it now. `reorder build` makes or refreshes the **pending list**; `reorder
   lines` changes quantities (0 allowed), drops a line or takes it back with
   `--keep`; `reorder reject` throws the list away. Check: `reorder list`.
3. `reorder accept` (manager only) turns the list into a **draft purchase
   order**; the CLI refuses it while `reorder.autoPlace` is on. It places
   nothing with hafo; continue with recipe 5 (`po show`, then the owner
   places and `po sent`).

## 8. "Where is my stock?"

```sh
siruk ops goods list royal
siruk ops goods list --low
siruk ops goods show 387957
siruk ops stock --location MAIN
siruk ops stock --at 2026-10-31
siruk ops history 387957 --from 2026-10-01
siruk ops hafo stock royal
```

1. `goods list <text>` finds goods with their stock (`--low` = at or below
   their low-stock level); `goods show` gives stock per warehouse and the
   barcodes.
2. `ops stock` is stock and its value, per location, now or `--at` a day.
   `ops history <good>` lists every movement of one good (`--from`, `--to`,
   `--location`); this is how to see why a number is what it is. Both are
   manager reports; a warehouse person's key uses `goods show`.
3. `ops hafo stock` is what hafo has, as Ops last read it. siruk's own stock
   figure (`siruk stock show <variant id>`) is a cache of Ops while the Ops
   switch is on; when the two differ, Ops is right.

## 9. Handle a web order: accept, gift, pack, ship

A siruk or Glovo order waiting in Ops. Any signed-in person's key does these,
with the scope `office:write`.

```sh
siruk ops orders list --prep-status new
siruk ops orders show 10452
siruk ops orders accept 10452
siruk ops orders gift add 10452 RC-1 2
siruk ops orders pack 10452
siruk ops orders ship 10452
siruk ops orders show 10452
```

1. `list` / `show`: the order, its lines and its prep status (`new`, `picking`,
   `waiting_hafo`, `packed`, `shipped`). Every write below runs as: dry run →
   show it to the user → the user's yes (for `pack`, `damaged` and `ship` the
   owner's yes, each time) → the same command with `--apply <code>`.
2. `accept` starts picking (`draft`). `gift add <order> <good> <quantity>` adds
   a gift at 0 AMD from our own stock, **before packing**; `gift rm` takes one
   back that was added in Ops. A line waiting on hafo goes through a purchase
   order (recipe 5, `po from-web-order`).
3. `pack` is `irreversible`: the order's own-warehouse lines leave stock.
   `orders damaged <order> --lines <goods>` writes off packed lines that are
   unfit to sell (owner, manager or warehouse; `irreversible`).
4. `ship` is `real-world` and **only for siruk orders**: the courier has it. A
   Glovo order is refused (exit 1): its handover is Ready for pickup in the Ops
   app, never from here. The owner's yes, each time.
5. **The HDM receipt is printed in the Ops app** by the person, after packing;
   it is on the never-list, as is Glovo's "ready for pickup". Check: `orders
   show` says shipped.

## 10. Change an order's status in the admin

The website's own record of the order (customer notice, payment, the bank),
not the warehouse steps of recipe 9.

```sh
siruk admin orders list --list current --status pending
siruk admin orders show 1234
siruk admin orders set-status 1234 accepted
siruk admin orders show 1234
```

1. The order's record lists the statuses it may go to (`show --json`,
   `allowed_next_statuses`); a status outside them is refused (exit 1).
2. `set-status` is `real-world`: dry run → show it to the user → the owner's
   yes, each time → the same command with `--apply <code>`. The dry run lists
   what the move does for this order: the customer notice, the Ops event, the
   stock, and for a card order the bank (completed captures, cancelled cancels
   the authorization, refunded refunds). Show that list.
3. The payment side is separate and also `real-world`, same steps:
   `set-payment-status` (no bank call), `set-payment-type` (no capture), and
   `siruk admin payments check <id>` asks the bank for a card payment's status.
4. Check: `show` prints the new status.

## 11. Create a promotion or a voucher

These are the website's (siruk's). The till's own promotions are `siruk ops
promotions add` (Ops, `real-world`).

```sh
siruk admin promotions list
siruk admin promotions create runs/<date>/promotion.json
siruk admin promotions show 5
siruk admin promotions update 5 runs/<date>/promotion.json --lang ru
siruk admin vouchers create runs/<date>/voucher.json
siruk admin vouchers show 5
```

1. A promotion needs `name` and `status`, and the server needs `discount_type`
   (plus `discount_value` for `percentage` or `fixed`) and, for one shown in
   the home hero, `home_hero_desktop_<lang>`. A voucher needs `code` and
   `amount`. Money a customer pays or is given is a multiple of 10 AMD.
2. `create` is `real-world` for a promotion and a voucher: it changes live
   prices and what customers can use. Dry run, show it, the owner's yes, then
   `--apply <code>`.
3. **Update** replaces the form: `promotions show <id> --json`, edit the file,
   send the whole record. The CLI merges the record's relation keys back
   (`product_ids`, `gifts`, …), but `discount_type` (and the hero keys) must
   still be in the body, or the server answers a loud 422 (exit 2) and writes
   nothing. A promotion's ru / hy text is written with `--lang ru|hy`.
4. A delete's dry run prints the whole record, so a deleted promotion can be
   rebuilt (`irreversible`). Check: `show <id>`.

## 12. Add a category, brand or product type

Only on an explicit ask: the agent never invents a category, attribute or value.

```sh
siruk admin categories list --search royal
siruk admin brands list --search monge
siruk admin brands create runs/<date>/brand.json
siruk admin brands update 5 runs/<date>/brand-ru.json --lang ru
siruk admin brands update 5 runs/<date>/brand-hy.json --lang hy
siruk admin product-types create runs/<date>/type.json
siruk ids brands
siruk refresh
```

1. Search first: `list --search` for the name and its spellings; a duplicate
   brand or category is a mistake that is hard to merge later.
2. `create` makes the record in `en` (`draft`): dry run → show it to the user
   → the user's yes → the same command with `--apply <code>`; the same for
   each update and delete. A brand or category needs
   `name` and `slug`; a product type `name` and `code`, with `attributes` a list
   of `{id, role: option|attribute, is_required, is_filterable,
   show_on_product_card}`. A brand's logo and a category's image are media ids
   from `siruk media`. A product goes in a leaf category.
3. ru and hy are written by an update per language (`--lang ru`, `--lang hy`);
   an update sends the whole form (`show <id> --json` first).
4. Check: `show <id>`, then `siruk ids …` and `siruk refresh` so the menus the
   product payloads are checked against include it. `delete` refuses a
   category that still has subcategories or products.

## 13. Archive, move or merge variants

Alternatives, not a sequence: pick the one the job needs. `restore` and
`release-sku` need an archived variant, and `move` and `merge` do not follow an
archive.

```sh
siruk admin variants list --product 874
siruk admin variants archive 4512 --product 874
siruk admin variants archived --product 874
siruk admin variants restore 4512
siruk admin variants release-sku 4512
siruk admin variants move-targets 4512
siruk admin variants move 4512 --product 874 --to 880 --values runs/<date>/values.json
siruk admin products merge-targets 874
siruk admin products merge 874 --to 880 --variants runs/<date>/variants.json
siruk show 880
```

1. **Every write here is: dry run → show it to the user → the user's yes →
   the same command with `--apply <code>`.** `archive`, `move` and `merge` are
   `irreversible`, so the yes is to that exact dry run; `restore` and
   `release-sku` are `draft`.
2. **Archive**: the variant is archived, or deleted for good when it has no
   history; the server refuses the last variant of a product and a variant with
   reserved stock. `archived` lists them with the SKU each released; `restore`
   brings an archived one back; `release-sku` frees its SKU for reuse (an
   archived variant only). A move or merge cannot be undone.
3. **Move or merge**: `move-targets` / `merge-targets` list the products it can
   go into, same brand first. `move` puts one variant into another product;
   `merge` folds a mis-split product into another, every variant moving. The
   dry run shows both products.
4. Rule 9a is checked before any call: every option set on every variant of
   the target, no two variants with the same options and size. `--values`
   (`{attribute id or code: [value ids]}`) and `--variants` (`{"<variant id>":
   {"attribute_values": {...}}}` for every live variant) give the target's
   values. A descriptive value the target does not receive is refused unless it
   is re-sent or `--drop-values` is passed.
5. Check: `siruk show <product id>` for both products; `archived` after an
   archive.

## 14. Add a person or change a setting in Ops

Needs a key whose person is a manager (`reference/ops.md` "Staff, tills and
settings"): `office:read` for the `list` commands, and `office:admin` **and**
`office:read` for every write. Every write is `real-world`: dry run → show it to
the user → the owner's yes to that dry run, each time → the same command with
`--apply <code>`.

```sh
siruk ops staff list
siruk ops staff add --name 'Anna Petrosyan' --role cashier
siruk ops staff set 'Anna Petrosyan' --inactive
siruk ops tills list
siruk ops tills set 'Till 2' --inactive
siruk ops settings list
siruk ops settings set reorder.autoPlace false
siruk ops catalog auto-sync off
```

1. `staff add` makes a cashier or warehouse person only (a manager's key cannot
   make a manager or an owner). They **cannot sign in** until a human sets a
   password or PIN in the Ops app; the CLI never sets one. `staff set` changes
   name, email, role or `--active` / `--inactive` (there is no delete), and
   never the key's own person.
2. `tills set` renames a till or switches it on or off. A till is created in
   the Ops app.
3. `settings list` shows the keys with their values and defaults;
   `settings set <key> <json>` changes one. A warned key (`reorder.autoPlace`,
   `hafo.placeDryRun`, the Telegram and Glovo ones, …) prints a `!! REAL-WORLD
   SWITCH` block: read it to the owner and wait for the yes; nothing on the
   server stops it.
4. Check: `staff list`, `tills list` or `settings list` shows the new value.

## 15. Pull a report

Reads only, no code. Money is AMD (`--json` gives minor-unit strings).

```sh
siruk ops report sales --from 2026-10-01 --to 2026-10-31 --group-by variant
siruk ops report margin --from 2026-10-01 --to 2026-10-31 --channels till
siruk ops report analytics --from 2026-10-01 --to 2026-10-31
siruk ops report accountant --month 2026-10 -o runs/<date>/oct.xlsx
siruk admin report overview --from 2026-10-01 --to 2026-10-31
siruk admin report sales --from 2026-10-01 --to 2026-10-31 --export
siruk admin report search-queries --type zero --still-failing
siruk admin stock dashboard
```

1. `siruk ops report …` is Ops's numbers across the till, siruk and Glovo
   (`--channels till,siruk,glovo`): sales by day, good, payment or price type,
   margin, analytics, and the accountant's month file. They are manager reports.
2. `siruk admin report …` is the website's analytics (overview, sales,
   products, customers, promotions, margin, searches); `--export` or `-o`
   downloads the xlsx into `runs/<today>/`. Its role is developer, admin or
   analytics manager. `siruk admin stock …` is out-of-stock and low-stock.
3. Name the period and the source in the answer. For stock rather than sales,
   recipe 8.
