# Filling gaps on live products: how to gather a card

For whoever reads source pages and writes gap cards (`runs/<date>/gapcards/<variant_id>.json`).
**Gatherers never write to the admin.** `scripts/fill-gaps.py` checks every card and writes only
fields that are empty live. The card format is in that script's docstring. Learned on the
2026-10-12 pilot (products 683, 1024, 705, 640, 1192, 545), each verified with
`scripts/verify-fill.py`.

## The loop per product

1. **Read the gap row** (`final/catalogue-gaps-<date>.xlsx` / `.siruk-cache/gap-matrix.json`):
   which fields are EMPTY, and the variant ids and SKUs.
2. **Find the official page** (`reference/brand-sites.md`) and **prove identity** before copying
   anything. Proof means our article or EAN printed on the page, in its spec table, or in the
   photo file name. Write the proof in the card's `identity.how`.
3. **Save the raw page text** as `evidence/<product>.txt`: url, name, every paragraph you use,
   composition, analysis, additives, instructions. Attribute quotes must be found verbatim in it.
4. **Write English HTML** from the page.
   - `<p>` for prose, `<ul><li>` for claims, `<table>` for feeding tables, `<strong>` labels:
     "Composition:", "Analytical constituents:", "Nutritional additives per kg:".
   - Rephrase lightly; keep every number exactly as printed.
5. **Translate to ru and hy** (machine translation is fine, user 2026-10-12).
   - Keep numbers, units, percentages and Latin names.
   - Use a decimal comma in ru/hy (7,5%).
   - Brand and line names stay in Latin.
6. **Attributes:** only filterable ones the type carries, only values from
   `reference/attribute-values.json`, each with a quote. A single-value attribute gets the
   **lead** claim, and the other claims go in `review_note`.
7. **Photos:** look at every image first.
   - Only add them when the live gallery is empty, only a hafo placeholder, or a weaker copy.
   - If a better official photo replaces a weaker copy of the same pack, set
     `replace_gallery: true` + `drop_existing: [old media id]`.
   - The first photo must be a clean pack shot.

## Never

- **Invent a number.** No feeding amount, dose or nutrient value that the source doesn't print.
  - If the pack has no feeding table, write only what the label says (e.g. "A complementary
    snack: give it alongside a complete food").
  - A typo on the source (e.g. "vitamin A 4600 kg") is written without the bad unit and flagged
    in `review_note`.
  - A suspicious brand value (Acana's 25–30 kg row equal to 30–40 kg) is copied as published and
    flagged.
- **Overwrite** a filled field. A messy existing text goes in `review_note`, and the tool keeps it.
- **Copy content from a page that only lists our EAN among "related products".** A Monge page
  carries ~130 EANs in its related strip. The right page is the one whose own EAN is ours, or the
  one whose photo file name carries it.

## Brand notes from the pilot

| Brand | Where | Notes |
|---|---|---|
| Monge / Gemon | monge.it `/en/product/<slug>/`; `scripts/monge-it-page.py --url` parses composition / analytical / additives / feeding | the description paragraph is in the page body after the size line (read it in the browser); feeding tables are images, so use the text only; match by the page whose own EAN is ours (`.siruk-cache/mongeit-all.json`: a page listing **only** our EAN) |
| Acana / Orijen | emea.acana.com, slug from the sitemap `eu-aca-<recipe>-new.html` | the feeding calculator lives in `#section3`: set `select.feedingRowKg` + `select.feedingColumnKg`, dispatch `change`, read `.feeding-section.results` (Submit reloads the page, so don't click it) |
| Trixie | trixie.de page via `scripts/trixie-catalogue.py --lookup <article>` | spec-sheet pages with no prose. The packaging PDF (`backend.trixie.de/en/public/pdf/download/<id>`) carries the full label: render with `qlmanage -t -s 5000`, crop, rotate 180° with `sips` and read. Snacks print no feeding amounts. Save the PDF in `evidence/` |
| Beaphar | `https://www.beaphar.cz/product/<our SKU>` | prints SKU and barcode in its spec table; Czech text → translate to English; gallery files `CMP9365/<sku>-hero_<n>.jpg` (often the same shot twice) |

## Data errors found on the way

Fix them in the admin. They are data, so they are ours to fix (user 2026-10-12). Log each one to
`runs/<date>/corrections.csv` with its evidence. Examples:
- 683 was named "Paté" but the EAN pages say "Chunks", so it was renamed in en/ru/hy.
- 561 was a cat treat tagged Puppy; it now says Kitten.
