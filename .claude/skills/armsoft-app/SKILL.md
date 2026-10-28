---
name: armsoft-app
description: Drive the ArmSoft desktop program (AS Trade / ՀԾ-Առևտուր, database "Siruk") with computer use — export all goods and the price list, add barcodes per unit, read units and prices. Use whenever a Siruk ↔ ArmSoft sync needs fresh data from ArmSoft or a change typed into it; /armsoft-sync says WHAT to change, this skill says HOW.
---

# Driving ArmSoft (AS Trade 9.3.6)

ArmSoft is a Windows desktop app. Control it with the `mcp__computer-use__*`
tools (load them all: ToolSearch `computer-use`). Learned 2026-10-23 — improve
this file every time something new is found (memory: skills-for-recurring-work).

## Before anything

- `request_access` with `["ՀԾ-Առևտուր", "AS Trade"]` (the Armenian name uses
  **և**, not ե‌ւ — the resolver refuses "Առեւտուր").
- **Never call `open_application`** when ArmSoft is already running: it starts
  a second instance on the login screen. If that happens, press its
  "Դադարեցնել" and close the empty window (title without "Siruk -").
- A black block in screenshots is a window of an app you have no grant for.
  Find it with PowerShell `EnumWindows` (title + rect). On 2026-10-23 it was an
  elevated "Administrator: Install Office" cmd window: elevated windows cannot
  be moved by us; granting "Command Prompt" (click tier, view only) unmasked it.
- Never type passwords; the user is signed in already.

## Hard rules for every good you touch

The full list is in `/armsoft-sync` → "Hard rules". In the edit form that means:
`Name` under 50 characters (HDM limit), the ԱԱՀ (VAT) box **unticked**, and
for a good sold per kg: main unit 303, alt unit 003 with the recalculation
coefficient = bag kg, Քաշային ticked. Fix any of these you see while you are
in a good's form anyway; a price change still goes to the user.

## Layout

Main window title "Siruk - ՀԾ-Առևտուր 9.3.6". Ribbon tabs: Գլխավոր (main:
Ավելացնել add, Խմբագրել edit, Հեռացնել delete, Փնտրել find), Արտահանել
(export). Left "Ուղղորդիչ" navigator has a search box — type e.g. `գներ`
(prices) or `գծիկավոր` (barcodes) to find a list, double-click to open it.
Lists open as tabs. The goods list is "Ապրանքներ և ծառայություններ".

