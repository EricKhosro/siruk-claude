# Resolved (and still standing) blockers

Newest first. "Lifted" = no longer a blocker; "Still" = still stops us.

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
