# Price audit before opening — 2026-10-03 (read-only, nothing written)

Production read: public storefront API `api.siruk.am/api/products/<id>`, 948 products / 1,522 variants
(every variant of yesterday's admin snapshot is there, same prices, + 18 products created since).
hafo.am: `scripts/hafo-lookup.py` by article code, only the per-variant price.
Scripts: `fetch-live.py` → `compare.py` → `differences.py`.

## 1. `AllAngineProduct-FINAL-2026-09-28.xlsx` — 1,371 rows

| Result | Rows |
|---|---|
| `Վաճառքի գին` filled and live = it | **109 / 109 — all match** |
| `Kg` column vs the "1 kg" variant | **74 / 74 — all match** |
| `Վաճառքի գին` blank → live = hafo | 622 |
| `Վաճառքի գին` blank → **live ≠ hafo** | 458 (457 of them: live = PM price in `Product.numbers`) |
| `Վաճառքի գին` blank, hafo has no price | 165 (160: live = PM price; 5 from another source) |
| not on the site | 17 (known holds / no code, same as 2026-10-02) |

1,262 of 1,371 rows have no `Վաճառքի գին` in this xlsx. Their prices were set from `csv/Product.numbers`
(CLAUDE.md rule 2c — the PM register outranks hafo), so a hafo difference there is by design, not an error.

**Only real mismatch:** 00908 Trixie Freeze Dried Cat Snacks Lamb Liver & Salmon 25 g (42804Tx,
product 562): live **1,500**, hafo **1,400**, PM price **1,400**, cost 875.

Notable hafo gaps in group 2 (live = PM price): Mnyams Crunchy Pillows 60 g ×5 live 1,700 vs hafo 800;
Club 4 Paws jelly 85 g ×2 live 400 vs hafo 270; Trixie 12767 belt live 9,000 vs hafo 600 and 13077 USB collar
10,150 vs 550 (hafo below our cost → hafo row is wrong); Trixie 4161 ID tag live 600 vs hafo 4,800;
23472 poop bags 1,200 vs 4,400. Full list: `differences.csv`.

Duplicate register lines on one variant: 00774/00775 (23772Tx), 00592/00693 (4046Tx) — same price, harmless.

### Double check (same day)

- Identity of every pairing: 1,354/1,354 mapped rows have sku = article code; 1,326 also have register
  cost = production cost price (admin snapshot 2026-10-02); the other 28 were created after that snapshot.
- 00908 re-traced: xlsx row has no code and no price ("In Siruk? No"); the code 42804Tx is the 2026-10-01
  hand match (exact hafo row name, cost 875 equal, only such row; EAN 4011905428048). hafo listing 6950
  today: sku 42804Tx, price 1,400, wholesale 875, no active discount (page shows 1,400). PM price 1,400.
  Production variant 1397, sku 42804, "Lamb Liver & Salmon 25 g", 1,500 — set before the register run;
  on 2026-10-02 it was "already live, not re-imported", so the register price never reached it. Its twin
  00907 / 42805 Chicken & Cheese 25 g (same cost 875) is live at 1,400.
- Do NOT bulk-move group 2 to hafo: for 5 rows hafo is at/below our cost (00586, 00603, 01152, 01185, 01186).

## 2. `Price Royal Canin Nor _ SIRUK.xlsx` — 52 rows with a number in column E

- 46 live rows: **every pack price = `Վաճառքի Գին`, every 1 kg variant = `Վաճառքի Գին կիլոգրամով`,
  every single 85 g pouch = 750, Mother & Babycat 195 g = 2,300. 0 differences.**
- 6 not live: rows 54, 66, 144, 155, 158 (skipped on your instruction 2026-10-01), 82 (no price in the file).
- Cosmetic: the 21 retired "12 × 85 g" case variants are still on the product pages at 8,600, stock 0
  (not orderable) — the developers were to delete them (2026-10-01).
