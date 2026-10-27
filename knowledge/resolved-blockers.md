# Resolved (and still standing) blockers

Newest first. "Lifted" = no longer a blocker; "Still" = still stops us.

## 2026-10-27

- **Fact — the catalogue export grew (siruk-web efbf2d33).** `GET
  /api/admin/products/export` now also returns `brand_id`, `category_ids`,
  `image_ids`, `image_urls` (originals) and `about_this_item_html`, and
  `format=json` gives the same records as JSON (`{"data": [...]}`). The whole
  catalogue (1041 products, 1644 variants) comes back in about 12 s. The
  CLAUDE.local.md note that it has "no media ids / image urls, category ids,
  brand id" predates this. Wrapped as `siruk export` / `--audit` and the MCP
  tools `export_catalogue`, `catalogue_audit`, `save_catalogue_export`.

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
