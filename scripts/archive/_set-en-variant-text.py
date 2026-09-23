#!/usr/bin/env python3
"""Write the English variant texts (about_this_item / ingredient_information /
feeding_instructions) onto an existing product, without touching anything else.

Same read-modify-write discipline as set-translation.py: every single-language
field is copied back from the live record, so the PUT that replaces the
variants array cannot lose prices, images, attributes or labels.

    scripts/_set-en-variant-text.py <product-id> <texts.json>

texts.json: {"<sku>": {"about_this_item": "<html>", "ingredient_information": "<html>",
                       "feeding_instructions": "<html>"}}
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
KEEP = ("slug", "category_ids", "brand_id", "attribute_family_id", "is_best_seller",
        "is_on_sale", "is_discontinued")
VKEEP = ("id", "name", "pricing_type", "sku", "price", "price_per_kg", "min_allowed_price",
         "cost_price", "compare_at_price", "weight", "is_default", "stock", "vendor_stock",
         "sort_order", "images", "attribute_value_ids")
VTEXT = ("about_this_item", "ingredient_information", "feeding_instructions")

def api(method, path, payload=None):
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "_en-text.json")
        json.dump(payload, open(p, "w"), ensure_ascii=False)
        args.append(p)
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=180,
                       env=dict(os.environ, SIRUK_LANG="en"))
    i = r.stdout.find("{")
    if i < 0:
        sys.exit(f"api {method} {path} failed: {r.stderr.strip()[-300:]}")
    return json.loads(r.stdout[i:])

def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    pid, tfile = sys.argv[1], sys.argv[2]
    texts = json.load(open(tfile))
    en = api("GET", f"/products/{pid}")["data"]
    skus = {v["sku"] for v in en["variants"]}
    unknown = set(texts) - skus
    if unknown:
        sys.exit(f"texts name SKUs not on product {pid}: {sorted(unknown)}")
    for sku, t in texts.items():
        extra = set(t) - set(VTEXT)
        if extra:
            sys.exit(f"variant {sku}: only {VTEXT} may be set, got {sorted(extra)}")

    before = {v["sku"]: {k: v.get(k) for k in ("name", "price_per_kg", "price", "weight",
                                               "cost_price", "stock", "images",
                                               "attribute_value_ids")}
              for v in en["variants"]}
    body = {k: en.get(k) for k in KEEP}
    body["name"] = en["name"]
    body["locale"] = "en"
    body["variants"] = []
    for v in en["variants"]:
        nv = {k: v.get(k) for k in VKEEP if k in v}
        nv["images"] = nv.get("images") or []
        nv["attribute_value_ids"] = nv.get("attribute_value_ids") or {}
        t = texts.get(v["sku"], {})
        for f in VTEXT:
            nv[f] = t.get(f) if t.get(f) is not None else (v.get(f) or "")
        body["variants"].append(nv)

    api("PUT", f"/products/{pid}", body)
    got = api("GET", f"/products/{pid}")["data"]
    problems = []
    if got["name"] != en["name"]:
        problems.append(f"name changed: {got['name']!r}")
    for v in got["variants"]:
        b = before.get(v["sku"])
        if b is None:
            problems.append(f"variant {v['sku']} appeared/vanished"); continue
        for k, old in b.items():
            if (v.get(k) or ("" if isinstance(old, str) else old)) != old:
                problems.append(f"{v['sku']}.{k} changed: {old!r} → {v.get(k)!r}")
        t = texts.get(v["sku"], {})
        for f in VTEXT:
            if t.get(f) is not None and (v.get(f) or "") != t[f]:
                problems.append(f"{v['sku']}.{f} not stored")
    print(f"product {pid}: variants={len(got['variants'])} "
          + ("OK" if not problems else "PROBLEMS: " + "; ".join(problems[:6])))
    sys.exit(1 if problems else 0)

if __name__ == "__main__":
    main()
