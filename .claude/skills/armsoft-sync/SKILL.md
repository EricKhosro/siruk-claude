---
name: armsoft-sync
description: Compare a fresh ArmSoft goods export (XML) with what Siruk sells and build the files to bring ArmSoft up to date — new goods to import, barcodes to add or fix, missing 1 kg (303) units, and a price sheet (code next to price). Also re-checks ArmSoft after an import. Use when the user hands over an ArmSoft XML export, or asks what is missing in ArmSoft.
argument-hint: <path to the ArmSoft export .xml> [verify]
---

Bring ArmSoft in line with Siruk. The user exported the goods from ArmSoft:

$ARGUMENTS

(`verify` after the path = the export was taken right after an import; only
run step 6.)

ArmSoft is the shop's accounting / till program. Siruk (the website) is the
catalogue of record: every live Siruk variant must exist in ArmSoft as a good
with the right unit, barcode and price. **This skill never writes to the Siruk
admin, and never to ArmSoft itself** — it only reads the export and writes
files the user imports by hand.

## Files

| File | What it is |
|---|---|
| the export (argument) | ArmSoft's current state. Copy it to `Scale/armsoft-export-<YYYY-MM-DD>.xml` first; never overwrite `Scale/all-xml.xml` (the 2026-10-02 export, kept for history). |
| `csv/all-xml-scale.xml` (= `Scale/all-xml-scale.xml`, keep the two identical) | **our target**: every good ArmSoft should have, 1,439 goods on 2026-10-09, barcodes fixed that day. |
| `Scale/scale-codes-per-kg.csv` | Siruk variant id ↔ ArmSoft good code, with SKU, EAN and price. |
| `final/siruk-source-of-truth.csv` | every live Siruk variant: name, variant, price, buying price, margin, margin %, barcode, PLU (1 kg scale code). |
| `state/armsoft-extra-prices.csv` | sourced prices for goods that are not on Siruk. |
| `scripts/build-armsoft-import.py` | `parse_goods()` reads the XML; `prices_rows()` gives the price per good + unit. Reuse them (import the file with `importlib`) instead of re-writing the logic. Its own output is `csv/Siruk-hx.xlsx` — rebuild only the sheets that changed (`--sheets MATERIALS,MTBARCODES`), PRICES only when the user wants today's date on it. |
| `Scale/armsoft-new-goods-1342-1439.xml`, `final/armsoft-new-goods-prices.xlsx` | the 2026-10-09 new-goods import + its prices. Superseded by whatever this run builds. |
| `state/open-items.csv` | ArmSoft rows are `scale: …` / `armsoft …` areas — read them, update them at the end. |

Python: `uv run --with openpyxl python …` (system python has no openpyxl).

## XML format (ArmSoft Accountant 6.0)

`<Exchange xmlns="http://www.armsoft.am/Accountant/6.0">` holding `<Goods>`
blocks. Per good: `Code` (4 digits), `Name` (Armenian), `LongName`, `Unit`,
`AltUnit`, `IsWeight`, `BarCode` (main), `GoodQuantityUnits/QuantityUnitPart`
(`Unit`, `Coef`), `GoodBarCodes/MTBarCode` (`GoodsCode`, `Unit`, `BarCode`).
Units: `001` piece, `003` bag, `303` kg. A good sold loose is `IsWeight true`,
`Unit 303`, `AltUnit 003` (Coef = bag kg); its main `BarCode` and the 303
MTBarCode are the 5-digit scale code, the 003 MTBarCode is the bag's EAN.
The export may start with a BOM — read with `utf-8-sig`. Edit the XML as text,
block by block, keeping its exact indentation and tag style; parse the result
with `xml.dom.minidom` before handing it over.

## Steps

1. **Read and sanity-check the export.** Count goods, list the code range,
   compare with `Scale/all-xml.xml` (what changed in ArmSoft since 2026-10-02:
   goods added, removed, renamed, barcodes changed). Same code with a
   **different product** in ArmSoft and in our target = stop and show the user;
   never renumber on your own.

2. **Goods.** For every good in the target, by code:
   - not in the export → **new good** (goes in the new-goods XML);
   - in the export → compare name, unit set, `IsWeight`, barcodes.
   For every good in the export but not in the target → **ArmSoft-only**: list
   it (code, name, barcode), don't delete it.
   **ArmSoft creates goods by itself when the shop posts a supplier invoice**
   (user, 2026-10-16). Such a good has the invoice's line as its name (often
   the supplier SKU or "26x75g" in it), no barcode, no price, and **cannot be
   deleted** because the invoice is a movement on it. So before planning a
   new good for a Siruk variant, look for an invoice-made good for the same
   product (name, SKU, pack, codes above the last target code) and map the
   variant to **that** code. When an invoice-made good and one of our imported
   goods are the same product, keep the invoice-made one, move the barcodes
   and prices onto it, and list ours for deletion. Never build a new-goods XML
   for a product that has been invoiced into ArmSoft. This is how RC
   1443–1472 and Felix/Pro Plan 1474–1495 happened on 2026-10-16.
   Then every live variant in `final/siruk-source-of-truth.csv` must reach a
   good through `scale-codes-per-kg.csv` (or, for a "1 kg" row, the bag's good
   with unit 303). List any that don't.

