# Siruk Ops from the CLI — who owns what, sign-in, the write protocol, the never-list

Ops is the warehouse and till system (siruk-web `ops/docs/DESIGN.md` "Who owns
what", `ops/docs/GUIDE.md`). `siruk ops …` drives its back office with the
person's own key. Commands: `reference/siruk-cli.md`; recipes:
`reference/workflows.md`. The server's list of what a key reaches:
siruk-web `ops/docs/contracts/office-api-keys.md`.

## Who owns what

| Data | Owner | So the CLI… |
| --- | --- | --- |
| Products, variants, names, images, texts, categories | siruk | writes them with `siruk create` / `add-variant` / `set-variant` |
| **Every price** (website, store, glovo, …), compare-at, minimum, and a price type's own barcode / PLU | siruk | writes them with the catalogue commands and `siruk prices set` |
| **Stock** (every document: receipt, write-off, count, transfer, bag opening) | Ops | posts documents with `siruk ops docs …`, `po receive`, `einvoices post`, `open-bag` |
| **Cost** (weighted average of paid invoice prices) | Ops | never sets it; it reaches siruk's `cost_price`, read-only there |
| **Barcodes, PLU, fiscal name, ADG code**, reorder levels | Ops | `siruk ops goods set`, `goods barcode`, `goods plu` |
| Suppliers (Ops's), purchase orders, e-invoices, goods | Ops | `siruk ops suppliers`, `po`, `einvoices` |
| Web-order prep (accept, gifts, pack, ship), till services, shop promotions | Ops | `siruk ops orders …`, `services …`, `promotions …` |
| Staff, tills, shop settings | Ops | `siruk ops staff`, `tills`, `settings` (a section below) |
| Till sales, shifts, HDM receipts | Ops | read only (`ops sales`, `ops receipts`) |

Ops mirrors siruk's catalogue (`siruk ops catalog sync` pulls it now), so a
new product is created in siruk first. A new variant has **no stock**: on a
price-types server the CLI drops `initial_stock` with a warning, and stock
arrives through a receipt (`reference/workflows.md` recipe 1). `siruk stock
receive|write-off|set` refuse on a server where stock lives in Ops and point at
`siruk ops docs new receipt|write_off|count`.

**Codes never split stock.** Any code (main barcode, extra barcode, a price
type's barcode or PLU) resolves to one variant; the variant owns the stock and
the price type only sets the price. A type with no barcode uses the variant's
main one.

**No price at or below cost.** `siruk prices set` and every catalogue write
that sets a price (`create`, `add-variant`, `set-variant`, `bulk-create`)
refuse a price at or below the variant's cost, for any price type. The refusal
covers the prices the patch sets (every type when the patch changes the
cost); a below-cost row of another type that the patch leaves alone is only a
warning. The override is `--allow-below-cost`, on the user's say-so only.

## Units

- **Command line: AMD.** `--amount-amd 1300`, `"unit_cost_amd": 1300.5`. Whole
  dram or up to two decimals; a negative number or a third decimal is refused.
  The one exception is `suppliers adjust --amount-amd`, which is signed
  (`=-500` takes the balance down).
- **JSON from the API (`--json`, `ops api`): minor-unit strings.** `"130000"`
  is 1300 AMD. Never mix them: the CLI converts at the edge.
- **Quantities are base units**: whole grams, millilitres or pieces. A bare
  number is base units. A unit suffix is read against the good's own stock
  unit: `2.5kg`, `500g`, `1.5l`, `250ml`, `3pcs`. The wrong suffix for the
  good (`2kg` on a piece good) or a negative number is refused.
- A bag sold loose and its sealed pack are two goods; `siruk ops open-bag`
  moves the weight from one to the other.

## Sign in: one key, bound to one person

There is **no login command**. Ops answers a request from an `ops_…` API key
the **owner** made on the Ops "API keys" screen (Office → API keys), shown once.

1. **The owner makes the key** with a name, scopes and one **person**: an
   active staff member who is not an owner. The key acts as that person with
   the role they have now, so documents carry their name; a person who is
   deactivated or made owner closes the key.
2. **Scopes** (none implies another): `office:read` (the `GET`s the contract lists; it closes several, e.g. the HDM
   config, `/api-keys` and the connectors),
   `office:write` (documents, goods, purchasing, e-invoices, …),
   `office:manage` (services, shop promotions), `office:admin` (staff, tills,
   settings; give it last). A normal warehouse key is `office:read` +
   `office:write`. The person's role still applies on top: a warehouse person's
   key gets `403 Your role cannot do this` on a manager-only command.
3. **The user stores it**, from the clipboard, never from the chat:
   `pbpaste | uv run --no-sync siruk ops token set` (Windows PowerShell:
   `Get-Clipboard | uv run --no-sync siruk ops token set`). The command refuses
   a terminal and refuses arguments, checks the key with `GET /auth/me`, and
   writes `.ops-token` (gitignored). `SIRUK_OPS_TOKEN` in the environment wins
   over the file.
4. **`siruk ops doctor`** shows: the API URL and whether it is production, the
   token file and whether a token is set, `health`, the kind (`key` or `JWT`),
   the person's `role`, and for a key its name, its first characters and its
   scopes (for a JWT, when it expires). Exit 2 when anything is wrong.
   `siruk ops whoami` prints the person and the key's scopes.
5. **Revoking.** The owner revokes the key on the same screen (or deactivates
   the person); the next call answers 401 and `ops doctor` exits 2. The user
   then asks the owner for a new key and repeats step 3.

**An agent never types, prints, pastes, reads back or asks for a key, a token
or a password** — not in a command, a file, a test, a commit message or a
report. A missing, expired or refused key is a message to the user ("ask the
owner for a key"), then stop. A key can never set a password or PIN, edit its
own person, make keys or create a till.

## The write protocol

Every `siruk ops` write (and `prices set`) is **dry by default**:

1. Run the command bare. It prints the target, whether it is production, the
   tier, a one-line summary, each request it would send, the state it read
   (stock now and after, for a post) and a code: `re-run with --apply <code>`.
   Nothing is written.
2. **Show the user** that dry run in plain words: what, which goods, how many,
   which server.
3. On the user's yes **to that run**, repeat the same command with
   `--apply <code>`. It sends each request once, in order, stops at the first
   error and prints the answers. A different code (the plan or the target
   changed) writes nothing, prints the new dry run and exits 1: show it again.
4. **Exit 3 = unknown outcome.** The request may or may not have landed
   (timeout, 502, a broken answer). The message names a check, usually
   `siruk ops docs list` / `docs show` / `po show`. **Run it before anything
   else; repeat the write only when the check shows it did not happen.** Never
   retry blind.

Replays are safe by design: `docs new` twice on the same day returns the draft
already made, and exits 1 if that document is already posted (`--key` makes a
second one). `open-bag` folds the shown on-hand count into its request id, so
a run after a successful opening sees a lower count and **opens another bag**.
It exits 1 ("refused … `--tag` opens another") only when Ops answers with an
earlier opening and the count did not fall; `--tag` makes a deliberate repeat.

The raw `siruk ops api METHOD /path` is a last resort (tier `real-world`).
It refuses these write paths and names the typed command: reorder
accept, `einvoices pull`, `outbox resend`, `open-bag`, `docs new` / `docs post`,
web-order picking / pack / ship / damaged / gifts, a setting (`settings/<key>`),
`users`, `tills/<id>`, `catalog/auto-sync`, services and shop promotions. It also
refuses any `/users` body with a password or PIN key. Any other allowed path goes
through with tier `real-world` and **none of the typed command's warnings or
checks**, so never use it where a typed command exists. It follows the same
protocol, writes only under the areas the CLI knows (`siruk/ops/policy.py`) and
never to the paths in the never-list.

## The three tiers

| Tier | Meaning | Examples |
| --- | --- | --- |
| `draft` | editable or deletable afterwards | `docs new`, `docs lines`, `docs delete`, `goods set`, `po create`, `einvoices match`, `catalog sync` |
| `irreversible` | posts stock or money; a posted document never changes, only a new document corrects it | `docs post`, `einvoices post`, `po receive`, `open-bag`, `suppliers pay`, `goods-links link` |
| `real-world` | reaches siruk, a customer or a third party | `einvoices pull` (the tax service, with the owner's saved login), `outbox resend`, `orders ship`, `services add\|set`, `promotions add\|set`, `staff add\|set`, `tills set`, `settings set`, `catalog auto-sync`, `ops api` |

**"The owner's yes, each time"** (the `real-world` tier) means: the owner says
yes to *this* dry run, in this conversation, every time. A yes to an earlier
run, a yes to a whole plan, "go ahead with everything" or a standing
permission never counts, and the commands are never chained or put in a loop.
For every tier the user's yes to the shown dry run comes before `--apply`; a
`draft` can still be edited or deleted afterwards, an `irreversible` write
cannot. When unsure which tier, read the tier column of `siruk commands`.

Two facts about `ops reorder accept`: it is manager-only, and the CLI refuses
(exit 1) while the setting `reorder.autoPlace` is on, because accepting would
then place a real hafo order. The user decided (2026-11-16) not to close the
hafo / Telegram settings to keys on the server, so the CLI refusal plus the
owner's yes for every settings change is the guard.

## Staff, tills and settings

`siruk ops staff list|add|set`, `tills list|set`, `settings list|set` and
`catalog auto-sync` are reachable only by a key whose person is a manager.
The three `list` commands need `office:read` (the contract lists `GET /users`,
`/tills`, `/settings`). Each write needs `office:admin` **and** `office:read`,
because every write reads the current row first and scopes do not imply each
other. Every write is tier `real-world`: the owner's yes to this dry run, each
time. A person, till or setting is found by id, exact email or exact name (a
setting by its key) and must be exactly one; only what differs from the
current row is sent, and "nothing to change" is a refusal.

What a key can do:

- add a person (`staff add --name … --role …`), change a person's name, email,
  role or whether they are active (`--inactive` is the only way to remove
  someone; there is no delete);
- rename a till or switch it on or off (`tills set`);
- change one shop setting at a time (`settings set <key> <json>`; `null` goes
  back to the default where the setting allows it) and turn the scheduled
  catalogue pull on or off.

What a key cannot do. **The CLI refuses** (before any request):

- set or reset a password or PIN, in any body. A person added through a key has
  no way to sign in until a human sets one in the Ops app; moving a person to
  `cashier` removes their back-office login (the dry run says so);
- create a till or rotate a till's key, make or revoke API keys, or write to a
  sale, a shift, the HDM or a connector login (the never-list).

**Only the server refuses** (the CLI sends it and shows the error):

- create, edit or promote anyone at or above its own rank, so a manager's key
  makes and changes only cashiers and warehouse staff;
- edit its own person (`403 KEY_SELF_PROTECTED`).

**The warned settings keys.** These reach hafo, Telegram, Glovo, siruk or the
fiscal receipt. Their dry run carries a `!! REAL-WORLD SWITCH` block with the
before and after value; **nothing on the server stops them, the owner's yes is
the only lock**. Show the block in plain words and wait for that yes:

| Key | What it switches |
| --- | --- |
| `reorder.autoPlace` | an accepted restock list goes into hafo's basket by itself |
| `hafo.placeDryRun` | off, Ops can place real hafo orders |
| `hafo.placeMaxTotalAmd` | the largest hafo order; raising it lets bigger real orders through |
| `hafo.placeMaxLines` | the most lines in one hafo basket; same effect |
| `telegram.hafoConfirmers` | who may confirm a hafo basket in Telegram |
| `telegram.managerChatId` | the chat that hears about restock lists and confirms baskets |
| `telegram.ordersChatId` | the channel that hears about every new order |
| `telegram.notifyTillSales` | till sales are posted to the orders channel |
| `glovo.pushAssortment` | Glovo's customers see the prices and free stock Ops pushes |
| `glovo.sendOrderStatus` | "ready for pickup" goes to Glovo and sends the courier |
| `siruk.pushStock` | Ops pushes stock, cost and barcodes to the public website |
| `hafo.pushToSiruk` | Ops pushes hafo's stock to siruk's hafo warehouse |
| `einvoices.autoPull` | e-invoices are pulled on a schedule with the owner's saved login |
| `reorder.enabled` | the daily 15:30 restock list, announced in the manager chat |
| `fiscal.deliveryAdgCode` | the ADG code on the delivery line of the fiscal receipt |

A Telegram id is a string (`'"-100123"'`). `stock.lowStockDefault` is not
warned, but while `siruk.pushStock` is on it queues a full stock push to siruk.

## The `siruk-ops` MCP server

`siruk-ops` in `.mcp.json` (`python -m siruk.ops_mcp`, stdio) is every `siruk
ops` command through three tools, beside the `siruk` server that owns the
catalogue. It runs the CLI in-process with the one Ops key it holds, so the key's
person and role limit it exactly as on the command line. `argv` is the command
without the leading `ops`, e.g. `["goods", "show", "387957"]`. `ops_commands`
returns a list; `ops_read` and `ops_write` return `{exit_code, data, stderr}`
(exit codes as above; on 3 check before repeating).

| Tool | Does |
| --- | --- |
| `ops_commands(filter)` | the ops commands with api, tier, roles, help, example; `filter` matches name, endpoints and help |
| `ops_read(argv)` | runs a `read`-tier command only |
| `ops_write(argv, confirm_code)` | runs everything else |

`ops_write` is the same two-step as the CLI. Call it without `confirm_code`: it
is a dry run, and `data` holds the summary, the requests, the target, the tier
and the code. Show that to the user; on their yes to that run call it again with
the same `argv` and `confirm_code` set to the code. A confirm code is valid only
for the environment its dry run ran against; a changed plan or target is
refused (exit 1) and the new plan comes back.

Refused by the server: `ops token`, `ops api`, anything that is not an ops
command, an `argv` carrying `--apply` (the code goes only in `confirm_code`),
`-o/--out` (a downloaded file lands in the default `runs/<date>/` folder) and
`--no-pace`. Use the CLI for those, and never to get around a refusal. A new
project MCP server needs a one-time approval in Claude Code; the user approves
it, or adds `siruk-ops` to `enabledMcpjsonServers` in their own settings. An
agent never edits settings to do that.

## The never-list

Never from the CLI, an agent or a key — each is the owner or a person at the
till, in the Ops app:

| Never | Why |
| --- | --- |
| HDM (fiscal register) calls, its config and device | a live fiscal receipt is a legal record; the device holds a password and PIN |
| Till sales, refunds, shifts, the Z report | money and the cash drawer; only a person at a registered till |
| Sending to the scale | a live change to the shop's label scale (the PLU itself can be set: `ops goods plu`) |
| Connector logins (siruk, Glovo, hafo, the tax service): setting, reading or typing one | they are the owner's own logins; `einvoices pull` uses the saved one on the server and needs the owner's yes |
| API keys: making, revoking, reading | a key must never make or widen keys, its own included |
| Setting or resetting a password or PIN | it would give a key a normal session that reaches till sales and the HDM |
| Creating a till or rotating a till's key (`POST /tills`, `/tills/:id/rotate-key`) | it returns a registration secret |
| Placing a hafo order (`POST /purchase-orders/:id/place`, `/release`) | a real purchase; the owner's yes on the final basket (`/hafo-restock`) |
| Printing a web order's HDM receipt (`POST /web-orders/:id/print-hdm`) | prints a live fiscal receipt: the person does it in the Ops app after packing |
| Glovo's "ready for pickup" | it tells Glovo and sends the courier |
| Acknowledging a replacement invoice | owner only: it accepts that an invoice was replaced |

Everything outside the areas the CLI knows is refused by `siruk/ops/policy.py`
(its `WRITE_AREAS`: documents, goods, locations, open-bag, suppliers, purchase
orders, e-invoices, goods links, the reorder list, catalogue sync, the outbox,
web orders, services, shop promotions, users, tills, settings and auto-sync),
and a short `NEVER` list is refused by name even inside them (place or release,
acknowledge-replacement, print-hdm, `POST /tills`, rotate-key). The server enforces its own
table of routes (`office-api-keys.md`); the CLI's policy is the second lock
behind it. The admin side has its own never-list (`reference/siruk-cli.md`
"Admin commands").
