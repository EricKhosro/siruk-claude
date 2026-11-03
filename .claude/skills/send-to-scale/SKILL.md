---
name: send-to-scale
description: Send every ArmSoft good (names, sale prices, scale codes) to the shop's Axiom label scale, from ArmSoft's own export. Use after prices change, after a new per-kg / per-100 g good or PLU is added, or when the seller says the scale shows a wrong or missing price — "export products to the scale", "update the scale", "send prices to the scale".
---

# Send all goods to the scale

Who runs it: the office or the seller on the shop computer (user 2026-11-03,
`shop/CLAUDE.local.md`). To the seller: short and plain, no codes.

What it does: ArmSoft pushes its goods list to the label scale over the
network — name, sale price (price list 01) and the barcode as the code the
scale keys on (the 5-digit PLU on a per-kg good's 303 unit). Nothing changes in
ArmSoft or on Siruk. Learned from the user 2026-11-03 — **steps marked
*unseen* were not yet shown; fill them in on the first run** and drop the mark.

How to drive ArmSoft: `/armsoft-app` → "Before anything" and "Layout"
(title bar must say **Siruk**, never open a second copy).

## The scale (what ArmSoft knows)

Ctrl+K → `կշեռ` → **Էլ. կշեռքներ, տերմինալներ (Off-line)**, Կատարել: one
device, **001 Axiom**, type Էլ. կշեռք (Off-line), model **TM-A (ուղիղ կապ)**,
**192.168.0.99:33581**, active. Its settings (Ctrl+E, read only — Escape):

- Գնացուցակ **01** Վաճառքի գին — the sale price list.
- Name from Անվանում (the good's name; HDM rule: under 50 chars).
- Code on the scale = **3 Գծիկավոր կոդը** (the barcode): the PLU from
  `knowledge/goods-setups.md` → "Picking a new scale PLU".
- Խումբ / Սեգմենտ empty → no filter, every good is offered.
- "Մաքրել ցանկը արտահանումից առաջ" (clear the list first) off.
- Label format 10 for weight goods and for piece goods.

Don't change these settings without the user.

## Where it runs

The scale sits on the shop's own subnet (192.168.0.x); the shop PC reaches it
on its second fixed address 192.168.0.10 (`knowledge/resolved-blockers.md`).
Check first: `Test-NetConnection 192.168.0.99 -Port 33581` → True. False → the
computer isn't on the shop network; stop. *Unseen*: whether the office
computer can send at all (likely not, like the HDM printing).

## Steps

1. Goods list **Ապրանքներ և ծառայություններ** (Ctrl+K → `ապրանքներ`).
2. Click a row, **Ctrl+A** — status bar "Նշված է 1574 տող" (all goods ticked;
   Ctrl+A toggles, so check the count).
3. Right-click a ticked row → **Արտահանել** ▸ **Խմբային (Էլ. կշեռքներ,
   տերմինալներ)**. (The other two, Էլ. կշեռքի ֆորմատով and Տերմինալի
   ֆորմատով, write a file instead.)
4. *Unseen*: the "Արտահանել ապրանքները" window — Ամսաթիվ (today), the Axiom
   row's tick box, Կատարել. Tick Axiom, Կատարել.
5. *Unseen*: what success looks like (message, progress), and how long it
   takes for ~1574 goods.
6. *Unseen*: check on the scale — key one PLU (e.g. 00001) and compare the
   price with ArmSoft's 303 price.

Afterwards clear the selection (Ctrl+A again) so the next edit doesn't walk
through every ticked row.

## When to run it

After anything that changes what the scale shows: a sale-price change on a
per-kg / per-100 g good, a new PLU, a renamed good. Then also reprint the
counter's code lists (`scripts/scale-code-sheets.py`,
`knowledge/resolved-blockers.md`).

## Write it down

A dated bullet in `knowledge/goods-setups.md` (or the area's file): date, how
many goods went, anything the scale refused.

## Never

- Change the scale's settings or the prices from here.
- Send while ArmSoft is on TestAPI_SIRUK.
