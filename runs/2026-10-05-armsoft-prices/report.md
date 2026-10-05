# ArmSoft import workbook + the 3 priced goods — 2026-10-05

## What this run produced

1. `csv/Siruk-hx.xlsx` filled for the ArmSoft import (all four sheets), from
   `csv/all-xml-scale.xml` — generator `scripts/build-armsoft-import.py`.
2. The 13 goods that still have no sale price, as
   `runs/2026-10-05-armsoft-prices/no-hafo-price.csv` for the PM.
3. One new product written to **production** siruk.am.

## 1. The workbook

| Sheet | Rows | Source |
|---|---|---|
| MATERIALS | 1,439 | one row per `<Goods>`, all 39 columns 1:1 with the XML elements |
| PRICES | 1,536 | `01` / good `Code` / unit / 2026-10-05 / AMD / the live Siruk sale price |
| MTQUNIT | 1,536 | one row per `<QuantityUnitPart>` + `<Coef>`; the 97 `<AltUnit>` rows flagged `1` |
| MTBARCODES | 1,490 | one row per `<MTBarCode>` |

Prices come from `runs/2026-10-04-rival-prices/siruk-source-of-truth.csv` through
`Scale/scale-codes-per-kg.csv`, which already joins each source-of-truth variant
to its ArmSoft good. A good sold loose gets two rows under one code: **303** =
its "1 kg" variant price, **003** = its bag price (good 0001, Monge BWild Wild
Boar 12 kg → 42,000 and 3,700). 97 goods, matching the 97 that carry both units.

Checks run after writing: MATERIALS codes identical to the XML and in XML order,
no required field empty; MTQUNIT and MTBARCODES reproduce the XML exactly; no
duplicate good/unit; no barcode shared between goods; every PRICES unit is a
real unit of that good; no duplicate (code, unit); every row `01` / AMD /
price > 0.

Two decisions taken without asking:
- Goods **0321** and **0326** (Gemon paté) each have two Siruk variants, one a
  `-OLD` duplicate, both at 800 — one PRICES row each.
- Good **1341** is the only good in the XML with `<VAT>true</VAT>`. Carried
  through faithfully, but it looks like a data slip — worth checking in ArmSoft.

MTQUNIT mirrors the XML, including each good's main unit, on the user's choice.

## 2. Prices for the 16 goods not yet on Siruk

Searched for all 16: hafo by article code, by the full 6,627-product local
catalogue dump and by EAN; zoovet's whole 344-item Trixie list plus live search;
nemo by name. Three got a price (`state/armsoft-extra-prices.csv`), 13 did not.

| Good | Price | Source |
|---|---|---|
| 0469 | 1,100 | hafo SKU 703823 + EAN 4610011703829 + variant name all match |
| 0471 | 3,050 | hafo SKU 10778S + EAN 4048422107781 |
| 0962 | 1,600 | sibling rule 2a — the cost-1,000 Trixie Batik Collar (variant 1025) |

**Rejected:** hafo's hit on `2410Tx` is a collision with Tetra `TT 24101`, an
aquarium filter. zoovet prices the 41590 collar at 950, below our 1,000 cost
(rule 5), so the sibling price stands and is higher anyway.

### Identity work that did land

trixie.de prints our register EAN on each article page, which confirmed six
Trixie rows that earlier runs had parked as unidentified
(`state/armsoft-trixie-identities.csv`):

| Good | Article | Official product |
|---|---|---|
| 0898 | 22858 | Poop Bag Dispenser, elastic loop |
| 0947 | 2410 | Lice Comb, Flea and Dust Comb **for cats** |
| 0962 | 41590 | Collar, Reflecting, removable bell |
| 1265 | 45765 | Cat Toy Plush Bird, with feathers |
| 1303 | 45665 | Bear |
| 1304 | 45689 | Monster |

Good 0947's register name is wrong: article 2410 is a **cat** lice/flea comb,
not the dog rotating-pin comb the register describes. Good 0962's EAN does not
embed its article number, unlike the other five — that is not a mismatch, the
official page prints exactly that EAN.

## 3. Written to production

### Good 0962 → product 1340 — CREATED