3. **Barcodes.** Per good and unit, ArmSoft vs target:
   - missing in ArmSoft → to add; different → to fix (show both);
   - every barcode must pass the EAN/UPC check digit (5-digit scale codes
     excepted) and sit on **one good only**, across ArmSoft and the new goods;
   - **the barcode is what the till's scanner reads off the pack, digit for
     digit**: ArmSoft matches the exact string. Pro Plan 1478's bag scans as
     `07613033566547` (14 digits, leading 0). With the 13-digit
     `7613033566547` the till did not find it (user, 2026-10-16). A barcode
     the user typed from a scan or from the pack beats ours. Never strip or
     add a leading 0 to "normalise" it. Compare as strings, and treat a
     difference that is only a leading 0 as a question for the user, not
     a fix;
   - a barcode we don't have anywhere: find it with the barcode rules in
     `reference/image-sources.md` → "Barcode lookup" (official page, or two
     independent pages with every axis matching) — never derive one from a
     pattern. Unconfirmed → leave empty and list it.
   Known on 2026-10-09: Iv San Bernard Dermobrush "Fantasia" (good 0902) has no
   barcode (read it off the pack); goods 0210, 0355, 0462, 0463, 0659, 1340,
   1341 are not on Siruk and have none.

4. **Units.** A good whose Siruk product has a "1 kg" variant needs unit 303
   with the variant's PLU as its scale barcode. On 2026-10-09 goods 0009,
   0010, 0011, 0012, 0013, 0014, 0019 (Acana / Orijen 4.5 kg) had no 303 unit
   (PLU 00099, 00098, 00100, 00101, 00102, 00104, 00105).

5. **Prices.** `prices_rows()` gives the Siruk price per good + unit. If the
   export carries prices, compare and list the differences. Never invent a
   price: no Siruk variant and no row in `state/armsoft-extra-prices.csv` →
   list it as needing a price.

6. **Verify** (after an import): every good, unit and barcode from the import
   files is in the new export, with the same values. Report anything that did
   not land.

7. **Mirror the codes onto Siruk** (CLAUDE.md 10b, since 2026-10-12). Every
   Siruk variant carries `accounting_code` = its ArmSoft good code and
   `barcode` = the pack EAN (the 5-digit PLU on a `-KG` 1 kg variant). Once
   `Scale/scale-codes-per-kg.csv` and `final/siruk-source-of-truth.csv` hold
   the new goods, run `scripts/backfill-variant-codes.py --run runs/<date>`.
   It only plans. Hand the user the plan and run `--apply` only after they say
   yes: it writes to Siruk, which this skill otherwise never does.

## What to hand the user

Write everything to `final/armsoft-<YYYY-MM-DD>/`:

- `new-goods.xml` — only the goods ArmSoft does not have, in the export's
  format, taken from the target with today's barcodes.
- `update-goods.xml` — goods ArmSoft has but whose barcodes or units must
  change. Build each block from **ArmSoft's own exported block** and change
  only the barcode / unit parts, so nothing else in ArmSoft is overwritten.
  ArmSoft may or may not update an existing code on import — tell the user to
  try it on one good first, and that `changes.xlsx` lets them do it by hand.
- `prices.xlsx` — column A `Code`, column B `Price (AMD)`, then unit, unit
  code, Armenian name, English name, note. One row per good + unit (a loose
  good has a bag row and a 1 kg row). Code stored as text (keep the zeros).
- `changes.xlsx` — one sheet each: barcodes to add, barcodes to fix, units to
  add, ArmSoft-only goods, Siruk variants with no good, still missing
  (barcode / price).
- `report.md` — the counts, the decisions you need from the user, and what
  you could not do.

Then update `state/open-items.csv` (close what is fixed, add what is open),
and keep `csv/all-xml-scale.xml`, `Scale/all-xml-scale.xml` and
`Scale/scale-codes-per-kg.csv` in step with any barcode you confirmed.

## Decisions that belong to the user — ask, don't assume

- **Royal Canin 12-box goods** (22 of them, odd codes 1365–1407): Siruk
  archived the box variants on 2026-10-07 because boxes are opened and the
  pouches sold one by one. The box goods carry the 12-box EAN (Royal Canin
  mt/ie/za/au sites) and the old box price. Ask whether to import them at all.
- A code clash, a renamed good, or a barcode ArmSoft has that differs from
  ours: show both, let the user pick.
- Anything to be deleted from ArmSoft. Only our own imported goods can go.
  An invoice-made good can't be deleted, so it is always the one we keep
  (Royal Canin, user 2026-10-16: keep 1443–1472 and delete our 1342–1407
  duplicates once they are empty).

Answer in plain language: what ArmSoft is missing, what to import, in which
order (new goods → updates → prices), and what still needs a person (a pack to
read, a price to set).
