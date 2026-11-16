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

And before anything goes in the basket, **whether our prices still hold**
(user 2026-11-16): the buying price may have moved, a rival may sell the item
for something else, and Zoovet may have put it on Glovo. See step 2b.

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
  --out final/hafo/hafo-restock-<today>.xlsx --cart runs/<today>/hafo-cart.json \
  --lines runs/<today>/restock-lines.json
```

**Quantity** = sales over the next `--cover` days (14 by default) − stock − on the way.
Trixie goods are matched by article + "Tx" when the EAN misses: hafo gives its
loose treats an internal barcode (2026-11-16).
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

## 2b. Price check (always, before asking)

1. Refresh Zoovet's Glovo prices when the cache is over a day old:
   `uv run --no-sync --with openpyxl python scripts/glovo-prices-into-sheet.py harvest` (~5 min).
   The hafo snapshot must come from step 1.3 of this run. Snapshots before 2026-11-16
   carry no wholesale.
2. Run the check on the lines we may order (A and B only, not the whole catalogue):
   ```
   uv run --no-sync --with openpyxl python scripts/restock-price-check.py \
     --lines runs/<today>/restock-lines.json --siruk .siruk-cache/glovo/siruk-export.json \
     --out runs/<today>/restock-prices.json
   ```
   It adds a **Prices** sheet to the restock Excel. Per line:
   - **Cost**: hafo's `wholesale_price` (our buying price, equal to Pet House's
     invoice) vs Siruk `cost_price`. "UP" in red. A hafo listing whose `price`
     equals its `kg_price` is per kg (Trixie loose treats): the script multiplies
     price and wholesale by bag kg and says so in Notes. On a bag listing,
     `kg_price` is hafo's loose per-kg price, shown next to our `-KG` / `-100G` twin.
     A cost of exactly wholesale × 0.97 is the same cost (a 3% invoice discount on
     ~50 goods), shown as "= wholesale − 3%", with no TO DO.
   - **Loose twins** get their own rows: new cost = bag cost ÷ kg (or ÷ 100 g
     units). Their price is never proposed, only shown beside hafo's loose price.
   - **WARNING lines** (stale hafo snapshot, no wholesale, old Zoovet Glovo
     harvest, old Siruk export) mean that part was not checked. Re-run the
     source and the check before telling the user anything is fine.
   - **Rivals**: hafo retail always. zoovet / nemo **only from a confirmed
     page**: the variant's `price_source_url`, a row of `state/rival-urls.csv`,
     or, for zoovet, the Glovo match's ME code. Anything else is only a name search:
     the "Rival candidates" column lists them. Confirm one by hand (every axis:
     brand, line, flavour, size) and add it to `state/rival-urls.csv`
     (`sku,site,url,checked,note`), then re-run. A candidate's price is never used.
   - **Rule price** = the highest confirmed rival price (reference/pricing.md).
     A rule price at or below the new cost is not proposed; it's flagged
     "CHECK BY HAND" (rule 5).
   - **Glovo**: our price (Glovo sheet col F) vs Zoovet's Glovo price
     (`state/glovo-zoovet-matches.csv`). "NEW on Zoovet Glovo?" means a
     brand + size name candidate with no checked match yet. Confirm it the
     /glovo-portal way and add it to the matches CSV.
3. The TO DO column is a **proposal**. Nothing is written here.

## 3. Ask (always)

Send the Excel (SendUserFile) and say in chat, short:
- the A lines: product, stock, on the way, sold in the window, how many;
- the hafo-price total;
- B and S in one line each, with counts;
- C: what needs the other supplier;
- which hafo orders you counted as on the way;
- **prices** (from the Prices sheet), short: costs that went up or down, price
  changes the rivals call for, any LOSS line, Glovo lines at or above Zoovet,
  new Zoovet Glovo items to confirm, and the A total at hafo wholesale.
  A cost jump may change what to order, so say it before the basket question.

Ask the basket question first: fill the basket with A as listed? If there are
price lines, ask separately whether to apply them, and apply only the ones the user
says yes to. Apply them in this order, each through its own tool:
0. A price line that comes from hafo: confirm it first with
   `uv run --no-sync siruk recheck-prices --only <product ids>`. That command checks
   hafo's discount markers and its `/product/change` price, and the snapshot doesn't.
1. Siruk cost, then price: `siruk set-variant <id> <sku> <patch>` (or
   `update_variant`), dry run first, then the write. Price stays above cost.
   `price_source_url` = the rival page the price came from.
2. `final/siruk-source-of-truth.csv`: the variant's row (keyed by its
   `/dp/<variant id>` link): price, buying price, margin, source. Regenerate the
   `.xlsx` from it, then run `scripts/yandex-prices-into-sot.py` for column N.
   A loose twin (`-KG` / `-100G`) follows its bag's cost. Its price changes only on
   the user's word (rule 8a), and the scale gets the new price (step 5).
3. Glovo: `glovo-prices-into-sheet.py fill` then `--write`, then
   `glovo-portal.py prices` (dry run, then `--apply`); /glovo-portal → "Prices".
4. ArmSoft: price type 01 (shop), and 02 (Glovo, /glovo-portal step 5).
   A short code/price table for the user to type in (`armsoft-app`).
5. A loose good (1 kg / 100 g variant) whose price moved → `/send-to-scale`.

Take their basket changes (drop
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
   A cart line with `"unit": "kg"` is one of hafo's by-weight listings (Trixie
   loose treats, 31526Tx…): its `qty` is kilos (whole bags × bag kg, e.g. 5.4 for
   3 × 1.8 kg). The first time, check that hafo's quantity box takes the
   decimal and `quantityError` stays empty. If it doesn't, stop and ask, and
   write what hafo accepts here.
3. Check the basket against the plan (`/basket`: one row per line, quantity
   input, `NNN դր.` price, "Ընդհանուր գումարը").
   - Note which price the basket charges per line: hafo retail (`price`) or
     wholesale (the Prices sheet's "hafo wholesale"). Not settled yet
     (2026-11-16). Write the answer into `knowledge/costs-and-rivals.md` the
     first time you see it, and if the basket is charging wholesale, check
     each line's basket price against our cost.
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

- Change a price, a cost or a Glovo price without the user's yes on that line.
  Never use a zoovet/nemo name-search candidate's price before it's confirmed.
- Place an order, or change a placed one, without the user's yes in this run.
- Sign in, solve a CAPTCHA, enter card or bank details, or pick a payment
  other than cash.
- Change the account's delivery details, or remove basket items you didn't add.
- Order Royal Canin from hafo (user: RC comes from the other supplier).
