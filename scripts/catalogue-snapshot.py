#!/usr/bin/env python3
"""Snapshot the whole live catalogue: every product with its variants' SKUs.

    scripts/catalogue-snapshot.py            # -> .siruk-cache/catalogue-snapshot.json
    scripts/catalogue-snapshot.py --ids 535 536 …   # re-read just these (a 404 drops the entry)

Resumable: products already in the snapshot file are not re-fetched unless
--refresh is given. `--ids` is for after a merge or an import: it re-reads the
products that changed and removes the ones that were deleted, instead of
re-reading all 700+ (about an hour at the configured pacing).
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, ".siruk-cache", "catalogue-snapshot.json")


def api(path):
    r = subprocess.run([os.path.join(ROOT, "scripts/api.sh"), "GET", path],
                       capture_output=True, text=True, cwd=ROOT, timeout=180)
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:]) if i >= 0 else {}


def shape(pid, p):
    return {
        "id": pid, "name": p.get("name"), "slug": p.get("slug"),
        "brand": (p.get("brand") or {}).get("name") if isinstance(p.get("brand"), dict) else p.get("brand"),
        "brand_id": p.get("brand_id"),
        "attribute_family_id": p.get("attribute_family_id"),
        "is_discontinued": p.get("is_discontinued"),
        "attribute_family_name": p.get("attribute_family_name"),
        "category_ids": p.get("category_ids") or [c.get("id") for c in (p.get("categories") or []) if isinstance(c, dict)],
        "variants": [{"id": v.get("id"), "sku": v.get("sku"), "label": v.get("label") or v.get("name"),
                      "pricing_type": v.get("pricing_type"),
                      "price": v.get("price"), "price_per_kg": v.get("price_per_kg"),
                      "cost_price": v.get("cost_price"), "weight": v.get("weight"),
                      "stock": v.get("stock"),
                      "attrs": {av.get("attribute_code"): av.get("label")
                                for av in (v.get("attribute_values") or [])},
                      "images": len(v.get("images") or []),
                      "image_ids": [i if isinstance(i, int) else (i or {}).get("id")
                                    for i in (v.get("images") or [])]}
                     for v in (p.get("variants") or [])],
    }


def main():
    refresh = "--refresh" in sys.argv
    snap = {} if refresh else (json.load(open(OUT)) if os.path.exists(OUT) else {})
    if "--ids" in sys.argv:
        ids = [x for x in sys.argv[sys.argv.index("--ids") + 1:] if x.isdigit()]
        for pid in ids:
            d = api(f"/products/{pid}")
            p = d.get("data")
            if not p or not p.get("id"):
                snap.pop(str(pid), None)
                print(f"  {pid}: gone — dropped", file=sys.stderr)
            else:
                snap[str(pid)] = shape(int(pid), p)
                print(f"  {pid}: {p.get('name')} ({len(p.get('variants') or [])} variants)", file=sys.stderr)
        json.dump(snap, open(OUT, "w"), indent=1)
        print(f"wrote {OUT}: {len(snap)} products, "
              f"{sum(len(v['variants']) for v in snap.values())} variants", file=sys.stderr)
        return
    ids, page, last = [], 1, 1
    while page <= last:
        d = api(f"/products?page={page}")
        last = d.get("meta", {}).get("last_page", 1)
        ids += [p["id"] for p in d.get("data", [])]
        print(f"list page {page}/{last} ({len(ids)} ids)", file=sys.stderr)
        page += 1
    todo = [i for i in ids if str(i) not in snap]
    print(f"{len(ids)} products, {len(todo)} to fetch", file=sys.stderr)
    for n, pid in enumerate(todo, 1):
        d = api(f"/products/{pid}")
        p = d.get("data", d)
        snap[str(pid)] = shape(pid, p)
        if n % 20 == 0:
            json.dump(snap, open(OUT, "w"), indent=1)
            print(f"  {n}/{len(todo)}", file=sys.stderr)
    json.dump(snap, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}: {len(snap)} products, "
          f"{sum(len(v['variants']) for v in snap.values())} variants", file=sys.stderr)


main()
