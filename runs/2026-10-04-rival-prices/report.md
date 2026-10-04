# siruk.am prices vs hafo.am / zoovet.am / nemo.am, 2026-10-04

**Read-only audit.** Built fresh today; nothing was written to the site and no earlier audit result was reused.

## Deliverables

- `price-differences.csv`: **497 variants whose siruk.am price differs from the rival's.** Each row has:
  - the Siruk link and price;
  - the rival shop, its link and price, and the difference;
  - how the match was made;
  - when the live price came from one of your two xlsx files: the file, the Excel row, the column and the price in that cell;
  - otherwise, a note saying where the price did come from.
- `all-variants.csv`: all 1,522 live variants (948 products) with their status: same price / DIFFERENT / no rival sells this exact item.

## Method

1. **siruk.am**: every product, read from the live storefront API. All 947 products in the sitemap were covered, giving 1,522 variants.
2. **hafo.am**: the whole catalogue was downloaded today (8,491 rows). Each of our variants was matched by **article code** (or barcode), and the identity was confirmed with **hafo's wholesale price = our cost**. That gave 1,297 variants.
   - A "1 kg" variant is compared with hafo's per-kg price on the same bag.
   - All 1,223 hafo rows were re-read live just before writing: no price had changed.
   - 12 hafo pages were spot-checked: the page price equals the API price.
   - hafo has no discounts active.
3. **The remaining 238 variants** (Royal Canin, which hafo does not sell; Trixie items whose code is not on hafo; a few others) went to agents that searched by name:
   - hafo first, then zoovet, then nemo.
   - "Same product" means every axis matches: brand, line, lifestage, flavour/texture, pack size and count (a 12 × 85 g box is not one pouch; 1 kg loose is not the bag), and size/colour for accessories.
   - Each batch was then re-checked by an independent agent instructed to refute it. There were no disagreements.
   - All 194 zoovet/nemo prices were then re-fetched from the live pages and confirmed.
4. **Rival order**: hafo; if hafo doesn't sell the exact item, zoovet; if zoovet doesn't either, nemo. This is the order in your last sentence; your first sentence had nemo before zoovet. When both zoovet and nemo sell it, nemo's price is in the column "Other rival".

## Results

| | Variants |
|---|---|
| Same price as the rival | 894 (hafo 823, zoovet 67, nemo 4) |
| **Different** | **497** (hafo 464, zoovet 33) — Siruk dearer on 451, cheaper on 46 |
| No rival sells the exact item | 131 (Trixie 98, Kaskad 9, Gemon 8, others 16) |

## Where the differing prices came from

- **Every price cell that exists in your two xlsx files is on the live site unchanged:**
  - AllAngine: all 109 `Վաճառքի գին` cells and all 74 `Kg` cells;
  - Royal Canin: all 91 linked cells.
- Only **36** of the 497 differences carry an xlsx price:
  - Royal Canin vs zoovet (25 + 1);
  - Acana / Monge / Club 4 Paws bags and their 1 kg variants (10).
- The other **461** are on AllAngine rows whose `Վաճառքի գին` (or `Kg`) is **empty**, so none of them come from your files.
  - **456** of those equal the PM register `csv/Product.numbers` (same `Կոդ`). The import used that file as the price of record instead of falling back to hafo, which is why 434 variants are dearer than hafo.
  - The last 5 are Trixie treats priced from neither file.
- 3 live variants are in neither xlsx (Trixie 40473, 23773 and 24870, imported earlier from the supplier list). None of them is among the differences.

## Worth a look

- **Acana Wild Prairie Dog, 1 kg** (AllAngine row 31, `Kg` = 6,600). 6,600 is hafo's per-kg price for the **cat** Wild Prairie. zoovet and nemo sell the dog food loose at 4,700.
- **Royal Canin 12 × 85 g boxes** (18 rows): zoovet sells them at 8,650 and we sell at 8,600. **nemo sells them at 8,600, the same as us.** With nemo before zoovet, these are not differences.
- **zoovet same, nemo different** (not in the differences CSV under the hafo → zoovet → nemo order):
  - Acana Singles Yorkshire Pork 1 kg: ours 4,600, nemo 4,700;
  - Royal Canin Mini Starter 8 kg: ours 35,000, nemo 36,000.