**Selection**: Ctrl+A in a list *toggles* select-all (status bar "Նշված է N
տող"). Clicking the header checkbox toggles a "show only ticked rows" filter
instead — avoid it. Clear the selection (Ctrl+A again) before right-click
editing, or the edit form walks through every ticked row ("1/2").

Context menu on a good (right-click): Խմբագրել (Ctrl+E), Գներ (prices),
Չափման միավորներ (units), **Գծիկավոր կոդեր** (barcodes), Փնտրել գծ. կոդով (F2).

## Export (read ArmSoft's state)

- **All goods → XML**: goods list, click a row, Ctrl+A (all 1574 ticked),
  ribbon Արտահանել → "Արտահանել XML", file name field: Ctrl+A, type the full
  path (`C:\Users\Eric\Downloads\armsoft-goods-<date>.xml`), Enter, wait ~12 s.
  Without a selection it exports only the focused row. Copy the file to
  `Scale/armsoft-export-<date>.xml`.
- **Prices → Excel**: navigator `գներ` → Վաճառքներ → Գներ, set the start date
  to 01/01/01 (click the date, Ctrl+A, type `010101`, Tab), Կատարել. Then
  ribbon "Արտահանել Excel" ▾ → "Արտահանել Excel (առանց ձևավորման)", save as
  `armsoft-prices-<date>.xlsx`. Header row has Ամսաթիվ, Կոդ, Գնի տեսակ
  (01 = sale), Միավոր, Գին.
- `scripts/armsoft-gaps.py <goods.xml> <prices.xlsx> --out x.xlsx` lists every
  good + unit with no barcode or no sale price.

## Add a barcode

Open any good's barcodes tab (right-click → Գծիկավոր կոդեր). Ribbon
Ավելացնել opens the "Գծիկավոր կոդ" form with three fields, and the **good code
field is editable**, so one tab adds barcodes to any good:

| field | coords (1456×819 frame) | input |
|---|---|---|
| Ապրանք կամ ծառայություն | (690, 363) | Ctrl+A, the 4-digit code, Tab, wait 0.8 s |
| Չափման միավոր | (focused) | `001` / `003` / `303`, Tab |
| Գծիկավոր կոդ | (focused) | the barcode, Tab |
| Կատարել (save) | (665, 442) | wait 1.5 s |

Adding the default unit's barcode also fills the good's main `BarCode`.
Generate the action list from a CSV with a script — never type a barcode by
hand (on 2026-10-23 a hand-typed placeholder nearly went in). 12 goods per
`computer_batch` worked without a miss; verify with a fresh export at the end.

The global list (navigator `գծիկավոր` → Գնումներ → Գծիկավոր կոդեր) shows every
barcode; ribbon Փնտրել opens a filter box. **Don't press Enter in that box** —
it also opens the edit form of the focused row. An existing barcode's good
code and unit are read-only: a move is delete + add.

## The edit form (Ctrl+E on a selected good)

Filter the goods list first: ribbon Փնտրել opens a box at (400, 198) — click
it, **Ctrl+A, type the code** (triple-click there garbled the text once).
Click the row (600, 251), Ctrl+E. The form opens at a random spot: maximize it
once (its □ button) and it stays maximized, then these work:

| what | coords |
|---|---|
| Name / Long name | (500, 105) / (500, 129): click, Ctrl+A, type (Armenian pastes fine; a too-early click after opening drops the paste — wait 3 s) |
| tabs Ընդհանուր / Գծիկավոր կոդեր / Գներ | (55, 200) / (160, 200) / (242, 202) |
| main unit / alt unit / recalculation coefficient | (240, 255) / (240, 280) / (310, 304) |
| barcodes tab: first row / its red X (remove row) | (333, 273) / (52, 232) |
| save (disk icon, = Ctrl+S) / close | (40, 15) / (1433, 13) → "Այո" to close without saving |

**The find box matches every column, not just the code** (2026-10-23):
typing `1507` also listed 0720, whose old name held `00315071`, and the
first row was opened instead of 1507. So: after filtering, click the first
row, **Ctrl+End** (the target is almost always the highest code), Ctrl+E,
and **read the Կոդ field in the form before saving**. Fast, safe rhythm for
a batch of edits — one `computer_batch` per good: [Ctrl+S + close the
*previous* good (already checked)] → filter → Ctrl+End → Ctrl+E → wait 3 s →
click Name, wait 1 s, Ctrl+A, type → zoom (0,0,1456,140). Look at the zoom:
right code and text → next batch starts with its save; wrong code → close
with "Այո" (discard). Waits of 1.5 s around save/close are enough. The
clipboard paste into Name sometimes doesn't land (name still selected in the
zoom) — retype it. Before Ctrl+E, untick any rows (Ctrl+A toggles) or the
form walks through all ticked rows.

An asterisk in the title = unsaved. After closing, move the mouse away from
(1433, 13) — that is also the main window's close button. **Escape closes a
document form by itself**, so never press Escape and then click (1433, 13):
the click lands on the main window and asks "Պատուհանը համակարգից դուրս
գա՞լ" (exit the program). Read every dialog's title before answering: the
form's own close asks "Հաստատեք պատուհանի փակելը" under the form's name
(Այո = close without saving); the exit prompt is titled "Աշխատանքի ավարտ"
(answer Ոչ). Exiting by mistake happened twice on 2026-10-23; after a restart,
press Կատարել on the login screen and close the news popup (Փակել).

**Move a barcode to another good** (one barcode can sit on one good only —
ArmSoft refuses a duplicate with "…արդեն կցված է"): open the OLD good → Barcodes
tab → select the row → red X → save. Then add it on the new good with the
barcode dialog. An empty barcode cell is not allowed. Removing a row this way
in the edit form is fine; the Delete button in the global barcode list was
refused by the permission check.

