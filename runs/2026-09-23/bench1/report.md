# Worker benchmark 2026-09-23 — 20 live rows re-done as if new (nothing written)

`prepare-run.py --bench` → 3 Sonnet workers (brand + type batches) → `validate-card.py` →
comparison with the live products (`compare.md`).

## Cost
| Batch | Rows | Tokens | Per row | Time |
|---|---|---|---|---|
| Monge dry food | 6 | 146K | 24K | 4.6 min |
| Monge wet food | 7 | 150K | 21K | 6.0 min |
| Trixie toys | 7 | 128K | 18K | 6.0 min |
| **Total** | **20** | **424K** | **21K** | ~6 min in parallel |

The orchestrator (main session) received one line per row — ~1K tokens for all 20.

## Quality
- 19 pass, 1 hold. The hold (011477) was right: the CSV calls it wet food, it is dry kibble.
- Identity: 20/20 correct product; the 6 wet-food rows found the live product as `existing_id`
  unprompted. EAN-confirmed where the brand page carries it.
- Categories: 17/19 identical; the 2 differences are toy-leaf judgment calls (plush hippo with an
  inner rope: Plush vs Rope & Tug; ball on a rope: Fetch vs Rope & Tug).
- Attributes: 75 identical, 6 different, 16 extra in the card, 14 only live. Of the 14, 13 are
  `packaging` (never quoted in page text — fixed: packaging/colour may now rest on the photo). Of
  the 6 differences, at least 2 look like the card is right and live is wrong (Grill Salmon
  "in a sauce" → Chunks in Gravy, live says Jelly; BWild Large Breed "all life stage", live says Adult).
- Names follow the rules better than live (no pack size in the name); a few are long
  ("BWild Grain Free Large Breed All Life Stage Buffalo with Potatoes and Lentils").
- Weak spot: galleries. Dry-food cards carried 1 image where live has 3–6 — brief now demands the
  whole gallery and the validator warns on a single brand-site image.

## Fixed after the benchmark
- prepare-run.py: a brand printed in the invoice name beats hafo's product_maker (hafo said TRIXIE for 014507).
- validate-card.py: `basis: "photo"` for packaging/colour; `type_reason` to correct a wrong CSV type; single-image warning.
- worker-brief.md: packaging/colour by eye, whole gallery, correct a wrong type instead of holding.
