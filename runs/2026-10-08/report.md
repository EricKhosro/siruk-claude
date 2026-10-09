# 2026-10-08 — 1 kg variants for the six 4.5 kg Acana/Orijen bags

**Environment: PRODUCTION** (`https://api.siruk.am/api/admin`). `demo-api.siruk.am`
no longer serves the API — it 301s to a Next.js storefront. The production API
accepts the same `dev@conceptstudio.club` credentials; a catalog-only service
account is still not requested.

## What was asked
A list of every product with a 2–10 kg bag and no 1 kg variant, then a 1 kg
variant added to each, priced from rivals.

## Audit
All 949 products were read individually (`GET /products/<id>`) — not filtered by
variant label, so nothing with a blank label could hide. 85 products have a mass
variant ≥ 2 kg; 6 had no 1 kg sibling. All 39 Royal Canin products were checked
by hand: every one of its 22 dry bags (4.5–15 kg) already carries a 1 kg variant.

Workbook: `missing-1kg-variant.xlsx` — sheet 1 now empty, sheet 2 the 85-row audit.

## Prices (none derived)
hafo publishes `variant_kg_price` per article; zoovet.am and nemo.am list each bag
a second time as "на развес 1 кг" / «կիլոգրամով».

| id | product | sku | 1 kg price | cost | margin | source |
|---|---|---|---|---|---|---|
| 967 | Acana Homestead Harvest | 7143712-KG | 5950 | 4511 | 31.9% | hafo 5950 + zoovet 5950 (agree) |
| 971 | Acana HP Wild Prairie Cat | 7145812-KG | 6600 | 5000 | 32.0% | hafo 6600 + nemo 6600 (agree) |
| 974 | Acana HP Grasslands Cat | 7147212-KG | 6900 | 5222 | 32.1% | zoovet 6900 (hafo has no rate) |
| 978 | Acana HP Pacifica Cat | 7146512-KG | 7200 | 5489 | 31.2% | zoovet 7200 (hafo has no rate) |
| 982 | Orijen Small Breed | 7147712-KG | 8000 | 6000 | 33.3% | hafo 8000 (neither rival stocks it loose) |
| 985 | Acana Indoor Entree | 7145112-KG | 6000 | 4511 | 33.0% | zoovet 6000 (hafo has no rate) |

Cost = bag cost ÷ 4.5, rounded. Every price beats cost. Corroboration: zoovet's
loose prices for the dog siblings (Grasslands 5400, Pacifica 5050, Wild Prairie
4700) equal what those products already charge live.

## Written
Six `sale_mode: pack` variants via `scripts/add-variant.sh` (fresh GET → append →
verify → PUT → read back): `measure_type: mass`, `content` 1000, `pack_count` 1,
label "1 kg", `initial_stock` 10, bag's gallery and attribute values copied.
New variant ids 2080–2085. No `sale_mode: weight` anywhere (PM paused it 2026-10-01).

## Checks after the write
- read-back of all six: content/price/cost/stock/images/default as intended
- `backfill-variant-axes.py --ids …` → 0 axis values to set (rule 9a clean)
- `product-types.py --check` → 6/6 pass before the write
- hafo re-check for 967/971/982 → bag and per-kg rate unchanged
- zoovet re-check for 974/978/985 → 6900 / 7200 / 6000 unchanged

## Open
The register does NOT price these six per kg — its `kg` column is the per-kg sale
price, filled for all 17 products that had a 1 kg variant and blank for exactly
these six (`register-ledger.csv`: `not-sold-by-kg`). They were added on the user's
explicit instruction (2026-10-08) with rival prices. The register's `kg` column
should be filled in to match, or the variants removed.

Pre-existing: product 969 Bountiful Catch (7144412) is also blank in the register
yet has carried a 1 kg variant at 5950 — same situation, predates this run.

## Source-of-truth and scale files

`csv/siruk-source-of-truth.csv` — 6 rows inserted after each product's bag row
(1523 → 1529 data rows). Source wording follows the file's convention; the
hafo-priced three cite hafo, the zoovet-priced three cite the zoovet loose-kilo
page (links written without the `/ru/` prefix, as the existing zoovet rows are).

`csv/Siruk-hx-303-prices-cat.xlsx` (+5) and `-dog.xlsx` (+1). These are NOT raw
`scale-303-prices.py` output: the generator emits 97 rows keyed by the ArmSoft
goods code, and the committed files carry the PLU renumbered through
`state/scale-codes.json` (ArmSoft code → sequential 5-digit scale code). ArmSoft
has no unit-303 price row for any of these goods, so there was no PLU to derive —
the six were appended by hand with the next free scale codes, following the
Bountiful Catch precedent (goods 0010, appended at PLU 00098 on 2026-10-08).

| goods | PLU | file | price/kg | Siruk name |
|---|---|---|---|---|
| 0009 | 00099 | cat | 5950 | Homestead Harvest, 4.5 kg |
| 0011 | 00100 | cat | 6600 | Highest Protein Wild Prairie, 4.5 kg |
| 0012 | 00101 | cat | 6900 | Highest Protein Grasslands, 4.5 kg |
| 0013 | 00102 | cat | 7200 | Highest Protein Pacifica, 4.5 kg |
| 0014 | 00103 | dog | 8000 | Small Breed, 4.5 kg |
| 0019 | 00104 | cat | 6000 | Indoor Entree, 4.5 kg |

Names are verbatim from `csv/all-xml-scale.xml` (`Name` / `LongName`), as the
generator writes them. After the edit: 104 PLUs across both files, contiguous
1–104, no duplicates, both files still ascending by PLU.

`state/scale-codes.json` now holds all seven new entries (the six above plus
Bountiful's 0010 → 00098, which was missing) so a re-run of `scale-export.py`
cannot renumber the scale.

**Still to do by hand:** the `.numbers` companions
(`Siruk-hx-303-prices-cat-Print.numbers`, `Siruk-hx-303-prices-dog.numbers`) and
ArmSoft itself — these goods need a real unit-303 price row, after which the
generator will produce the PLU instead of us assigning it.
