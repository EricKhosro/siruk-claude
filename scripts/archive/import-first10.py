#!/usr/bin/env python3
"""Create the first batch of hafo-sourced products on the demo admin.

Reads a plan file (see .siruk-cache/first10-plan.json), and for each product:
  search the catalogue first -> upload each variant image -> POST -> verify by GET.
Images are uploaded through scripts/upload-media.sh so they get the filename
sanitising, alpha-flattening and readability check that endpoint needs.
"""
import json, subprocess, sys, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ATTR = json.load(open(os.path.join(ROOT, "reference/attribute-values.json")))


def sh(cmd, **kw):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, **kw)


def api(method, path, payload=None):
    cmd = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        cmd.append("-")
        r = sh(cmd, input=json.dumps(payload))
    else:
        r = sh(cmd)
    body = r.stdout
    i = body.find("{")
    return (json.loads(body[i:]) if i >= 0 else {}), r.stdout.splitlines()[0] if r.stdout else r.stderr


def upload(url):
    if not url:
        return None
    r = sh([os.path.join(ROOT, "scripts/upload-media.sh"), url])
    m = re.findall(r"\b(\d{3,6})\b", r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
    ids = re.findall(r"media(?:\s+id)?\s*[:=]?\s*(\d+)", r.stdout, re.I) or m
    if not ids:
        print(f"      ! image upload failed: {r.stdout.strip()[-160:]} {r.stderr.strip()[-160:]}")
        return None
    return int(ids[-1])


def main():
    plan = json.load(open(sys.argv[1]))
    created = []
    for p in plan:
        print(f"\n=== {p['name']}")
        found, _ = api("GET", f"/products?search={p['name'].split()[0]}")
        dup = [x for x in found.get("data", []) if x.get("slug") == p["slug"]]
        if dup:
            print(f"    already exists as id {dup[0]['id']} — skipping")
            continue

        variants = []
        for i, v in enumerate(p["variants"]):
            mid = upload(v.get("img"))
            print(f"    {v['sku']:<10} {v['label']:<26} media={mid}")
            av = {}
            for code, vid in (v.get("attrs") or {}).items():
                av[code] = vid
            variants.append({
                "name": v["label"], "sku": v["sku"], "pricing_type": "fixed",
                "price": v["price"], "cost_price": v["cost"],
                "compare_at_price": None, "min_allowed_price": 0, "price_per_kg": None,
                "weight": None, "is_default": i == 0, "stock": v["stock"],
                "vendor_stock": False, "sort_order": i,
                "images": [mid] if mid else [],
                "attribute_value_ids": av,
                "about_this_item": p.get("about", ""),
                "ingredient_information": "", "feeding_instructions": "",
            })

        payload = {
            "name": p["name"], "slug": p["slug"], "category_ids": p["category_ids"],
            "brand_id": p["brand_id"], "attribute_family_id": p.get("family"),
            "is_best_seller": False, "is_on_sale": False, "variants": variants,
            "meta": {"title": p["name"][:60], "description": re.sub("<[^>]+>", "", p.get("about",""))[:160]},
        }
        res, status = api("POST", "/products", payload)
        pid = (res.get("data") or {}).get("id")
        if not pid:
            print(f"    FAILED {status}\n    {json.dumps(res, ensure_ascii=False)[:500]}")
            continue
        chk, _ = api("GET", f"/products/{pid}")
        vs = (chk.get("data") or {}).get("variants", [])
        print(f"    created id={pid}  variants={len(vs)}  skus={[v.get('sku') for v in vs]}")
        created.append({"id": pid, "name": p["name"], "slug": p["slug"],
                        "skus": [v.get("sku") for v in vs]})
    print(f"\n{len(created)} products created")
    json.dump(created, open(os.path.join(ROOT, ".siruk-cache/first10-created.json"), "w"),
              ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
