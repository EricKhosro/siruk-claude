# Input CSV shapes

In every shape, **a price column is our cost**. The sale price comes from hafo
(`reference/pricing.md`). CSV always wins over brand-site data for identity
fields (pack weight, flavour…).

## Shape C — invoice extract (`csv/products.csv`, current)

Columns: `Article Code`, `Brand`, `Product Name (as printed)`, `Species`,
`Category`, `Buy Price (AMD)`, `Qty Received`, `Sale Price (AMD)`,
`Invoice Date`, `Source`, `Brand Source`.

- `Article Code` → hafo lookup key and variant **SKU**
- `Brand` is **derived** (`Brand Source` says how); only `article-code suffix`
  is reliable — see `reference/hafo.md`
- `Buy Price (AMD)` → `cost_price`
- `Sale Price (AMD)` → empty = fetch from hafo; filled = the user's figure
- `Qty Received` → `stock`
- `csv/productsneedsreview.csv` holds rows without a resolvable brand

## Shape A — starter product list

Columns: `#`, `Product Name`, `Brand / Vendor`, `Category`, `Buy Price (AMD)`,
`Sale Price (AMD)`, `Margin %`, `Qty`, `Total Cost (AMD)`, `Total (USD)`,
`Priority`, `Notes`. Headers may contain quoted newlines.

- `Product Name` → brand-site search term and admin Name (brand stripped)
- `Brand / Vendor` → brand + which official site
- `Category` → admin categories (map in `reference/product-rules.md`)
- `Buy Price (AMD)` → `cost_price`; `Sale Price (AMD)` as in Shape C
- `Qty` → stock (default 10 if empty); `Priority` → import order;
  `Notes` → hints (which pack/flavour); `Margin %`, totals → ignore

## Shape B — vendor price sheets (`Vendors_Siruk - *.csv`)

Armenian-headed export, one sheet per vendor block. Columns: `Կոդ` (article
code), `Անվանում` (product string), `Unit H/S Cost`, `R/Price`, `PRICE/KG`.
Numbers may be quoted with thousands separators and padding (`"  21,500 "`);
`-` = unavailable.

⚠️ Sheet names do not describe contents: the `Royal Canin 1` sheet held 191
Schesir + 65 Stuzzy rows and no Royal Canin. Derive the brand from the row.

- `Կոդ` → SKU minus the `W-` prefix (`W-21123003` → `21123003`)
- `Անվանում` → resolve to the real product; **not** the admin Name
- `Unit H/S Cost` → `cost_price`. `R/Price` is the vendor's suggested retail,
  **never a sale price**: hafo first, always. If a sheet carries `R/Price` for
  rows hafo cannot price, ask the user before using it (2026-09-10)
- `R/Price` blank → not stocked; skip the row
- `PRICE/KG` present → dry-food bag, `pricing_type: per_kg`; it is the vendor's
  rounded rate, not ours
- no `Qty` → stock 10; no Brand → `SCH`/`SCHESIR` = Schesir, `STUZZY`/`STZ` =
  Stuzzy; no Category → species from the brand site (Schesir `BAG DRY
  MAINTENANCE` 10 kg is cat, 12 kg is dog)

**Prices are per retail unit, not per case.** Strip the leading multiplier:
`12X70G` = a 70 g can, `6X1,5KG` = a 1.5 kg bag, `12X6X15G` = a 6×15 g pouch
pack, `1X12X80G` = a 12×80 g variety box.

### Decoding vendor strings (Schesir, verified 2026-08-13)

- `AD` = **After Dark** (the only 80 g format), not Adult. Rows spelling
  `AFTER DARK` out are the variety packs. `BABY` and `SILVER` are 70 g lines.
- `WHOLEFOOD` = "in broth"; `VELVET MOUSSE` = "in mousse"; `JEL`/`JELLY` =
  "in jelly"; `PATE` = "in paté".
- Flavours: `POLLO` chicken, `MANZO` beef, `VITELLO`/`VIT` veal, `PROSC.` ham,
  `PESCE` fish, `TONNO` tuna, `SALMONE` salmon, `AGNELLO` lamb, `ANATRA` duck,
  `CONIGLIO` rabbit, `TACCHINO` turkey, `MAIALE` pork, `CINGHIALE` boar,
  `TROTA` trout, `TRIPPA` tripe, `ZUCCA` pumpkin, `CAROTE` carrots, `PISELLI`
  peas, `MELA` apple, `ALICETTE` anchovies, `GAMBERETTI` prawns, `CALAMARI`
  squid, `SGOMBRO` mackerel, `SPIGOLA` seabass.
- Stuzzy: `BOCCONCINI` chunks, `SFILACCETTI` shreds, `PATE` paté,
  `MONOPR.`/`MONOP.` monoprotein.
- Armenian prefixes: `Կատվի կեր` cat, `Շան կեր` dog, `Ձկան յուղ` fish oil.
  ~60% of rows have none.

Normaliser: `scripts/normalize-vendor-csv.py`.
