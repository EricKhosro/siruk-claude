#!/usr/bin/env python3
"""One-off: put the merged products back on their clean slugs.

The first merge run was driven by a plan whose slug step ran twice, so every
surviving product got its own id appended ("trixie-premium-collar-979").
This re-reads the corrected plan and PUTs name + slug only, rebuilding the body
from a fresh GET so no variant is lost.

    scripts/plan-product-merge.py --out /tmp/fixplan
    scripts/_fix-merged-slugs-2026-09-12.py /tmp/fixplan/merge-plan.json [--dry-run]
"""
import json, os, subprocess, sys, pathlib

ROOT = pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = ROOT / ".siruk-cache"
KEEP_V = ("id", "name", "pricing_type", "sku", "price", "price_per_kg",
          "min_allowed_price", "cost_price", "compare_at_price", "weight",
          "is_default", "stock", "vendor_stock", "sort_order", "images",
          "about_this_item", "ingredient_information", "feeding_instructions")


def api(method, path, payload=None):
    args = [str(ROOT / "scripts/api.sh"), method, path]
    if payload is not None:
        p = CACHE / "_slugfix.json"
        json.dump(payload, open(p, "w"), ensure_ascii=False)
        args.append(str(p))
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=300)
    i = r.stdout.find("{")
    if i < 0:
        raise RuntimeError(f"{method} {path}: {r.stderr.strip()[-200:]}")
    return json.loads(r.stdout[i:])


def main():
    plan = json.load(open(sys.argv[1]))["plan"]
    dry = "--dry-run" in sys.argv
    for p in plan:
        cur = api("GET", f"/products/{p['target']}")["data"]
        if cur["slug"] == p["slug"] and cur["name"] == p["name"]:
            continue
        print(f"{p['target']}: {cur['slug']} -> {p['slug']}", file=sys.stderr)
        if dry:
            continue
        body = {"name": p["name"], "slug": p["slug"],
                "category_ids": cur["category_ids"], "brand_id": cur["brand_id"],
                "attribute_family_id": cur["attribute_family_id"],
                "is_best_seller": cur.get("is_best_seller", False),
                "is_on_sale": cur.get("is_on_sale", False),
                "is_discontinued": cur.get("is_discontinued", False),
                "variants": []}
        for v in cur["variants"]:
            out = {k: v.get(k) for k in KEEP_V if k in v}
            out["attribute_value_ids"] = v.get("attribute_value_ids") or {}
            body["variants"].append(out)
        api("PUT", f"/products/{p['target']}", body)
        back = api("GET", f"/products/{p['target']}")["data"]
        assert len(back["variants"]) == len(cur["variants"]), \
            f"{p['target']}: variant count changed"
        if back["slug"] != p["slug"]:
            print(f"  ! server stored {back['slug']}", file=sys.stderr)


if __name__ == "__main__":
    main()
