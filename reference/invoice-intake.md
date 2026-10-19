# Invoice intake: step 0 of every batch (user, 2026-10-14)

A new batch starts from the **invoices** we received for it, not from a
prepared CSV. They come as PDFs, scans, phone photos or spreadsheets, in
Armenian, Russian, English or the supplier's own language, each with its own
headers. Step 0 turns all of them into **one Excel per batch**,
`batches/<batch>/batch.xlsx`. That file is the batch's **source of truth**:
the import (`/add-products`) reads only the CSV exported from it, and a
correction goes into it, not into a run folder.

Skill: `/invoice-intake`. Script: `scripts/build-batch-sheet.py`.

## Folder

```
batches/<YYYY-MM-DD>-<supplier or name>/
  invoices/        the originals, untouched (photos are gitignored like every image)
  lines/<n>.json   one transcription per invoice (the shape below)
  batch.xlsx       Products · Lines · Invoices · Questions (built by the script)
  products.csv     Shape C (reference/csv-formats.md), exported from the Products sheet
```

`batches/` is committed. It outlives the run, like `state/`.

## Decisions (user, 2026-10-14)

- **Cost = unit price including VAT.** A net price + VAT invoice is grossed up
  with the line's own VAT when printed, else the invoice's VAT rate. The
  printed figures stay in the Lines sheet.
- **Foreign currency: ask the user for the rate** (or the landed cost) per
  batch. It goes in the invoice's `fx_rate`. Never look one up or guess. Until
  it is set, the invoice's costs are blank and the row cannot be priced
  (rule 5 needs a cost).
- **Review gate: only when there are questions.** The Questions sheet empty
  and every invoice reconciling with its printed total → go straight on to
  `/add-products`. Otherwise stop, give the user the sheet, and wait.

## Reading an invoice

Transcribe **every** line, including service lines (delivery, discounts)
recorded with a `note`. Never skip a line because it looks irrelevant: the
printed total check depends on it. Read the original's own headers and map
them to our fields. Write the mapping in `headers` so the Invoices sheet
shows how each one was read.

| Our field | Armenian | Russian | English / other |
|---|---|---|---|
| `code` | Կոդ, Ապրանքի կոդ, Արտիկուլ | Артикул, Код, Код товара | Code, SKU, Art., Item no., Codice, Artikelnr. |
| `name` | Անվանում, Ապրանքի անվանում | Наименование, Товар, Номенклатура | Description, Product, Item, Descrizione |
| `unit` | Չափման միավոր, Միավոր | Ед., Ед. изм. | Unit, UoM, U.M. |
| `qty` | Քանակ | Кол-во, Количество | Qty, Quantity, Q.tà, Menge |
| `unit_price` | Գին, Միավորի գին | Цена | Price, Unit price, Prezzo, Preis |
| `line_total` | Գումար, Արժեք | Сумма, Стоимость | Amount, Total, Importo, Betrag |
| `line_vat` | ԱԱՀ, ԱԱՀ գումար | НДС, Сумма НДС | VAT, IVA, MwSt |
| `barcode` | Շտրիխ կոդ | Штрихкод, EAN | Barcode, EAN, GTIN |
| `supplier_rrp` | Մանրածախ գին | Розн. цена, РРЦ | RRP, Retail price |
| `printed_total` | Ընդամենը, Ընդհանուր | Итого, Всего к оплате | Total, Grand total, Totale |
| `printed_subtotal` | Ընդամենը առանց ԱԱՀ | Итого без НДС | Subtotal, Net total, Imponibile |

When a column's meaning is unclear (two price columns, a discount column), say
which one you used in the line's `note`. Don't guess silently.

- **As printed, digit for digit.** Names stay in their language and spelling
  (the identity steps read them). Numbers are copied as they appear, without
  conversion.
- A cell you cannot read → its field name in `unreadable`. Never a guess.
- **Cases.** A line priced per case (`12X70G`, `уп. 6 шт`) that we sell one by
  one gets `units_per_item` (12). The script divides the cost and multiplies
  the qty. A case we sell whole stays at 1. Not sure → leave it out, and the
  script asks.
- `supplier_rrp` is the supplier's suggestion, **never our sale price**
  (CLAUDE.md rule 1). It is kept in the Lines sheet only.
- Spreadsheet invoices: read the cells with openpyxl, but still write the same
  JSON, so every invoice goes through one check.

## The transcription (`lines/<n>.json`)

```json
{
  "file": "invoices/hafo-0412.pdf",
  "supplier": "Hafo LLC", "invoice_no": "0412", "date": "2026-10-10",
  "language": "hy", "currency": "AMD", "fx_rate": null,
  "prices_include_vat": true, "vat_rate": 20,
  "printed_subtotal": null, "printed_total": 26900,
  "headers": {"Կոդ": "code", "Անվանում": "name", "Քանակ": "qty", "Գին": "unit_price", "Գումար": "line_total"},
  "lines": [
    {"page": 1, "line": 1, "code": "40261Tx", "name": "Լցանյութ կատուների գրանուլ 5 լ",
     "unit": "հատ", "qty": 2, "unit_price": 3655, "line_total": 7310,
     "line_vat": null, "barcode": "", "units_per_item": 1, "supplier_rrp": null,
     "unreadable": [], "note": ""}
  ]
}
```

Required: `file`, `date`, `currency`, `prices_include_vat`, and per line `name`,
`qty`, `unit_price`. Everything else when printed. `fx_rate` = AMD per one
unit of `currency`, from the user.

## What the script checks and builds

`uv run --with openpyxl python3 scripts/build-batch-sheet.py batches/<batch>`

- **Line:** qty × unit price = line total (±1 or 0.5 %).
- **Invoice:** the sum of the lines = the printed total. When prices exclude
  VAT, the subtotal is checked against the lines, and the total against lines
  + VAT. A mismatch means a misread or missing line: re-read the original
  before you answer the question yourself.
- **Products sheet:** one row per article code. A codeless line keys by its
  name (rule 6 identifies it later). Qty is summed in retail units. When the
  cost differs between invoices, the latest invoice wins and the row is
  flagged. Brand / Species / Category are guesses from
  `build-product-catalogue.py`'s batch-1 rules. **Brand is a hint**: the EAN
  prefix and hafo decide (memory: CSV Brand column is unreliable).
  `Sale Price (AMD)` is left empty.
- **Questions sheet:** every doubt, one row each, with an empty `Answer`
  column for the user.

The user's edits go in `batch.xlsx`. Then `--from-xlsx` re-exports
`products.csv` (exit 2 while a question has no answer or a row has no cost).
Rebuilding from the JSON needs `--force` and **discards edits in the xlsx**.
Fold any answer back into the JSON first, or make that edit in the xlsx only.

## Into the import

`/add-products batches/<batch>/products.csv` →
`scripts/prepare-run.py batches/<batch>/products.csv`. From here the hard
rules apply unchanged: identity by code, the sale price from hafo → zoovet /
nemo → sibling → recommendation, initial stock 10 whatever the qty.
`Qty Received` is kept for the record only.

## ArmSoft makes its own goods from the invoice (user, 2026-10-16)

When the shop posts the same invoice in ArmSoft, ArmSoft adds a good for
every new line by itself. The good is named from the invoice line, with no
barcode and no price, and **it can't be deleted** because the invoice is a
movement on it. Those codes are the batch's real ArmSoft codes. After the
import, `/armsoft-sync` maps each new Siruk variant onto its invoice-made
good and only adds barcodes, units and prices. It never creates a second
good for the same product (`armsoft-sync` skill, step 2).
