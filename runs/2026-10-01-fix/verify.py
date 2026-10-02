#!/usr/bin/env python3
"""Read-only check of production after the 2026-10-01 fixes + the hafo-image list.

Needs media-index.json (media-index.py). Re-reads every product once → snapshot/,
then checks:
  * every bag in kg-rows.json has a weight twin at the Kg price, 1 kg min/step
  * every pack variant on_hand 10, weight 10000, retired -1KG twins 0 (or allocated)
  * no product name (en) ends in a pack size
  * every variant still showing a hafo.am photo (file-name test, as scripts/hafo-audit.py)
Writes verify.json and hafo-images.csv (with siruk.am links).

    verify.py [--reuse]     # --reuse: use snapshot/ as is
"""
import csv, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
os.environ.update(SIRUK_API="https://api.siruk.am/api/admin",
                  SIRUK_TOKEN_FILE=os.path.join(ROOT, ".siruk-token-prod"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import api  # noqa: E402

SNAP = os.path.join(HERE, "snapshot")
os.makedirs(SNAP, exist_ok=True)
if "--reuse" not in sys.argv:
    ids, page = [], 1
    while True:
        d = api("GET", f"/products?page={page}")
        ids += [p["id"] for p in d.get("data", [])]
        if page >= d["meta"]["last_page"]:
            break
        page += 1
    for f in os.listdir(SNAP):
        os.remove(os.path.join(SNAP, f))
    for i in ids:
        json.dump(api("GET", f"/products/{i}")["data"], open(os.path.join(SNAP, f"{i}.json"), "w"))
P = {}
for f in os.listdir(SNAP):
    d = json.load(open(os.path.join(SNAP, f)))
    P[d["id"]] = d
link = lambda p, v: f"https://siruk.am/product/{p['slug']}/dp/{v['id']}/"
out = {"products": len(P), "problems": []}
bad = out["problems"].append

# loose sale
rows = [r for r in json.load(open(os.path.join(HERE, "kg-rows.json"))) if r["insiruk"] == "Yes"]
V = {v["id"]: (p, v) for p in P.values() for v in p["variants"]}
for r in rows:
    bag_id = int(re.search(r"/dp/(\d+)", r["link"]).group(1))
    p, bag = V[bag_id]
    tw = [v for v in p["variants"] if v["sku"] == f"{bag['sku']}-KG"]
    if not tw or tw[0]["sale_mode"] != "weight" or tw[0]["price"] != int(r["kg"]) \
            or tw[0]["qty_min"] != 1000 or tw[0]["qty_step"] != 1000:
        bad(["weight", p["id"], bag["sku"], tw[0]["sale_mode"] if tw else "missing"])
# stock
for p in P.values():
    for v in p["variants"]:
        lvl = next((l for l in v["stock_levels"] if l["warehouse_id"] == 1), {"on_hand": 0, "allocated": 0})
        want = lvl["allocated"] if v["sku"].endswith("-1KG") or p["is_discontinued"] else (
            10000 if v["sale_mode"] == "weight" else 10)
        if lvl["on_hand"] != want:
            bad(["stock", p["id"], v["sku"], lvl["on_hand"], want])
# names
SZ = re.compile(r"(?<![–\-\d.,])\b\d+(?:[.,]\d+)?\s*(?:kg|g|ml)\.?\s*$", re.I)
for p in P.values():
    if SZ.search(p["name"] or "") and not p["is_discontinued"]:
        bad(["name", p["id"], p["name"]])

# hafo photos
idx = {int(k): m for k, m in json.load(open(os.path.join(HERE, "media-index.json"))).items()}
CDN = {int(v) for u, v in json.load(open(os.path.join(ROOT, ".siruk-cache", "media-cache.json"))).items()
       if "d1b3l6j8a0ngef.cloudfront.net" in u and isinstance(v, int)}   # media ids = demo ids (prod is a copy)


def kind(mid):
    """'cdn' = uploaded from hafo's CDN (certain); 'name' = hafo-style file name (probable:
    a bare 10+ digit name can also be an EAN — look at it); None = not hafo."""
    if mid in CDN:
        return "cdn"
    fn = str((idx.get(mid) or {}).get("filename") or "")
    head = fn.split("-")[0]
    if fn.lower().startswith("hafo") or (head.isdigit() and len(head) >= 10 and len(head) != 13):
        return "name"
    return None
hafo_rows = []
for p in sorted(P.values(), key=lambda p: p["id"]):
    if p["is_discontinued"]:
        continue
    for v in p["variants"]:
        if v["sku"].endswith("-1KG"):
            continue
        kinds = [kind(m) for m in v["images"]]
        pos = [i + 1 for i, k in enumerate(kinds) if k]
        unknown = [m for m in v["images"] if m not in idx]
        if pos or unknown:
            hafo_rows.append({"product_id": p["id"], "product": p["name"], "variant_id": v["id"], "sku": v["sku"],
                              "variant": v["size_label"] or v["name"], "images": len(v["images"]),
                              "hafo_positions": " ".join(map(str, pos)),
                              "only_hafo": len(pos) == len(v["images"]),
                              "detected_by": " ".join(sorted({k for k in kinds if k})),
                              "hafo_media": " ".join(str(m) for m, k in zip(v["images"], kinds) if k),
                              "unindexed_media": " ".join(map(str, unknown)), "siruk_link": link(p, v)})
with open(os.path.join(HERE, "hafo-images.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(hafo_rows[0]) if hafo_rows else ["product_id"])
    w.writeheader(); w.writerows(hafo_rows)
out["hafo_variants"] = len(hafo_rows)
json.dump(out, open(os.path.join(HERE, "verify.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in out.items()}))
for b in out["problems"][:40]:
    print(b)
