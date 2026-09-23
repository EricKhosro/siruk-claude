#!/usr/bin/env python3
"""Write runs/<date>/{no-hafo-price,not-found,sibling-priced,needs-packshot,blocked-no-category}.csv from the plan files."""
import csv, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(ROOT, "runs", sys.argv[1] if len(sys.argv) > 1 else "2026-09-11")
os.makedirs(RUN, exist_ok=True)
plans = [json.load(open(os.path.join(ROOT, ".siruk-cache", f))) for f in ("trixie-plan.json", "monge-plan.json") + tuple(sys.argv[2:])]
COLS_UNP = ["Article Code", "Brand", "Official Site", "Proposed Product Name", "Proposed Variant", "Buy Price (AMD)", "Sale Price (AMD)", "Qty", "Species", "Invoice Name (as printed)", "Why no price", "Status"]
COLS_NF = ["Article Code", "Brand", "Invoice Name (as printed)", "Buy Price (AMD)", "Qty", "Species", "Note"]
COLS_SIB = ["Article Code", "Brand", "Product (admin id)", "Variant", "Buy Price (AMD)", "Sale Price (AMD)", "Priced from (sibling code)", "Sibling hafo price", "Why hafo had no price", "Date"]


def write(name, cols, rows):
    with open(os.path.join(RUN, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    print(name, len(rows))


unp, nf, sib, blocked = [], [], [], []
for p in plans:
    unp += p.get("unpriced", [])
    for r in p.get("notfound", []):
        nf.append({"Article Code": r["Article Code"], "Brand": r["Brand"], "Invoice Name (as printed)": r.get("Product Name (as printed)", r.get("Invoice Name (as printed)", "")),
                   "Buy Price (AMD)": r["Buy Price (AMD)"], "Qty": r.get("Qty Received", r.get("Qty", "")), "Species": r.get("Species", ""), "Note": r.get("Note", "")})
    for r in p.get("needs_category", []):
        nf.append({"Article Code": r["Article Code"], "Brand": r["Brand"], "Invoice Name (as printed)": r["Product Name (as printed)"],
                   "Buy Price (AMD)": r["Buy Price (AMD)"], "Qty": r["Qty Received"], "Species": r["Species"], "Note": "NEEDS CATEGORY — " + r.get("Note", "")})
    sib += [dict(s, **{"Product (admin id)": s.get("Product", "")}) for s in p.get("sibling", [])]
    for b in p.get("blocked_no_category", []):
        for v in b["variants"]:
            blocked.append({"Article Code": v["_code"], "Brand": "Trixie", "Proposed Product Name": b["name"], "Proposed Variant": v["name"], "Buy Price (AMD)": v["cost_price"],
                            "Sale Price (AMD)": v["price"], "Qty": v["stock"], "Invoice Name (as printed)": v["_inv"], "Source": b["source"],
                            "Why": "no product category: 13 Accessories cannot hold products (absent from /categories?forProducts); needs a Supplies leaf (e.g. Chewy's Bowls & Feeders / Collars, Leads & Harnesses / Beds & Mats / Hygiene / Cleaning) — categories are created only on your explicit ask"})
    for r in p.get("blocked_rows", []):  # small plan: rows with no category at all (Mr. Fresh cleaning)
        blocked.append({"Article Code": r["Article Code"], "Brand": r["Brand"], "Proposed Product Name": r["Proposed Product Name"], "Proposed Variant": "",
                        "Buy Price (AMD)": r["Buy Price (AMD)"], "Sale Price (AMD)": r["Sale Price (AMD)"], "Qty": r.get("Qty", ""), "Invoice Name (as printed)": r.get("Invoice Name (as printed)", r["Proposed Product Name"]),
                        "Source": r.get("Source", ""), "Why": r["Why"]})
write("no-hafo-price.csv", COLS_UNP, unp)
write("not-found.csv", COLS_NF, nf)
write("sibling-priced.csv", COLS_SIB, sib)
write("blocked-no-category.csv", ["Article Code", "Brand", "Proposed Product Name", "Proposed Variant", "Buy Price (AMD)", "Sale Price (AMD)", "Qty", "Invoice Name (as printed)", "Source", "Why"], blocked)
# ---- needs-image.csv: created, but the brand site publishes no picture (rule 7a: hafo's own photos are watermarked and unusable)
try:
    img = json.load(open(os.path.join(ROOT, ".siruk-cache", "image-plan.json")))
except FileNotFoundError:
    img = {}
todo_rows = {r["Article Code"]: r for r in json.load(open(os.path.join(ROOT, ".siruk-cache", "todo-rows.json")))}
hafo_all = json.load(open(os.path.join(ROOT, ".siruk-cache", "hafo-all.json")))
noimg = []
for x in img.values():
    placeholder = bool(x["urls"]) and all("hafo.am" in x["sources"][u] for u in x["urls"])
    if x["urls"] and not placeholder:
        continue
    code = x["code"]
    brand = (hafo_all.get(code) or {}).get("brand") or todo_rows.get(code, {}).get("Brand", "")
    why = ("the article is gone from trixie.de and from its CDN (12 file prefixes × 26 indices and 10 name suffixes probed, "
           "no sibling page carries it) and from trixie.es, trixie.shop and trixiecz.cz — the whole approved chain "
           "(config.json → images.sources)") if code.lower().endswith("tx") else \
          ("monge.it publishes this line only in the other pack sizes (150 g / 300 g / 1230 g); no file names this pack" if code.startswith("0415") or code.startswith("0417") or code.startswith("0418")
           else "the brand's official site has no picture keyed to this article")
    noimg.append({"Article Code": code, "Brand": brand, "Product (admin id)": x["product_id"], "Product": x["name"], "Variant SKU": x["sku"],
                  "Invoice Name (as printed)": todo_rows.get(code, {}).get("Product Name (as printed)", ""),
                  "Current image": ("hafo.am placeholder (watermarked) — " + x["urls"][0]) if x["urls"] else "none",
                  "Why the brand site has none": why,
                  "What would fix it": "replace with an unwatermarked photo of this exact article: a pack photo, or the supplier's own file"})
write("needs-image.csv", ["Article Code", "Brand", "Product (admin id)", "Product", "Variant SKU", "Invoice Name (as printed)",
                          "Current image", "Why the brand site has none", "What would fix it"], noimg)

write("needs-packshot.csv", ["Article Code", "Brand", "Product", "Variant", "First image", "Why"], [
    {"Article Code": "201303Tx", "Brand": "Trixie", "Product": "Premium Adjustable Lead, XS, 2.00 m/10 mm, red (NOT imported — blocked, no category)", "Variant": "XS, 2.00 m/10 mm, red", "First image": "PHO_PRO_USE_CLIP_201303-… (person with dog)", "Why": "trixie.de lists only the in-use photo for this article; no packshot on the CDN"},
    {"Article Code": "25032Tx", "Brand": "Trixie", "Product": "Slow Feeding Plastic Bowl, 0.9 l/ø 23 cm (NOT imported — blocked, no category)", "Variant": "0.9 l/ø 23 cm", "First image": "PHO_PRO_DOG_25032-7 (dog eating)", "Why": "page has only dog photos and a group shot with the sibling sizes; no packshot on the CDN"}] + [
    {"Article Code": f["code"], "Brand": "Iv San Bernard", "Product": next((pp["name"] for pp in p.get("products", []) for v in pp["variants"] if v["sku"] == f["code"]), ""), "Variant": "", "First image": "isbusa.com group shot of the product's sizes", "Why": f["what"]}
    for p in plans for f in p.get("flagged", []) if "needs-packshot" in f["what"]])
