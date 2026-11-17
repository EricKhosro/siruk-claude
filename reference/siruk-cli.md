# The `siruk` CLI — setup, the two backends, exit codes, every command

One package (`siruk/`) talks to two servers. Run it as
`uv run --no-sync siruk <command>` (the `--no-sync` keeps `uv` from
re-installing it on Windows, CLAUDE.md "Venv lock"). `siruk --help` and
`siruk <command> --help` list the flags; each command's `--help` ends with an
example. Read `reference/ops.md` before any `siruk ops …` write and
`reference/workflows.md` for the end-to-end recipes.

## The two backends

| | admin (siruk's shop API) | ops (Siruk Ops: stock, cost, codes) |
| --- | --- | --- |
| Commands | everything that does not start with `ops` | `siruk ops …` |
| API | `SIRUK_API`, default `https://api.siruk.am/api/admin` | `SIRUK_OPS_API`, else `config.json` `{"ops": {"api": …}}`, default `https://ops.siruk.am/api` |
| Token file | `SIRUK_TOKEN_FILE`, default `.siruk-token` | `SIRUK_OPS_TOKEN_FILE`, default `.ops-token` |
| Token in the environment | `SIRUK_TOKEN` | `SIRUK_OPS_TOKEN` |
| What the token is | an admin JWT, set with `siruk token set` | an `ops_…` key bound to one person, set with `siruk ops token set` (`reference/ops.md` "Sign in") |
| Check it | `siruk doctor` | `siruk ops doctor` |

An env var wins over the file. The token files are gitignored; never print,
copy or commit one. `siruk ops doctor` and every guarded write (the Ops
commands, `prices set`, `siruk admin …`) print the target and a production flag.
The older catalogue commands do not, and `siruk doctor` calls any host without
"demo" in it production, a local one included. To rehearse safely, run them with
`--dry-run` and point `SIRUK_API` at a local server (for Ops: `SIRUK_OPS_API` at
`localhost`, `host.docker.internal` or `*.test`).

Pacing is the same on both: at least 1.0 s between calls, one call at a time
(CLAUDE.md "Environments"); `--no-pace` only drops the chunk pauses.

## Two write conventions, side by side

| | Catalogue commands (`create`, `add-variant`, `set-variant`, `rename`, `translate`, `bulk-create`, `media`, `stock`, …) | Ops commands, every `siruk admin …` write and `prices set` |
| --- | --- | --- |
| Without a flag | **writes** | **dry run**: prints the requests, the state it read, a code; writes nothing |
| Look first | `--dry-run` | run it bare |
| Send it | run again without `--dry-run` | run again with `--apply <code>` |

The code is 8 hex over the exact requests, the state the dry run showed and
the target URL. A plan that changed in between, or a different environment,
gets a different code and `--apply` writes nothing (exit 1, it prints the new
dry run). Repeat the dry run per environment.

## Exit codes

| Code | Meaning | What to do |
| --- | --- | --- |
| 0 | done (or a dry run printed) | — |
| 1 | refused by a rule, a wrong code, or a replay it will not repeat | read the message; change the input, never the rule |
| 2 | the API answered with an error, or no token | `siruk doctor` / `siruk ops doctor` |
| 3 | a write whose answer never arrived: **unknown outcome** | run the check the message names; never repeat the write first |

## Reads

A read prints a table (money in AMD) or, with `--json`, the API's unmodified
JSON (money stays a minor-unit string there). `-q` hides the HTTP log.

## Roles and tiers in the table

`roles` is who the panel or the Ops controller expects to run it, and for the
admin rows the server is the truth: `/api/admin` enforces only the Admin
middleware (any non-customer role), plus a role check on the groups named in
`routes/admin.php` (search settings, index, rebuild, playground, synonyms and
rules; the Algolia status and `sync-all`; analytics; the Ops resend; API keys). A `-` means no role is recorded. The Ops `roles`
follow the controllers' `@Roles`, and the owner passes every Ops role check, so
most Ops rows leave the owner out (a row that names it, like the e-invoices,
means the same). A key acts as one non-owner person (`reference/ops.md`), so
that person must hold one of the listed roles. `tier` is `read`, `draft`,
`irreversible` or `real-world` (`reference/ops.md` "The three tiers").

## Admin commands

`siruk admin <noun> <verb>` writes siruk's shop API (`api.siruk.am`) from the
admin panel's own endpoints: orders, payments, customers, promotions, vouchers,
campaigns, delivery, content, search, categories, brands, product types,
variants, suppliers, warehouses, reports. A resource has `list`, `show`,
`create`, `update` and `delete` where the panel does; the rest are named
(`orders set-status`, `variants move`, `campaigns send`, …). `siruk admin
<noun> --help` lists the verbs, `siruk admin <noun> <verb> --help` ends with an
example, and the table below lists them all.

- **Dry by default.** Every write prints what it would send and a code;
  `--apply <code>` sends it after the user's yes to that run
  (`reference/ops.md` "The write protocol", same exit codes). Reads need no code.
- **A body is JSON** (a file, `-` for stdin, or inline). An update **replaces
  the form**: send every field, and the dry run shows what differs from the
  record. A create names every required key, or it is refused before any call.
- **`--lang en|ru|hy`** is the language a write goes in (`Content-Language`;
  `SIRUK_LANG` is the default). A translatable record is created in `en`, then
  updated once per `ru` and `hy`; the language is part of the code.
- **Tiers on this side.** `draft`: you can edit or delete it afterwards, but
  *revertible is not unseen*: search settings, synonyms and rules change live
  customer search the moment they are saved. `irreversible`: a delete, a
  move, a merge, a balance adjustment; nothing brings it back (an archive can
  be undone with `variants restore`, but a variant with no history is deleted
  for good). Every delete's dry run prints the whole record (`record {...}`, up
  to 2000 characters; a longer one is cut, so run `show --json` first) so a
  deleted item can be rebuilt. `real-world`: it reaches
  customers, money, the bank, Ops or Algolia (an order status, a payment check,
  a promotion or delivery zone, a campaign send, an Ops resend). Every tier
  needs the user's yes to the shown dry run; a `real-world` yes is for that run
  only, never a standing one.
- **Promotion update.** The CLI merges the record's relation keys back
  (`product_ids`, `gifts`, `segment_ids`, …) so an update does not wipe them,
  but the server still needs `discount_type` (and `discount_value` for
  `percentage` or `fixed`), and `home_hero_desktop_<lang>` for a promotion
  shown in the home hero. Without them it is a loud 422 (exit 2) and nothing
  is written.
- **Post updates.** `siruk admin posts show <id> --json`, edit the file, send
  the whole record with `posts update`. An empty list clears on purpose.
- **Page updates are not whole-record.** `pages set <slug> <body>` writes only
  the keys sent, in `--lang`. A list of components replaces that whole group, so
  send each component's `id` to keep it. `meta` without `meta_image` clears the
  SEO image.
- **Move and merge** (`variants move`, `products merge`): a descriptive value
  the target type does not receive is refused unless it is re-sent in `--values`
  / `--variants` or `--drop-values` is given.
- **The admin never-list** (`siruk/admin/policy.py`, checked first, for `siruk
  admin api` too): sign-in, admin users and API keys; clearing logs, unused
  media, web-push tokens, `global-data`, `reposition`, `replicate-record`;
  product bodies (`siruk create`); stock (`siruk ops`); media (`siruk media`);
  deleting a customer. A write outside the listed areas is refused with "do it
  in the admin panel", and a path that is not canonical with "use the canonical
  path …". It is a second lock behind the server's role check.

## Every command

The table is generated: run `python scripts/update-cli-reference.py`, never
edit it by hand (`tests/test_docs_manifest.py` compares it).

