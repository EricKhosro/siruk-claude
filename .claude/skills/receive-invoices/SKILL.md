---
name: receive-invoices
description: The shop computer's one job — pull new supplier e-invoices into ArmSoft and, when every line is a good Siruk already sells, post the warehouse receipt so the goods can be sold. An invoice with even one product Siruk doesn't have is NOT received; it is left for the office to import first. Use when the seller asks to check for new invoices, receive a delivery, or "add the invoice to the warehouse".
---

# Receive new invoices (seller, shop computer)

Who runs it: the seller in the shop, on the shop computer (`shop/README.md`).
What it does: new supplier e-invoice → ArmSoft warehouse receipt, **restocks
only**. It never creates a product, a good or a price, and it never changes
Siruk. Anything it can't settle by the rules below goes to the office as a
written note — the seller is not asked to decide it.

Speak to the seller in their language, short and plain. No codes, XML or
rule numbers in what you tell them unless they ask.

How to drive ArmSoft (pulling invoices, reading lines, importing a receipt
XML, posting): `/armsoft-app` → "e-invoicing and warehouse receipts". Read it
first. Unit and cost traps: `knowledge/goods-setups.md`,
`knowledge/costs-and-rivals.md`. What was received before:
`knowledge/armsoft-documents.md`.

## 0. Before anything

- Git first: `shop/CLAUDE.local.md` → "Git on this computer" (main, pull,
  a new `shop/<date>-receive` branch). A failed pull → stop, the office.
- `account_status` (siruk MCP) → 200. A 401 means the Siruk login expired:
  tell the seller someone from the office has to log in again; stop.
- ArmSoft is open and signed in (database "Siruk"). Don't open a second copy
  (`/armsoft-app` → "Before anything").

## 1. Pull and list the new invoices

1. Pull from the tax service: e-invoicing → "Ստացված հաշիվների ներմուծում",
   source 1 e-invoicing (ուղիղ կապ), period = the last pull date in
   `knowledge/armsoft-documents.md` (a few days earlier, to be safe) to today,
   **Հարկային հաշիվներ** ticked.
2. An invoice is **new** when no receipt cites it: export "Գնման փաստաթղթեր"
   (from 01/01/25) and check each receipt's `InvoiceNumber` and its "Հիմք
   փաստաթուղթ"; also check the receipts table in
   `knowledge/armsoft-documents.md`. Look for a receipt that **replaces** the
   invoice too (the invoice's Մեկնաբանություն says "<number>հաշվի փոխարեն" —
   A6840667000 replaced A3778015660, already received as 0009).
   A receipt already there → never a second one (receipt 0016 was exactly
   that mistake).
3. Not stock → no receipt, just note it: services (Ucom, Toz-Master, the
   ArmSoft vendor), shop supplies (carrier bags), equipment (printer, scanner,
   till paper). Lines of type "Ծառայություններ" are services.

Nothing new → tell the seller "no new invoices", record the pull date (step
6) and finish.

## 2. Match every line

Per new invoice open the lines (tab Անվանացուցակ / Ապրանքացանկ). Every line
must land on **one ArmSoft good and one live Siruk variant**:

1. **ArmSoft good**: by the line's barcode, else the supplier's article code
   or name (identified through hafo the way receipt 0024's lines were) against
   a fresh goods export, with the cost agreeing with the good's last receipt
   price.
2. **Siruk variant**: the variant whose `accounting_code` is that ArmSoft code
   (`export_catalogue` / `find_products`), not discontinued. A bag and its
   "1 kg" variant share one code — that is one good, fine.
3. The line's **unit** fits the good: bags booked the way
   `knowledge/goods-setups.md` says (per-kg goods: 303 × bag kg at cost ÷ kg,
   or 003 × 1 at the bag cost when cost ÷ kg isn't 2 decimals — receipt
   0023); pack + single goods on their pack unit; litter by the bag.

A line is **unknown** when any of that fails: no ArmSoft good, no Siruk
variant, two candidates, an identity that only fits by guessing, or a unit
you can't place. Never guess a match; two candidates is unknown.

## 3. Decide per invoice

- **Every line matched → restock.** Go to step 4.
- **Any line unknown → don't receive the invoice at all.** No partial
  receipt, no "the known lines now, the rest later". Tell the seller: these
  goods can't go on sale yet, the office has to add the new products first.
  Write it down for the office (step 6) with the invoice number, supplier,
  date, total and every unknown line (name, quantity, price, barcode if
  printed). The office imports them (`/invoice-intake` → `/add-products`),
  then the next run receives the whole invoice.

Stop the invoice too (same note, reason given) when, on a matched line:

- the invoice cost (incl. VAT) is **at or above** the Siruk sale price —
  wrong match or a price the office must fix first;
- the cost moved more than 15 % from the good's last receipt price — maybe a
  different size or a case vs. a piece;
- the Siruk variant is discontinued.

## 4. Build and check the receipt

- Build the `MTIncome` XML exactly like the newest example in
  `final/armsoft-<date>/…-receipt-<no>.xml`: new `ISN` GUID, the next free
  `DocumentNumber`, `IsDraft` true, `Storage` 01, the supplier's
  `PartnerCode`, `InvoiceNumber` / `InvoiceDate`, `PartnerAmount` = the
  invoice total incl. VAT, each row's `UnitList` copied from the goods
  export. Price at most 2 decimals. Save it as
  `final/armsoft-<today>/<supplier>-<invoice>-receipt-<no>.xml`.
- Sum of the rows = the invoice total (a few drams of rounding at most —
  say so if any).
- Import it as a draft (`/armsoft-app` → "Making a receipt — import, don't
  type"), open it, and show the seller: supplier, invoice number, each line
  (name, quantity, price) and the total. **Post (Ctrl+S) only on the
  seller's yes.** A no → leave the draft and note it for the office.
- After posting, check a couple of lines' stock (lower panel "Մնացորդ").

## 5. Siruk: nothing

Siruk's stock is a placeholder (10 on every variant, on purpose); real stock
lives in ArmSoft only. A restock changes nothing on api.siruk.am — no stock
call, no price change. The goods are on sale the moment the receipt is posted.

## 6. Write it down (then commit, push and open the pull request per `shop/CLAUDE.local.md`)

- `knowledge/armsoft-documents.md`: the pull (date, period, how many
  invoices, which new) under "Reading the tax-invoice list", and a row per
  receipt in the documents table (newest first): number, date, supplier +
  invoice, total, the goods, "posted by Claude, seller yes".
- `state/open-items.csv`: one row per stopped invoice — what stopped it,
  every unknown line, "office: import first" (or what has to be fixed).
- The receipt XML under `final/armsoft-<today>/`.

Finish with a two-line summary for the seller: what was received and is on
sale, what is waiting for the office.

## Never, from this command

- Create or edit a product, variant, brand, price or translation on Siruk;
  create a good or set a price in ArmSoft.
- Edit or delete a posted receipt or any other document, or receive an
  invoice twice.
- Receive part of an invoice.
- Solve a CAPTCHA, type a password, or log in anywhere — a login prompt goes
  to the office.
- Anything the seller asks beyond receiving invoices: "that has to be done
  from the office".