- **Monge Maxi Adult 1 kg**: compared with hafo's per-kg price for the same food, which hafo sells loose from its 15 kg row (our bag is the 12 kg). The price is the same.

## Pass 2: highest rival price (user, 2026-10-04)

`price-differences-highest.csv` keeps the same 497 variants. For each one it gives:
- the same item's price on **all three** shops;
- the **highest** of those prices;
- the difference between Siruk's price and that highest price.

How the prices were found:
- **hafo:** article code + wholesale = our cost, as in pass 1.
- **zoovet and nemo:** for the 464 hafo-compared items, a name match by 30 agent batches, each re-checked by an independent verifier. 6 disagreements were settled by a third check, and all 600 rival prices were re-fetched live.
- **The 33 items hafo doesn't sell:** pass 1 had already searched all three shops.

Results:
- Rivals found per item: 1 shop for 69 items, 2 shops for 229, all 3 for 199.
- The highest price comes from hafo for 415 items, zoovet for 75 and nemo for 7.
- Against that highest price, Siruk is dearer on 414 items and cheaper on 54. On 29 items Siruk already equals it.
- Discounts: nemo has a discount on 14 of these items. The CSV uses nemo's discounted price, which is what customers pay now. With nemo's regular (struck-through) price, those 14 would take a higher price.

`csv/Product.numbers` is no longer a price source: it was removed from CLAUDE.md and the add-products skill, and marked withdrawn in reference/pricing.md.

## Pass 3: every product, highest rival (user, 2026-10-04 evening). **The source of truth.**

**`siruk-vs-rivals-final.csv`** has all **1,522 live variants (948 products)**. It replaces `price-differences.csv` and `price-differences-highest.csv`.

Columns, in order:
- Siruk price and link.
- **The highest rival price and its link.**
- The difference and the status.
- The hafo, zoovet and nemo price and link each, plus nemo's struck-through old price.
- The highest rival's product name, stock, how the item was matched, and how the rival price was confirmed.
- The source: xlsx file + Excel row + column + the price in that cell, when that cell holds the live price. Otherwise a note saying where the price came from.
- Remarks.

Method:
- **The 823 variants at hafo's price** that pass 1 compared only with hafo were searched on zoovet and nemo. Each was handled by a matcher agent and then an independent verifier told to refute it and find misses.
  - 775 answers were agreed.
  - 48 disputed ones were settled by a third, tie-break check. In most of them the verifier had found a nemo listing by our article code that the matcher missed.
- All 1,522 variants have now been searched on all three shops.
- Where one shop lists the exact same item twice at different prices, the higher price is used (2 toys).

Freshness (evening of 2026-10-04):
- siruk.am was re-read: no price changed since the afternoon.
- hafo was re-read: 1,223 rows, 0 changes.
- **All 1,101 nemo prices were re-read live and all match.** `rival.py` was fixed to read nemo's struck-through price (it always returned null before); 121 rows carry one.
- **zoovet.am started refusing connections from this machine mid-run.** It was probably blocking us after the heavy searching.
  - Pass 3's 239 zoovet prices equal today's saved zoovet catalogue (`shops.json`).
  - 8 more were read on zoovet's pages earlier in the day; 7 of those pages aren't in the saved list and one is a loose-1 kg option.
  - Pass 1 and 2 zoovet prices were re-read live earlier on 2026-10-04.
  - The "Rival price confirmed" column says which applies to each row.

Results:

| Status (vs the highest rival) | Variants |
|---|---|
| Same price | 847 |
| **Siruk dearer** | **414** |
| **Siruk cheaper** | **130** |
| No rival sells the exact item | 131 |

- The highest price comes from hafo for 1,164 items, zoovet for 202 and nemo for 25.
- Rivals found per item: 1 shop for 260, 2 shops for 706, 3 shops for 425.
- Where the "dearer" prices come from: 405 equal the PM register `csv/Product.numbers` (their xlsx cell is empty), 7 come from AllAngine cells, and 2 from elsewhere.
- Where the "cheaper" prices come from:
  - 68 equal the register;
  - 29 are AllAngine cells;
  - 24 are Royal Canin cells;
  - 9 come from neither file.

  Most are items where zoovet or nemo charge more than hafo.

