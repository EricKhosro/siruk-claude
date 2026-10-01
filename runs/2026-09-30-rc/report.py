#!/usr/bin/env python3
"""report.md + barcodes.csv from plan.json (and state.json once the import has run)."""
import csv, json, os

R = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(f"{R}/plan.json")); P = d["products"]
state = json.load(open(f"{R}/state.json")) if os.path.exists(f"{R}/state.json") else {"done": {}, "problems": []}
skipped = json.load(open(f"{R}/skipped-by-user.json")) if os.path.exists(f"{R}/skipped-by-user.json") else {}
nv = sum(len(p["variants"]) for p in P)
imgs = sum(len(v["_image_urls"]) for p in P for v in p["variants"] if not v.get("_twin_of"))

with open(f"{R}/barcodes.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["file_row", "name_in_file", "product", "product_id", "variant", "sold_as", "sku", "barcode_ean",
                "barcode_source", "price", "cost", "stock"])
    for p in P:
        pid = (state["done"].get(p["key"]) or {}).get("product_id", "") or ("skipped" if p["key"] in skipped else "")
        for v in p["variants"]:
            sold = {"per kg": "loose, per kg", "single pouch": "single pouch"}.get(v.get("_loose"), "pack")
            stock = f"{v['initial_stock']} g" if v["sale_mode"] == "weight" else v["initial_stock"]
            w.writerow([v["_row"], v["_file_name"], p["name"], pid, v["name"], sold, v["sku"], v["_ean"] or "",
                        (v["_ean_url"] if v.get("_ean") and not v.get("_twin_of") else
                         ("same page (single pouch)" if v.get("_ean") else
                          "no barcode — loose sale" if v.get("_loose") == "per kg" else
                          "no barcode published for this size")),
                        int(v["price"]), v["cost_price"], stock])

L = ["# Royal Canin import — production (2026-09-30)\n",
     "Source: `Price Royal Canin Nor _ SIRUK.xlsx`, the 52 rows with a number in column E. Sale price = column C "
     "`Վաճառքի Գին`, cost = column B, column D `Վաճառքի Գին կիլոգրամով` = the loose price (see below). Stock 10 each "
     "(by-weight variants: 10 kg = 10,000 g). Content, photos and barcodes: royalcanin.com (UK; Malta for Sterilised "
     "Loaf and the Sterilised 37 15 kg barcode).\n",
     f"**{len(P) - len(skipped)} products to import · {sum(len(p['variants']) for p in P if p['key'] not in skipped)} variants · "
     f"{len(skipped) + 1} rows not imported.** "
     + (f"Imported: {len(state['done'])}/{len(P) - len(skipped)}." if state["done"] else "Nothing written yet.") + "\n",
     "## Column D — the loose variant",
     "- **Dry food**: every bag also gets a **by-weight** variant (`sale_mode: weight`): price = column D per kg, "
     "the customer buys whole kilograms (minimum 1 kg, step 1 kg — user, 2026-10-01); cost = column B ÷ bag kg; stock 10 kg. SKU = bag barcode + `-KG`.",
     "- **Wet food**: D (750) is below our cost per kg (7,500 ÷ 1.02 kg), so it is the price of **one 85 g pouch** — "
     "a single-pouch pack variant at 750, cost 7,500 ÷ 12 = 625, stock 10. SKU = the single pouch's own barcode where "
     "royalcanin.com lists it, else the 12-pack barcode + `-1`.",
     "- The backend allows one by-weight variant per option combination (all loose food shares the size \"by weight\"), "
     "so a line whose bags differ only in size gets one loose variant, not one per bag. In this batch every dry "
     "product has one bag, so each gets exactly one.\n",
     "| # | Product | id | Type | Categories | Variant | Sold as | Price | Cost | Barcode (SKU) |",
     "|---|---|---|---|---|---|---|---|---|---|"]
for i, p in enumerate([p for p in P if p["key"] not in skipped], 1):
    pid = (state["done"].get(p["key"]) or {}).get("product_id", "")
    for v in p["variants"]:
        sold = {"per kg": "loose / kg", "single pouch": "single pouch"}.get(v.get("_loose"), "pack")
        L.append(f"| {i} | {p['name']} | {pid} | {'Dry' if p['type'] == 1 else 'Wet'} | {p['categories']} | {v['name']} | {sold} "
                 f"| {int(v['price']):,} | {v['cost_price']:,} | {v['_ean'] or '— (' + v['sku'] + ')'} |")
skipped = json.load(open(f"{R}/skipped-by-user.json")) if os.path.exists(f"{R}/skipped-by-user.json") else {}
names = {p["key"]: p for p in P}
L += ["", "## Not imported"] + [f"- row {k}: {v}" for k, v in d["held"].items()]
L += [f"- row {row}: {names[k]['variants'][0]['_file_name']} → '{names[k]['name']}' — skipped on the user's instruction (2026-10-01)"
      for k, row in skipped.items()]
L += ["", "## Decisions and notes",
      "- Gravy / jelly / loaf of one recipe are one product with a texture variant each (Hair & Skin, Instinctive, "
      "Kitten, Light Weight Care, Sterilised); Renal chicken + fish are one product with a flavour variant each.",
      "- Loaf: there is no Loaf texture value, so loaf variants use **Pate** (Royal Canin's loaf is a pâté; the Russian "
      "label is «паштет»); the variant label says \"Loaf\".",
      "- Sensory Smell / Taste / Feel: the file doesn't say gravy or jelly — imported as **gravy**, Royal Canin's default.",
      "- Row 188 Mother & Babycat: one case of 12 × 195 g cans at 2,300 (user, 2026-09-30).",
      "- Row 58 Fit 32 15 kg: no barcode published for the 15 kg bag (royalcanin.com lists 2 / 4 / 10 kg) — SKU `RC-FIT-32-15000G`.",
      "- Row 194 'Instinctive 12+ jelly' = Royal Canin product 4153, sold in the UK as 'Ageing 11+ in jelly' (same "
      "product id); its photo and text say 11+. Named 'Ageing 12+ Chunks in Jelly'.",
      "- Veterinary dry foods for dogs also go in Dog › Food › Health Condition (5); cats have no such leaf.",
      "- Feeding guides are not in royalcanin.com's page data, so feeding instructions are empty.",
      "- Royal Canin's page data had CMS labels in some bullets (\"4B- Nutrient 1-Fop\", \"Claim 1 - … Long Text\") — "
      "stripped. Gastrointestinal Dog and Gastrointestinal Puppy carried cat wording copied from the cat pages — "
      "corrected to dog/puppy in all three languages. Cardiac Dog's broken \"IRIS stage 3 or stage\" is left as "
      "Royal Canin wrote it.",
      "- Product 1229 (Maxi Adult): its first upload attempt stopped at the duplicate-name guard (a **Monge** product is also "
      "named \"Maxi Adult\"); the 10 photos uploaded then were reused, not uploaded twice. Same-name products of other brands are fine.",
      "- Translations (ru / hy): worth a native speaker's look at vet terms (metabolisable energy, zootechnical "
      "additives, green-lipped mussel, IBD/EPI abbreviations in Armenian)."]
if state["problems"]:
    L += ["", "## Problems during the import"] + [f"- {k}: {m}" for k, m in state["problems"]]
open(f"{R}/report.md", "w").write("\n".join(L) + "\n")
print(len(P), nv, imgs)
