# Multiple categories per product — 2026-09-12

## What I checked in the admin panel

Opened the product edit form with chrome-devtools (route is
`/admin/catalog/products/edit/<id>`, not `.../<id>/edit`). The **Categories**
control is `ant-select-multiple ant-tree-select` — a tag-style multi-select
tree — and its dropdown lets you pick parents as well as leaves. A two-id
`PUT /products/871` read back as `[43, 88]`, so the API stores several ids too.
You were right: the schema always allowed it, and the bulk imports each wrote
one id.

Screenshots: `admin-categories-multiselect.png` (before, one tag) and
`admin-dual-category.png` (product 504 now carrying two).

## Parent categories must NOT be added

Worth stating because it changes what "all the categories they belong to"
means. The storefront rolls children up by itself: `/dog/treat/` renders **48
product cards** although **nothing** is assigned to category 6. I confirmed
the cards come from three different leaves — Bacon Pâté (88 Lickable), Bagels
(82 Soft & Chewy), Barbecue Ribs (85 Long-Lasting Chews). So adding `Treat`,
`Food` or `Dog` to a product buys no listing and breaks the leaf rule. All the
work below is leaf-to-leaf.

## What was already right

29 products were **already** multi-category: the Inspector, Gelmintal,
Insectal, Cliny, Iv San Bernard, Trixie paw-spray/first-aid and Monge
VetSolution rows. The reason is instructive — the `supplements` skill was the
only product-type spec that carried the sentence "A product for both species
goes in both leaves". The `grooming`, `treats`, `toys` and `accessories`
imports had no such line, so they wrote one id. That is now fixed in the docs.

## What changed

**17 products gained their mirror leaf** in the other species' tree, each on a
suitability claim quoted from its own brand text. 0 failures, and a before/after
check confirmed nothing was dropped (name, brand, attribute family and variant
count all unchanged; `category_ids` is a strict superset in every case).

| Products | Was | Now | Evidence |
|---|---|---|---|
| 475, 477, 478, 479, 502 Claw scissors & clippers | 31 Paw & Nail Care | + 38 | "for (small) dogs, cats" |
| 504, 508, 589, 614, 868 Toothbrushes, dental pads, wipes | 30 Grooming Tools | + 37 | "for dogs and cats" |
| 568, 571, 615 Eye balm, tearstain remover, eye wipes | 33 Skin Care | + 40 | "for dogs, cats" |
| 569, 588, 616 Ear care, ear pads, ear wipes | 32 Ear Care | + 39 | "for dogs, cats" |
| 581 Dry Shampoo | 29 Shampoos & Conditioners | + 36 | "for dogs, cats" |

Full list with the quote per row: `runs/2026-09-12/multi-category.csv`.

## Two things I got wrong and corrected mid-run

1. **I invented a "dewormer also goes in 47 Pharmacy" rule** from a listing
   that printed category *names*, and briefly wrote it into CLAUDE.md as if it
   were an established convention. Checking the ids showed the real pattern:
   46 holds 12 dewormers, 55 holds the cat ones (Cat has **no** dewormer leaf),
   and 47 holds only the First Aid Kit and SexControl. So a dual-species
   dewormer is **46 + 55** — which is just the mirror rule — and 12 dog
   dewormers were correctly left alone. The docs now say this, and the script
   carries a comment so the mistake is not repeated.
2. **Three Acana dog kibbles were nearly filed under Cat Dry Food** on the
   phrase "help your dog and cat live a full and healthy life" — Acana range
   boilerplate, not a claim about those bags. The detector now requires a
   suitability anchor (for/of/on/with), plural species, and rejects the
   possessive "your". Regression-checked both ways: all 8 known dual-species
   products still match, all 3 Acana bags are rejected.

A third bug: products already shelved in **both** trees were collecting a
redundant third leaf (Inspector Quadro Tabs would have gained 47). The mirror
step now skips any species the product is already filed in.

## Gaps — these need your decision, I did not invent categories

1. **Seven cat veterinary diets have nowhere to go.** Dog has `5 Health
   Condition`; Cat has no equivalent, so these sit in Dry/Wet Food only, while
   their six dog counterparts are correctly `4 + 5`:
   632 Urinary Struvite · 646 Gastrointestinal · 647 Renal · 648 Hepatic ·
   649 Diabetic · 719 Renal & Oxalate · 720 Recovery (all Monge VetSolution).
   Shall I create **Cat > Health Condition**? It is the one missing mirror that
   affects a whole product line.
2. **Two place mats** (811 Place Mat, 812 BE NORDIC Place Mat) are invoiced
   `շն/կատ` — for dog *and* cat — but sit in `70 Bowls & Feeders`, which Cat
   has no counterpart for (Cat Supplies has only 67 and 79). Same question:
   add **Cat > Bowls & Feeders**, or leave them dog-only?

## Notes

- Only 17 of 834 products had a dual-species claim in their own text. That is
  the honest number under rule 8 — I add a species only where the brand claims
  it, never because a bowl or collar "could" suit both. If you want a broader
  sweep (e.g. treat every Trixie bowl, bed and collar as dual-species), say so
  and I will do it as an explicit policy rather than as evidence.
- The admin form shows both tags as plain "Grooming Tools", with no parent to
  tell the dog leaf from the cat one. Not something I can fix from here, but
  worth raising with the dev — a tree path in the tag would help.
- No species mis-filings remain: a full sweep of all 834 found none (546 was
  the only one, fixed earlier today).
- These 17 grooming products have **no attribute family** set — that was
  already the case before this run, not something the writes touched, but it
  means they carry no filterable attributes.

## Files

- `scripts/multi-category.py` — audit + writer; only ever extends
  `category_ids`, never adds a parent, reports missing mirrors
- `runs/2026-09-12/multi-category.csv` — the 17 changes with evidence
- `runs/2026-09-12/multi-category-gaps.csv` — the 9 gaps
- Docs: CLAUDE.md rule 7d · `reference/product-rules.md` ("Multiple categories
  per product") · `reference/admin-api.md` · the `add-products`, `grooming`,
  `treats`, `supplements` and `accessories` skills
