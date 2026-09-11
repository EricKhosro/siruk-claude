#!/usr/bin/env python3
"""Move imported toys from the parent Toys category into their leaf category.

Products belong in a leaf ("Dry Food"), not a parent ("Food") -- so a plush dog
toy lives in Dog > Toys > Plush. The first import ran before those leaves
existed, so this re-files what is already in the catalogue.

The PUT body is rebuilt from a fresh GET every time: PUT replaces the whole
variants array, so anything omitted is silently deleted.
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
KEEP = ("name", "slug", "category_ids", "brand_id", "attribute_family_id",
        "is_best_seller", "is_on_sale", "variants")


def api(method, path, payload=None):
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "_recat.json")
        json.dump(payload, open(p, "w"), ensure_ascii=False)
        args.append(p)
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=180)
    out = r.stdout
    try:
        return json.loads(out[out.index("{"):])
    except Exception:
        return {"_raw": out, "_err": r.stderr}


def main():
    plan = {p["slug"]: p for p in json.load(open(os.path.join(CACHE, "toy-plan.json")))["planned"]}
    state = json.load(open(os.path.join(CACHE, "toy-import-state.json")))["done"]

    moved = same = failed = 0
    for slug, rec in state.items():
        want = plan.get(slug, {}).get("category_id")
        if not want:
            continue
        pid = rec["id"]
        cur = api("GET", f"/products/{pid}").get("data")
        if not cur:
            print(f"  GET failed for {pid} {slug}", file=sys.stderr); failed += 1; continue
        if cur.get("category_ids") == [want]:
            same += 1; continue
        body = {k: cur[k] for k in KEEP if k in cur}
        body["category_ids"] = [want]
        res = api("PUT", f"/products/{pid}", body)
        ok = (res.get("data", {}).get("category_ids") == [want])
        nvar = len(res.get("data", {}).get("variants", []))
        if ok and nvar == len(cur["variants"]):
            moved += 1
            print(f"  {pid:<4} {cur['name'][:34]:<36} -> cat {want}  ({nvar} variants kept)",
                  file=sys.stderr)
        else:
            failed += 1
            print(f"  {pid:<4} {cur['name'][:34]:<36} FAILED "
                  f"(cats={res.get('data',{}).get('category_ids')} variants={nvar}"
                  f" was {len(cur['variants'])})", file=sys.stderr)
    print(f"\nmoved={moved} already-correct={same} failed={failed}", file=sys.stderr)


if __name__ == "__main__":
    main()