- Trixie article **41590** "Collar, Reflecting", EAN 4011905692487 confirmed on
  trixie.de; trixie.es independently calls it "cat collar, fluorescent, various".
- Name `Collar, Reflecting`, slug `trixie-collar-reflecting`, brand 8 (Trixie),
  category **79** (Cat → Collars, Leashes & Harnesses), product type **8**
  Accessories.
- Variant **2078**, sku `41590`, label "various colours", **1,600 AMD**,
  cost 1,000, stock 10, no net content (a collar — `ALLOW_NO_SIZE=1`, as the
  Batik sibling also has none).
- Attributes: `material` → **Nylon** (311), evidence the register's "Վզնոց
  **նեյլոնե** կատվի" and the packshot's nylon webbing; `color-family` →
  **Color Varies** (339), evidence trixie.de "Colour: various" / trixie.es
  "varios". `size` left empty — no dimension is printed anywhere.
- Gallery: 5 official trixie.de CDN images — 4 `PHO_PRO_CLIP` packshots then the
  group shot. The lead image was looked at before writing: a clean packshot of
  the pink collar with fluorescent paw prints, bell and Snap & Easy buckle, no
  animal or scene. All 5 verified HTTP 200 with real bytes after upload.
- Translations: `ru` "Ошейник светоотражающий", `hy` "Վզնոց լուսանդրադարձիչ",
  both read back from the API in their own locale.
- `FORCE=1` was needed: the guard flagged product 894 "Junior Collar,
  Reflecting". That is article 41685, the **kitten** collar with a flower motif
  on a different trixie.de page — a genuinely different product.

### Good 0469 → NOT imported, already live

Article **703823** is the renumbered code for the Mnyams tuna & shrimp purée
that is already on Siruk as **variant 1622** of product 1137, under the older
sku **540693**. hafo lists both codes as separate rows, both at 1,100
(EANs 4610011703829 new, 4620202540690 old), and the four siblings already use
the 7038xx codes. So the PRICES row for good 0469 at 1,100 is right and nothing
needed creating. Open item: update variant 1622's sku to 703823 so the scale
export can link the good — after checking which barcode the pack prints.

### Good 0471 → HELD, pack size disputed

8in1 Delights Chicken Balls, article 10778S, EAN 4048422107781.
**Our EAN is the M pack, 2 pieces — not S.** Three EAN-keyed sources agree
(upcitemdb "Medium"; aumondedesanimaux.fr URL `delight-m-x2`; hubun.pl
"Delights balls M … 2szt"), and the S pack is the sibling EAN 4048422107798
(e.leclerc "S POULET X4 BALLS 36G", bricomarche "Delight S x4", recordit.com).
hafo and the register both have the size letter wrong.

The net weight is still contested — hafo 40 g, laroygroup.com's article
204107781.000 titled "Delights balls 36 xg", upcitemdb "6 × 80g" — and Treats
is a sized product type, so content is mandatory. 8in1.eu has only the XS 36 g
page (the `/S` path serves it), so there is also no size-specific photo, which
would mean `needs-image.csv` with reason "other size". Not written: it would
have baked in a possibly-wrong pack size. **Need the weight read off the pack.**

The hafo price 3,050 is still keyed to our exact article code, so the PRICES row
for good 0471 stands.

## 4. The last 13 prices — same-brand comparables (approved 2026-10-05)

With no rival carrying these rows, the user approved pricing them from
**same-brand products on our own site at the identical cost**. The markup is set
per brand, not globally — a flat x1.6 would have overpriced two brands badly:

| Brand | Modal markup | Consistency |
|---|---|---|
| Trixie | x1.60 | 701 of 792 |
| 8in1 | x1.55 | 30 of 30 |
| Kaskad | x1.60 | 13 of 14 |
| Mnyams | x1.65 | 6 of 10 |
| Beaphar | x1.55 | ~40 of 44 |
| **Club 4 Paws** | **x1.20** | 19 of 22 |
| **Myau** | **x1.29** | 7 of 8 |