<!-- commands:start -->
| command | backend | tier | roles | endpoints | help | example |
| --- | --- | --- | --- | --- | --- | --- |
| `siruk doctor` | admin | read | - | GET /account | check token, API, config and pacing | siruk doctor |
| `siruk token` | admin | read | - | GET /account | store a JWT (validated with /account) | siruk token set < token.txt |
| `siruk ids` | admin | read | - | GET /brands, GET /categories, GET /attribute-families, GET /attributes | live ids: brands, categories, types, attributes | siruk ids brands |
| `siruk refresh` | admin | read | - | GET /attribute-families, GET /attributes | rewrite reference/attribute-values.json + product-types.json | siruk refresh |
| `siruk find` | admin | read | - | GET /products?search= | search products by name (before any create) | siruk find "royal canin mini" |
| `siruk show` | admin | read | - | GET /products/:id | one product, one line per variant | siruk show 874 --lang hy |
| `siruk check` | admin | read | - | GET /attribute-families/:id, GET /attributes | validate payloads against the live product types (no write) | siruk check runs/<date>/p1.json |
| `siruk create` | admin | draft | - | GET /products?search=, GET /price-types, POST /products | create a product from a payload | siruk create p.json --dry-run |
| `siruk add-variant` | admin | draft | - | GET /products/:id, GET /price-types, PUT /products/:id | append a variant to an existing product | siruk add-variant 874 v.json --dry-run |
| `siruk set-variant` | admin | draft | - | GET /products/:id, GET /price-types, PUT /products/:id, PUT /product-variants/:id | patch one variant in place | siruk set-variant 874 387957 '{"price": 2200}' --dry-run |
| `siruk rename` | admin | draft | - | GET /products/:id, PUT /products/:id | rename a product (no brand, no size in the name) | siruk rename 874 "All Breeds Adult" --dry-run |
| `siruk translate` | admin | draft | - | GET /products/:id, PUT /products/:id | store a ru/hy translation | siruk translate 874 hy hy.json --dry-run |
| `siruk stock` | admin | irreversible | - | GET /stock, GET /stock/variants/:id/movements, POST /stock/variants/:id/receive, POST /stock/variants/:id/write-off, PUT /stock/variants/:id | stock ledger of a variant | siruk stock receive 1030 12 --note "delivery" --dry-run |
| `siruk listing-order` | admin | draft | - | GET /listing-groups, PUT /listing-groups | brand + category groups that lead Relevance listings (the PM's / user's order) | siruk listing-order show |
| `siruk bulk-create` | admin | draft | - | GET /products?search=, GET /price-types, POST /products/bulk | create many NEW products in one call (en/ru/hy) | siruk bulk-create runs/<date>/bulk/*.json --dry-run |
| `siruk verify-translations` | admin | read | - | GET /products, GET /products/:id, GET /categories/:id, GET /brands/:id | the ru/hy audit (rule 13); exit 1 if anything missing | siruk verify-translations --only 874,875 |
| `siruk recheck-prices` | admin | draft | - | GET /brands, GET /products, GET /products/:id, GET /price-types, PUT /products/:id | hafo price recheck (rule 4) → runs/<date>/price-check.csv | siruk recheck-prices --only 874 |
| `siruk restock-check` | admin | draft | - | GET /products/export, GET /products/:id, GET /price-types, PUT /products/:id, PUT /product-variants/:id | after a receipt: invoice cost vs Siruk cost, and the highest of hafo / zoovet / nemo vs our price → runs/<date>/restock-check.csv | siruk restock-check 1234=5600 --json |
| `siruk export` | admin | read | - | GET /products/export | the catalogue export (one row per variant) → xlsx/json/csv, or --audit | siruk export --audit |
| `siruk media` | admin | draft | - | GET /media-folders, GET /brands, POST /media-folders, POST /medias, GET /medias/:id, DELETE /medias/:id | upload / check media | siruk media upload photo.jpg --folder products/gemon/wet-food |
| `siruk price` | admin | read | - | - | rival price lookups: hafo (by code), zoovet / nemo (by name) | siruk price hafo --code 12345 --name "Gemon" |
| `siruk api` | admin | irreversible | - | GET\|POST\|PUT\|PATCH\|DELETE /* | raw API call (escape hatch) | siruk api GET /account |
| `siruk pace` | admin | read | - | - | wait like pace.sh (between rows: `siruk pace product`) | siruk pace product |
| `siruk tui` | admin | draft | - | GET /account, GET /products?search=, GET /products/:id, PUT /products/:id, GET /price-types, PUT /product-variants/:id, GET /stock, GET /stock/variants/:id/movements, POST /stock/variants/:id/receive, POST /stock/variants/:id/write-off, PUT /stock/variants/:id, GET /brands, GET /categories, GET /attribute-families, GET /attributes | full-screen browser and editor | siruk tui |
| `siruk mcp` | admin | draft | - | GET /account, GET /products?search=, GET /products/:id, POST /products, POST /products/bulk, PUT /products/:id, GET /price-types, PUT /product-variants/:id, GET /stock, GET /stock/variants/:id/movements, POST /stock/variants/:id/receive, POST /stock/variants/:id/write-off, PUT /stock/variants/:id, GET /listing-groups, PUT /listing-groups, GET /products/export, GET /brands, GET /categories, GET /categories/:id, GET /brands/:id, GET /attribute-families, GET /attributes, GET /media-folders, POST /media-folders, POST /medias | run the MCP server on stdio | siruk mcp |
| `siruk commands` | admin | read | - | - | every command: backend, endpoints, tier, example | siruk commands --json |
| `siruk ops doctor` | ops | read | - | GET /health, GET /auth/me | check the Ops API, the token and whose it is | siruk ops doctor |
| `siruk ops token set` | ops | read | - | GET /auth/me | store the Ops key or JWT read from stdin | pbpaste \| siruk ops token set |
| `siruk ops whoami` | ops | read | - | GET /auth/me | the person and role the token belongs to | siruk ops whoami --json |
| `siruk ops api` | ops | real-world | per endpoint | GET /*, POST\|PUT\|PATCH\|DELETE /<allowed area>/* | raw Ops call: GET free, writes only in the allowed areas | siruk ops api GET /goods?q=royal |
| `siruk price-types` | admin | read | - | GET /price-types | the price types (website, store, glovo, …) | siruk price-types |
| `siruk prices show` | admin | read | - | GET /products/:id | every variant's price and barcode per price type | siruk prices show 874 |
| `siruk prices set` | admin | draft | - | GET /products/:id, GET /price-types, PUT /product-variants/:id | set or remove one variant's price / barcode for one price type | siruk prices set 874 387957 --type store --price 2000 --barcode 20001 |
| `siruk ops goods list` | ops | read | any signed-in user | GET /goods | find goods in Ops with their stock | siruk ops goods list royal --low |
| `siruk ops goods show` | ops | read | any signed-in user | GET /goods, GET /goods/:id | one good: barcodes, Ops fields, stock per warehouse | siruk ops goods show 387957 |
| `siruk ops goods set` | ops | draft | manager, warehouse | GET /goods, PATCH /goods/:id | set the Ops-only fields: fiscal name, ADG, reorder levels | siruk ops goods set 387957 --fiscal-name "Royal Canin Mini 2 kg" --adg 2309.10 |
| `siruk ops goods set-many` | ops | draft | manager, warehouse | GET /goods, PATCH /goods/:id | set the Ops-only fields of many goods from a JSON list: one dry run, one code | siruk ops goods set-many fiscal.json |
| `siruk ops goods barcode add` | ops | draft | manager, warehouse | GET /goods, POST /goods/:id/barcodes | add an extra barcode to a good | siruk ops goods barcode add 387957 4048422122074 --units 26 |
| `siruk ops goods barcode rm` | ops | draft | manager, warehouse | GET /goods, DELETE /goods/:id/barcodes/:code | remove an extra barcode from a good | siruk ops goods barcode rm 387957 4048422122074 |
| `siruk ops goods plu` | ops | irreversible | manager, warehouse | GET /goods, PUT /goods/:id/plu | make a PLU the main barcode of a loose good (its EAN moves to the extra barcodes) | siruk ops goods plu 387957-KG 121 |
| `siruk ops locations list` | ops | read | any signed-in user | GET /locations | locations: shops, storerooms, supplier warehouses | siruk ops locations list |
| `siruk ops locations create` | ops | draft | manager | GET /locations, POST /locations | add a shop or storeroom | siruk ops locations create --code SH2 --name "Shop 2" --kind shop |
| `siruk ops locations set` | ops | draft | manager | GET /locations, PATCH /locations/:id | rename, (de)activate or re-map a location | siruk ops locations set SH2 --name "Shop 2 (new)" |
| `siruk ops open-bag` | ops | irreversible | any signed-in user | GET /goods, GET /goods/:variantId, GET /locations, POST /stock/open-bag | open sealed bags: their weight moves to the loose good | siruk ops open-bag SHOP 387957 2 |
| `siruk ops docs list` | ops | read | manager, warehouse | GET /documents, GET /locations | list stock documents (newest first) | siruk ops docs list --status draft --type receipt |
| `siruk ops docs show` | ops | read | manager, warehouse | GET /documents/:id | one document with its lines | siruk ops docs show <id> |
| `siruk ops docs new` | ops | draft | manager, warehouse | POST /documents, GET /goods, GET /goods/:variantId, GET /locations, GET /suppliers | save a draft document (opening_balance, receipt, supplier_return, write_off, count, transfer, bag_opening) | siruk ops docs new receipt --location shop --supplier Hafo --invoice AB123456 --lines '[{"variant": "RC-2KG", "quantity": 12, "unit_cost_amd": 1300}]' |
| `siruk ops docs lines` | ops | draft | manager, warehouse | GET /documents/:id, GET /goods, GET /goods/:variantId, PUT /documents/:id/lines | replace every line of a draft | siruk ops docs lines <id> --lines lines.json |
| `siruk ops docs post` | ops | irreversible | manager, warehouse | GET /documents/:id, GET /goods/:id, POST /documents/:id/post | post a draft: stock moves and the document never changes (the dry run shows stock now and after) | siruk ops docs post <id> |
| `siruk ops docs delete` | ops | draft | manager, warehouse | GET /documents/:id, DELETE /documents/:id | delete a draft (a posted document is never deleted) | siruk ops docs delete <id> |
| `siruk ops suppliers list` | ops | read | manager, warehouse | GET /suppliers | suppliers and what we owe each | siruk ops suppliers list |
| `siruk ops suppliers show` | ops | read | manager | GET /suppliers, GET /suppliers/:id | one supplier: balance and received-not-invoiced | siruk ops suppliers show 'Pet House' |
| `siruk ops suppliers create` | ops | draft | manager | POST /suppliers | add a supplier | siruk ops suppliers create 'Pet House' --tin 00000000 |
| `siruk ops suppliers set` | ops | draft | manager | GET /suppliers, PATCH /suppliers/:id | rename, change codes, switch a supplier on or off | siruk ops suppliers set 'Pet House' --inactive |
| `siruk ops suppliers ledger` | ops | read | manager | GET /suppliers, GET /suppliers/:id/ledger | invoices, payments and the running balance | siruk ops suppliers ledger 'Pet House' --from 2026-11-01 |
| `siruk ops suppliers pay` | ops | irreversible | manager | GET /suppliers, POST /suppliers/:id/payments | record a payment to a supplier (takes the balance down) | siruk ops suppliers pay 'Pet House' --amount-amd 1300 --method bank |
| `siruk ops suppliers adjust` | ops | irreversible | manager | GET /suppliers, POST /suppliers/:id/adjustments | put a balance right with a signed entry (+ we owe more, - less) | siruk ops suppliers adjust 'Pet House' --amount-amd=-500 --note 'credit note 17' |
| `siruk ops suppliers statement-check` | ops | read | manager | GET /suppliers, POST /suppliers/:id/statement-check | compare a month's invoices with the supplier's statement | siruk ops suppliers statement-check hafo --month 2026-10 --statement-amd 1250000 |
| `siruk ops po list` | ops | read | manager, warehouse, cashier | GET /suppliers, GET /purchase-orders | purchase orders | siruk ops po list --status placed |
| `siruk ops po show` | ops | read | manager, warehouse, cashier | GET /purchase-orders, GET /purchase-orders/:id | one order: lines, what is received and still open, receipts | siruk ops po show PO-0042 |
| `siruk ops po create` | ops | draft | manager, warehouse | GET /suppliers, GET /goods, POST /purchase-orders | a draft order (hafo unless --supplier) | siruk ops po create --line 8009470387958=6 --line 387967=12@1300 |
| `siruk ops po lines` | ops | draft | manager, warehouse | GET /purchase-orders, GET /purchase-orders/:id, GET /goods, PUT /purchase-orders/:id/lines | replace every line of a draft order | siruk ops po lines PO-0042 --line 387957=6 --line 387967=12 |
| `siruk ops po sent` | ops | irreversible | manager, warehouse | GET /purchase-orders, GET /purchase-orders/:id, POST /purchase-orders/:id/placed | record that the order was sent to the supplier (hafo's number is required) | siruk ops po sent PO-0042 --ref 2026-1187 |
| `siruk ops po receive` | ops | irreversible | manager, warehouse, cashier | GET /purchase-orders, GET /purchase-orders/:id, GET /locations, POST /purchase-orders/:id/receive | book goods into stock from a placed order: one receipt per press | siruk ops po receive PO-0042 --line 387957=4 |
| `siruk ops po not-received` | ops | draft | manager, warehouse, cashier | GET /purchase-orders, GET /purchase-orders/:id, POST /purchase-orders/:id/not-received | mark lines the supplier did not bring | siruk ops po not-received PO-0042 --line 387957 |
| `siruk ops po reopen` | ops | draft | manager, warehouse, cashier | GET /purchase-orders, GET /purchase-orders/:id, POST /purchase-orders/:id/reopen | put lines marked not received back on the order | siruk ops po reopen PO-0042 --line 387957 |
| `siruk ops po delivered` | ops | irreversible | manager, warehouse | GET /purchase-orders, GET /purchase-orders/:id, POST /purchase-orders/:id/delivered | close a placed order as delivered | siruk ops po delivered PO-0042 |
| `siruk ops po cancel` | ops | irreversible | manager, warehouse | GET /purchase-orders, GET /purchase-orders/:id, POST /purchase-orders/:id/cancel | cancel an order with nothing received | siruk ops po cancel PO-0042 |
| `siruk ops po from-web-order` | ops | draft | manager, warehouse | POST /purchase-orders/from-web-order/:webOrderId | the draft order for one web order (the one there is, or a new one) | siruk ops po from-web-order 0b9c3a52-7c1d-4e0a-9d52-3f1d6c1f0a11 |
| `siruk ops reorder show` | ops | read | manager, warehouse | GET /hafo/reorder | every variant as the reorder rule sees it now | siruk ops reorder show --due |
| `siruk ops reorder list` | ops | read | manager, warehouse | GET /hafo/reorder/list | the pending reorder list | siruk ops reorder list |
| `siruk ops reorder build` | ops | draft | manager, warehouse | GET /hafo/reorder/list, POST /hafo/reorder/list/build | build or refresh the pending list | siruk ops reorder build |
| `siruk ops reorder lines` | ops | draft | manager, warehouse | GET /hafo/reorder/list, PUT /hafo/reorder/list/:id/lines | change quantities, drop or keep lines of the pending list | siruk ops reorder lines --set 387957=6 --drop 387967 |
| `siruk ops reorder accept` | ops | draft | manager | GET /hafo/reorder/list, GET /settings, POST /hafo/reorder/list/:id/accept | turn the pending list into a draft purchase order | siruk ops reorder accept |
| `siruk ops reorder reject` | ops | draft | manager, warehouse | GET /hafo/reorder/list, POST /hafo/reorder/list/:id/reject | discard the pending list | siruk ops reorder reject |
| `siruk ops hafo stock` | ops | read | any role | GET /hafo/stock | what hafo has, as the watch tower last read it | siruk ops hafo stock royal |
| `siruk ops einvoices list` | ops | read | owner, manager, warehouse | GET /einvoices | received supplier e-invoices | siruk ops einvoices list --status new |
| `siruk ops einvoices show` | ops | read | owner, manager, warehouse | GET /einvoices, GET /einvoices/:id | one invoice: lines, matches, blockers, receipt | siruk ops einvoices show A6840667000 |
| `siruk ops einvoices pull` | ops | real-world | owner, manager | POST /einvoices/pull | pull received invoices from the tax service (uses the owner's saved login) | siruk ops einvoices pull --from 2026-11-01 --to 2026-11-15 |
| `siruk ops einvoices rematch` | ops | draft | owner, manager, warehouse | GET /einvoices, GET /einvoices/:id, POST /einvoices/:id/rematch | match the lines again by barcode and supplier map | siruk ops einvoices rematch A6840667000 |
| `siruk ops einvoices match` | ops | draft | owner, manager, warehouse | GET /einvoices, GET /einvoices/:id, GET /goods, GET /goods/:variantId, PUT /einvoices/:id/lines/:lineId/match | match one line to a good and the base units it receives | siruk ops einvoices match A6840667000 3 RC-MED-4KG 2pcs |
| `siruk ops einvoices unmatch` | ops | draft | owner, manager, warehouse | GET /einvoices, GET /einvoices/:id, DELETE /einvoices/:id/lines/:lineId/match | clear one line's match | siruk ops einvoices unmatch A6840667000 3 |
| `siruk ops einvoices link` | ops | irreversible | owner, manager | GET /einvoices, GET /einvoices/:id, GET /purchase-orders/:id, POST /einvoices/:id/link | link the invoice to its purchase order (on a web order it passes through and books what we owe) | siruk ops einvoices link A6840667000 <purchase order id> |
| `siruk ops einvoices unlink` | ops | irreversible | owner, manager | GET /einvoices, GET /einvoices/:id, DELETE /einvoices/:id/link | take the invoice off its purchase order (undoing a pass-through reverses the payable) | siruk ops einvoices unlink A6840667000 |
| `siruk ops einvoices receive` | ops | draft | owner, manager, warehouse (override: owner, manager) | GET /einvoices, GET /einvoices/:id, GET /locations, POST /einvoices/:id/receive | make the draft receipt (--override accepts the listed cost checks) | siruk ops einvoices receive A6840667000 --location MAIN |
| `siruk ops einvoices post` | ops | irreversible | owner, manager, warehouse | GET /einvoices, GET /einvoices/:id, POST /einvoices/:id/post | post the draft receipt: stock in, supplier owed | siruk ops einvoices post A6840667000 |
| `siruk ops einvoices discard` | ops | draft | owner, manager, warehouse | GET /einvoices, GET /einvoices/:id, POST /einvoices/:id/discard-draft | delete the draft receipt of an invoice | siruk ops einvoices discard A6840667000 |
| `siruk ops einvoices settle` | ops | irreversible | owner, manager, warehouse (accept differences: owner, manager) | GET /einvoices, GET /einvoices/:id, POST /einvoices/:id/settle-order | settle the invoice of an order already received from: cost and what we owe, no stock | siruk ops einvoices settle A6840667000 |
| `siruk ops einvoices not-stock` | ops | irreversible | owner, manager | GET /einvoices, GET /einvoices/:id, POST /einvoices/:id/not-stock | mark the invoice not stock (services, supplies): books what we owe, no undo | siruk ops einvoices not-stock A6840667000 |
| `siruk ops goods-links list` | ops | read | owner, manager, warehouse | GET /goods-links/unlinked | goods made from invoice lines, waiting for a link | siruk ops goods-links list |
| `siruk ops goods-links link` | ops | irreversible | owner, manager, warehouse | GET /goods, GET /goods/:variantId, GET /goods-links/unlinked, POST /goods-links/:variantId/link | merge an invoice-made good onto its siruk variant (its stock moves, no way back) | siruk ops goods-links link <good> <siruk variant> --evidence 'EAN 4607...' |
| `siruk ops stock` | ops | read | manager | GET /reports/stock, GET /locations | stock and its value at a date, per location | siruk ops stock --at 2026-10-31 --location MAIN |
| `siruk ops history` | ops | read | manager | GET /goods/:id, GET /goods, GET /locations, GET /reports/variants/:id/history | every stock movement of one good | siruk ops history 4820000000017 --from 2026-10-01 |
| `siruk ops sales list` | ops | read | cashier, manager, warehouse | GET /sales | till sales, newest first | siruk ops sales list --limit 20 |
| `siruk ops sales show` | ops | read | cashier, manager, warehouse | GET /sales/:id, GET /sales | one till sale with its lines and payments | siruk ops sales show 000123 |
| `siruk ops report sales` | ops | read | manager | GET /reports/sales | sales by day, good, payment or price type | siruk ops report sales --from 2026-10-01 --to 2026-10-31 --group-by variant |
| `siruk ops report margin` | ops | read | manager | GET /reports/margin | revenue, cost and margin of a period | siruk ops report margin --from 2026-10-01 --to 2026-10-31 --channels till |
| `siruk ops report analytics` | ops | read | manager | GET /reports/analytics | sales and margin by channel, top goods | siruk ops report analytics --from 2026-10-01 --to 2026-10-31 |
| `siruk ops report accountant` | ops | read | manager | GET /reports/accountant.xlsx | download the accountant's month file (xlsx) | siruk ops report accountant --month 2026-10 -o runs/2026-11-16/oct.xlsx |
| `siruk ops orders list` | ops | read | any signed-in user | GET /web-orders | web orders (siruk, Glovo), newest first | siruk ops orders list --prep-status new --channel glovo |
| `siruk ops orders show` | ops | read | any signed-in user | GET /web-orders/:id, GET /web-orders | one web order with its lines | siruk ops orders show 10452 |
| `siruk ops receipts list` | ops | read | cashier, manager, warehouse | GET /fiscal/receipts | fiscal (HDM) receipts | siruk ops receipts list --status failed |
| `siruk ops incidents` | ops | read | manager | GET /fiscal/incidents | fiscal incidents the office should look at | siruk ops incidents |
| `siruk ops outbox list` | ops | read | manager | GET /outbox/failed | messages to siruk or Telegram the outbox gave up on | siruk ops outbox list |
| `siruk ops outbox resend` | ops | real-world | manager | GET /outbox/failed, POST /outbox/:id/resend | send one failed message to its target (siruk or Telegram) again | siruk ops outbox resend 0b9c3a52-7c1d-4e0a-9d52-3f1d6c1f0a11 |
| `siruk ops catalog status` | ops | read | manager | GET /catalog/status | last catalogue sync and whether one is running | siruk ops catalog status |
| `siruk ops catalog sync` | ops | draft | manager | GET /catalog/status, POST /catalog/sync | pull siruk's catalogue into Ops | siruk ops catalog sync --full |
| `siruk ops settings list` | ops | read | manager | GET /settings | the shop settings and their defaults | siruk ops settings list |
| `siruk ops services list` | ops | read | cashier, manager, warehouse | GET /services | services sold at the till (delivery…) | siruk ops services list --active |
| `siruk ops promotions list` | ops | read | manager | GET /shop-promotions | the shop's own till promotions | siruk ops promotions list |
| `siruk ops orders accept` | ops | draft | any signed-in user | GET /web-orders/:id, GET /web-orders, POST /web-orders/:id/picking | accept a web order: start picking it | siruk ops orders accept 10452 |
| `siruk ops orders gift add` | ops | draft | any signed-in user | GET /web-orders/:id, GET /web-orders, GET /goods, GET /goods/:variantId, POST /web-orders/:id/gifts | add a gift at 0 AMD from our own stock, before packing | siruk ops orders gift add 10452 RC-1 2 |
| `siruk ops orders gift rm` | ops | draft | any signed-in user | GET /web-orders/:id, GET /web-orders, DELETE /web-orders/:id/gifts/:lineId | remove a gift added in Ops, before it is packed | siruk ops orders gift rm 10452 RC-1 |
| `siruk ops orders pack` | ops | irreversible | any signed-in user | GET /web-orders/:id, GET /web-orders, POST /web-orders/:id/pack | pack a web order: its own-warehouse lines leave stock | siruk ops orders pack 10452 |
| `siruk ops orders ship` | ops | real-world | any signed-in user | GET /web-orders/:id, GET /web-orders, POST /web-orders/:id/ship | ship a packed web order: the courier has it | siruk ops orders ship 10452 |
| `siruk ops orders damaged` | ops | irreversible | owner, manager, warehouse | GET /web-orders/:id, GET /web-orders, POST /web-orders/:id/damaged | mark packed lines of an order as unfit to sell: their value is written off | siruk ops orders damaged 10452 --lines RC-1,RC-2 |
| `siruk ops services add` | ops | real-world | owner, manager | GET /services, POST /services | add a service sold at the till (delivery, nail trim…) | siruk ops services add NAIL_TRIM --name-en "Nail trim" --price 3000 |
| `siruk ops services set` | ops | real-world | owner, manager | GET /services, PATCH /services/:id | change a service: name, price, receipt name, ADG code, on or off | siruk ops services set NAIL_TRIM --price 3500 |
| `siruk ops promotions add` | ops | real-world | owner, manager | GET /shop-promotions, GET /goods, GET /goods/:variantId, POST /shop-promotions | add a shop promotion: percent or amount off a good, product or brand | siruk ops promotions add --name "Autumn" --brand Monge --percent 10 --from 2026-11-20 --to 2026-11-30 |
| `siruk ops promotions set` | ops | real-world | owner, manager | GET /shop-promotions, GET /goods, GET /goods/:variantId, PUT /shop-promotions/:id | change a shop promotion (it is replaced whole) | siruk ops promotions set Autumn --percent 15 --inactive |
| `siruk ops staff list` | ops | read | owner, manager | GET /users | the people in Ops, their role and whether they can sign in | siruk ops staff list |
| `siruk ops staff add` | ops | real-world | owner, manager | GET /users, POST /users | add a person (no sign-in is set up here) | siruk ops staff add --name 'Anna Petrosyan' --role cashier |
| `siruk ops staff set` | ops | real-world | owner, manager | GET /users, PATCH /users/:id | change a person's name, email, role or whether they are active | siruk ops staff set boris@example.am --role warehouse |
| `siruk ops tills list` | ops | read | owner, manager | GET /tills | the tills and whether each is active | siruk ops tills list |
| `siruk ops tills set` | ops | real-world | owner, manager | GET /tills, PATCH /tills/:id | rename a till or switch it on or off | siruk ops tills set 'Till 2' --inactive |
| `siruk ops settings set` | ops | real-world | owner, manager | GET /settings, PUT /settings/:key | change one shop setting (before → after; the loud ones carry a warning) | siruk ops settings set telegram.managerChatId '"-100123"' |
| `siruk ops catalog auto-sync` | ops | real-world | owner, manager | GET /catalog/status, PUT /catalog/auto-sync | turn the scheduled catalogue pull on or off | siruk ops catalog auto-sync off |
| `siruk admin api` | admin | irreversible | per endpoint | GET /*, POST\|PUT\|PATCH\|DELETE /<allowed area>/* | raw admin call: GET free, writes only in the allowed areas | siruk admin api GET /brands |
| `siruk admin orders list` | admin | read | admin | GET /orders | list orders, newest first (one page, or --page all) | siruk admin orders list --list current --payment-status unpaid |
| `siruk admin orders show` | admin | read | admin | GET /orders/:id | one order | siruk admin orders show 5 |
| `siruk admin orders set-status` | admin | real-world | admin | GET /orders/:id, POST /orders/:id/update-status | move an order to another status (what it does depends on the move; the dry run lists it) | siruk admin orders set-status 1234 delivered |
| `siruk admin orders set-payment-status` | admin | real-world | admin | GET /orders/:id, POST /orders/:id/update-payment-status | set an order's payment status (Ops hears it only if accepted and already sent; no bank call) | siruk admin orders set-payment-status 1234 paid |
| `siruk admin orders set-payment-type` | admin | real-world | admin | GET /orders/:id, POST /update-order-payment-type | correct how an order is paid (Ops hears it only if accepted and already sent; no capture) | siruk admin orders set-payment-type 1234 cash_on_delivery |
| `siruk admin payments list` | admin | read | admin | GET /payments | list payments, newest first (one page, or --page all) | siruk admin payments list --status pending |
| `siruk admin payments show` | admin | read | admin | GET /payments/:id | one payment, with its live details from the bank (nothing changes) | siruk admin payments show 88 |
| `siruk admin payments check` | admin | real-world | admin | GET /payments/:id, POST /payments/:id/check-status | ask the bank for a card payment's status; a pending order is confirmed or failed | siruk admin payments check 88 |
| `siruk admin customers list` | admin | read | admin | GET /customers | list customers (one page, or --page all) | siruk admin customers list --search anna |
| `siruk admin customers show` | admin | read | admin | GET /customers/:id | one customer | siruk admin customers show 5 |
| `siruk admin customers adjust-balance` | admin | irreversible | admin | GET /customers/:id, POST /customers/:id/adjust-balance | add to or subtract from a customer's balance, in AMD (multiples of 10), with a note | siruk admin customers adjust-balance 42 add 1000 --note 'refund 1234' |
| `siruk admin subscribers list` | admin | read | admin | GET /subscribers | list newsletter subscribers (one page, or --page all) | siruk admin subscribers list --page all |
| `siruk admin promotions list` | admin | read | admin | GET /promotions | list promotions (all of them: the API ignores --search) | siruk admin promotions list --gifts |
| `siruk admin promotions show` | admin | read | admin | GET /promotions/:id | one promotion | siruk admin promotions show 5 |
| `siruk admin promotions create` | admin | real-world | admin | POST /promotions | create a promotion from a JSON body | siruk admin promotions create '{"name": "…", "status": "…"}' |
| `siruk admin promotions update` | admin | real-world | admin | GET /promotions/:id, PUT /promotions/:id | replace a promotion's form with a JSON body | siruk admin promotions update 5 '{"name": "…", "status": "…"}' |
| `siruk admin promotions delete` | admin | irreversible | admin | GET /promotions/:id, DELETE /promotions/:id | delete a promotion | siruk admin promotions delete 5 |
| `siruk admin vouchers list` | admin | read | admin | GET /vouchers | list vouchers (all of them: the API ignores --search) | siruk admin vouchers list |
| `siruk admin vouchers show` | admin | read | admin | GET /vouchers/:id | one voucher | siruk admin vouchers show 5 |
| `siruk admin vouchers create` | admin | real-world | admin | POST /vouchers | create a voucher from a JSON body | siruk admin vouchers create '{"code": "…", "amount": "…"}' |
| `siruk admin vouchers update` | admin | real-world | admin | GET /vouchers/:id, PUT /vouchers/:id | replace a voucher's form with a JSON body | siruk admin vouchers update 5 '{"code": "…", "amount": "…"}' |
| `siruk admin vouchers delete` | admin | irreversible | admin | GET /vouchers/:id, DELETE /vouchers/:id | delete a voucher | siruk admin vouchers delete 5 |
| `siruk admin segments list` | admin | read | admin | GET /segments | list segments (one page, or --page all) | siruk admin segments list --search royal |
| `siruk admin segments show` | admin | read | admin | GET /segments/:id | one segment | siruk admin segments show 5 |
| `siruk admin segments create` | admin | draft | admin | POST /segments | create a segment from a JSON body | siruk admin segments create '{"name": "…", "rules": "…"}' |
| `siruk admin segments update` | admin | draft | admin | GET /segments/:id, PUT /segments/:id | replace a segment's form with a JSON body | siruk admin segments update 5 '{"name": "…", "rules": "…"}' |
| `siruk admin segments delete` | admin | irreversible | admin | GET /segments/:id, DELETE /segments/:id | delete a segment | siruk admin segments delete 5 |
| `siruk admin campaign-templates list` | admin | read | admin | GET /campaign-templates | list campaign-templates (one page, or --page all) | siruk admin campaign-templates list --search royal |
| `siruk admin campaign-templates show` | admin | read | admin | GET /campaign-templates/:id | one campaign template | siruk admin campaign-templates show 5 |
| `siruk admin campaign-templates create` | admin | draft | admin | POST /campaign-templates | create a campaign template from a JSON body | siruk admin campaign-templates create '{"name": "…", "template_type": "…"}' |
| `siruk admin campaign-templates update` | admin | draft | admin | GET /campaign-templates/:id, PUT /campaign-templates/:id | replace a campaign template's form with a JSON body | siruk admin campaign-templates update 5 '{"name": "…", "template_type": "…"}' |
| `siruk admin campaign-templates delete` | admin | irreversible | admin | GET /campaign-templates/:id, DELETE /campaign-templates/:id | delete a campaign template | siruk admin campaign-templates delete 5 |
| `siruk admin campaigns list` | admin | read | admin | GET /campaigns | list campaigns (one page, or --page all) | siruk admin campaigns list --search royal |
| `siruk admin campaigns show` | admin | read | admin | GET /campaigns/:id | one campaign | siruk admin campaigns show 5 |
| `siruk admin campaigns create` | admin | draft | admin | POST /campaigns | create a campaign from a JSON body | siruk admin campaigns create '{"name": "…", "template_id": "…", "recipients_type": "…"}' |
| `siruk admin campaigns update` | admin | draft | admin | GET /campaigns/:id, PUT /campaigns/:id | replace a campaign's form with a JSON body | siruk admin campaigns update 5 '{"name": "…", "template_id": "…", "recipients_type": "…"}' |
| `siruk admin campaigns delete` | admin | irreversible | admin | GET /campaigns/:id, DELETE /campaigns/:id | delete a campaign | siruk admin campaigns delete 5 |
| `siruk admin delivery-zones list` | admin | read | admin | GET /delivery-zones | list delivery-zones (all of them: the API ignores --search) | siruk admin delivery-zones list |
| `siruk admin delivery-zones show` | admin | read | admin | GET /delivery-zones/:id | one delivery zone | siruk admin delivery-zones show 5 |
| `siruk admin delivery-zones create` | admin | real-world | admin | POST /delivery-zones | create a delivery zone from a JSON body | siruk admin delivery-zones create '{"name": "…", "type": "…", "geometry": "…", "shipping_cost": "…", "priority": "…"}' |
| `siruk admin delivery-zones update` | admin | real-world | admin | GET /delivery-zones/:id, PUT /delivery-zones/:id | replace a delivery zone's form with a JSON body | siruk admin delivery-zones update 5 '{"name": "…", "type": "…", "geometry": "…", "shipping_cost": "…", "priority": "…"}' |
| `siruk admin delivery-zones delete` | admin | irreversible | admin | GET /delivery-zones/:id, DELETE /delivery-zones/:id | delete a delivery zone | siruk admin delivery-zones delete 5 |
| `siruk admin segments fields` | admin | read | admin | GET /segments/fields | the fields and operators a segment rule may use | siruk admin segments fields |
| `siruk admin campaigns logs` | admin | read | admin | GET /campaigns/search-logs | who a campaign went to and what happened to it | siruk admin campaigns logs 12 --search @gmail |
| `siruk admin campaigns send` | admin | real-world | admin | GET /campaigns/:id, GET /segments/:id?isShow=1, POST /campaigns/:id/send | send a campaign to its recipients, for real | siruk admin campaigns send 12 |
| `siruk admin delivery-settings show` | admin | read | admin | GET /delivery-settings | cut-off time, non-working days, holidays and the stale-stock window | siruk admin delivery-settings show |
| `siruk admin delivery-settings set` | admin | real-world | admin | GET /delivery-settings, PUT /delivery-settings | change the delivery promise settings (only the keys sent) | siruk admin delivery-settings set '{"cutoff_time": "15:00"}' |
| `siruk admin faq-categories list` | admin | read | admin | GET /faq-categories | list faq-categories (one page, or --page all) | siruk admin faq-categories list --search royal |
| `siruk admin faq-categories show` | admin | read | admin | GET /faq-categories/:id | one FAQ category | siruk admin faq-categories show 5 |
| `siruk admin faq-categories create` | admin | draft | admin | GET /faq-categories?search=, POST /faq-categories | create a FAQ category in en from a JSON body | siruk admin faq-categories create '{"name": "…"}' |
| `siruk admin faq-categories update` | admin | draft | admin | GET /faq-categories/:id, PUT /faq-categories/:id | replace a FAQ category's form with a JSON body; --lang ru\|hy writes that language | siruk admin faq-categories update 5 '{"name": "…"}' --lang ru |
| `siruk admin faq-categories delete` | admin | irreversible | admin | GET /faq-categories/:id, DELETE /faq-categories/:id | delete a FAQ category (also deletes every FAQ in that category) | siruk admin faq-categories delete 5 |
| `siruk admin faqs list` | admin | read | admin | GET /faqs | list faqs (one page, or --page all) | siruk admin faqs list --search royal |
| `siruk admin faqs show` | admin | read | admin | GET /faqs/:id | one FAQ | siruk admin faqs show 5 |
| `siruk admin faqs create` | admin | draft | admin | GET /faqs?search=, POST /faqs | create a FAQ in en from a JSON body | siruk admin faqs create '{"category_id": "…", "question": "…", "answer": "…"}' |
| `siruk admin faqs update` | admin | draft | admin | GET /faqs/:id, PUT /faqs/:id | replace a FAQ's form with a JSON body; --lang ru\|hy writes that language | siruk admin faqs update 5 '{"category_id": "…", "question": "…", "answer": "…"}' --lang ru |
| `siruk admin faqs delete` | admin | irreversible | admin | GET /faqs/:id, DELETE /faqs/:id | delete a FAQ | siruk admin faqs delete 5 |
| `siruk admin post-categories list` | admin | read | admin | GET /post-categories | list post-categories (one page, or --page all) | siruk admin post-categories list --search royal |
| `siruk admin post-categories show` | admin | read | admin | GET /post-categories/:id | one post category | siruk admin post-categories show 5 |
| `siruk admin post-categories create` | admin | draft | admin | GET /post-categories?search=, POST /post-categories | create a post category in en from a JSON body | siruk admin post-categories create '{"name": "…", "slug": "…"}' |
| `siruk admin post-categories update` | admin | draft | admin | GET /post-categories/:id, PUT /post-categories/:id | replace a post category's form with a JSON body; --lang ru\|hy writes that language | siruk admin post-categories update 5 '{"name": "…", "slug": "…"}' --lang ru |
| `siruk admin post-categories delete` | admin | irreversible | admin | GET /post-categories/:id, DELETE /post-categories/:id | delete a post category (its posts are left without a category) | siruk admin post-categories delete 5 |
| `siruk admin authors list` | admin | read | admin | GET /authors | list authors (one page, or --page all) | siruk admin authors list --search royal |
| `siruk admin authors show` | admin | read | admin | GET /authors/:id | one author | siruk admin authors show 5 |
| `siruk admin authors create` | admin | draft | admin | GET /authors?search=, POST /authors | create a author in en from a JSON body | siruk admin authors create '{"name": "…"}' |
| `siruk admin authors update` | admin | draft | admin | GET /authors/:id, PUT /authors/:id | replace a author's form with a JSON body; --lang ru\|hy writes that language | siruk admin authors update 5 '{"name": "…"}' --lang ru |
| `siruk admin authors delete` | admin | irreversible | admin | GET /authors/:id, DELETE /authors/:id | delete a author | siruk admin authors delete 5 |
| `siruk admin vets list` | admin | read | admin | GET /vets | list vets (one page, or --page all) | siruk admin vets list --search royal |
| `siruk admin vets show` | admin | read | admin | GET /vets/:id | one vet | siruk admin vets show 5 |
| `siruk admin vets create` | admin | draft | admin | GET /vets?search=, POST /vets | create a vet in en from a JSON body | siruk admin vets create '{"name": "…"}' |
| `siruk admin vets update` | admin | draft | admin | GET /vets/:id, PUT /vets/:id | replace a vet's form with a JSON body; --lang ru\|hy writes that language | siruk admin vets update 5 '{"name": "…"}' --lang ru |
| `siruk admin vets delete` | admin | irreversible | admin | GET /vets/:id, DELETE /vets/:id | delete a vet | siruk admin vets delete 5 |
| `siruk admin posts list` | admin | read | admin | GET /posts | list posts (one page, or --page all) | siruk admin posts list --search royal |
| `siruk admin posts show` | admin | read | admin | GET /posts/:id | one post | siruk admin posts show 5 |
| `siruk admin posts create` | admin | draft | admin | GET /posts?search=, POST /posts | create a post in en from a JSON body | siruk admin posts create '{"post_category_id": "…", "title": "…", "slug": "…"}' |
| `siruk admin posts update` | admin | draft | admin | GET /posts/:id, PUT /posts/:id | replace a post's form with a JSON body; --lang ru\|hy writes that language | siruk admin posts show 7 --json > post.json; edit it; siruk admin posts update 7 post.json --lang hy |
| `siruk admin posts delete` | admin | irreversible | admin | GET /posts/:id, DELETE /posts/:id | delete a post | siruk admin posts delete 5 |
| `siruk admin pages show` | admin | read | admin | GET /pages/:slug | one CMS page in one language | siruk admin pages show about-us --lang ru |
| `siruk admin pages set` | admin | draft | admin | GET /pages/:slug, PUT /pages/:slug | edit a CMS page: the keys sent are written in --lang (default en) | siruk admin pages set faqs '{"title": "…"}' --lang hy |
| `siruk admin report overview` | admin | read | developer, admin, analytics_manager | GET /analytics/overview, GET /analytics/overview/export | the overview report, or its xlsx with --export | siruk admin report overview --from 2026-10-01 --to 2026-10-31 |
| `siruk admin report sales` | admin | read | developer, admin, analytics_manager | GET /analytics/sales, GET /analytics/sales/export | the sales report, or its xlsx with --export | siruk admin report sales --from 2026-10-01 --to 2026-10-31 |
| `siruk admin report products` | admin | read | developer, admin, analytics_manager | GET /analytics/products, GET /analytics/products/export | the products report, or its xlsx with --export | siruk admin report products --from 2026-10-01 --to 2026-10-31 |
| `siruk admin report customers` | admin | read | developer, admin, analytics_manager | GET /analytics/customers, GET /analytics/customers/export | the customers report, or its xlsx with --export | siruk admin report customers --from 2026-10-01 --to 2026-10-31 |
| `siruk admin report promotions` | admin | read | developer, admin, analytics_manager | GET /analytics/promotions, GET /analytics/promotions/export | the promotions report, or its xlsx with --export | siruk admin report promotions --from 2026-10-01 --to 2026-10-31 |
| `siruk admin report margin` | admin | read | developer, admin, analytics_manager | GET /analytics/margin, GET /analytics/margin/export | the margin report, or its xlsx with --export | siruk admin report margin --from 2026-10-01 --to 2026-10-31 |
| `siruk admin report searches` | admin | read | developer, admin, analytics_manager | GET /analytics/searches, GET /analytics/searches/export | the searches report, or its xlsx with --export | siruk admin report searches --from 2026-10-01 --to 2026-10-31 |
| `siruk admin report search-queries` | admin | read | developer, admin, analytics_manager | GET /analytics/searches/queries | the paged top searches / searches with no results | siruk admin report search-queries --type zero --still-failing |
| `siruk admin stock stats` | admin | read | any admin role | GET /stock-statistics | stock statistics for a period | siruk admin stock stats --from 2026-10-01 |
| `siruk admin stock dashboard` | admin | read | any admin role | GET /stock/dashboard | out-of-stock and low-stock variants | siruk admin stock dashboard |
| `siruk admin stock list` | admin | read | any admin role | GET /stock | one page of products with their variants' stock | siruk admin stock list --status low_stock |
| `siruk admin search settings show` | admin | read | developer, admin | GET /search-settings | the search settings | siruk admin search settings show |
| `siruk admin search settings set` | admin | draft | developer, admin | GET /search-settings, PUT /search-settings | change search settings (only the keys sent) | siruk admin search settings set '{"engine": "local"}' |
| `siruk admin search synonyms list` | admin | read | developer, admin | GET /search-synonyms | list the search synonyms | siruk admin search synonyms list |
| `siruk admin search synonyms show` | admin | read | developer, admin | GET /search-synonyms/:id | one search synonym | siruk admin search synonyms show 3 |
| `siruk admin search synonyms create` | admin | draft | developer, admin | POST /search-synonyms | create a search synonym from a JSON body | siruk admin search synonyms create '{"terms": ["kitten", "kitty"]}' |
| `siruk admin search synonyms update` | admin | draft | developer, admin | GET /search-synonyms/:id, PUT /search-synonyms/:id | replace a search synonym's form with a JSON body | siruk admin search synonyms update 3 '{"terms": ["kitten", "kitty"]}' |
| `siruk admin search synonyms delete` | admin | irreversible | developer, admin | GET /search-synonyms/:id, DELETE /search-synonyms/:id | delete a search synonym | siruk admin search synonyms delete 3 |
| `siruk admin search rules list` | admin | read | developer, admin | GET /search-rules | list the search rules | siruk admin search rules list |
| `siruk admin search rules show` | admin | read | developer, admin | GET /search-rules/:id | one search rule | siruk admin search rules show 3 |
| `siruk admin search rules create` | admin | draft | developer, admin | POST /search-rules | create a search rule from a JSON body | siruk admin search rules create '{"query": "royal canin", "match_type": "contains", "pinned_product_ids": [12]}' |
| `siruk admin search rules update` | admin | draft | developer, admin | GET /search-rules/:id, PUT /search-rules/:id | replace a search rule's form with a JSON body | siruk admin search rules update 3 '{"query": "royal canin", "match_type": "contains", "pinned_product_ids": [12]}' |
| `siruk admin search rules delete` | admin | irreversible | developer, admin | GET /search-rules/:id, DELETE /search-rules/:id | delete a search rule | siruk admin search rules delete 3 |
| `siruk admin search playground` | admin | read | developer, admin | GET /search/playground | run a query and see why each result ranked | siruk admin search playground 'royal canin' --engine local |
| `siruk admin search index show` | admin | read | developer, admin | GET /search/index | the local search index status | siruk admin search index show |
| `siruk admin search index rebuild` | admin | draft | developer, admin | POST /search/index/rebuild | rebuild the local search index | siruk admin search index rebuild |
| `siruk admin algolia status` | admin | read | developer, admin | GET /algolia/status | Algolia: configured, auto-sync, last full sync | siruk admin algolia status |
| `siruk admin algolia sync` | admin | real-world | any admin role | POST /algolia/sync/:type/:id | push one record to Algolia (a dry run until --apply) | siruk admin algolia sync product 1234 |
| `siruk admin algolia sync-all` | admin | real-world | developer, admin | POST /algolia/sync-all | queue a full catalogue sync to Algolia (a dry run until --apply) | siruk admin algolia sync-all |
| `siruk admin categories list` | admin | read | developer, admin | GET /categories | list categories (one page, or --page all) | siruk admin categories list --search royal |
| `siruk admin categories show` | admin | read | developer, admin | GET /categories/:id | one category | siruk admin categories show 5 |
| `siruk admin categories create` | admin | draft | developer, admin | GET /categories, POST /categories | create a category from a JSON body (only on an explicit ask) | siruk admin categories create '{"name": "…", "slug": "…"}' |
| `siruk admin categories update` | admin | draft | developer, admin | GET /categories/:id, PUT /categories/:id | replace a category's form with a JSON body | siruk admin categories update 5 '{"name": "…", "slug": "…"}' |
| `siruk admin categories delete` | admin | irreversible | developer, admin | GET /categories/:id, DELETE /categories/:id | delete a category | siruk admin categories delete 5 |
| `siruk admin brands list` | admin | read | developer, admin | GET /brands | list brands (one page, or --page all) | siruk admin brands list --search royal |
| `siruk admin brands show` | admin | read | developer, admin | GET /brands/:id | one brand | siruk admin brands show 5 |
| `siruk admin brands create` | admin | draft | developer, admin | GET /brands, POST /brands | create a brand from a JSON body | siruk admin brands create '{"name": "…", "slug": "…"}' |
| `siruk admin brands update` | admin | draft | developer, admin | GET /brands/:id, PUT /brands/:id | replace a brand's form with a JSON body | siruk admin brands update 5 '{"name": "…", "slug": "…"}' |
| `siruk admin brands delete` | admin | irreversible | developer, admin | GET /brands/:id, DELETE /brands/:id | delete a brand | siruk admin brands delete 5 |
| `siruk admin attributes list` | admin | read | developer, admin | GET /attributes | list attributes (one page, or --page all) | siruk admin attributes list --search royal |
| `siruk admin attributes show` | admin | read | developer, admin | GET /attributes/:id | one attribute | siruk admin attributes show 5 |
| `siruk admin attributes create` | admin | draft | developer, admin | GET /attributes, POST /attributes | create a attribute from a JSON body (only on an explicit ask) | siruk admin attributes create '{"name": "…", "code": "…"}' |
| `siruk admin attributes update` | admin | draft | developer, admin | GET /attributes/:id, PUT /attributes/:id | replace a attribute's form with a JSON body | siruk admin attributes update 5 '{"name": "…", "code": "…"}' |
| `siruk admin attributes delete` | admin | irreversible | developer, admin | GET /attributes/:id, DELETE /attributes/:id | delete a attribute | siruk admin attributes delete 5 |
| `siruk admin attribute-values list` | admin | read | developer, admin | GET /attribute-values | list attribute-values (one page, or --page all) | siruk admin attribute-values list --search royal |
| `siruk admin attribute-values show` | admin | read | developer, admin | GET /attribute-values/:id | one attribute value | siruk admin attribute-values show 5 |
| `siruk admin attribute-values create` | admin | draft | developer, admin | GET /attribute-values, POST /attribute-values | create a attribute value from a JSON body (only on an explicit ask) | siruk admin attribute-values create '{"attribute_id": "…", "value": "…"}' |
| `siruk admin attribute-values update` | admin | draft | developer, admin | GET /attribute-values/:id, PUT /attribute-values/:id | replace a attribute value's form with a JSON body | siruk admin attribute-values update 5 '{"attribute_id": "…", "value": "…"}' |
| `siruk admin attribute-values delete` | admin | irreversible | developer, admin | GET /attribute-values/:id, DELETE /attribute-values/:id | delete a attribute value | siruk admin attribute-values delete 5 |
| `siruk admin product-types list` | admin | read | developer, admin | GET /attribute-families | list product-types (one page, or --page all) | siruk admin product-types list --search royal |
| `siruk admin product-types show` | admin | read | developer, admin | GET /attribute-families/:id | one product type | siruk admin product-types show 5 |
| `siruk admin product-types create` | admin | draft | developer, admin | GET /attribute-families, POST /attribute-families | create a product type from a JSON body | siruk admin product-types create '{"name": "…", "code": "…"}' |
| `siruk admin product-types update` | admin | draft | developer, admin | GET /attribute-families/:id, PUT /attribute-families/:id | replace a product type's form with a JSON body | siruk admin product-types update 5 '{"name": "…", "code": "…"}' |
| `siruk admin product-types delete` | admin | irreversible | developer, admin | GET /attribute-families/:id, DELETE /attribute-families/:id | delete a product type | siruk admin product-types delete 5 |
| `siruk admin price-types list` | admin | read | developer, admin | GET /price-types | list price-types (one page, or --page all) | siruk admin price-types list --search royal |
| `siruk admin price-types show` | admin | read | developer, admin | GET /price-types/:id | one price type | siruk admin price-types show 5 |
| `siruk admin price-types create` | admin | draft | developer, admin | GET /price-types, POST /price-types | create a price type from a JSON body | siruk admin price-types create '{"code": "…", "name": "…"}' |
| `siruk admin price-types update` | admin | draft | developer, admin | GET /price-types/:id, PUT /price-types/:id | replace a price type's form with a JSON body | siruk admin price-types update 5 '{"code": "…", "name": "…"}' |
| `siruk admin price-types delete` | admin | irreversible | developer, admin | GET /price-types/:id, DELETE /price-types/:id | delete a price type | siruk admin price-types delete 5 |
| `siruk admin reviews list` | admin | read | developer, admin | GET /product-reviews | list reviews (one page, or --page all) | siruk admin reviews list --search royal |
| `siruk admin reviews show` | admin | read | developer, admin | GET /product-reviews/:id | one review | siruk admin reviews show 5 |
| `siruk admin reviews update` | admin | draft | developer, admin | GET /product-reviews/:id, PUT /product-reviews/:id | replace a review's form with a JSON body | siruk admin reviews update 9 '{"is_approved": true, "reply": "…"}' |
| `siruk admin review-reports list` | admin | read | developer, admin | GET /product-review-reports | list review-reports (one page, or --page all) | siruk admin review-reports list --search royal |
| `siruk admin review-reports show` | admin | read | developer, admin | GET /product-review-reports/:id | one review report | siruk admin review-reports show 5 |
| `siruk admin review-reports update` | admin | draft | developer, admin | GET /product-review-reports/:id, PUT /product-review-reports/:id | replace a review report's form with a JSON body | siruk admin review-reports update 2 '{"is_resolved": true}' |
| `siruk admin variants list` | admin | read | admin | GET /product-variants | list variants (id, name, product), one page or --page all | siruk admin variants list --product 874 |
| `siruk admin variants archived` | admin | read | admin | GET /product-variants/archived | archived variants (newest 500), with the SKU each released | siruk admin variants archived --product 874 |
| `siruk admin variants archive` | admin | irreversible | admin | GET /products/:id, DELETE /product-variants/:id | archive a variant, or delete it for good when it has no history; refused for the last variant or reserved stock | siruk admin variants archive 4512 --product 874 |
| `siruk admin variants restore` | admin | draft | admin | GET /product-variants/archived, POST /product-variants/:id/restore | restore an archived variant | siruk admin variants restore 4512 |
| `siruk admin variants release-sku` | admin | draft | admin | GET /product-variants/archived, POST /product-variants/:id/release-sku | free the SKU of an archived variant for reuse | siruk admin variants release-sku 4512 |
| `siruk admin variants move-targets` | admin | read | admin | GET /product-variants/:id/move-targets | products a variant can move into, same brand first | siruk admin variants move-targets 4512 |
| `siruk admin variants move` | admin | irreversible | admin | GET /products/:id, GET /attribute-families/:id, POST /product-variants/:id/move | move a variant into another product; the dry run shows both products, rule 9a is checked first | siruk admin variants move 4512 --product 874 --to 880 --values '{"12": [38]}' |
| `siruk admin products merge-targets` | admin | read | admin | GET /products/:id/merge-targets | products a product can be merged into, same brand first | siruk admin products merge-targets 874 |
| `siruk admin products discontinue` | admin | irreversible | admin | GET /products/:id, POST /products/:id/discontinue | mark a product discontinued | siruk admin products discontinue 874 |
| `siruk admin products merge` | admin | irreversible | admin | GET /products/:id, GET /attribute-families/:id, POST /products/:id/merge | fold a mis-split product into another: every variant moves; the dry run shows both products, rule 9a is checked first | siruk admin products merge 874 --to 880 --variants '{"4512": {"attribute_values": {"12": [38]}}}' |
| `siruk admin suppliers list` | admin | read | admin | GET /suppliers | list suppliers | siruk admin suppliers list --active yes |
| `siruk admin suppliers show` | admin | read | admin | GET /suppliers/:id | one supplier | siruk admin suppliers show 5 |
| `siruk admin suppliers delete` | admin | irreversible | admin | GET /suppliers/:id, DELETE /suppliers/:id | delete a supplier | siruk admin suppliers delete 5 |
| `siruk admin suppliers create` | admin | draft | admin | GET /suppliers, POST /suppliers | create a supplier from a JSON body | siruk admin suppliers create '{"code": "hafo", "name": "hafo"}' |
| `siruk admin suppliers update` | admin | draft | admin | GET /suppliers/:id, PUT /suppliers/:id | update a supplier from a JSON body: code and name required, keys left out stay as they are | siruk admin suppliers update 3 '{"code": "hafo", "name": "hafo"}' |
| `siruk admin suppliers products` | admin | read | admin | GET /suppliers/:id/products | a supplier's product rows, 25 a page | siruk admin suppliers products 3 --search royal |
| `siruk admin suppliers add-product` | admin | draft | admin | GET /suppliers/:id, POST /suppliers/:id/products | link a variant to a supplier (product_variant_id and terms) | siruk admin suppliers add-product 3 '{"product_variant_id": 4512, "cost_price": 9250}' |
| `siruk admin suppliers stock-check` | admin | real-world | admin | GET /suppliers/:id, POST /suppliers/:id/stock-check | record that every stock level of a supplier was read now (unchanged levels stay fresh) | siruk admin suppliers stock-check 3 |
| `siruk admin suppliers ops-stock-sync` | admin | real-world | admin | GET /suppliers/:id, POST /suppliers/:id/ops-stock-sync | read a supplier's stock from Siruk Ops now | siruk admin suppliers ops-stock-sync 3 |
| `siruk admin supplier-products set` | admin | draft | admin | GET /suppliers/:id/products, PUT /supplier-products/:id | change a supplier product row (only the keys sent) | siruk admin supplier-products set 17 '{"is_active": false}' --supplier 3 |
| `siruk admin supplier-products rm` | admin | irreversible | admin | GET /suppliers/:id/products, DELETE /supplier-products/:id | remove a supplier product row (not one Siruk Ops keeps) | siruk admin supplier-products rm 17 --supplier 3 |
| `siruk admin supplier-products set-stock` | admin | draft | admin | GET /suppliers/:id/products, PUT /supplier-products/:id/stock | set a supplier row's stock quantity | siruk admin supplier-products set-stock 17 12 --supplier 3 |
| `siruk admin warehouses list` | admin | read | admin | GET /warehouses | the site's own warehouses (not the Ops locations) | siruk admin warehouses list |
| `siruk admin warehouses create` | admin | draft | admin | GET /warehouses, POST /warehouses | create a warehouse from a JSON body | siruk admin warehouses create '{"code": "main", "type": "own", "name": {"en": "Main", "hy": "", "ru": ""}, "lead_days": 0}' |
| `siruk admin warehouses update` | admin | draft | admin | GET /warehouses, PUT /warehouses/:id | update a warehouse from a JSON body: name and lead_days required, code and type never change | siruk admin warehouses update 2 '{"name": {"en": "Main"}, "lead_days": 1}' |
| `siruk admin ops purchase-orders` | admin | read | admin | GET /ops/purchase-orders | Ops purchase orders, newest first (at most 200) | siruk admin ops purchase-orders --status placed |
| `siruk admin ops purchase-order` | admin | read | admin | GET /ops/purchase-orders/:uuid | one Ops purchase order with its lines | siruk admin ops purchase-order 0b7e1c52-6f1c-4a90-b417-2a9000000000 |
| `siruk admin ops locations` | admin | read | admin | GET /ops/locations | Ops locations (warehouses, shop, supplier feeds) | siruk admin ops locations |
| `siruk admin ops location-stock` | admin | read | admin | GET /ops/locations/:uuid/stock | one Ops location's goods, 50 a page, in Ops units | siruk admin ops location-stock 2a900000-6f1c-4a90-b417-2a9000000000 --search royal |
| `siruk admin ops resend-order` | admin | real-world | developer, admin | GET /orders/:id, POST /ops/orders/:id/resend | send an order's failed Ops pushes to Siruk Ops again | siruk admin ops resend-order 5120 |
<!-- commands:end -->
