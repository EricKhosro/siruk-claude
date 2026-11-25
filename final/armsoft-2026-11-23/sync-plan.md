# ArmSoft ↔ Ops sync plan — 2026-11-23 18:52

Snapshots: ArmSoft turnover `Scale/armsoft-turnover-2026-11-23-1852.xlsx`, goods `Scale/armsoft-export-2026-11-23.xml`, Ops `runs/2026-11-23/ops-stock-1852.json`. Last sync point: 22/11 13:52 (CN-000006).

Already done today: CN-000008 Hairball Care 1 kg → 803 g; CN-000009 Urinary S/O 1 kg → 0; Monge 851 track_inventory on.

## 1. Ops count (ArmSoft-only sales since 22/11 13:52 → Ops)

| SKU | ArmSoft code | counted |
|---|---|---|
| 301097 | 0212 | 18 |
| 013627 | 0221 | 10 |
| 012787 | 0225 | 20 |
| 301067 | 0246 | 19 |
| 299957 | 0307 | 0 |
| 061787 | 0322 | 21 |
| 83041J | 0349 | 31 |
| 142645 | 0359 | 5 |
| 009517 | 0366 | 0 |
| 009077 | 0367 | 1 |
| 009547 | 0369 | 0 |
| 300907 | 0370 | 6 |
| 300747 | 0398 | 0 |
| 08539MG | 0434 | 0 |
| 3182550939904-KG | 1460 | 13000 g — after Ops open-bag of the 14 kg bag (ArmSoft sold 1 kg loose) |
| 12512737 | 1477 | 21 |
| 12512741 | 1482 | 22 |
| 45534 | 1677 | 0 |

## 2. ArmSoft new goods (XML `final/armsoft-2026-11-23/new-goods-1678-1679.xml`)

- 1678 Trixie Cat Malt Plus 100 g, EAN 4011905042213, CPA 2309, 01 = 3,000, 02 = 3,750
- 1679 Trixie Tofu Clumping Litter 2.5 kg, EAN 4011905730080, CPA 3824 (invoice), 01 = 4,500, 02 = 5,650

## 3. ArmSoft receipts (XML `final/armsoft-2026-11-23/pethouse-receipts-0061-0062.xml`)

- 0061 = A7305674976 / Ops RC-000005: 0235 0236 0237 × 2 — 6,480
- 0062 = A7995305466 / Ops RC-000006: 0418×5 1141×2 0820×2 0823×2 1679×2 0217×1 0218×3 1678×2 — 39,140

## 4. ArmSoft issue order (Ops-only till sales / web orders since 21/11 → ArmSoft)

| code | qty | unit | Ops doc |
|---|---|---|---|
| 0005 | 0.26 | 303 | SL-000011 |
| 0048 | 4 | 303 | WEB-000012 |
| 0052 | 1 | 303 | WEB-000009 |
| 0057 | 1 | 303 | WEB-000010 |
| 0074 | 1 | 303 | SL-000014 |
| 0081 | 2 | 303 | WEB-000012 |
| 0127 | 1 | 001 | WEB-000008 |
| 0141 | 1 | 001 | SL-000010 |
| 0166 | 1 | 001 | SL-000010 |
| 0180 | 1 | 001 | WEB-000009 |
| 0181 | 1 | 001 | WEB-000009 |
| 0350 | 1 | 001 | SL-000008 |
| 0456 | 1 | 001 | SL-000012 |
| 0495 | 1 | 001 | SL-000014 |
| 0644 | 1 | 001 | WEB-000008 |
| 0737 | 1 | 001 | SL-000012 |
| 1122 | 1 | 001 | WEB-000008 |
| 1220 | 1 | 001 | WEB-000008 |
| 1378 | 10 | 001 | WEB-000008 |
| 1450 | 2 | 303 | SL-000006, WEB-000006 |
| 1457 | 1 | 303 | WEB-000011 |
| 1485 | 1 | 001 | SL-000005 |
| 1486 | 1 | 001 | SL-000009 |
| 1556 | 1 | 001 | WEB-000008 |
| 1585 | 1 | 001 | WEB-000008 |
| 1619 | 1.2 | 303 | SL-000007 |
| 1620 | 2 | 001 | WEB-000008, WEB-000010 |
| 1622 | 1 | 001 | WEB-000008 |
| 1624 | 1 | 001 | WEB-000010 |

## 5. Small fixes

- Ops 40250 ADG 1404 → 3824 (invoice classifier)
- Siruk accounting_code: variant 2302 → 1678, 2301 → 1679

## 6. Needs a person (not touched)

- 1454 Fit 32 loose: ArmSoft 4 kg, Ops 2 kg (Ops web order WEB-000007 5 kg on 21/11 never in ArmSoft; ArmSoft sold 2 kg since 22/11; Ops till add TA-000006 +1 kg today) → shelf count
- 0820 Monge Gift Dental rabbit: after receipt ArmSoft 2, Ops 3 (Ops till add TA-000003 +1 on 21/11) → shelf count
- 1451 Mini Adult 8+ loose: ArmSoft 0, Ops 300 g (CN-000007) → is the 300 g still there?
- 1625 / 1628 YOKO bull roots: Ops grams vs ArmSoft pieces (known)
- Ops-only goods at 0 stock, not added to ArmSoft: 40211 Trixie Litter Tray Carlo (discontinued), 387807-OLD / 387817-OLD Gemon (discontinued)
