# Treat subcategories — 2026-09-12

The user's ask: dog treats had a single subcategory, cat treats none, and every
treat product was sitting in the parent. Screenshots of Chewy's dog and cat
treat menus were supplied for naming.

## What changed

**13 leaves created** (ids 82–94) and **leaf 7 renamed**, so both treat parents
now hold nothing but leaves:

| Dog > Treat | | Cat > Treat | |
|---|---|---|---|
| 7 | Bones, Bully Sticks & Naturals *(renamed from "Dog Bones, Bully Sticks & Chews")* | 89 | Crunchy Treats |
| 82 | Soft & Chewy Treats | 90 | Lickable Treats |
| 83 | Dental Treats | 91 | Soft & Chewy Treats |
| 84 | Biscuits & Cookies | 92 | Dental Treats |
| 85 | Long-Lasting Chews | 93 | Catnip |
| 86 | Jerky Treats | 94 | Cat Grass |
| 87 | Freeze-Dried & Dehydrated | | |
| 88 | Lickable Treats | | |

Names follow the Chewy screenshots exactly, minus the redundant "Dog " prefix
on leaf 7. All 14 carry `ru` and `hy` names (`scripts/translate-categories.py`).

**164 treat products re-filed**, 162 moved and 2 already correct, 0 failures.
Every product is now in a leaf; **nothing is left in parent 6 or 14**
(verified by re-reading all 834 catalogue rows after the write).

| Leaf | Dog | Cat |
|---|---:|---:|
| Bones, Bully Sticks & Naturals | 6 | — |
| Soft & Chewy Treats | 49 | 25 |
| Dental Treats | 2 | 2 |
| Biscuits & Cookies | 5 | — |
| Long-Lasting Chews | 33 | — |
| Jerky Treats | 14 | — |
| Freeze-Dried & Dehydrated | 2 | — |
| Lickable Treats | 5 | 5 |
| Crunchy Treats | — | 11 |
| Catnip | — | 4 |
| Cat Grass | — | 1 |
| **total** | **116** | **48** |

## How each row was decided

Not from the product name — from the **brand page text already stored on the
variant** (composition, analytical constituents, the bullet list). The rule
table now lives in the `treats` skill so future imports file themselves, and
`scripts/classify-treats.py` implements it and can re-run over the catalogue.
`runs/2026-09-12/treat-recategorisation.csv` has all 164 rows with the rule
that fired and the quote that justified it.

Two brands needed evidence fetched during this run:

- **Monge Gift** (23 products) had no stored text at all. Resolved from
  monge.it's own product pages: *Filled & Crunchy* = "an external crunchy layer
  … and a soft cheese filling" → Crunchy; *Meat Minis* and *Soft Sticks* and
  the dog *Sticks* carry no crunch or dental claim → Soft & Chewy; the two
  **Dental** variants say "sodium tripolyphosphate to support dental hygiene …
  fresh breath" → Dental.
- **Trixie 00265** "Denta Fun Chew Bites with Mint" was a hafo/invoice fallback
  row with no text. Its article is 31501 on trixie.de, whose page says "support
  dental hygiene and promote fresh breath" → Dental. Page-verified.

## One data fix found on the way

**Product 546 "Creamy Snack with Chicken Breast" was filed under Dog** but its
article is 42681 and its Trixie shelf is `cat/cat-snacks/cat-treats` — its two
siblings (547, 548) were already under Cat. Moved to Cat > Lickable Treats.
No other species mismatch found across the 164.

## Open questions for you

1. **Cat has six leaves, so four freeze-dried cat treats sit on Crunchy
   Treats** — 562 Freeze Dried Shrimps, 563 Chicken Hearts, 566 lamb liver &
   salmon, 567 chicken meat & cheese. Freeze-dried *is* crunchy, so it is not
   wrong, but Chewy's dog menu gives it its own shelf. Want a
   **Freeze-Dried & Dehydrated** leaf under Cat too? Four products would move.
2. **Rawhide beats texture, by design.** Three products name themselves soft
   but list rawhide in the composition, so they went to Long-Lasting Chews:
   374 Marbled Softies with lamb & fish, 387 Crispies with Duck, 363 Premio
   Lolly with duck & cod. Say the word and they move to Soft & Chewy.
3. **Pill pockets.** 332 / 510 "Hiding Place for Tablets" are soft treats with
   a hole for a tablet — filed as Soft & Chewy (dog / cat). Chewy shelves these
   under Pharmacy. Move them to 47 / 55 if you'd rather.
4. **Dried catnip in the Toys tree.** Product 593 "Catnip" (loose dried catnip)
   and the two Matatabi sprays (597, 598) sit in Cat > Toys > Catnip (25).
   They were not treat products so this run left them alone, but 593 in
   particular looks like it belongs on the new Cat > Treat > Catnip (93)
   shelf. The four Matatabi Lollies that *were* in Treat did move to 93.
5. **Two discontinued Trixie articles were filed from their live sibling**,
   not from a page of their own: 382 Premio Stars with Chicken and Rice (31667)
   and 398 Sticks with Chicken and Fish 300 g (31803). Neither article exists
   on trixie.de, trixie.shop or trixiecz.cz any more.

## Files

- `scripts/classify-treats.py` — the rule table, re-runnable (`--apply`)
- `runs/2026-09-12/treat-categories.json` — the category spec
- `runs/2026-09-12/treat-recategorisation.csv` — 164 rows, rule + evidence
- `.siruk-cache/treats/plan.json` — the machine-readable plan
- Docs updated: `CLAUDE.md` quick ids, `reference/product-rules.md` category
  map, `.claude/skills/treats/SKILL.md` (the routing table),
  `scripts/translate-categories.py` (10 new ru/hy names)
