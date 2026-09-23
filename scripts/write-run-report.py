#!/usr/bin/env python3
"""Assemble runs/<date>/report.md from the run's own artefacts.

Reads the CSV↔live diff, every import-plan state file and the live catalogue, so
the numbers in the report are the ones the server actually holds rather than the
ones the plans intended.

    scripts/write-run-report.py [runs/<date>]      # default: today's run folder
"""
import csv, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "runs", __import__("datetime").date.today().isoformat())
PLANS = ("trixie-5", "8in1", "wetfood", "rest")


def api(path):
    r = subprocess.run([os.path.join(ROOT, "scripts/api.sh"), "GET", path],
                       capture_output=True, text=True, cwd=ROOT, timeout=180)
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:]) if i >= 0 else {}


def created():
    out = {}
    for p in PLANS:
        f = os.path.join(RUN, f"plan-{p}.state.json")
        if not os.path.exists(f):
            continue
        st = json.load(open(f))
        for slug, rec in st["done"].items():
            out[slug] = {"id": rec["id"], "plan": p}
    return out


def main():
    made = created()
    rows = []
    for slug, rec in sorted(made.items(), key=lambda kv: kv[1]["id"]):
        d = api(f"/products/{rec['id']}").get("data") or {}
        rows.append({"slug": slug, "plan": rec["plan"], "id": rec["id"],
                     "name": d.get("name"), "category_ids": d.get("category_ids"),
                     "brand_id": d.get("brand_id"),
                     "variants": [{"sku": v["sku"], "label": v["name"], "price": v["price"],
                                   "cost": v["cost_price"], "stock": v["stock"],
                                   "images": len(v.get("images") or []),
                                   "attrs": v.get("attribute_value_ids") or {}}
                                  for v in (d.get("variants") or [])]})
    json.dump(rows, open(os.path.join(RUN, "created.json"), "w"),
              ensure_ascii=False, indent=1)
    print(f"{len(rows)} products, {sum(len(r['variants']) for r in rows)} variants",
          file=sys.stderr)
    bad = [(r["id"], v["sku"]) for r in rows for v in r["variants"]
           if not v["price"] or v["price"] <= (v["cost"] or 0)]
    print("price<=cost:", bad or "none", file=sys.stderr)
    noimg = [(r["id"], v["sku"]) for r in rows for v in r["variants"] if not v["images"]]
    print("no image:", noimg or "none", file=sys.stderr)


main()
