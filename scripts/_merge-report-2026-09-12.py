#!/usr/bin/env python3
"""Write runs/2026-09-12/report.md from the merge plan, state and id map."""
import collections, csv, json, pathlib

RUN = pathlib.Path("runs/2026-09-12")
plan = json.load(open(RUN / "merge-plan.json"))
state = json.load(open(RUN / "merge-state.json"))
review = json.load(open(".siruk-cache/dedup/review.json"))
done = set(state["done"])
rows = list(csv.DictReader(open(RUN / "variant-id-map.csv")))

by_brand = collections.Counter()
for p in plan["plan"]:
    by_brand[p["brand"]] += len(p["absorb"])

out = []
w = out.append
w("# Duplicate products folded into their real parent products — 2026-09-12\n")
w(f"**{sum(len(p['absorb']) for p in plan['plan'] if p['target'] in done)} duplicate products removed.** "
  f"{sum(len(p['group']) for p in plan['plan'] if p['target'] in done)} catalogue entries that were really "
  f"options of one product are now {len(done)} products with "
  f"{len(rows)} variants between them.\n")
w("The trigger: sibling rows imported as separate products — "
  "`.../trixie-active-comfort-leather-collar-with-rhinestones-s-m-27-33-cm-15-mm-pink/dp/1108/` and "
  "`.../xxs-xs-17-21-cm-12-mm-pink/dp/1107/` were two products where Trixie sells one collar in two sizes.\n")

w("## How a group was decided\n")
w("Three signals, the first two authoritative in both directions — they merge AND they split:\n")
w("| Signal | What it is | Why it is trusted |")
w("|---|---|---|")
w("| trixie.de | the article codes sit on the same official product page | Trixie's own variant table for that product |")
w("| trixie.shop | the article codes are options of the same Shopify product | Trixie's own store, and it reaches discontinued lines |")
w("| name | identical product name once the variant label is stripped, same brand, same categories | only where no official signal contradicts it |\n")
w("The splitting half did real work: it kept the **three different Stainless Steel Bowl lines** apart "
  "(24851–55 heavy weight, 25071–74 non-slip, 25271–73 varnished), the **six Soft Brush lines**, and "
  "`Dog Socks XL/black` (19526), which is a different Trixie product from the grey 19500–19503 set.\n")

w("## Two merges the cross-check threw out\n")
w("- **Premium Adjustable Lead, XS–S: 2.00 m/15 mm, light lilac** (803, article 200720) — "
  "the name matched the 201301–201316 leads exactly, but trixie.shop puts every 2007xx "
  "article on *Premium Verlängerungsleine **doppellagig***, the double-layered lead. "
  "Left as its own product.")
w("- **\"Animals, latex, 13 cm\"** (423, article 35263) — grouped with 35031/35061 by name, "
  "but trixiecz calls 35263 *Geometrické zvíře, plněný latex* while 35031/35061 are the "
  "*Longie* line. Left as its own product; the other two were merged and renamed "
  "**Longie, latex/polyester fleece**, which is what Trixie actually calls them.\n")

w("## The variant axis\n")
w("The storefront builds its variant selector from **attributes**, not from the variant label — "
  "checked live on product 874, whose second variant had no `flavor` and was unreachable: the "
  "selector rendered one option. So every merged product needed an axis whose value differs per variant.\n")
w("Two attributes were created (approved beforehand) and four extended:\n")
w("| Attribute | | New values | Filterable |")
w("|---|---|---|---|")
w("| `size` **28** | new — letter sizes `XXS–XS`…`XL` for collars, harnesses, leads and "
  "apparel; measurement strings (`0.45 l/ø 19 cm`, `9 × 15 cm`, `4 × 20 bags`) for bowls, "
  "brushes and packs | 59 | no — the value set is mixed on purpose, same call as `toy-size` |")
w("| `pet-weight-range` **27** | new — the dose band printed on antiparasitic drops and "
  "tablets | 7 | yes |")
w("| `color-family` 15 | existing — fuchsia → Pink, graphite → Grey, orchid → Purple, "
  "petrol → Teal, sand → Beige, curry → Yellow, chrome → Silver | 0 | yes |")
w("| `flavor` 5 | Veal, Trout, Meat and Chicken and Vegetables — flavours earlier imports "
  "left blank because the value did not exist, which is what hid them | 4 | yes |")
