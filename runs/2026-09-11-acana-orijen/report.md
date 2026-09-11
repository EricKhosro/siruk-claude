# Acana & Orijen import — 2026-09-11

Source: `Ստացված ապրանքների ցանկ.xlsx` (the received-goods tax register the PM
supplied), invoice **A6833625890**. 23 rows, all of them Acana or Orijen, none
of which existed in the catalogue before this run.

**23 products created, 23 variants, 86 images, 0 failures.**

## Why these were missing

`csv/products.csv` — the input every earlier run used — was built from the
invoice scans in `~/Downloads/Siruk Products`. Invoice A6833625890 was never
scanned into that folder, so its 81 dry-food rows (Acana, Orijen, Farmina,
Monge, Gemon, 4 Paws, Simba, My Love, GAF, Մյաու) never entered the pipeline.
They were not in a queue and not rejected; they were never seen. The brands
Acana (id 1) and Orijen (id 6) had existed since 2026-08-13 with logos, holding
zero products.

## Identity without an article code

The register carries **no article codes** — only an Armenian name, a quantity
and a price. CLAUDE.md rule 6 wants identity from the code, so the code was
recovered rather than assumed, on three independent locks:

1. **Name.** hafo stores its own row `name` as the *same string* the invoice
   prints (same distributor wrote both). All 23 matched exactly.
2. **Cost.** hafo's per-row `wholesale_price` equalled our invoice cost to the
   dram on all 23 — the tie-break `reference/hafo.md` names as the reliable one.
3. **Pack size.** the recipe's page on the brand's own EU site lists the exact
   pack weight the invoice bought, for all 23.

The codes so recovered were then re-queried **by code**: all 23 return
`confirmed: true` and `price_source: "variant"`, so the final records rest on a
true article-code match, not on a name search.

## Prices

Every sale price is the hafo price for our own row (`price_source: "variant"`).
The register price is the cost. No price was derived, rounded or estimated, and
every sale price beats its cost. Pricing type is `per_kg` for all 23 (dry
kibble), rate = hafo price ÷ pack weight.

| code | product | pack | cost | sale | ֏/kg |
|---|---|---|---|---|---|
| 5431112 | Highest Protein Ranchlands, 11.4 kg | 11.4 kg | 49500 | 63800 | 5596.49 |
| 7143712 | Homestead Harvest, 4.5 kg | 4.5 kg | 20300 | 26300 | 5844.44 |
| 7144412 | Bountiful Catch, 4.5 kg | 4.5 kg | 20300 | 26300 | 5844.44 |
| 7145812 | Highest Protein Wild Prairie, 4.5 kg | 4.5 kg | 22500 | 29000 | 6444.44 |
| 7147212 | Highest Protein Grasslands, 4.5 kg | 4.5 kg | 23500 | 30550 | 6788.89 |
| 7146512 | Highest Protein Pacifica, 4.5 kg | 4.5 kg | 24700 | 31950 | 7100.0 |
| 7147712 | Small Breed, 4.5 kg | 4.5 kg | 27000 | 35000 | 7777.78 |
| 7145112 | Indoor Entree, 4.5 kg | 4.5 kg | 20300 | 26300 | 5844.44 |
| 5621212 | Classics Wild Coast, 9.7 kg | 9.7 kg | 31500 | 40950 | 4221.65 |
| 5601112 | Classics Prairie Poultry, 9.7 kg | 9.7 kg | 27000 | 35000 | 3608.25 |
| 5611212 | Classics Red Meat, 9.7 kg | 9.7 kg | 30750 | 40000 | 4123.71 |
| 5401112 | Highest Protein Wild Prairie, 11.4 kg | 11.4 kg | 40650 | 52400 | 4596.49 |
| 5121112 | Light & Fit, 11.4 kg | 11.4 kg | 34750 | 45000 | 3947.37 |
| 2815412 | Six Fish, 5.4 kg | 5.4 kg | 32700 | 42000 | 7777.78 |
| 5721212 | Singles Yorkshire Pork, 11.4 kg | 11.4 kg | 40200 | 52000 | 4561.4 |
| AC 5301112 | Sport & Agility, 11.4 kg | 11.4 kg | 34750 | 45000 | 3947.37 |
| AC 5701212 | Singles Grass-Fed Lamb, 11.4 kg | 11.4 kg | 44700 | 58000 | 5087.72 |
| AC 5026012 | Puppy Small Breed, 6 kg | 6 kg | 20300 | 26300 | 4383.33 |
| AC 5001112 | Puppy, 11.4 kg | 11.4 kg | 34400 | 44500 | 3903.51 |
| AC 5236012 | Adult Small Breed, 6 kg | 6 kg | 20300 | 26300 | 4383.33 |
| AC 5421112 | Highest Protein Grasslands, 11.4 kg | 11.4 kg | 46150 | 60000 | 5263.16 |
| AC 5411112 | Highest Protein Pacifica, 11.4 kg | 11.4 kg | 43150 | 56000 | 4912.28 |
| AC 5711212 | Singles Free-Run Duck, 11.4 kg | 11.4 kg | 48600 | 63000 | 5526.32 |

