---
name: treats
description: Product-type spec for TREATS (snacks, chews, dental sticks, training treats) — categories, attribute family, the Chewy-style attributes and values a treat carries, its variant axes and fixed pricing. Read by /add-products for every treat row and by /manage-attributes when building the vocabulary.
---

# Treats — product-type spec

Chewy treat filters (user decision 2026-09-10): **Flavor, Ingredient, Special
Diet, Breed Size, Health Feature, Lifestage, Packaging Type**.

## Where it is filed

Treats go in a **leaf**, never the parent (6 / 14 hold nothing). The leaves
replicate Chewy's treat menu (created 2026-09-12). Pick by the **form of the
treat**, decided from the brand page's composition and bullets — not from the
name alone where text exists. First match wins:

| # | Test (evidence from the product's own text) | Dog | Cat |
|---|---|---|---|
| 1 | composition says **freeze-dried** | 87 Freeze-Dried & Dehydrated | 89 Crunchy |
| 2 | **single-ingredient dried animal part** — "100 % … skin/headskin, dried", rabbit ears/legs/tails, fish skin — and no hide substrate | 7 Bones, Bully Sticks & Naturals | 91 Soft & Chewy |
| 3 | composition contains **rawhide / collagen / buffalo or beef skin** | 85 Long-Lasting Chews | 91 Soft & Chewy |
| 4 | **liquid snack / pâté / paste / malt** (moisture ≳ 55 %, spreadable) | 88 Lickable | 90 Lickable |
| 5 | the product's **own line or claim is dental** — Denta Fun, Dentros, Monge Gift Dental, "support dental hygiene", "fresh breath" | 83 Dental | 92 Dental |
| 6 | **baked cookie/biscuit**: name says cookie/biscuit/farmies/loops/choco drops **and** the composition is cereal- or flour-led (or declares no moisture) | 84 Biscuits & Cookies | 89 Crunchy |
| 7 | the pack's form word is a **flat sliced-meat format** — filet, stripe/strip, coin, carpaccio, tender | 86 Jerky | 91 Soft & Chewy |
| 8 | an explicit **crunchy** layer or format | 82 Soft & Chewy | 89 Crunchy |
| 9 | **catnip / matatabi attractant** (dried herb, matatabi stick, lolly) | — | 93 Catnip |
| 10 | **grass to grow or eat** (seed-substrate, ryegrass) | — | 94 Cat Grass |
| 11 | *default* — semi-moist meaty or cereal morsels, the main treat shelf | 82 Soft & Chewy | 91 Soft & Chewy |

Notes that matter:
- **Rule 3 is a bright line**: rawhide anywhere in the composition means
  Long-Lasting Chews, even when the name says "Softies" or "Crispies". It is
  what a shopper filtering rawhide-free needs, and it keeps the call reviewable.
- Rule 7 is deliberately narrow — a *stick*, ball, cube or roll is not jerky.
- **Cat has six leaves, not eight.** A cat row that lands on Naturals, Chews or
  Jerky goes to 91 Soft & Chewy (those are moist meat treats); a cat row that
  lands on Freeze-Dried or Biscuits goes to 89 Crunchy. Open question with the
  user: whether cat should get its own Freeze-Dried & Dehydrated leaf (4
  products would move out of 89).
- `scripts/classify-treats.py` implements this table and can re-file the whole
  catalogue (`--apply`); its plan lands in `.siruk-cache/treats/plan.json` with
  an evidence quote per row.

Family **3 Treats**: product-weight, flavor, lifestage, special-diet,
health-feature, breed-size, packaging, ingredient.

**Dual species → both trees.** `category_ids` is a list. When the pack or brand
page says the product is for dogs *and* cats, file it in the **mirror leaf of
both** species' trees (the pattern already in the catalogue: Ear Care 32 + 39,
Shampoos 29 + 36, Grooming Tools 30 + 37, Paw & Nail 31 + 38, Skin Care
33 + 40, Flea & Tick 42 + 51, Vitamins 43 + 52, Pharmacy 47 + 55, Collars
69 + 79). Never add a parent — parents roll their children up. Never add a
species the brand does not claim. See `reference/product-rules.md`.


## Attributes
All picks from the closed menu `reference/attribute-values.json` (full lists in
`reference/chewy-attributes.json`), **one value per attribute per variant** —
the API rejects arrays (verified 2026-09-10) — with an evidence quote from the
brand page or the CSV row. Empty beats a guess. Our definitions in
`reference/data-tables.md` (lifestage bands, texture words) beat the brand's
wording. Do not create values for this type without an explicit ask.
Skipped on purpose from Chewy: Made In, Deals & Savings.

| Attribute | Values | How to fill |
|---|---|---|
| `flavor` | Chewy's 61 (incl. treat flavours: Cranberry, Smoked, Blueberry, Strawberry, Ginger, Mint, Vanilla, Honey, Cinnamon, Carob, Hickory, Ostrich…) | the named flavour/protein in the product name |
| `ingredient` | Chewy's 69 (incl. Bananas, Butternut Squash, Chia Seeds, Coconut Flour, Gelatin, Glycerin, Oat Flour, Oats, Pumpkin Puree…) | first ingredient of the composition |
| `special-diet` | Chewy's 42 (Grain-Free, Rawhide-Free, Sugar Free, Odor-Free, Low Phosphorus, Low Sodium…) | front-of-pack claim |
| `breed-size` | Chewy's 6 | only on a stated size ("for small dogs", "S/M/L" on dental sticks) |
| `health-feature` | Chewy's 52 | "dental" → Dental & Breath Care; "digestion" → Digestive Health; "calming" → Calming |
| `lifestage` | Puppy, Kitten, Adult, Senior, All Lifestages | explicit claim only ("puppy treats") |
| `packaging` | Bag, Pouch, Box, Tub, Tube, Can, Tray, Roll, Cup, Bottle, Shaker | from the format |
| `product-weight` | pack weight menu | the unit weight |

### Single-value consequence
Chewy's Special Diet, Health Feature and Ingredient are multi-tag; ours hold
one value each. Pick the claim the pack leads with (front-of-pack claim >
sub-line name > body text) and put the rest in `about_this_item` so it is at
least searchable. `ingredient` = the **first named ingredient** of the
composition (the headline protein), nothing else.

## Variant axes
Pack weight and flavour (a dental stick in S / M / L is a **breed-size split**,
not a variant — separate products, per the shelf test).

## Pricing
`pricing_type: "fixed"`, `price` = hafo's row for that article code,
`cost_price` = CSV price. One hafo lookup per variant.