**Sale prices in the edit form** (user showed it, 2026-10-23): tab **Գներ**
(242, 202) has one row per price type (Վաճառքի գին) and one "Նոր գներ
(<unit>)" column per unit — the pack and the 1 kg / single unit side by side.
Click the cell, type, Enter, next cell, Ctrl+S. After the save the cells
read 0.00 again: that is normal, the price is saved. "Լրաց. գործող գները"
(87, 231) fills the cells with the current prices — use it to verify.
A click into a cell that already holds a value can append to it (200 became
2,000): End, Backspace ×12, retype, then check the zoom before saving.
The first click on the row edits the column that had focus before, not the
one clicked (1478: the kg price landed in the bag column) — click the cell
twice, zoom to see which cell is green, then type.

**A single unit next to a pack** (Treat Sticks 1599/1536, 2026-10-23): keep
the stock and receipts right by making the PACK the main unit and the single
the alt unit. General tab: main unit → 004 Փաթեթ (picker popup, double-click
the row at (262, 402)), alt unit 001 Հատ, coefficient 0.1; the form then shows
"1 փաթեթ = 10 հատ / 1 հատ = 0.1 փաթեթ". The old 001 quantities (packs) become
004 quantities unchanged. A barcode row on 001 stays on 001, so the pack EAN
must move to 004 (the row delete is the user's click; then type the EAN in
the main barcode field, which adds the 004 row).

**Piece good with a pack unit for receiving** (Trixie Nappy pads 0197 0132 0129,
2026-10-27): main unit stays **001 Հատ** (one piece), alt unit 004 Փաթեթ with
the coefficient = pieces per pack ("1 փաթեթ = 8 հատ"). Save. Then **Barcodes
tab: the Unit cell of an existing row is editable here** (click it twice, a
dropdown shows, Ctrl+A, `004`, Tab), so the pack EAN moves 001 → 004 without a
delete. Save, then type the internal code into the General tab's main barcode
field — it adds the 001 row. Zoom on the grid before each save: once the
barcode cell came out as "1" after the unit edit (0132); retyping the EAN in
that cell fixed it before saving.

After a fresh start the news popup ignores clicks for ~30 s while it loads;
wait, then press Փակել. The goods list opens with a filter dialog — press
Կատարել (667, 502) with it empty.

