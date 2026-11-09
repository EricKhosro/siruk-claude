---
name: hafo-restock
description: Decide what to reorder from hafo.am and how many, from ArmSoft stock, recent sales and the hafo orders already on the way, then fill the hafo basket and place the order only after the user says yes. Use when the user asks to restock, reorder from hafo, "what should we order", "place a purchase order on hafo", or to fill the hafo cart.
---

# Restock from hafo (office)

Learned 2026-11-09 (first order: hafo #12126). The order is a real purchase:
**nothing is ordered without the user's explicit yes on the final basket and
total**, every time. A yes from an earlier run never counts.

What it decides from:
- **ArmSoft stock now**. Real stock lives only in ArmSoft; Siruk shows a placeholder 10.
- **Sales speed**: ArmSoft sales between two turnover exports, normally about 14 days apart.
- **What is already on the way**: hafo orders placed but not yet received into ArmSoft.
- **hafo's live stock**: what can actually be ordered.

## 1. Gather (read-only)

1. **ArmSoft stock**: `/armsoft-app` → "Stock / turnover". The period starts
   01/01/01 and "Բացված ըստ գործողությունների" is ticked. Save as
   `Scale/armsoft-turnover-<today>.xlsx`; add `-HHMM` when there's already one today.
   The checkbox does not stay ticked: zoom on it before Կատարել.
2. **The earlier export** for the sales window: the `Scale/armsoft-turnover-*.xlsx`
   closest to 14 days old, and at least 7 days old. None that old → tell the
   user and use the oldest one there is, saying how many days it covers.
3. **hafo's stock**: `uv run --no-sync --with tzdata python scripts/hafo-watch.py crawl`
   (read-only, ~3 min). Without `--with tzdata` it dies on "Asia/Yerevan".
4. **Siruk catalogue**: `uv run --no-sync siruk export --format json -o .siruk-cache/glovo/siruk-export.json`.
   It maps ArmSoft codes to hafo rows by EAN, else by article code.
5. **On the way**: open `https://hafo.am/my-orders` in the **built-in browser**,
   where the user is signed in. **Never sign in** for them; if you see a login
   page, ask them to sign in. An order is still on the way when its goods
   haven't been received into ArmSoft:
   - `state/open-items.csv` rows "Waiting: Pet House invoice for hafo order #N";
   - orders newer than the last Pet House receipt in `knowledge/armsoft-documents.md`;
   - when in doubt, compare an order's lines with the goods' receipt column in
     the turnover export (Պահեստի մուտքի օրդեր).

   Read each open order's lines with this snippet and save them as
   `runs/<today>/hafo-pending.json`:
   ```js
   const out=[];for(const id of [/* open order numbers */]){const h=await (await fetch('/my-orders/'+id)).text();
   const d=new DOMParser().parseFromString(h,'text/html');for(const r of [...d.querySelectorAll('table tr')].slice(1)){
   const c=[...r.querySelectorAll('td')].map(x=>x.innerText.replace(/\s+/g,' ').trim());if(c.length>=4){
   const m=c[3].match(/([\d.,]+)\s*(.*)/);out.push({order:id,sku:c[2],qty:m?+m[1].replace(',',''):1,unit:m?m[2]:''})}}}
   JSON.stringify(out)
   ```
   Drop lines already received (the receipt column moved for them).

## 2. Decide

```
uv run --no-sync --with openpyxl python scripts/hafo-restock.py \
  --now Scale/armsoft-turnover-<today>.xlsx --before Scale/armsoft-turnover-<earlier>.xlsx \
  --pending runs/<today>/hafo-pending.json [--cover 14] \
  --out final/hafo/hafo-restock-<today>.xlsx --cart runs/<today>/hafo-cart.json
```

**Quantity** = sales over the next `--cover` days (14 by default) − stock − on the way.
Bags of dry food are counted in kg and ordered in whole bags; the loose kilos
left count as stock (user 2026-11-09: an open bag isn't "out"). The quantity
is capped at hafo's stock. The groups:

| | Group | In the basket? |
|---|---|---|
| A | sells and runs short within the cover | yes |
| B | out of stock, nothing coming, sold before but not lately: 1, optional | only if the user says |
| S | a toy / accessory / grooming / litter / treat with a similar item on the way (same category leaf). Food and supplements are never skipped this way | no (user 2026-11-09: "remove things that are similar like toys") |
| D | hafo has none now | no |
| C | not on hafo (Royal Canin, Pro Plan, …): other supplier | no, list it for the user |

## 3. Ask (always)

Send the Excel (SendUserFile) and say in chat, short:
- the A lines: product, stock, on the way, sold in the window, how many;
- the hafo-price total;
- B and S in one line each, with counts;
- C: what needs the other supplier;
- which hafo orders you counted as on the way.

Ask one question: fill the basket with A as listed? Take their changes (drop
lines, change quantities, add B items) into `runs/<today>/hafo-cart.json`.

## 4. Fill the basket (on their yes)

1. `https://hafo.am/basket` must be **empty**. If it holds anything, show it to
   the user and ask; never remove things you didn't add.
2. Add each line through hafo's own product page in a hidden iframe, so its
   JavaScript sets the variant and price (`/add-basket` takes the page's form):
   ```js
   window.addOne = async (url,rowId,qty)=>{const fr=document.createElement('iframe');
     fr.style.cssText='width:1300px;height:900px;position:absolute;left:-5000px';document.body.appendChild(fr);
     await new Promise((res,rej)=>{fr.onload=res;fr.src=url;setTimeout(()=>rej('timeout'),30000)});
     const w=fr.contentWindow,$=w.jQuery,d=w.document,sel=d.getElementById('select1');
     if(!sel||![...sel.options].some(o=>o.value==String(rowId))){fr.remove();return {url,err:'variant not on page'}}
     $('#select1').val(String(rowId)).trigger('change');await new Promise(r=>setTimeout(r,500));
     $('#quantity').val(qty).trigger('change');let st=null;
     const done=new Promise(r=>$(d).ajaxComplete((e,x,s)=>{if((s.url||'').includes('add-basket')){st=x.status;r()}}));
     $(d).find('.addInBasket').first().trigger('click');await Promise.race([done,new Promise(r=>setTimeout(r,15000))]);
     const err=d.getElementById('quantityError').innerText;fr.remove();return {url,rowId,qty,status:st,err}};
   ```
   Run batches in the background: `window.cartLog=[]; (async()=>{for(...) cartLog.push(await addOne(...))})()`.
   Then poll `cartLog`, because a call over ~45 s times out the browser tool.
   If the user navigates the tab, the loop stops: re-read the basket and add what's missing.
3. Check the basket against the plan (`/basket`: one row per line, quantity
   input, `NNN դր.` price, "Ընդհանուր գումարը").
   - Remove a line with `$.ajax({url:'https://hafo.am/delete-product-in-basket',
     type:'POST',data:{id}})`, where `id` is the row's `input[name=id]`.
   - Then front the basket tab (`tabs_select`) so the user sees it.

## 5. Confirm and place (only on a fresh yes)

1. Show the final basket: lines, units, and **hafo's total**, which can be a
   little under the sum of the prices. Ask: "Place the order?".
2. On yes: open `https://hafo.am/basket/pay`. The form `choose_episode_form`
   posts to `https://hafo.am/order-cash`; the account fills in name Siruk,
   phone, region Երևան and address Verin Antarain 13/2. **Check those fields
   and leave them as they are.** Payment is **cash**: never card or bonus,
   and never type card details.
3. Click ՈւՂԱՐԿԵԼ (button). Success page: "Պատվերը ընդունված է…". The new
   order is first in `/my-orders` (status "Սպասման մեջ").
4. Write it down:
   - a `state/open-items.csv` row "Waiting: Pet House invoice for hafo order
     #N (date, total, lines / units)";
   - the Excel stays in `final/hafo/`.

   When its e-invoice arrives: warehouse receipt, then Glovo `stock
   --on-codes` (`/glovo-portal` → "After every posted warehouse receipt").

Finish with: order number, total, delivery address, what was left out and why
(C, D, S).

## Never

- Place an order, or change a placed one, without the user's yes in this run.
- Sign in, solve a CAPTCHA, enter card or bank details, or pick a payment
  other than cash.
- Change the account's delivery details, or remove basket items you didn't add.
- Order Royal Canin from hafo (user: RC comes from the other supplier).
