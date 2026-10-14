# batches/: one folder per batch of new products

Each folder is the **source of truth** for one batch. It holds the invoices as
received, their transcriptions, and `batch.xlsx` (Products · Lines · Invoices
· Questions), plus `products.csv` exported from it for `/add-products`. Built
by `/invoice-intake` (`reference/invoice-intake.md`). Committed. It outlives
the run folder, but photos of invoices are gitignored like every image.

Batch 1 (2026-09) predates this step. Its invoice ledger is
`csv/products.csv`.
