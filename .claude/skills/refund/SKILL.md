---
name: refund
description: The shop computer's second job — refund a till sale in ArmSoft and print the HDM return slip, for a customer bringing goods back or a sale rung up wrong (cash instead of card, wrong goods or quantity). Makes one Վերադարձ (Կտրոն) against the original HDM receipt, on the seller's yes. Use when the seller asks to refund, return, cancel or "undo" a receipt or a sale.
---

# Refund a till sale (seller, shop computer)

Who runs it: the seller, on the shop computer — the cash register (ՀԴՄ) is
attached there, and **the return slip only prints there** (ՀԴՄ / F3 from the
office did nothing, 2026-11-02). What it does: one return document
(Վերադարձ (Կտրոն)) against the original sale, printed on the register. It
never changes Siruk, a good, a price, or another document.

Speak to the seller in their language, short and plain. No codes or rule
numbers unless they ask.

How to drive ArmSoft: `/armsoft-app` → "Before anything" and "Refund a wrong
HDM receipt" (clicks, the Data Matrix prompt, the restart when the journal
doesn't show the slip number). Read them first.

## The stock answer (checked 2026-11-03)

**The return puts the goods back in the warehouse by itself. Never add a
warehouse receipt (Պահեստի մուտք) for a refund** — it would count them twice.
Checked on the 02/11 case: sale 124 (cash, wrong) and sale 125 (card, right)
each took 11 Felix pouches, return 126 against 124 gave them back; the
movement journal of 1479 / 1483 / 1484 shows +26 receipt, the October sales,
−2/−4/−5 twice and +2/+4/+5 once, leaving 20 / 20 / 17 = what was really sold.
Siruk: nothing (its stock is a placeholder, 10 on every variant).

So what happens to the goods is decided by why they came back:

- **Sale rung up wrong** (wrong payment type, wrong good, wrong quantity, a
  double ring): goods never left, or the right sale is rung again → the return
  is the whole fix.
- **Customer brought goods back, fit to sell** (sealed, undamaged) → the
  return is the whole fix; the goods go back on the shelf.
- **Customer brought goods back, not fit to sell** (opened, damaged,
  expired) → the return brings them into stock, so they must come out again:
  do not write them off from here — note it for the office (step 5), which
  makes the issue order (Պահեստի ելքի օրդեր, `/armsoft-app` → "Write off a
  few pieces") with the reason.

## 0. Before anything

- ArmSoft is open, title bar says **Siruk** — not TestAPI_SIRUK (it was left
  on the test database once). Switch per `/armsoft-app` if it isn't.
- The register is on and connected (the sale slips print).

## 1. Find the original sale

Navigator search `կտրոն` → **ՀԴՄ կտրոններ**, period = the sale's day (or a
few days around it) → Կատարել. Ask the seller what they know: time, amount,
payment type, the goods, the slip's ՀԴՄ number (printed on the slip — the
best key). Open the candidate (double-click, read-only; Escape closes it) and
check its lines and total against what the seller says.

- One sale fits every detail → go on.
- None, or two that fit → stop; ask the seller for the slip number. Never
  guess which sale to refund.

## 2. Already refunded?

In the same journal look for a return row (type Վերադարձ…) after the sale:
open it — its **Հիմք փաստաթուղթ** field names the sale it returns
("Վաճառք (Կտրոն) N 0000142 … ՀԴՄ կտրոնի N 00000124"). A return already cites
this sale → **don't make a second one** (it would put the goods back twice).
If that return has no ՀԴՄ number yet (made at the office, never printed),
the job is only step 4's printing.

## 3. Make the return (draft until the seller says yes)

1. Right-click the sale → Ստեղծել փաստաթղթի հիման վրա → **Վերադարձ (Կտրոն)**.
   The lines, quantities and the cash/card amount are copied from the sale.
2. **Part of the sale only** (customer returns 1 of 3): reduce or remove the
   other lines before saving so only what comes back is on the return; the
   amount on the right (Վերադարձման) must equal the money given back.
   *Not tried yet* — the first partial refund: check the amount follows the
   lines, and write what happened into `/armsoft-app`.
3. Show the seller: the original slip (number, date, total), each line on the
   return (name, quantity, price) and the amount to give back, and how
   (cash / card). **Save only on the seller's yes** → "Գրանցված".

## 4. Print it on the register

Still in the return, **ՀԴՄ (F3)**. Marked goods (Felix) with no codes give
"Data Matrix … ծածկագրերը անցկացված չեն … Շարունակե՞լ" → Այո (the sale sent
none either). The return slip prints. Read its ՀԴՄ number back from the
journal (refresh; if it stays empty, restart ArmSoft per `/armsoft-app`).

Money:

- **Cash** → the seller gives the cash back from the till.
- **Card** → the card refund on the bank's POS terminal is the seller's to
  do on the terminal (ArmSoft doesn't move card money). *Not settled yet*
  how the terminal side is done — if the seller isn't sure, stop after the
  slip and note it for the office.
- **Wrong payment type** (the 02/11 case): refund the wrong slip, then the
  seller rings the sale again the right way — unless that's already done
  (sale 125 was rung before the refund).

Then check one returned good's stock (lower panel "Մնացորդ", or the movement
journal per `/armsoft-app` → "One good's history"): it went up by the
returned quantity, once.

## 5. Write it down (before the seller's `git push`)

- `knowledge/armsoft-documents.md`, documents table (newest first): the
  return's document and ՀԴՄ numbers, date, which sale it refunds, the goods
  and amount, why, "made by Claude, seller yes".
- `state/open-items.csv`, only when the office has something to do: goods
  not fit to sell (write-off), an unsure card refund, a partial refund that
  didn't behave.

Finish with two lines for the seller: what was refunded and how much money
goes back, and anything left for the office.

## Never, from this command

- A warehouse receipt or a second return for the same sale.
- Edit or delete a posted sale or return; refund a sale you couldn't match
  for sure.
- Write off stock, change a price, a good or anything on Siruk.
- Type a password or a card number, or log in anywhere.
