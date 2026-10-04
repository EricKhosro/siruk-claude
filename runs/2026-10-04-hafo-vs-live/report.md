# Every live variant vs hafo.am — 2026-10-04 (read-only, nothing written)

Production: public storefront API, 948 products / 1,522 variants (fresh read today).
hafo: whole catalogue downloaded today, 6,627 listings / 8,491 variant rows (`hafo-all.json`).
hafo price used = the variant row's regular `price`. A discount would come from the listing's `discount` %;
**no hafo listing has an active discount today**, so `price` is what hafo actually sells at.
Identity check per match: hafo wholesale price = our cost price ⇒ same article, same pack.

| Result | Variants |
|---|---|
| Same price as hafo | 805 (747 packs + 58 "1 kg") |
| **Different from hafo, same pack confirmed** | **461** (439 dearer than hafo, 22 cheaper) |
| hafo has the article but no per-kg price (our "1 kg" variants) | 10 |
| Not on hafo at all (Trixie 110, Royal Canin 91, …) | 240 + 6 Trixie false matches |

Of the 461 differences, 453 are live at the PM's register price (`Product.numbers`): the import followed
CLAUDE.md rule 2c ("the PM's register is the price of record — outranks hafo"). That rule is why the site differs.

Customer's screenshot: Inspector Quadro C 1–4 kg on hafo 11,680 is **790662, a box of 3 pipettes**; ours
(077592, 4,900) is **one pipette**, which hafo sells at 4,870. Not the same pack.

Files: `all-variants-vs-hafo.csv` (every variant), `proposed-price-changes.csv` (the 461, with variant id,
current price, hafo price, cost, hafo link — hafo price beats cost on all 461).
