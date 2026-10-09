# Production image audit — 2026-10-06 → 2026-10-08

Why: warehouse staff now pick orders by the product photo, so every photo on a variant must show
that exact item (brand, line, flavour, lifestage, colour, pack size). Scope: all of production.

## What was checked
- 949 products, 1,523 variants, 4,453 image placements (3,717 distinct files), downloaded from
  production and **every one opened and judged by eye** against its variant (REVIEW.md).
  Each reviewer confirmed afterwards that every image actually displayed (`verdicts/`).
  Exception found by that check: batch 35 (Royal Canin 1246–1259, 148 images) had been judged
  without the images displaying; on 2026-10-08 all 148 were re-opened (downscaled copies) and
  re-judged — no verdict changed, four `seen` notes corrected.
- Verdicts: 3,813 ok · 234 unclear · 119 wrong-size · 106 not-packshot-lead · 101 wrong-colour ·
  63 wrong-product · 15 wrong-flavour · 2 wrong-lifestage. 266 products had at least one issue.

## What was changed on production
- Gallery fix plan per variant (`plan-out/`, PLAN.md): wrong images dropped, the pack shot
  moved to the lead, other-product cross-sell / range / carton shots removed.
  **201 products** written in pass 1 (`apply-write.log`, + 3 pilot), **34** in pass 2 after new
  photos, **3** after the second Lens round, **2** restored on the user's preview review.
  Every PUT read back; nothing but `images` changed (spot-checked prices/stock/texts).
- **72 new photos for 41 variants** sourced (zooplus.pl by EAN for all 9 Acana 11.4 kg bags,
  trixiecz/tiierisch/carrefour/hornung by article or EAN, Monge PDFs/4lapy/farmacosmo by EAN,
  biostyle for Beaphar, brand files for Eco-Premium, Google + Lens in the headed browser for the
  rest), each looked at and keyed to our article/EAN, uploaded into the product's media folder
  (`found-uploaded.json`).
- Royal Canin 12 × 85 g case variants: not purchasable / stock 0 (sold as single pouches since
  2026-10-01) — no case photos added; carton/x12 images removed from the single-pouch variants.

## Final live check (`verify-live.json`, 2026-10-08)
- 0 variants without an image.
- Leads still flagged: 105 accepted by policy (brand packshot prints no size but nothing
  contradicts it — Royal Canin bags, one photo per colour for collars/bowls across sizes);
  12 held or excluded by the user on 2026-10-07; the rest are listed below.

## Still open (also in state/open-items.csv, "image audit 2026-10-06")
- **201018 Premium Lead papaya (805)** — lead still shows the black lead; no papaya photo exists
  for this article anywhere (Trixie, distributors, Google/Lens). Needs a photo taken in-store or
  a decision (hide variant / use hafo photo).
- **13238 Car Seat Cover (901)** — only an in-car photo exists.
- **804 purple 200725 / light lilac 200720** — labels and Trixie's photos disagree; which article
  is which colour? (held, unchanged)
- **DL711836 (1201)** — Dog Fest pouch photos carry our EAN; product brand is Derevenskie. Which
  pack is on the shelf? (held)
- User-excluded 2026-10-07: 009157, 011257, 011477, 25032, 36121, PM902085, PM902075 (+ -KG
  twins) — galleries left as they were (some still show another size; see verify-live.json).
- Monge Best for Breeders 15 kg (005947, MG006067, MG006077, 006487): one generic bag front for
  every recipe; the recipe sheet is in each gallery — a photo of the recipe sticker would help.
- Versele Crispy Guinea Pigs 400 g / 1 kg (461698V, 461711V): no photo printing the weight found.
  (User 2026-10-07: keep the current photos for the breeder bags, 13238 and Crispy; MG006027 got
  the eliteshop.am MAXI Puppy & Junior bag, not EAN-keyed, user-approved.)
- Special Dog Excellence (060347 / 060357): Monge's photo for our EAN prints 1250 g, our label
  says 1275 g — fix the label?
- 39 data questions raised by the planners (names that don't match the pack, colours, packaging
  type attribute Pouch vs Tray/Can): `questions.json`.

## Files
`images.csv` (every placement) · `verdicts/` · `findings.csv` · `plan-out/` · `found/` +
`found-uploaded.json` · `apply-*.log` · `verify-live.json` · REVIEW.md / PLAN.md / SOURCE.md.
