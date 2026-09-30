# Row card — what a worker hands back

One file per CSV row, `runs/<date>/cards/<code>.json`, written by a worker
subagent from its `rows.jsonl` line (made by `scripts/prepare-run.py`) plus the
brand page. Workers never write to the admin. `scripts/validate-card.py`
checks every card against the hard rules; only a passing card is imported.

```json
{
  "code": "41116Tx",
  "status": "ready",
  "hold_reason": null,
  "type": "toys",
  "brand_id": 8,
  "name": "Playing Rope",
  "label": "60 cm",
  "existing_id": null,
  "category_ids": [19],
  "price": {"source": "prepared"},
  "attributes": {
    "toy-type": {"value": "Rope & Tug", "quote": "tug rope made of cotton"},
    "material": {"value": "Cotton", "quote": "made of cotton"}
  },
  "images": ["https://…/packshot.jpg", "https://…/lifestyle.jpg"],
  "first_image": "packshot",
  "texts": {"about_this_item": "…", "ingredient_information": null, "feeding_instructions": null},
  "source": {"kind": "brand-site", "url": "https://www.trixie.de/…"},
  "evidence_file": "cards/41116Tx.source.txt"
}
```

| Field | Rule |
|---|---|
| `code` | the row's code from `rows.jsonl`; the file is `cards/<code>.json` |
| `status` | `ready`, or `hold` + `hold_reason` (a hold card needs nothing else) |
| `type` | a key of `reference/types.json`; decides family, allowed leaves, pricing |
| `brand_id` | a live brand; `prepare-run.py`'s pick unless the pack proves otherwise |
| `name` | brand-less; no pack weight/volume; flavour/colour/dose only while single-variant (WARN) |
| `label` | the variant axis in English (`8 kg`, `Chicken 85 g`, `M`) |
| `existing_id` | the live product this row joins as a variant (rule 9), else `null` |
| `category_ids` | leaves only, every leaf that fits, all inside the type's leaves |
| `price.source` | `prepared` (use the row's price as is) · `zoovet` / `nemo` (+ `amount`, `url`, `how_confirmed`; row must be `needs-price`) · `sibling` (+ `existing_id`; checked against the live product) |
| `type_reason` | required when `type` differs from the row's (CSV category proved wrong) |
| `attributes` | `code → {value, quote}` (packaging / color-family may use `{value, basis: "photo"}` instead of a quote); the value a label of `reference/attribute-values.json`, the code in the type's family, the quote found verbatim in the evidence |
| `images` | full gallery, in order, at least one; first a clean packshot |
| `first_image` | `packshot` or `not-packshot` (the latter lists the row on `needs-packshot.csv`) |
| `texts` | English; `about_this_item` required. Or `texts_file` pointing at a JSON with the same keys |
| `source` | where name/images/texts came from: `brand-site`, `country-site`, `barcode` (pages printing our EAN, 2026-09-25), `4lapy`, `zoovet`, `petshop` (texts only), `hafo`, `web` |
| `evidence_file` | the raw page text the quotes came from, relative to the run folder |

Evidence that a quote may come from: `evidence_file`, the card's own texts, the
CSV name, and hafo's title / variant name / keywords (all in `rows.jsonl`).
