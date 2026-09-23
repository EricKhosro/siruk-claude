#!/usr/bin/env python3
"""Point the planners (plan-trixie / plan-monge / plan-small) at today's reality.

They read two cache files:
  .siruk-cache/todo-rows.json      the CSV rows still to import
  .siruk-cache/live-catalogue.json what is already live (slug, name, variant SKUs)

Both are rebuilt here from the fresh catalogue snapshot and the CSV diff, so a
re-plan skips everything that went live in an earlier run.

    scripts/refresh-planner-inputs.py --diff runs/<date>/csv-vs-live.json
"""
import argparse, json, os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diff", required=True)
    a = ap.parse_args()
    diff = json.load(open(a.diff))
    snap = json.load(open(os.path.join(CACHE, "catalogue-snapshot.json")))

    for f in ("todo-rows.json", "live-catalogue.json"):
        p = os.path.join(CACHE, f)
        if os.path.exists(p) and not os.path.exists(p + ".pre-2026-09-15"):
            shutil.copy(p, p + ".pre-2026-09-15")

    todo = [{k: v for k, v in r.items() if not k.startswith("_")} for r in diff["missing"]]
    json.dump(todo, open(os.path.join(CACHE, "todo-rows.json"), "w"),
              ensure_ascii=False, indent=1)

    live = {str(p["id"]): {"name": p["name"], "slug": p["slug"],
                           "category_ids": p.get("category_ids") or [],
                           "variants": [{"id": v["id"], "sku": v["sku"], "name": v["label"],
                                         "price": v["price"], "cost_price": v["cost_price"]}
                                        for v in p["variants"]]}
            for p in snap.values()}
    json.dump(live, open(os.path.join(CACHE, "live-catalogue.json"), "w"),
              ensure_ascii=False, indent=1)
    print(f"todo-rows.json: {len(todo)} rows; live-catalogue.json: {len(live)} products, "
          f"{sum(len(p['variants']) for p in live.values())} variants", file=sys.stderr)


main()
