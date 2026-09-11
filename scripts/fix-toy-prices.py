#!/usr/bin/env python3
"""Correct live toy prices to hafo's real per-SKU price.

The first import priced from hafo's TOP-LEVEL `price`, which is only the
cheapest size in a multi-size listing (see reference/pricing.md). This rewrites the
affected variants with the price from that SKU's own
product_additional_information[] row.

Two guards, because prices are not something to get wrong:
  * the correction is applied only when hafo's per-SKU `wholesale_price` equals
    our invoice `cost_price` -- that equality identifies the right row;
  * a variant is never written to a price at or below its cost.

The PUT body is rebuilt from a fresh GET (PUT replaces the whole variants
array), and any variant a human has since edited by hand is left alone.
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
KEEP = ("name", "slug", "category_ids", "brand_id", "attribute_family_id",
        "is_best_seller", "is_on_sale", "variants")


def api(method, path, payload=None):
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "_fixprice.json")
        json.dump(payload, open(p, "w"), ensure_ascii=False)
        args.append(p)
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=180)
    try:
        return json.loads(r.stdout[r.stdout.index("{"):])
    except Exception:
        return {"_raw": r.stdout, "_err": r.stderr}


def main():
    diff = json.load(open(os.path.join(CACHE, "toy-price-diff.json")))
    todo = [r for r in diff if r["new"] and r["new"] != r["live"]]

    by_product = {}
    for r in todo:
        if r["ws"] != r["cost"]:
            print(f"  SKIP {r['sku']}: wholesale {r['ws']} != our cost {r['cost']}", file=sys.stderr)
            continue
        if r["new"] <= r["cost"]:
            print(f"  SKIP {r['sku']}: new price {r['new']} <= cost {r['cost']}", file=sys.stderr)
            continue
        by_product.setdefault(r["pid"], []).append(r)

    fixed = skipped = failed = 0
    for pid, items in by_product.items():
        cur = api("GET", f"/products/{pid}").get("data")
        if not cur:
            print(f"  GET failed {pid}", file=sys.stderr); failed += 1; continue
        want = {i["sku"]: i for i in items}
        body = {k: cur[k] for k in KEEP if k in cur}
        touched = []
        for v in body["variants"]:
            w = want.get(v["sku"])
            if not w:
                continue
            if v["price"] != w["live"]:        # someone edited it since we read it
                print(f"  SKIP {v['sku']}: live price {v['price']} is not the "
                      f"{w['live']} we recorded — hand-edited, leaving alone", file=sys.stderr)
                skipped += 1
                continue
            v["price"] = w["new"]
            touched.append((v["sku"], w["live"], w["new"]))
        if not touched:
            continue
        res = api("PUT", f"/products/{pid}", body)
        got = {v["sku"]: v["price"] for v in res.get("data", {}).get("variants", [])}
        for sku, old, new in touched:
            if got.get(sku) == new:
                fixed += 1
                print(f"  {pid:<4} {sku:<8} {old:>6} -> {new:>6}  OK", file=sys.stderr)
            else:
                failed += 1
                print(f"  {pid:<4} {sku:<8} FAILED (now {got.get(sku)})", file=sys.stderr)
    print(f"\nfixed={fixed} skipped={skipped} failed={failed}", file=sys.stderr)


if __name__ == "__main__":
    main()
