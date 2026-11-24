# Ops ↔ ArmSoft goods check — 2026-11-24 11:07

Trigger: the seller sent a till screenshot of **Natural Wood Woodchips · 1 kg (SKU 424128V, 1,600 ֏)** and said it is not in ArmSoft.

Snapshots:
- ArmSoft: `Scale/armsoft-export-2026-11-24.xml`, 1,650 goods, exported 11:06 after a refresh of the goods list.
- Ops: `runs/2026-11-24/ops-goods-p1..9.json` (`siruk ops goods list --json`), 1,737 variants, 0 inactive.
- Script: `scripts/ops-vs-armsoft-goods.py`. Result: `ops-vs-armsoft.json`.

## Woodchips: it is in ArmSoft

| | Ops | ArmSoft |
|---|---|---|
| code | accounting code 1439 | good **1439** |
| name | Natural Wood Woodchips, 1 kg; fiscal name "Թեփ՝ կրծողների համար, 1 կգ" | **"Թեփ՝ կրծողների համար, 1 կգ"**; long name "Versele-Laga Natural Wood Woodchips — 1 kg" |
| barcode | 5410340241288 | 5410340241288 on unit 001 |
| price | 1,600 | 01 = 1,600 (since 05/10), Glovo 02 = 1,850 |
| stock | 1 | 1 (turnover 23/11 19:26) |

ArmSoft's find-by-barcode (F2) with 5410340241288 jumps straight to 1439.

ArmSoft does not know "424128V". That is Siruk's SKU, printed under the name on the Ops till. ArmSoft's name is in Armenian, and "Woodchips" appears only in its long name.

The good can be found in ArmSoft by:
- code **1439**,
- barcode **5410340241288**, or
- name **Թեփ**.

**Open question for the seller:** how did they search, and if they scanned, what did the scanner read off the pack?

## Ops → ArmSoft

- **1,734 of 1,737 Ops variants** reach an existing ArmSoft good through their accounting code.
- Every Ops barcode sits on that good.
- Every loose (per-kg) variant's good has unit 303.
- No ArmSoft code is shared by two Ops products.
- Goods **1678–1695** (Malt Plus, Tofu litter, and the 16 Pet House goods of 22/11) were imported last night. ArmSoft's import window confirms it: 16 goods and 32 prices. They are now in the export.

Three Ops variants have no code. All three are discontinued, at 0 stock, and were left out on purpose on 23/11:

| SKU | product | note |
|---|---|---|
| 387807-OLD | Gemon Adult Dog Paté Beef & Tripe 400 g | old twin, no barcode |
| 387817-OLD | Gemon Adult Dog Paté Lamb 400 g | old twin, no barcode |
| 40211 | Trixie Litter Tray Carlo 31×14×43 | ArmSoft's matching good is retired duplicate 0302 (→ 0300) |

## ArmSoft → Ops

29 ArmSoft goods have no Ops variant. All 29 are known and none is a gap:

- **21 retired duplicates**, listed in `state/armsoft-duplicate-codes.csv`: 0302, 0436–0441, 0464–0466, 0468, 0469, 0803, 0901, 1030, 1051, 1224, 1229, 1312, 1508, 1552.
  - They can't be deleted, because they have movements.
  - Each kept twin is live in Ops.
- **7 Royal Canin 12×85 g boxes**, 1466–1472. These are receiving units; pouches are sold one by one.
- **1473 Delivery**, a service.

All 29 had 0 stock in ArmSoft on 23/11 19:26.

## Not covered

- This check covers goods, codes and barcodes. It does not compare stock or prices across all goods; that was done in the 23/11 sync.
