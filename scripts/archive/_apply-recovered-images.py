#!/usr/bin/env python3
"""Put a hand-verified image set on a variant and drop its hafo placeholder.

Input: {article code: [url, …]} in a JSON file. Each url has been looked at
(rule 7). hafo media on that variant are removed, the new images lead.

    scripts/_apply-recovered-images.py <file.json>
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
VKEYS = ("id", "name", "about_this_item", "ingredient_information", "feeding_instructions", "pricing_type", "sku",
         "price", "price_per_kg", "min_allowed_price", "cost_price", "compare_at_price", "weight", "is_default",
         "stock", "vendor_stock", "sort_order", "images", "attribute_value_ids")
KEEP = ("name", "slug", "category_ids", "brand_id", "attribute_family_id", "is_best_seller", "is_on_sale", "is_discontinued")


def sh(a, t=900):
    r = subprocess.run(a, capture_output=True, text=True, cwd=ROOT, timeout=t)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def api(method, path, payload=None):
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "_recov.json"); json.dump(payload, open(p, "w"), ensure_ascii=False); args.append(p)
    rc, out, err = sh(args)
    i = out.find("{")
    return json.loads(out[i:]) if i >= 0 else {"_err": err[-300:]}


def hafo_ids():
    mc = json.load(open(os.path.join(CACHE, "media-cache.json"))) if os.path.exists(os.path.join(CACHE, "media-cache.json")) else {}
    st = json.load(open(os.path.join(CACHE, "enrich-images.state.json"))) if os.path.exists(os.path.join(CACHE, "enrich-images.state.json")) else {"media": {}}
    return {v for u, v in list(mc.items()) + list(st.get("media", {}).items())
            if "d1b3l6j8a0ngef.cloudfront.net" in u and isinstance(v, int) and v}


def find_product(sku):
    plan = json.load(open(os.path.join(CACHE, "image-plan.json")))
    for x in plan.values():
        if x["code"] == sku or str(x["sku"]) == str(sku).replace("Tx", ""):
            return x["product_id"], str(x["sku"])
    return None, None


def main():
    want = json.load(open(sys.argv[1]))
    bad = hafo_ids()
    for code, urls in want.items():
        pid, sku = find_product(code)
        if not pid:
            print(f"{code}: no product found"); continue
        ids = []
        for u in urls:
            rc, out, err = sh([os.path.join(ROOT, "scripts/upload-media.sh"), u])
            last = out.splitlines()[-1] if out else ""
            if re.fullmatch(r"\d+", last):
                ids.append(int(last))
            else:
                print(f"{code}: upload failed for {u}: {(err or out)[-120:]}")
        if not ids:
            continue
        p = api("GET", f"/products/{pid}").get("data") or {}
        variants, changed = [], False
        for v in p.get("variants", []):
            nv = {k: v.get(k) for k in VKEYS if k in v}
            nv["attribute_value_ids"] = nv.get("attribute_value_ids") or {}
            if str(v.get("sku")) == sku:
                keep = [i for i in (nv.get("images") or []) if i not in bad and i not in ids]
                new = ids + keep
                if new != (nv.get("images") or []):
                    nv["images"] = new; changed = True
            variants.append(nv)
        if changed:
            body = {k: p.get(k) for k in KEEP if p.get(k) is not None}
            body["variants"] = variants
            api("PUT", f"/products/{pid}", body)
            back = api("GET", f"/products/{pid}").get("data") or {}
            got = [x.get("images") for x in back.get("variants", []) if str(x.get("sku")) == sku]
            print(f"{code}: product {pid} -> {got}")
        else:
            print(f"{code}: product {pid} unchanged")


if __name__ == "__main__":
    main()