## Sourcing

Names, descriptions, composition, analytical constituents and every photo come
from **Champion Petfoods' own European sites**, `emea.acana.com/en/` and
`emea.orijenpetfoods.com/en/` — added to `reference/brand-sites.md`. The
`www.acana.com` / `www.orijenpetfoods.com` hosts serve the North-American
catalogue, where three of our recipes carry different names (Yorkshire Pork is
"Pork & Squash" there), so the EMEA hosts are the correct source for this stock.
No hafo photo was used, so nothing here is a watermarked placeholder and
`needs-image.csv` is empty for this run.

## Feature-image audit

`scripts/feature-image.py --only <the 23> ` reports **0 variants to reorder** —
`images[0]` is the clean front packshot on every product.

The audit classified by filename and knew only Trixie's CDN prefixes, so on the
first pass it flagged all 23 as `unknown`, which would have handed you a
`needs-packshot.csv` of 23 false entries. The classifier now also understands
Champion Petfoods' convention, where the view is written into the file name
(`… Front Right 6kg EMEA APAC` = the bag alone on white, `… Back …` = the back of
the same bag, `Bowl Image` / `Key Features` / `New Look` = graphics). Trixie
classification is unchanged.

Two products remain flagged — **982 Orijen Small Breed** and **1015 Orijen Six
Fish**. Orijen names its files `Small-Breed (1).png` … `(6).png`, with no view
word, so the filename cannot prove what the picture is. Both were opened and
looked at during the run: image 1 is the front packshot, bag alone on white, and
the printed net weight on each bag (4.5 kg and 5.4 kg) matches the pack we sell.
They are correct as they stand; the flag means "filename gives no view word",
not "wrong image".

## Open items for the PM

1. **Packshot weight.** The brand publishes exactly one packshot per recipe;
   requesting another size 404s. For 9 products the bag in the photo reads 6 kg
   while we sell 11.4 kg — artwork identical, printed net weight different.
   Listed in `packshot-weight-mismatch.csv`. Using it beat shipping no image,
   but it is a deliberate call, not an oversight.
2. **Grouping.** Several of these are one brand line in several flavours —
   Highest Protein (Ranchlands / Wild Prairie / Grasslands / Pacifica, 11.4 kg),
   Classics (Wild Coast / Prairie Poultry / Red Meat, 9.7 kg), Singles
   (Yorkshire Pork / Grass-Fed Lamb / Free-Run Duck, 11.4 kg) and the three cat
   Highest Protein recipes. The shelf test calls flavour a variant axis, but
   each recipe here has its own pack artwork, which the same rule calls a
   product split; the rule's tiebreaker for an unclear case is "separate
   products + flag". They are separate products. Regrouping later is
   `rename-product.sh` + `add-variant.sh`; say the word.
3. **Translations.** Names and the descriptive copy are written in ru and hy for
   all 23 (verified by reading all three locales back off the server). The
   **composition and analytical constituents stay in English** — the brand's own
   wording — with translated headings and a note in each locale saying so. A
   mistranslated ingredient list is an allergen risk, so that text is left for a
   professional pass rather than guessed at.
4. **Stock** is the standing placeholder 10 for every row (register Qty = 1).
5. **The rest of invoice A6833625890.** 58 more dry-food rows on the same
   invoice are still missing — Monge, Gemon, 4 Paws, Farmina N&D, Simba, Մյաու,
   GAF, My Love. Beyond that, 288 rows of the register are absent from
   `csv/products.csv` altogether. Scope for this run was Acana and Orijen only.

## Note on the count

The register holds **23** Acana/Orijen rows, not 50. hafo lists roughly 50
Acana/Orijen SKUs in total, but we only received these 23.

## Files

- `IMPORTED.csv` — the 23 products with ids, slugs, prices, EANs and source page
- `packshot-weight-mismatch.csv` — the 9 galleries whose photo shows another pack size
- `manager-register.csv` — the PM's spreadsheet converted to CSV
- `csv/acana-orijen.csv` — the resolved input (codes, costs, hafo prices, EANs)
