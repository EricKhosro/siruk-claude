# 2026-08-13 — Schesir product/variant regrouping

Reported: several storefront pages look like the same product at a different
pack size, and the three Born Carnivore 255 g pages look like they should be
variants.

## What the URLs actually meant

`/product/<slug>/dp/<id>` — **`dp` is the VARIANT id, not the product id.**

| Reported URL | Really |
|---|---|
| `…/schesir-flavored-snacks-283g/dp/171` and `/dp/172` | variants Bacon / Chicken of **product 119** |
| `…/schesir-born-carnivore-pollo-uovo-255g/dp/206`, `/dp/214`, `/dp/215` | three variants of **product 153** |
| `…/schesir-training-snacks-flavoured-with-chicken-113g/dp/115` | **product 101** — a genuinely separate product |

So the Born Carnivore three **were already variants**; the training snacks were
not, and that part was a real import bug.

## Storefront bug (NOT in this repo — for the Siruk dev team)

The category listing renders **one card per variant** while `/api/search`
renders **one card per product**. Three variants therefore produce three
near-identical category cards no matter how the data is grouped — merging
products does not reduce the card count. Either the listing should collapse to
one card per product (matching search), or the cards need to show the variant
label so they are distinguishable.

Verified after the fix: `/dog/dog-treat/` still shows 3 cards for the single
3-variant product 119 (`/dp/171`, `/dp/172`, `/dp/226`).

## Root causes — all in `scripts/plan-schesir.py`

CLAUDE.md's shelf test defines the variant axes as **pack weight, flavor,
texture**. The product grouping key used two of the three as *product*
discriminators, plus parser residue:

1. **`unit_g` in the product key** — the same range at a different pack size
   became a different product. Split the 113 g training snack from the 283 g.
2. **`texture` in the product key** — same violation; split the broth / paté /
   jelly formats of one range apart.
3. **`&`-joined flavors never parsed.** `norm()` splits on `/` but not `&`, so
   `POLLO&UOVO` missed `FLAVOR_MAP` and fell into `extra` — which *is* part of
   the key. 5 rows hit this, 4 of them Born Carnivore. It also left variant 206
   with **no flavor attribute** and all three labels reading `"255 g"`.
4. **Unknown fields acted as discriminators.** Container is read off the matched
   site handle; `flavoured-with-chicken-6x113g` is the one Schesir product with
   no article code in its image filenames (`ALL_MAIN_<uuid>.jpg`), so it failed
   the code match, got a null container, and split off on that alone.
5. **Variant labels were flavor-only** with a pack-weight fallback, so siblings
   could end up labelled identically.

`scripts/fix-schesir-leftovers.py` had already hand-patched Born Carnivore
(item 4 of its docstring) — a band-aid over cause 3, which is why 153's variants
were merged but still carried the broken labels.

## Fixes

`scripts/plan-schesir.py`
- `parse_vendor` splits `&`-joined flavor tokens, but only when *every* part is
  a known flavor (so `M&S` stays one token and is filtered as noise).
- product key is now `(species, line, container, multipack, extra)` — pack
  weight and texture removed. `extra` stays: it carries the sub-range
  ("Training", "Meatballs", "Maintenance"), which is a different shelf product.
- a group whose species or container is *unknown* is folded into the one group
  that agrees on every known field (left alone if several match).
- product names drop an axis as soon as it varies; ranges with no line tag fall
  back to `<Species> <Container>` instead of a bare size.
- new per-variant `label` built from the axes that actually vary.

`scripts/import-schesir.py`
- variant label comes from the plan's `label`.
- `attrs_for` reads texture off the variant (it is a variant axis now).

Result: **81 → 70 planned products** from the same 129 priced rows. No new
attribute-combination collisions (the 3 that remain are pre-existing — see
below).

## Live catalogue repair

`scripts/regroup-schesir.py` (new) replays the corrected plan onto the live
catalogue. It keeps the live product names (already cleaned by
`fix-schesir-names.py`) and only renames a product that actually merged, and
then only to strip an axis that now varies.

**125 → 119 products.**

| Kept | Absorbed | Result |
|---|---|---|
| 105 After Dark in Broth 80g | 100 After Dark in Paté 80g | After Dark 80g, 8v |
| 99 Tuna in Jelly 85g | 118 Broth 85g | Cat Can 85g, 8v |
| 109 Jelly 150g | 113 Chicken Fillets 150g | Dog Can 150g, 7v |
| 116 Baby Aloe Kitten 140g | 125 Chicken w/ Aloe Kitten 85g | Baby Aloe Kitten, 3v |
| 117 Silver Senior in Broth 70g | 127 Chicken w/ Duck Mousse 70g | Silver Senior 70g, 3v |
| **119 Snack Flavored 283g** | **101 Training Snacks 113g** | **Snack Flavored, 3v** ← reported |

Relabelled: **153** (`255 g` ×3 → `Chicken & Egg` / `Herring & Salmon` /
`Chicken & Herring`, and variant 206 gained its missing flavor), 155, 157
(`145 g` → `Duck & Apple`), 132. Product 153's slug went from
`schesir-born-carnivore-pollo-uovo-255g` (one flavor naming all three) to
`schesir-born-carnivore-255g`.

Verified after: 0 duplicate variant labels, 0 duplicate attribute combinations,
103/103 images resolve, and both reported PDPs now render a working selector —
Snack Flavored shows *Product Weight 113 g / 283 g* + *Flavor Chicken / Bacon*,
Born Carnivore shows *Flavor Egg / Salmon / Herring*.

### Hazards the repair script had to handle

- **SKUs are unique catalogue-wide**, so the absorbed product must be DELETEd
  *before* the target can claim its SKUs (`SKU '…' is already in use by another
  variant`). Every affected product is dumped to
  `.siruk-cache/schesir-regroup-backup.json` first, so a failed PUT is
  recoverable.
- **Two planned products can resolve to the same live product** (product 111 —
  `fix-schesir-leftovers.py` had already merged its Lamb bag by hand). Since PUT
  replaces the whole variants array, writing them one at a time would have made
  the second call silently delete the first call's variants. The script buckets
  by target and writes once.
- **A live variant the plan does not mention** is carried over verbatim rather
  than dropped by the PUT.

## Vocabulary

- Created flavor value **Herring** (id 186) on user request — wanted by Born
  Carnivore `Herring & Salmon`. Menu refreshed.

## Open items for the dev team

1. **Category listing vs search inconsistency** (above) — the actual reason the
   duplicates are visible.
2. **One flavor id per variant.** `attrs_for` stores a single flavor, so a
   compound flavor keeps only the distinguishing qualifier — "Chicken & Egg"
   shows as *Egg* in the selector. It also leaves 3 products with colliding
   attribute combinations (`Soup 40g`, `Grill Wf 70g`, `Grill in Paté 70g`,
   where `Chicken & Pumpkin` and `Tuna & Pumpkin` both reduce to *Pumpkin*).
   Pre-existing, not caused by this change. Multi-value attributes would fix it.
3. **37 Schesir slugs do not match their product name** — the original import
   generated slugs from the raw plan names and `fix-schesir-names.py` later
   renamed the products without touching slugs. Cosmetic; fixing changes 37
   public URLs, so left alone. Ask before sweeping.
4. The catalogue holds **50 Schesir products** against **70 planned** — the
   remainder are rows that were never imported (no site match / not stocked).