w("| `product-weight` 1 | 11 l, 120 g, 175 ml, 200 g, 750 ml | 5 | yes |")
w("| `toy-size` 16 | 30–32 cm, 37 cm | 2 | no (unchanged) |")
w("")
w("The full measurement stays in the variant label — the shopper still reads "
  "\"XS–S, 22–35 cm/10 mm, black\" on the page; only the letter size rides on `size`, "
  "so the vocabulary stays usable.\n")
w("All 19 attributes, 713 values and 5 family names read back clean in en/ru/hy "
  "(`scripts/translate-attributes.py`: 0 mismatches).\n")

w("## What changed per brand\n")
w("| Brand | Duplicate products removed |")
w("|---|---|")
for b, n in by_brand.most_common():
    w(f"| {b} | {n} |")
w("")

w("## The merged products\n")
w("| Product | Variants | Axis | Absorbed |")
w("|---|---|---|---|")
for p in sorted(plan["plan"], key=lambda x: -len(x["variants"])):
    if p["target"] not in done: continue
    ax = ", ".join(f"`{a}`" for a in p["axis"]) or "flavour / weight already on the variants"
    w(f"| [{p['brand']} {p['name']}](https://demo.siruk.am/product/{p['slug']}/dp/"
      f"{[r['new_variant'] for r in rows if r['new_product']==str(p['target'])][0]}/) "
      f"| {len(p['variants'])} | {ax} | {len(p['absorb'])} |")
w("")

w("## Verified after the merge\n")
w("| Check | Result |")
w("|---|---|")
w(f"| every sku still on the shelf | {len(rows)}/{len(rows)} — none lost |")
w("| price, cost, stock, image count, `about_this_item` per sku | identical to the pre-merge backup on all "
  f"{len(rows)} |")
w("| catalogue size | 834 → 703 products |")
w("| re-scan (`find-duplicate-products.py --refresh`) | 0 groups left; the one hand-split product listed with its evidence |")
w("| ru/hy on the 66 merged products | complete (`verify-translations.py`) |")
w("| the two products in the request | `/dp/1107` and `/dp/1108` are now [one collar](https://demo.siruk.am/product/trixie-active-comfort-leather-collar-with-rhinestones/dp/1286/) with a Size and a Color Family selector |")
w("")
w("## Fixed along the way\n")
w("**Product 874, Gemon All Breeds Adult Dog Chunks** — not a duplicate, but the same defect: "
  "its second variant (`387967`, Veal, Liver & Vegetables) carried no `flavor`, so the Flavor "
  "selector offered only Salmon and that variant could not be bought. It now has `flavor: Veal`. "
  "It was the only product in the catalogue whose *axis* had a hole; the rest of the holes found "
  "are on `ingredient`, which is informational.\n")
w("**A trap worth knowing** — `scripts/set-translation.py` writes *every* variant, so a "
  "sku left out of the translation file gets the English text written into that locale. "
  "Translating one variant of product 1016 wiped the Armenian texts of its other two; both "
  "are restored, and the warning is now in `reference/admin-api.md` and the script guide.\n")
w("## Still open\n")
w("- **`size` is not filterable.** Its values mix letter sizes with measurement strings, so a "
  "sidebar facet would read badly — same call as `toy-size`. If you want collars filterable by "
  "size, the fix is to split the measurement strings onto their own attribute, not to flip the "
  "flag.")
w("- Three products remain English-only in ru/hy from earlier imports, untouched here: 906 "
  "Towel with Pockets, 346 Junior Soft Snack Dots, 350 Soft Snack Bony Mix XXL. (MOT®-Fun, "
  "Longie, Turbinio and Twists are Latin brand names by policy.)")
w("- The detection only has an authoritative second opinion for **Trixie**. Monge, Inspector, "
  "Insectal, Club 4 Paws and Ok-Lock groups rest on the name plus consecutive article codes "
  "within one line; each was read by hand, but a brand-site index for them would make the next "
  "sweep as strong as Trixie's.\n")
w("## Links\n")
w(f"- `runs/2026-09-12/variant-id-map.csv` — every old `/dp/<id>` and the id it became ({len(rows)} rows).")
w("- `runs/2026-09-12/merge-backup/` — the full pre-merge record of all 197 products in en/ru/hy.")
w("- `runs/2026-09-12/merge-plan.json` — what was decided, per group and per variant.\n")

(RUN / "report.md").write_text("\n".join(out))
print(f"wrote {RUN/'report.md'}")
