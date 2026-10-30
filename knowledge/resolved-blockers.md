# Resolved (and still standing) blockers

Newest first. "Lifted" = no longer a blocker; "Still" = still stops us.

## 2026-10-27

- **Fact — the invoices are the source of truth for what Siruk sells (PM via
  the user).** The PM's Excel lists were what she *ordered*; what the supplier
  didn't have was never sent. The first import (2026-08-12) was built from the
  Starter Inventory planning list, so it put never-received goods on the site.
  Audit of all 1644 variants against csv/products.csv, batches/* and the
  ArmSoft supplier receipts: 16 had nothing behind them, all Royal Canin
  (13 single 85 g pouches + Mother & Babycat 195 g). User-approved and done:
  products 1252 1254 1255 1259 1260 1261 1265 1266 1267 **discontinued**;
  variants 1850 1852 (product 1256), 1856 (1258) and 1868 (1262) set to stock 0
  (ledger reason correction). **Discontinued alone is not enough:** the
  product's own page (/dp/<variant id>) still opens from a direct link or
  Google and stays buyable (the cart doesn't check `is_discontinued`), so the
  12 variants of the 9 discontinued products were set to stock 0 as well → the
  page says out of stock, `orderable: false`. Hide = discontinue **and** stock
  0. To bring one back when it arrives: untick discontinued + receive the
  stock. Review sheet:
  `final/not-received-review-2026-10-27.xlsx`; scripts in
  `runs/2026-10-27-invoice-audit/`. Their ArmSoft goods (1366–1408 even codes
  outside the 7 box-fed ones, and 1409) were left untouched.
- **Lifted — `GET /admin/products/export` returned HTTP 500 on production
  around 12:00**, so the audit re-read every product one by one
  (`dump-products.py --refresh --fast`, ~40 min). By ~13:00 it answered 200
  again (`format=json`, 4 MB, ~19 s) — likely mid-deploy of efbf2d33. Retry
  it before falling back to the slow dump.

- **Fact — the catalogue export grew (siruk-web efbf2d33).** `GET
  /api/admin/products/export` now also returns `brand_id`, `category_ids`,
  `image_ids`, `image_urls` (originals) and `about_this_item_html`, and
  `format=json` gives the same records as JSON (`{"data": [...]}`). The whole
  catalogue (1041 products, 1644 variants) comes back in about 12 s. The
  CLAUDE.local.md note that it has "no media ids / image urls, category ids,
  brand id" predates this. Wrapped as `siruk export` / `--audit` and the MCP
  tools `export_catalogue`, `catalogue_audit`, `save_catalogue_export`.
- **Lifted — `uv run siruk` failed while an MCP server ran** ("failed to remove
  file … siruk-mcp.exe … used by another process"). `.mcp.json` started the
  server through the `siruk-mcp.exe` entry point, which every Claude window
  keeps open, and once a sync fails uv retries it on every `uv run`. The server
  now starts as `uv run --quiet python -m siruk.mcp_server` (python.exe is never
  replaced). Tested in a copy of the project: old launch → the CLI fails, new
  launch → the CLI re-installs and runs while the server keeps serving. Windows
  opened before 2026-10-27 15:30 still run the old launch until their MCP
  server restarts; meanwhile `uv run --no-sync siruk …` works.
- **Lifted — ArmSoft could not find the scale after the shop PC moved from
  Wi-Fi to the LAN cable.** The scale is at **192.168.0.99, port 33581**, on
  its own subnet, while the Ucom router (192.168.1.1) hands out 192.168.1.x.
  The PC's fixed IP had been set on its Wi-Fi adapter only, so the Ethernet
  adapter came up on DHCP. Fix: the shop PC's Ethernet (DESKTOP-L8T6UGG) now
  has two fixed addresses, **192.168.1.201** (gateway 192.168.1.1, DNS
  8.8.8.8 / 8.8.4.4, for internet) and **192.168.0.10** /24 (for the scale).
  Its old DHCP address .109 now belongs to another device, so don't reuse it.
  Check from the shop PC: `ping 192.168.0.99` and `Test-NetConnection
  192.168.0.99 -Port 33581`. Through AnyDesk, digits typed as keystrokes don't
  arrive; put the command on the clipboard and right-click to paste it into
  cmd.

## 2026-10-26

- **Lifted — hafo SKU matcher over-matched Trixie codes.** `hafo-lookup.py`
  `sku_matches` stripped *any* trailing letters off hafo's SKU for a `…Tx` form, so
  our Trixie 4123 (product 1416, 300 AMD) matched hafo's `04123IVS` (an Iv San
  Bernard 3 l shampoo whose listing has an empty `product_maker`, so the brand
  filter let it through). The old `check-hafo-prices.py --apply` would have set
  it to 54 550. `siruk/pricecheck.py` now rejects a Trixie match whose hafo SKU
  ends in letters other than Tx / Trx / TXN, and flags a hafo wholesale more
  than 3× off our cost.
  Fixed in the matcher too (same day): a Trixie-form match may only drop Tx /
  Trx / TXN. Against the cached hafo data (10 929 hafo SKUs × 3 288 of our code
  forms) it lost 22 matches and gained none, and kept 2 406. All 22 were other
  suppliers' goods (IVS perfumes, AQ heaters and sand, a Furminator `…F`, BP
  bird food, Ciao Churu `…IN`), and none of the Siruk variants they hit had that
  hafo price.
- **Lifted — `check-hafo-prices.py` and `bulk-create.py` on Windows.** Both
  executed `scripts/api.sh` directly, which Windows can't do. They now go
  through `siruk/` (Python client).

- **Lifted — Windows image prep on upload.** `upload-media.sh` flattens and
  downscales with macOS `sips`, which silently does nothing here. `siruk media
  upload` does the same with Pillow, so transparent PNGs and images over
  `max_pixels` are handled on this laptop.
- **Still — uv-managed Pythons.** `uv python install` fails here ("Missing
  expected target directory for Python minor version link" under
  `AppData\Roaming\uv\python`). The project pins `.python-version` 3.15, the
  system Python; `uv sync` works with it (textual, mcp 2.x, pillow, pydantic all
  have 3.15 wheels).
- **Fact — mcp 2.x.** `FastMCP` is now `mcp.server.mcpserver.MCPServer`. Only a
  `ToolError` message reaches the model; any other exception shows as "Error
  executing tool <name>" with its text hidden. `siruk/mcp_server.py` converts
  rule refusals and API errors to `ToolError`.

## 2026-10-23

- **Lifted — printing.** The shop printer (HP Color LaserJet MFP M183fw,
  10.0.1.17) is installed on this laptop as `NPI31B60B (HP Color LaserJet MFP
  M183fw)` — the user added it (Claude may not change Windows settings; Win+R →
  `rundll32 printui.dll,PrintUIEntry /il` opens the wizard). Claude prints
  through Excel COM (`PageSetup.PaperSize = 9` A4, `Orientation = 2` landscape,
  `PrintOut(..., printer name)`) and checks `Get-PrintJob`. Toner was low.
- **Scale-code lists for the counter**: `scripts/scale-code-sheets.py` →
  `final/armsoft-<date>/scale-codes-{cats,dogs}.xlsx` (one header per brand);
  rebuild and reprint after a price change.
- **Lifted — the barcode scanner on this laptop.** It is in serial mode (shows
  as "USB-SERIAL CH341", COM3/COM4), so it types nothing into Notepad or the
  chat. Claude can read it: open COM3 and COM4 at 9600 baud with PowerShell
  (`powershell.exe -EncodedCommand`, script in a temp file; the PowerShell tool's
  sandbox can't read `.siruk-cache/`) and print each line. A first read can
  carry a stray digit (44620… for 4620…): trust the value repeated.
- **Lesson — open items go stale.** "Gran Bonta only has the hafo
  placeholder" (from 2026-10-01) was already fixed (media 7540). Before
  reporting an open item to the user, re-check it live (fresh API GET / export).
- **Settled — API access.** No service account will be made (user). Use the
  dev@ login's token: the user logs in, Claude reads it from localStorage;
  Claude never types the password.
- **Settled — prescription medicine.** Inspector ear drops (762) stay on sale (user).
- **Lifted — the old RC box goods 1365–1407.** Never received, so ArmSoft let
  the user delete all 15 (ticked in the goods list; Claude ticks, user clicks
  Հեռացնել with a reason). Goods with no movement can be deleted.

- **Lifted — changing a good's main unit from piece to kg.** The ArmSoft
  update allows it (user). Done on the 5 Trixie treats 0403 0459 0516 0517
  0552. Recipe: `.claude/skills/armsoft-app/SKILL.md` → "Pack good → per-kg good".
- **Lifted — typing sale prices in ArmSoft.** Before, the price list was the
  user's job. The user showed the place: edit form (Ctrl+E) → tab **Գներ**,
  one "Նոր գներ (<unit>)" column per unit. Used on 1478, 1599, 1536 and the 5
  treats. Recipe and traps in the armsoft-app skill.
- **Lifted — deleting a barcode row and posting stock moves.** The permission
  check refused both until the user said "do it yourself" / "ok go" / "yes"
  in chat. Still: show the plan first, and only on the user's explicit yes.
- **Lifted — the 18 old duplicate goods.** They can't be deleted (Still: goods
  with any movement can't be deleted, "… ապրանքով գրանցված է գործողություն"),
  but their stock moved (issue order 0001 + receipt 0018) and their barcodes
  are gone, so they are harmless.
- **Lifted — Royal Canin stock sat on box goods** while the till sells pouches.
  Moved with issue order 0002 + receipt 0019 (see `armsoft-documents.md`).
- **Lifted — scripts that call `scripts/api.sh` from Python failed on
  Windows** (`WinError 193`). `scripts/dump-products.py` and
  `scripts/siruk_payload.py` now run it through `bash`. Any other script that
  does `subprocess.run([... "api.sh" ...])` needs the same `"bash"` first.
- **Lifted — no Siruk API token in a new session.** Open
  `https://api.siruk.am/admin/login` in the chrome-devtools window, the user
  logs in, then read `JSON.parse(localStorage.access_token).token` into
  `.siruk-token` (never type the password).
- **Lifted — `scale-export.py` used the 2026-10-02 export.** It now defaults to
  the newest `Scale/armsoft-export-*.xml`.
- **Still — `open_application` while ArmSoft runs starts another copy.**
  Bring it forward from the taskbar instead (three stray copies on 2026-10-23).
- **Still — ArmSoft's original receipts are read-only** on or before the lock
  date (09/09/26) and when created from an e-invoice; fix with a separate
  correction receipt.
- **Still — litter is never sold per kg** (user). 1441 keeps kg as its stock
  unit only because its stock and receipts are in kg.