**Pack good → per-kg good** (Trixie treats 0403 0459 0516 0517 0552,
2026-10-23, after the ArmSoft update unlocked it): use **001 Հատ for the pack,
never 003 Պարկ** (user). General tab: main unit field Ctrl+A, `303`, Tab — the
alt unit becomes 001 by itself; coefficient = pack kg ("1 հատ = 1.3 կգ").
Save. The pack EAN row on 001 stays as it is (don't delete it). Then type the
PLU into the main barcode field (adds the 303 row), tick Քաշային, save; Գներ:
kg price + pack price. Stock already counted in kg stays right; stock counted
in packs would need a correction first. Changing the alt unit leaves the old
one behind (0403 kept a stray 003): right-click the good → Չափման միավորներ,
select the row, ribbon Հեռացնել, Այո.

**Saving the edit form**: Ctrl+S right after typing into a field often does
nothing (the title keeps its `*`). Click an empty part of the form, then
Ctrl+S — or the disk icon (40, 15) — and check the `*` is gone before moving on.

**Never call open_application while ArmSoft is running** — it starts another
copy (three extra copies piled up on 2026-10-23). Bring it forward from the
taskbar icon (Explorer is granted at click tier) and pick the "Siruk -" preview.

**Units.** Right-click → Չափման միավորներ lists a good's units; ribbon
Ավելացնել adds one (unit + "coefficient to the main unit": 1 kg of a 10 kg bag
= 0.1). Ctrl+E (double-click) on a unit row edits its coefficient; ribbon
Հեռացնել + "Այո" removes a unit row (worked for an unused unit).

**Switching the main unit** (done on 1478, 2026-10-23, bag 001 → kg 303):
1. The main unit field is locked until **every other unit of the good is ×1**
   (user tip: "put the recalculation coefficient to 1"; a stray ×26 unit kept
   it locked). Set them to 1 in the units list, then open the edit form.
2. The new main unit must **not** already exist on the good (remove it first),
   or saving fails with "… արդեն գոյություն ունի".
3. Edit form: main unit → 303, save. Then alt unit 003 + coefficient 10
   ("1 պարկ = 10 կգ"), tick Քաշային (weight good), main barcode field = the
   5-digit PLU, Barcodes tab: move the bag EAN's row to 003. **The main barcode
   field adds its own row for the main unit** — don't also add one in the grid
   (duplicate error). Save.
4. Units list: put the old unit back to its real size (001 = ×10 for a 10 kg
   bag), remove strays.
Target shape = good 0001: Unit 303, AltUnit 003 (Coef = bag kg), IsWeight,
BarCode = PLU, MTBarCodes 003 = bag EAN, 303 = PLU.

A good keeps its unit as հատ (001) even when it is a box: 1 հատ = 1 box
(user, 2026-10-23, RC 1466–1472).

## e-invoicing and warehouse receipts (learned 2026-10-23)

- **Pull new invoices from the tax service first** (PM, 2026-10-27: they do
  not arrive by themselves). Home tab → e-invoicing → middle column
  "Ստացված հաշիվների ներմուծում" (double-click) → Ներմուծել ▾ → **1
  e-invoicing (ուղիղ կապ)** (double-click the row), Դուրս գրման
  ժամանակահատված = the period (both dates required), tick **Հարկային
  հաշիվներ**, Կատարել (~15 s). The report lists every invoice of the
  period: "Այո" = imported now, "Ոչ … փաստաթուղթը գոյություն ունի" = already
  in. Then read them in "Ստացված հաշիվների մատյան" (same middle column; set
  the period from 01/01/25) — it holds invoices the online list misses
  (Ucom, Toz-Master, the shop-bag supplier). Double-click → tab
  Անվանացուցակ for the lines.

- **e-invoicing** (home tile, or navigator search `հարկային`): "Ստացված
  հարկային հաշիվներ" lists the supplier tax invoices straight from the tax
  service (set both start dates to 01/01/25, Կատարել; slow, and the link
  sometimes needs a second double-click). The list shows totals only; **double-click an invoice → tab Անվանացուցակ** (314, 154) for its lines, footer = total quantity, Escape closes it (2026-10-26). If the navigator link does nothing, use the home tab (Գլխավոր էջ) → e-invoicing → "Ստացված հարկային հաշիվներ" (double-click), then clear Սերիա և համար to list all.
  Type "Ծառայություններ" rows are services, not goods. "Ստացված հաշիվների
  մատյան" (the local journal) was empty.
- **The goods arrive as warehouse receipts** ("Պահեստի մուտքի օրդեր"),
  listed under e-invoicing → "Գնման փաստաթղթեր" (start date 01/01/25). Most
  carry the invoice number; ArmSoft-made ones have the e-invoice as "Հիմք
  փաստաթուղթ". Export them all: tick all (Ctrl+A) → Արտահանել → XML; each
  `MTIncome` has `Specification/MTIncomeSpecificationRow` (Code, Unit,
  Quantity, Price, Amount). Copy to `Scale/armsoft-receipts-<date>.xml`.
- **Read-only receipts**: anything dated on or before the lock date in the
  status bar ("Հավաստիության ա/թ", 09/09/26 now), and every receipt created
  from an e-invoice (its lines are locked to the invoice). Fix those with a
  separate correction receipt, never by editing.
- **State column**: "Սևագիր" (draft, orange bar) does not move stock;
  "Գրանցված" does. The exported XML has `<IsDraft>`.
- **Making a receipt — import, don't type.** Build an `MTIncome` XML in the
  export's format (new `ISN` GUID, next free `DocumentNumber`, `IsDraft`
  true, `Storage` 01, `VAT` false per row, each row's `UnitList` copied from
  the goods export) and load it with navigator `Ներմուծել` → "Ներմուծել
  տվյալներ" → Բացել → tick the row → Ներմուծել ("Ներմուծումը բարեհաջող
  ավարտված է"). Then open it, check the lines and totals, and **Ctrl+S
  records the draft** (status bar turns "Գրանցված"). Typing lines in the grid
  went wrong: Tab after the code leaves the grid, Ctrl+A in a cell selects
  text elsewhere, and new rows scroll the grid so fixed coordinates drift.
  Example: `final/armsoft-2026-10-23/stock-fix-receipt-0017.xml`.
