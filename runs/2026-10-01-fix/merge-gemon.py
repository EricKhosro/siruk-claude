#!/usr/bin/env python3
"""Production fix 2026-10-01: fold Gemon "Adult Dog Paté" 400 g cans (product 678)
into "Adult Dog Paté, 150 g" trays (product 1102) — same line, a size/packaging
variant each (CLAUDE.md 9). The backend can't delete 678 (stock history), so:

  1. 678: its skus get "-OLD", the product is marked discontinued (hidden from the
     storefront — the backend's own way to retire a product with history), stock → 0;
  2. 1102: the two cans are added with their original skus, label, price, cost,
     texts, images, attributes (+ texture Paté, which every 1102 variant carries),
     initial_stock 10; their ru/hy texts are copied from 678.

    merge-gemon.py [--write]
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
os.environ.update(SIRUK_API="https://api.siruk.am/api/admin",
                  SIRUK_TOKEN_FILE=os.path.join(ROOT, ".siruk-token-prod"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import api, product_type, product_body, to_variant_payload, normalize_new, check_variants  # noqa: E402

WRITE = "--write" in sys.argv
SRC, DST = 678, 1102
VTEXT = ("about_this_item", "ingredient_information", "feeding_instructions")

src, dst = api("GET", f"/products/{SRC}")["data"], api("GET", f"/products/{DST}")["data"]
assert src["brand_id"] == dst["brand_id"] and not src["is_discontinued"], "unexpected state"
ptype = product_type(dst["attribute_family_id"])
allowed = {a["id"] for a in ptype.get("attributes") or []}
opt_ids = {a["id"] for a in ptype["attributes"] if a["role"] == "option"}
# the option every 1102 variant carries that 678's lack (texture)
dst_opts = {}
for v in dst["variants"]:
    for k, ids in (v["attribute_values"] or {}).items():
        if int(k) in opt_ids:
            dst_opts.setdefault(k, set()).update(ids)

new = []
for v in src["variants"]:
    av = {k: ids for k, ids in (v["attribute_values"] or {}).items() if int(k) in allowed}
    for k, vals in dst_opts.items():
        if k not in av:
            assert len(vals) == 1, f"option {k} has several values on {DST}: {vals}"
            av[k] = sorted(vals)
    nv = {"sku": v["sku"], "name": v["name"], "price": v["price"], "cost_price": v["cost_price"],
          "sale_mode": "pack", "measure_type": v["measure_type"], "content": v["content"],
          "pack_count": v.get("pack_count") or 1, "initial_stock": 10, "images": list(v["images"]),
          "attribute_values": av, **{f: v.get(f) or "" for f in VTEXT}}
    new.append(normalize_new(nv, ptype))

body_dst = product_body(dst)
body_dst["variants"] = [to_variant_payload(v, allowed) for v in dst["variants"]] + \
    [dict(nv, is_default=False, sort_order=len(dst["variants"]) + i) for i, nv in enumerate(new)]
errs, warns = check_variants(body_dst["variants"], ptype, {nv["sku"] for nv in new})
print("warnings:", warns)
if errs:
    sys.exit(f"refused: {errs}")
src_allowed = {a["id"] for a in product_type(src["attribute_family_id"]).get("attributes") or []}
body_src = product_body(src)
body_src["is_discontinued"] = True
body_src["variants"] = [dict(to_variant_payload(v, src_allowed), sku=v["sku"] + "-OLD") for v in src["variants"]]
print("678 →", [v["sku"] for v in body_src["variants"]], "discontinued")
print("1102 + ", [(nv["sku"], nv["name"], nv["price"], nv["attribute_values"]) for nv in new])
if not WRITE:
    sys.exit()

r = api("PUT", f"/products/{SRC}", body_src)
assert (r.get("data") or {}).get("is_discontinued"), f"678 PUT failed: {json.dumps(r)[:400]}"
r = api("PUT", f"/products/{DST}", body_dst)
assert {nv["sku"] for nv in new} <= {v["sku"] for v in (r.get("data") or {}).get("variants", [])}, \
    f"1102 PUT failed: {json.dumps(r)[:400]}"
for v in api("GET", f"/products/{SRC}")["data"]["variants"]:
    lvl = (v["stock_levels"] or [{}])[0]
    if lvl.get("on_hand"):
        api("PUT", f"/stock/variants/{v['id']}", {"warehouse_id": 1, "on_hand": lvl.get("allocated", 0),
            "reason": "correction", "note": "2026-10-01: product merged into 1102, this one discontinued"})
for lang in ("ru", "hy"):
    loc = {v["sku"]: v for v in api("GET", f"/products/{SRC}", lang=lang)["data"]["variants"]}
    t = {"variants": {nv["sku"]: {f: loc[nv["sku"] + "-OLD"].get(f) or "" for f in VTEXT} for nv in new}}
    f = os.path.join(HERE, "tr", f"merge-{DST}-{lang}.json")
    os.makedirs(os.path.dirname(f), exist_ok=True)
    json.dump(t, open(f, "w"), ensure_ascii=False, indent=1)
    r = subprocess.run([os.path.join(ROOT, "scripts/set-translation.py"), str(DST), lang, f],
                       capture_output=True, text=True, cwd=ROOT)
    print(lang, (r.stdout or r.stderr).strip()[-200:])
print("merged")
