# runs/

One folder per run (`runs/<date>/`): logs, plans, backups and that run's report.
Scratch, and gitignored: only this README is committed. Clear it once the run is
closed. Anything a later run needs goes in `state/` (see `state/README.md`);
open items go in `state/open-items.csv`.

Cleared 2026-09-23; everything up to then is summarised in
`state/final-report-2026-09-23.md`.

Cleared again 2026-10-14 (batch 1 closed: imported, live on api.siruk.am, synced
with ArmSoft). Every run folder from 2026-09-23 to 2026-10-13, plus the dated
review workbooks from `final/` and the old exports from `Scale/`, was moved to
`~/Siruk-archive/batch-1-2026-10-14/` on the project Mac, outside git. A
`runs/<date>/…` path cited in `reference/` or `state/open-items.csv` points
there. The barcode sources `scripts/scale-export.py` reads were moved to
`state/barcodes/`.
