# ArmSoft sync — 2026-10-09

Export: `C:\Users\Eric\Downloads\Export_All.xml`, copied to
`Scale/armsoft-export-2026-10-09-full.xml`. The untracked
`Scale/armsoft-export-2026-10-09.xml` from earlier today holds only 419 goods,
so it was left as it was.

## Counts

| | |
|---|---|
| Goods in ArmSoft | 1,473 (codes 0001–1473) |
| Goods in our target (`csv/all-xml-scale.xml`) | 1,439 (0001–1439) |
| New goods to import | **0** (ArmSoft already has 1342–1439, so there is no `new-goods.xml`) |
| Goods needing a barcode update | **54** (38 barcodes to add, 16 to fix) |
| Units to add | **0** (ArmSoft already has the 303 units for 0009–0014 and 0019) |
| Goods only in ArmSoft | 34 (1440–1473) |
| Live Siruk variants with no good | 0 |
| Price rows | 1,521 (good + unit) |
| Goods with no price from us | 56 (22 RC boxes + 34 ArmSoft-only) |
| Barcodes failing check digit / on two goods | 0 / 0 (checked after the update) |

## What changed in ArmSoft since 2026-10-02
- Goods 1342–1439 (the 2026-10-09 new-goods import) are all there. Their English `LongName` matches ours on every good, so no code clashes.
- The shop added 303 units and PLUs to the Acana/Orijen 4.5 kg goods. Our target and `Scale/scale-codes-per-kg.csv` now include them too (1 kg variants 2079–2085).
- 862 Armenian `Name`s were shortened to at most 51 characters. The products are the same (identical `LongName`), so they were left alone.
- The shop created 34 goods, 1440–1473, without barcodes.

## Files, in import order
1. **`update-goods.xml`**: 54 goods, each built from ArmSoft's own block. Only `BarCode` and `GoodBarCodes` change.
   - The Royal Canin pouch/box swap. In ArmSoft, the single-pouch EAN still sits on the 12-box good. Scanning a pouch therefore rings up the box. Each box good comes before its pouch good in the file.
   - Bag EANs for 0033 (My Love Junior) and 1353 (Fit 32).
   - 20 older goods that had no barcode.

   **Try one good first.** ArmSoft may not update an existing code on import. If it doesn't, `changes.xlsx` lists every barcode so they can be entered by hand.
2. **`prices.xlsx`**: column A is the code (as text), B the price. One row per good + unit. Prices come from live Siruk variants plus `state/armsoft-extra-prices.csv`. The export has no prices, so nothing could be compared.
3. **`changes.xlsx`** sheets: barcodes to add, barcodes to fix, barcodes only in ArmSoft, units to add (empty), ArmSoft-only goods, Siruk variants with no good (empty), and still missing.

## Decisions needed from you
1. **Duplicate Royal Canin goods.** ArmSoft goods 1443–1465 look like the same bags as our 1342–1364. Goods 1466–1472 look like seven of the 12-box goods (1369, 1377, 1383, 1387, 1401, 1399, 1403). The pairs are in `changes.xlsx`. Which codes stay? Nothing was deleted.
2. **Royal Canin 12-box goods** (22, odd codes 1365–1407). Siruk archived these box variants on 2026-10-07. The update only gives them the 12-box EAN, which frees the pouch EAN. There is no price for them in `prices.xlsx`. Keep them (at what price) or retire them?
3. **Good 0013** (Acana Pacifica) has an extra scale code `00103` on unit 303, next to its PLU 00102. 00103 is not assigned anywhere. Remove it?
4. **Goods 1440–1442 and 1473** are not on Siruk:
   - 1440: salt for rodents, 60 g
   - 1441: clumping litter, 8.1 kg
   - 1442: cat food "Sterilised" chicken, 10 kg (brand unknown)
   - 1473: Delivery

   No barcode or price from us.

## Still needs a person
- Barcode missing on 8 older goods, unchanged:
  - 0902 Dermobrush "Fantasia": read it off the pack.
  - 0210, 0355, 0462, 0463, 0659, 1340, 1341: not on Siruk.
- The 34 ArmSoft-only goods have no barcodes.

## What I did not do
- Nothing was written to Siruk or ArmSoft.
- I did not look up barcodes for 1440–1473. They are probable duplicates or non-Siruk goods, so they wait on decision 1.
- `csv/Siruk-hx.xlsx`: MATERIALS, MTQUNIT and MTBARCODES were rebuilt from the updated target. PRICES was not touched.