- **Editing a posted receipt**: Գլխավոր ribbon → "Սևագիր" (Ctrl+Shift+D)
  turns it back into a draft (its stock leaves until reposted), edit, Ctrl+S.
  In the grid, click a cell **then press ↓ before typing**: a click puts the
  cursor inside the number ("0" became 45,110.11); after ↓ a typed value
  replaces the cell. Type value + ↓ row by row.
- **A correction for a bag booked as 1 kg carries price 0**: the 1 kg line
  already holds the bag price, so cost/kg comes out right. Exception: if part
  of that "1 kg" was sold before the fix, the sale took the whole bag cost and
  the rest lands at 0 cost (1449 1451 1456 1455 on 2026-10-23) — those need
  the per-kg cost on their line.
- **Issue order** (navigator `ելքի` → Պահեստի ելքի օրդեր): the code box
  "Գծիկավոր կոդ (F2)" + F8 adds a line with quantity 1 per code; the cost is
  filled on save. Moving stock between two goods = issue order on the old
  code + receipt on the new one at the issue's cost.
- **Goods with any movement cannot be deleted** ("… ապրանքով գրանցված է
  գործողություն"). A duplicate is retired by moving its stock and removing
  its barcode; it stays in the list.
- The "Զեղչ %" column in a receipt only compares the price with the good's
  last purchase price; a big minus on a per-kg line means the last receipt
  booked a bag as 1 kg.
- The lower panel of a receipt ("Ընթացիկ տողի վահանակ") shows the good's
  current stock ("Մնացորդ"), a quick check after posting.

## One good's history (learned 2026-10-26)

Navigator `Ապրանքներ և ծառայություններ` → Գնումներ → **Ապրանքների
գործողությունների մատյան**: set the start date to 01/01/01, type the good code
in Ապրանք, Tab, Կատարել. One row per movement: date, document number, type
(Պահեստի մուտք receipt, Վաճառք (Կտրոն) till check), quantity (drag the bottom
scrollbar right; outgoing shows red and negative), comment. Double-click a row
to open the document read-only: maximize it to see the lines (unit 003 = a
whole bag, 303 + PLU = loose kg). Escape closes it without saving.

## What needs the user

- **Prices**: typing a price (edit form → Գներ, or the price list) was refused
  by the permission check ("real-world transactions") on 2026-10-23. When the
  user asks for the prices by code, unit and amount in their own message, it
  went through (1442, 2026-10-26). Without that, hand over code, unit and price.
- **"The desktop shell is frontmost" mid-form** (2026-10-28): the taskbar took focus and every click/key was refused; plain `SetForegroundWindow` returned False. What worked: PowerShell, find the AS Trade window whose title contains "(" (the edit form), `AttachThreadInput` to the foreground thread, `ShowWindow` 6 then 9, `BringWindowToTop`, `SetForegroundWindow`. Unsaved edits in the form survive it.
- **A barcode ArmSoft refuses as "already attached to <code>"**: stop. Don't
  move it. The code read off a tag may belong to a sibling good (1533 got
  1534's 4627090332307 on 2026-10-26). Check the other good, and Siruk, first.
- **Deleting** a good, a unit or a row in the global lists — refused. Hand over
  the exact list.
- Switching the main unit of a good with stock (e.g. 001 bag → 303 kg) changes
  what the existing quantities mean — ask first.
- Stock moves, invoices, receipts — accounting documents: only on the user's
  explicit go-ahead for that fix (2026-10-23 the user asked for the bag-stock
  correction receipt). Show the plan (goods, kg, price) first; deleting a
  document stays with the user.
