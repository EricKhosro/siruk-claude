# Final report — the PM's register vs the live site (2026-09-23)

**Compared:** `csv/AllAngineProduct.xlsx` ("Ապրանքների մնացորդներ — 15/09/26",
1,343 rows) against a **fresh full read of the demo admin taken today**:
787 products, 1,250 variants.
The xlsx and `csv/Product.numbers` hold the same 1,343 rows, name for name
and cost for cost. The only difference is that the `.numbers` copy has
`Վաճառքի գին` on 1,342 rows, where the xlsx has it on 81. Sale prices
therefore come from the `.numbers` copy (the price of record, rule 2c).

**Nothing was written to the site.** This is a read-only audit. Every open
item is in **`state/open-items.csv`**: 407 lines, 190 at priority 1.

---

## 1. Headline

| | register rows |
|---|---|
| **Live on the site** | **1,195** (89 %) |
| Missing, article code known | 23 |
| Missing, no article code yet | 125 |
| Live and priced exactly as the register says | **1,113** |
| Live, price differs from the register | 10 |
| Live, register price held for the PM (rule 2c) | 72 |

Six live variants are in no register row (`state/register/register-extras.csv`).
Those items are on the site but not in stock.

## 2. The important finding — 20 rows were matched to the wrong product

The invoice CSV (`csv/ALL_SIRUK_PRODUCTS.csv`) prints the **Trixie cat
treats 42681–42764 one row late**: the Armenian name at each article code
belongs to the previous article. The register was linked to article codes by
matching names against that CSV. As a result, **20 register rows pointed at a
neighbouring product**. On 2026-09-16 the price sync then wrote each of those
register prices onto the neighbour.

- Fixed in the local data: the 20 rows are re-mapped by name to the right
  live Trixie product. Every register cost now equals that variant's cost
  exactly, and no code is used twice (`state/register/match-overrides.json`).
- Fixed in the tooling: `scripts/match-register.py` no longer accepts a
  name match when the costs disagree, so this can't recur silently.
- **Still wrong on the site, 8 prices** (register → live today):

| Product | Register | Live |
|---|---|---|
| Premio Strips with Tuna & Whitefish 20 g | 700 | 1,100 |
| Cookies, Salmon & Catnip 50 g | 1,100 | 1,000 |
| Premio Tenders Chicken Breast 70 g | 1,400 | 1,350 |
| Freeze Dried Cat Snacks, Shrimps 25 g | 1,550 | 1,200 |
| Premio Rolls, Chicken Breast & Tuna 50 g | 1,500 | 1,100 |
| Freeze Dried Cat Snacks, Chicken Hearts 25 g | 1,100 | 1,550 |
| Cookies, Chicken & Prawn 50 g | 650 | 700 |
| **Junior Clouds 40 g** | 1,200 | **650 — below its 750 cost** (the only live rule-5 breach) |

  Three more rows in this block have a register price equal to cost, so they
  are held for you (Mini Nuggets 810, Premio Cubes Chicken 750, Premio Cubes
  Chicken & Cheese 750).
  `scripts/register-price-sync.py --run state/register --apply` corrects the
  eight. **Not run: it writes to the site.**

## 3. Prices

- **10 mismatches.** The 8 above, plus **Acana Light & Fit 11.4 kg** and
  **Acana Sport & Agility 11.4 kg**, live at 45,000 against a register price
  of 50,000.
- **72 held, not written** (rule 2c):
  - **69 rows where the register's sale price equals its cost** (64 of them
    Trixie). The site keeps its current, higher price.
  - **3 typo-level jumps:** Monge Solo Monoprotein Pork 150 g (register
    9,600 against cost 750 and our 1,000), Trixie Cat Collar 4207 (3,600 vs
    our 1,800) and Stainless Steel Bowl 0.75 l (9,400 vs our 4,700).
  Please correct them in the register or confirm them.
- Many of the 23 missing rows also have their register price equal to cost,
  which is why they were never imported (see §5).

## 4. Per-kg (the register's `Kg` column)

- 51 per-kg twins correct.
- **6 twins missing**, all Acana dog 11.4 kg: Wild Prairie 6,600/kg, Light &
  Fit 4,500, Sport & Agility 4,500, Puppy 4,000, Grasslands 5,400,
  Pacifica 5,050. `scripts/make-perkg-twin.py` creates them.
- **3 sold per kg although the register gives no `Kg`:** Acana Wild Prairie
  cat 4.5 kg, Acana Pacifica cat 4.5 kg, Simple'n'Clean Silicate Litter 5 l.
  They should be fixed-price packs.
- 17 missing rows carry a `Kg` rate: create the twin when they are imported.

## 5. What is not on the site

**23 rows with a known code**, and why they're still out:

- Price equals cost in the register, so importing would break rule 5 (the
  price is needed from you): Trixie rope toy 35718, bag dispenser 22858,
  comb 2410, cat collar 41590, three cat plush toys (45765 / 45665 / 45689),
  and the Derevenskie duck and goose sticks (711536, 208986).