**The method was validated on the three rows where an independent price already
existed, and reproduced each exactly:** 8in1 good 0471 cost 1,965 x1.55 = 3,050
= the hafo price; Trixie good 0962 cost 1,000 x1.60 = 1,600 = the sibling price
now live; Kaskad good 1046 cost 1,465 x1.60 = 2,350 = the hafo row our EAN
matched and which had been rejected on its name.

| Good | Brand | Cost | Price | Anchor |
|---|---|---|---|---|
| 0210 | Club 4 Paws | 225 | **400** | the FISH variant (Mackerel in Gravy) at the same cost; the six meat variants are 270 — user's call |
| 0355 | Myau | 160 | **220** | all 7 Myau Adult Cat Pouches at 220 (their cost 170) |
| 0462 | Mnyams | 515 | **850** | 4 of 5 same-cost Crunchy Pillows — user's call over the 800 outlier |
| 0463 | Mnyams | 515 | **850** | same |
| 0659 | Trixie | 1,310 | **2,100** | Ball 8 cm, Chicken 14 cm, Dragon 20 cm, Denta Fun Ball |
| 0898 | Trixie | 1,250 | **2,000** | Playing Rope Tugger, Hedgehog Ball, Set of Tubes, Squirrel |
| 0947 | Trixie | 1,310 | **2,100** | same cost-1,310 cluster |
| 1046 | Kaskad | 1,465 | **2,350** | the same collar at 12 mm (625 to 1,000) and 35 mm (2,310 to 3,700) |
| 1265 | Trixie | 1,000 | **1,600** | Rope Ring, Ball 7 cm, Mouse in display 9 cm |
| 1303 | Trixie | 1,000 | **1,600** | same |
| 1304 | Trixie | 1,000 | **1,600** | same |
| 1340 | ? | 1,675 | **2,600** | three Beaphar collars at exactly cost 1,675 — brand unconfirmed |
| 1341 | Monge | unknown | **600** | the three Monge VetSolution CAT 100 g products (Urinary Struvite, Renal & Oxalate, Recovery), all cost 470 to 600 — same line, species, format and size |

Every one beats its cost (rule 5), except 1341 where the cost is unknown; its
siblings' 470 is the likely figure and needs confirming.

**These are comparables, not sourced prices.** They are tagged as such in
`state/armsoft-extra-prices.csv` with the evidence per row, and flagged in
`state/open-items.csv` for a recheck against a real source when one appears
(CLAUDE.md rule 4).

PRICES is now **1,536 rows covering all 1,439 goods** — none left unpriced.

## Outputs

- `csv/Siruk-hx.xlsx` — the ArmSoft workbook
- `runs/2026-10-05-armsoft-prices/no-hafo-price.csv` — the 13 unpriced goods
- `runs/2026-10-05-armsoft-prices/import-priced.csv` — the 3-row import input
- `state/armsoft-extra-prices.csv` — the 3 sourced prices with evidence
- `state/armsoft-trixie-identities.csv` — the 6 confirmed Trixie articles
- `state/register/register-status.json` — 00964 → product 1340 / variant 2078;
  00469 → the existing product 1137 / variant 1622
- `state/open-items.csv` — 17 new rows

## Flagged for the user

1. **The 13 prices** — no rival carries them; `no-hafo-price.csv` has a per-row
   reason and an empty `Sale Price (AMD)` column to fill.
2. **Good 0471's pack weight** — 36 g or 40 g, and it is the M pack, not S.
3. **Good 1341** — not in the register, so no cost *and* no price; also the only
   `<VAT>true</VAT>` good in the XML.
4. **Variant 1622's sku** — 540693 is the retired code for article 703823.
5. **Product 1200** (8in1 Delights Bones) on production has an empty category
   list. Not touched; may be worth a catalogue-wide sweep.

No `not-found.csv`, `sibling-priced.csv` or `needs-packshot.csv` this run:
the one product written had a confirmed identity and a clean official packshot.
`needs-image.csv` is empty too — good 0471, the only row that would have gone on
it, was held before writing.

## Wanted but missing

Nothing. Every attribute value the one written product needed was already in the
menu (`material` → Nylon, `color-family` → Color Varies). No attribute, value,
category or product type was created in this run.
