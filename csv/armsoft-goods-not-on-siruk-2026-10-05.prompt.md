Import the 16 ArmSoft goods that are not on Siruk yet.

Input: `csv/armsoft-goods-not-on-siruk-2026-10-05.csv` (Shape C from
`reference/csv-formats.md`, plus `Product Type`, `Register No`,
`ArmSoft Good Code`, `EAN` and `Why not imported before`).

Target: **production siruk.am** (`api.siruk.am`, token `.siruk-token-prod`).
Confirm the token works (`GET /account` → 200) before anything else, and stop
and ask me if it doesn't.

Run `/add-products csv/armsoft-goods-not-on-siruk-2026-10-05.csv`, following
CLAUDE.md as usual. Notes for this batch:

1. **Read `Why not imported before` on every row first.** These 16 were held
   back on purpose in earlier runs; don't repeat a dead end it already
   records.
2. **Price.** `Sale Price (AMD)` is empty on purpose: price every row from
   hafo, then zoovet/nemo by name, then the sibling rule (CLAUDE.md 2–2b).
   - **Three are already sourced** (2026-10-05, `state/armsoft-extra-prices.csv`,
     evidence per row): good **0469** → 1,100 and **0471** → 3,050 from hafo by
     article code; **0962** → 1,600 from its cost-1000 sibling, Siruk variant
     1025 (Trixie Batik Collar with Bell). Use those, don't re-derive them.
   - The other 13 were re-checked the same day against hafo (by code, by the
     whole local catalogue dump and by EAN), zoovet's Trixie list and nemo by
     name, and none could be priced — see `state/open-items.csv`,
     area `armsoft prices`, for exactly what each one needs. Note hafo's
     `2410Tx` hit is a **collision with Tetra `TT 24101`** (aquarium filter),
     not our Trixie comb.
   - The old register sale prices are not a price source: on 8 rows they
     equal cost, and good 0210's 8,300 is a typo.
   - A row no rival prices goes on `no-hafo-price.csv` for me. Never invent
     a price.
3. **Identity.**
   - 0462 and 0463 (Mnyams pillows) have no article code: identify them by
     name, every axis matching (rule 6).
   - 1340 (good 01342, insect-repellent velvet cat collar, code 1000387) has
     no known brand.
   - 1341 (Monge VET Gastrointestinal cat pâté, 100 g) is not in the PM
     register, so it has **no cost**: ask me for it before writing.
4. **EAN.** Where the `EAN` column is filled, use it for the barcode lookup
   (rule 7). The Trixie EANs come from trixie.de's GTIN fields.
5. **Stock.** `initial_stock` is 10 on every variant, whatever `Qty Received`
   says (rule 10a).
6. **Search before create** (rule 9). 0471 (8in1 Chicken Balls S) may belong
   on an existing 8in1 product as a variant; the same goes for 1046 (Kaskad
   braided leather collar 25 mm) next to the 30 mm one (SKU 00030302).

After the import:
- Record each new variant against its `Register No` in
  `state/register/register-status.json` (`variant_id`, `product_id`, `code`),
  so `scripts/scale-export.py` links it to its ArmSoft good next time.
- Write the usual report plus the two CSVs, and fold anything still open into
  `state/open-items.csv`.