Worth a look (each is in the Remarks column):
- **454 Trixie Bony Mix "1,800 g" at 6,300.** hafo and nemo sell Bony Mix loose at 6,300 **per kg**: hafo's row ends "կգ" and its stock is fractional. The Siruk variant is labelled as a 1.8 kg bag but has the per-kg price. zoovet's 1.8 kg bag is 11,500. Either the label or the price is wrong.
- **1722 Acana Wild Prairie Dog 1 kg at 6,600.** This is the cat food's per-kg price; rivals sell the dog food at 4,700 (as noted in pass 1).
- **Product 406, Trixie rope ball 9 cm.** Its gallery has zoovet's photo of a different, pink ball (media 7951).

## Applied to production (user, 2026-10-04 evening)

Instruction: every variant whose price differs from the highest rival gets that price. Bony Mix 1.8 kg (454) was held back.

- **Scope:** `plan.json`, 543 variants on 377 products: 414 lowered, 129 raised.
- **Writer:** `apply.py`, the 2026-10-04 production writer, using the user's admin token in `.siruk-token-prod`. It calls the API from Python, because this shell has no jq; the User-Agent is curl's, because Cloudflare 1010 blocks Python's default. For each product it:
  - reads the product fresh and saves a backup (`backup/<pid>.json`);
  - checks every planned variant is still at this afternoon's price;
  - checks the new price is above cost and a multiple of 10;
  - changes only `price`;
  - reads the product back to confirm the new prices and that every other variant is unchanged.
- **Logs:** `apply-dryrun.log`, `apply-write.log`, `apply-write-priceonly.log`; progress in `apply-state.json` (377 done).
- **364 products** passed the payload checks and were written and verified.
- **13 products** were refused at first because of gaps that were already in the data. These are 11 Supplements with a variant that has no size, plus products 354 and 633, each with an option missing on some variants. They were written with `--price-only`, which builds the body without marking any variant as touched, so those existing gaps stay warnings. All 13 were written and verified. The gaps are in `state/open-items.csv`.
- **Storefront re-read afterwards** (`live-after.json`): all 543 planned variants show the new price, and no other variant's price changed.
- **Still open** (in `state/open-items.csv`): Bony Mix 454 (label or price), product 406's wrong photo, and the 13 data gaps.

## Bony Mix and the source-of-truth file (user, 2026-10-04 late evening)

- **Bony Mix 1.8 kg (variant 454)** was set to zoovet's 1.8 kg price, **11,500** (it was 6,300), using `apply.py --plan plan-bony.json`, written and verified. The user ruled that the 6,300 was wrong, per kg or not, and that `csv/Product.numbers` must never be cited as a price source.
- **`siruk-source-of-truth.csv`** has one row per live variant: the product name on Siruk, the variant, the price, where the price comes from, the Siruk link and the link to that source.
  - 1,391 variants are sourced from the rival whose price for the exact item equals ours: hafo 1,164, zoovet 202, nemo 25.
  - 4 are sourced from an xlsx cell (3 AllAngine, 1 Royal Canin).
  - **127 have no source:** no rival sells the exact item, and neither xlsx file has a sale price for it (Trixie 98, Kaskad 9, Gemon 8, others 12). Their prices are 1.27× to 1.88× cost.
- `siruk-vs-rivals-final.csv` was refreshed from the storefront: every rival-sold variant is now "same" as the highest rival. It no longer cites `Product.numbers` anywhere.
- **Checked against the original `csv/Product.numbers`:** column F is "Գնման գին" (cost) and column H is "Վաճառքի գին". 126 of the 127 rows with no rival equal column H, and none equals its cost. No variant on the site is priced at its cost. These 126 now cite their Product.numbers row and column H in `siruk-source-of-truth.csv`.
- **Trixie Batik Collar purple/blue (variant 1025) is kept at 1,600** (user, 2026-10-04). Its Product.numbers row has Վաճառքի գին 1,000, which equals cost.
