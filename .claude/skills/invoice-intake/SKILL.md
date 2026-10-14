---
name: invoice-intake
description: Step 0 of a batch import. Turn the invoices received for a new batch of products (PDFs, scans, photos or spreadsheets in any language, with any headers) into one Excel, batches/<batch>/batch.xlsx, the batch's source of truth, checked against every invoice's printed total, then start /add-products from it. Use when the user hands over invoices, says a new batch arrived, or asks to start an import from invoices.
argument-hint: [invoice files or folder] [batch name]
---

Turn this batch's invoices into one checked Excel, then start the import from it.
Read `CLAUDE.md`, then `reference/invoice-intake.md` (the folder, the
user's decisions, the header table, the JSON shape) before reading an invoice.

Invoices / batch name:

$ARGUMENTS

1. **Batch folder.** `batches/<today>-<supplier or name the user gave>/`. Copy
   the originals into `invoices/` unchanged, and never edit them. List them
   back to the user (file, pages) so a missing invoice is caught now.
2. **Transcribe each invoice** into `lines/<n>.json` (shape in the reference).
   - PDFs with the `pdf` skill: its text when it has a text layer, else read
     the page images.
   - Photos and scans with Read.
   - xlsx/csv with openpyxl or csv.

   Map the supplier's headers to our fields with the reference table and
   record the mapping in `headers`. Copy every line, digit for digit and
   name as printed. Anything you can't read goes in `unreadable`, never a
   guess. Cases sold singly get `units_per_item`. Big invoices: one
   `general-purpose` agent per invoice (or per ~10 pages), each given the
   reference doc and its output path. Check their files yourself.
3. **Build:** `uv run --with openpyxl python3 scripts/build-batch-sheet.py batches/<batch>`.
   - A **total mismatch** or a **line-total** question means a misread: open
     the original at that line, fix the JSON, then rebuild with `--force`.
     Only what the original really can't settle stays a question.
   - A **currency** question → ask the user for the AMD rate (or landed cost),
     put it in the invoice's `fx_rate`, and rebuild. Never look one up.
4. **Gate** (user, 2026-10-14):
   - **Exit 0** (no questions, every invoice reconciles) → say so in two lines
     and go straight on to step 5.
   - **Exit 2** → stop. Give the user the path to `batch.xlsx` and a short
     list of its Questions, and wait. Their answers go in the sheet's
     `Answer` column, or into the xlsx itself (any cell of Products). Then run
     `build-batch-sheet.py batches/<batch> --from-xlsx`, which must exit 0.
     Never `--force` over an xlsx the user has edited.
5. **Import:** run the `add-products` skill on `batches/<batch>/products.csv`
   (`prepare-run.py batches/<batch>/products.csv --run runs/<date>`). The CSV
   costs are our cost, the sale price still comes from hafo → zoovet/nemo →
   sibling → recommendation, and stock is 10 (CLAUDE.md rules 1–5, 10a).
6. **Keep the source of truth current.** A cost or identity corrected later
   in the run goes back into `batch.xlsx` (Products sheet, plus a `Notes`
   line), then `--from-xlsx`. The run's `report.md` links the batch folder.
   Commit `batches/<batch>/` when the run closes.
