---
name: treats
description: Product-type spec for TREATS (snacks, chews, dental sticks, training treats) — categories, product type, how to pick the Chewy-style values a treat carries, its net content (mass) and pack pricing. Read by /add-products for every treat row and by /manage-attributes when building the vocabulary.
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

Product type **3 Treats** (`measure_type: mass`, `default_sale_mode: pack`).
**The live product type decides which attributes exist, their role (`option` /
`attribute`) and flags** — `reference/product-types.json`
(`scripts/product-types.py --dump`); it wins over this file. Read 2026-09-30:
`flavor`, `health-feature` and `size` are `option`; lifestage, special-diet,
breed-size, packaging, ingredient are `attribute`. An attribute the batch
needs that the type lacks → the `attribute-manager` agent before the import
(CLAUDE.md 8b); a new value still needs an explicit ask (rule 8).

**Dual species → both trees.** `category_ids` is a list. When the pack or brand
page says the product is for dogs *and* cats, file it in the **mirror leaf of
both** species' trees (the pattern already in the catalogue: Ear Care 32 + 39,
Shampoos 29 + 36, Grooming Tools 30 + 37, Paw & Nail 31 + 38, Skin Care
33 + 40, Flea & Tick 42 + 51, Vitamins 43 + 52, Pharmacy 47 + 55, Collars
69 + 79). Never add a parent — parents roll their children up. Never add a
species the brand does not claim. See `reference/product-rules.md`.


## Attributes
All picks from the closed menu `reference/attribute-values.json` (full lists in
`reference/chewy-attributes.json`), **one value per attribute per variant**
(every attribute here is `select`) — with an evidence quote from the
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

### Single-value consequence
Chewy's Special Diet, Health Feature and Ingredient are multi-tag; ours hold
one value each. Pick the claim the pack leads with (front-of-pack claim >
sub-line name > body text) and put the rest in `about_this_item` so it is at
least searchable. `ingredient` = the **first named ingredient** of the
composition (the headline protein), nothing else.

## Pack size — net content, not an attribute (CLAUDE.md 8a)
`measure_type: "mass"`, `content` in grams, **when the pack prints a weight**.
The net pack weight, not the piece: `12 pcs./120 g` → `content 120,
pack_count 1`; `2 × 60 g` (two sealed packs sold as one) → `content 60,
pack_count 2` (evidence for the pack being the axis: product 527's sibling
variants are 140 g and 200 g). A **length** — `23 cm` Matatabi lolly — is not
content: leave it out and write with `ALLOW_NO_SIZE=1` (the rule-8a escape for
a chew measured in cm). No `product-weight` attribute any more (retired
2026-09-29).

## Variant axes
Net content and flavour (a dental stick in S / M / L is a **breed-size split**,
not a variant — separate products, per the shelf test). Once one variant of a
product carries an option, every variant needs it (rule 9a).
OPEN: the live type also makes `health-feature` and `size` options. That
contradicts "health function splits" below and the S/M/L split above; until
the user decides, keep splitting and give every variant of a product the same
`health-feature` value (or none).

**The flavour never goes in the product Name** — it is the variant label and
the `flavor` value. "Barbecue Ribs with Duck" and "Barbecue Ribs with Chicken"
are ONE product "Barbecue Ribs" with two variants, however the brand pages
them (trixie.de gives every flavour its own page — that is not a split
signal for food). Before creating a treat, look for the line product
(`scripts/find-product.sh "Barbecue Ribs"`); a single-variant product whose
Name carries the flavour or pack (`… with Duck 110 g`) takes the row as a
variant and is renamed to the line name (`scripts/rename-product.sh`). The
2026-09-16 sweep folded 21 Trixie
and Monge treat lines this way; `scripts/plan-variant-merge.py` is the tool.
A line whose members differ by lifestage or health function (Monge Gift
Sticks Adult vs Puppy; Filled & Crunchy Hairball vs Sterilised) stays split.

## Pricing
`price` = hafo's row for that article code (the pack price), `cost_price` =
CSV price; the server computes the rate. One hafo lookup per variant.