- Brand with no findable site or logo, skipped on your call on 2026-09-15:
  Dogman litter tray (61001K) and Inteko (03623K).
- No brand page to take name, photo and text from (2026-09-16 research):
  8in1 Pro Digest (11244S, dropped from 8in1.eu), flexi New Comfort XS
  (042718, page gone), Mnyams purée 703823 (not on mnyams.ru), Beaphar Vit
  Bits (12625, no page prints that article) and Myau sterilised turkey pouch
  (147245).
- Ready to import. These were identified by name on 2026-09-17 but never
  written: Gemon Sterilised cat 7 kg (297277), Gemon dog 20 kg ×3
  (MM005617, MM005627, GM005607), and Beaphar Duo Active paste for dog and
  cat (BP12960, 12959).
- Club 4 Paws salmon-in-jelly pouch 85 g (142535): register price 8,300
  against a cost of 225, which is almost certainly a typo.

Brand-site research for these rows is kept in
`state/register/research-missing.json`.

**125 rows with no article code.** These have Armenian names only, with
no match in the invoice CSV and no hafo name + cost match. Each open-item line
carries the best hafo name hit to start from (rule 6: hafo → nemo/zoovet →
web, every axis matching). `scripts/identify-by-name.py` now also searches
nemo.am and zoovet.am for them.

## 6. Data quality on live products

| Issue | Count | Where |
|---|---|---|
| **No attribute family** (rule 8b) | **36 products** | all Trixie accessories: Premium One Touch / H-Harness, BE NORDIC bowls, Neon Tape Lead, CityStyle… `scripts/set-attribute-family.py --apply` |
| **No image at all** (rule 7) | **7 products + 9 variants** | Monge cat 10 kg ×4 (Indoor, Kitten, Sensitive, Adult), Club 4 Paws Premium Active and Large Breeds 14 kg, Kitten Dry Food 11 kg; Trixie BE NORDIC bowl ×3, Premium Adjustable Lead ×4, Tennis Ball 16 cm, Grooming Glove |
| Only hafo's watermarked placeholder | 18 variants | Mr. Fresh Stop It sprays, Gran Bonta Chef, the cat/dog pouch and paté lines 1050–1054, No Stress Collar, one lead colour |
| First image not a clean packshot, confirm by eye | 42 variants | carried over from the 2026-09-11 packshot audits |
| Variant axis attribute missing (rule 9a) | 12 variants | Quadro Drops (dose band), Playing Rope, Rolls, Malt Bits, Poop Bags… `scripts/backfill-variant-axes.py` |
| Other attributes | 7 | 1 missing `product-weight` (Gift Soft Sticks), 5 `size` + 1 `pet-weight-range` from the 2026-09-14 list |

Nothing else was found against the register's cost: every other live
variant's `cost_price` equals the register's cost.

## 7. Housekeeping done today

- `runs/` cleared: 1,330 files, 27 MB. Everything a later run reads moved
  to **`state/`** first, and `state/README.md` says what each file is:
  - the register inputs and hand decisions (`state/register/`, including the
    14 name identifications from 2026-09-17 that had never reached
    `match-overrides.json`);
  - the info source and price source of every imported article
    (`state/import-sources.json`, read by `build-import-ledger.py`);
  - one worklist (`state/open-items.csv`). It replaces every old
    `no-hafo-price`, `not-found`, `needs-image`, `needs-packshot`,
    `held-rows` and `no-pack-weight` CSV. Each old line was re-checked
    against today's site, and all 230 old invoice-worklist rows are now
    either live or tracked through the register.
  A safety copy of the old folders is at
  `.siruk-cache/runs-archive-2026-09-23.tar.gz` (gitignored, 12.6 MB). The
  git-tracked part is also in history. Delete the tarball whenever you like.
- Scripts no longer default to dated run folders: the register chain,
  `make-perkg-twin.py` and `build-import-ledger.py` read `state/`.
- `register-audit.py` now also checks images and placeholders, cost,
  `product-weight`, variant axes and held prices, and lists live variants that
  aren't in the register. `catalogue-snapshot.py` keeps image ids.
- A matching bug fixed: hafo writes some codes with a no-break space
  (`MG 004807`), which made 5 live Monge cat 10 kg products look missing.
- The docs that cited run files now carry the substance themselves. The
  rejected image sites are in `reference/image-sources.md`.

## 8. Suggested next steps, in order

1. Confirm the §2 remapping (spot-check a pack or two), then run
   `scripts/register-price-sync.py --run state/register --apply`. That
   fixes the 8 cat-treat prices and the 2 Acana prices, including the
   below-cost Junior Clouds.
2. `scripts/set-attribute-family.py --apply` for the 36 accessories.
3. Photos for the 7 image-less food products and the 9 Trixie variants.
4. Acana: create the 6 per-kg twins and switch the 3 wrongly per-kg packs
   to fixed price.
5. Your answers on the 72 held prices and the 9 at-cost rows in §5.
6. Import the 6 ready rows (Gemon ×4, Beaphar Duo ×2), then work down the
   125 codeless rows.
