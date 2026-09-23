#!/usr/bin/env python3
"""Remove hafo.am pictures from any variant that also has a real one.

A hafo photo is a watermarked stand-in (rule 7a) and may stay only while it is
the ONLY picture of the article — once the brand's own photo is there, the
placeholder has done its job and must go.

    scripts/_drop-hafo-where-real.py [--dry-run]
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
VKEYS = ("id", "name", "about_this_item", "ingredient_information", "feeding_instructions", "pricing_type", "sku",
         "price", "price_per_kg", "min_allowed_price", "cost_price", "compare_at_price", "weight", "is_default",
         "stock", "vendor_stock", "sort_order", "images", "attribute_value_ids")
KEEP = ("name", "slug", "category_ids", "brand_id", "attribute_family_id", "is_best_seller", "is_on_sale", "is_discontinued")


def api(method, path, payload=None):
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "_drophafo.json"); json.dump(payload, open(p, "w"), ensure_ascii=False); args.append(p)
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=300)
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:]) if i >= 0 else {"_err": r.stderr[-200:]}


def main():
    dry = "--dry-run" in sys.argv
    gaps = json.load(open(os.path.join(CACHE, "image-gaps.json")))
    mc = json.load(open(os.path.join(CACHE, "media-cache.json")))
    st = json.load(open(os.path.join(CACHE, "enrich-images.state.json")))
    bad = {v for u, v in list(mc.items()) + list(st.get("media", {}).items())
           if "d1b3l6j8a0ngef.cloudfront.net" in u and isinstance(v, int) and v}
    pids = sorted({g["product_id"] for g in gaps if g["kind"] == "hafo among others"})
    print(f"{len(pids)} product(s) carry a hafo image next to a real one")
    changed = 0
    for pid in pids:
        p = api("GET", f"/products/{pid}").get("data") or {}
        if not p:
            continue
        variants, ch, rep = [], False, []
        for v in p.get("variants", []):
            nv = {k: v.get(k) for k in VKEYS if k in v}
            nv["attribute_value_ids"] = nv.get("attribute_value_ids") or {}
            imgs = nv.get("images") or []
            keep = [i for i in imgs if i not in bad]
            if keep and keep != imgs:          # never empty a gallery here
                nv["images"] = keep; ch = True
                rep.append(f"{v['sku']}: {len(imgs)}→{len(keep)}")
            variants.append(nv)
        if ch and not dry:
            body = {k: p.get(k) for k in KEEP if p.get(k) is not None}
            body["variants"] = variants
            api("PUT", f"/products/{pid}", body)
            changed += 1
        if rep:
            print(f"{pid:>4} {p.get('name','')[:38]:<38} {'; '.join(rep)}", flush=True)
    print(f"products updated: {changed}")


if __name__ == "__main__":
    main()
