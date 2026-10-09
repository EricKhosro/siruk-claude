"""Split products.json + images.csv into review batches (by product, ~N variants each) with hafo identity hints."""
import json, os, csv, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 70
prods = json.load(open(os.path.join(HERE, "products.json")))
rows = list(csv.DictReader(open(os.path.join(HERE, "images.csv"))))
hafo = json.load(open(os.path.join(ROOT, ".siruk-cache/hafo-all.json")))
hidx = {}
for k, h in hafo.items():
    for key in [k] + (h.get("articles") or []) + (h.get("skus") or []) + [h.get("variant_sku") or ""]:
        if key: hidx[key.replace(" ", "").upper()] = h
byv = collections.defaultdict(list)
for r in rows: byv[r["variant_id"]].append(r)
items = []
for pid, p in sorted(prods.items(), key=lambda x: int(x[0])):
    brand = next((r["brand"] for r in rows if r["product_id"] == pid), "")
    vs = []
    for v in p["variants"]:
        sku = v["sku"]; base = sku[:-3] if sku.endswith("-KG") else sku
        h = hidx.get(base.replace(" ", "").upper()) or {}
        vs.append({"variant_id": v["id"], "sku": sku, "label": v["name"], "size_label": v.get("size_label"),
                   "options": "; ".join(f'{a.get("attributeName")}={a.get("label")}' for a in (v.get("attribute_value_labels") or []) if a.get("role") == "option"),
                   "hafo_title_hy": h.get("title_hy"), "hafo_variant_hy": h.get("variant_name_hy"), "ean": (h.get("barcodes") or [None])[0],
                   "images": [{"pos": int(r["pos"]), "media": r["media"], "file": r["file"], "dims": r["dims"], "local": r["local"], "md5": r["md5"]}
                              for r in sorted(byv.get(str(v["id"]), []), key=lambda r: int(r["pos"]))]})
    items.append({"product_id": pid, "product": p["name"], "brand": brand, "type": p.get("attribute_family_name"), "variants": vs})
batches, cur, n = [], [], 0
for it in items:
    cur.append(it); n += len(it["variants"])
    if n >= N: batches.append(cur); cur, n = [], 0
if cur: batches.append(cur)
os.makedirs(os.path.join(HERE, "batches"), exist_ok=True)
for i, b in enumerate(batches, 1):
    json.dump(b, open(os.path.join(HERE, "batches", f"batch-{i:02d}.json"), "w"), ensure_ascii=False, indent=1)
print(len(batches), "batches", [sum(len(x["variants"]) for x in b) for b in batches])
