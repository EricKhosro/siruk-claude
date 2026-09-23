#!/usr/bin/env python3
"""Build the per-kg twin variant for a product the register sells BOTH ways.

The register's `Kg` column is an explicit per-kilo rate (it runs 2-3% above
`sale price ÷ pack weight` — that premium is deliberate), and a row that has
one is sold loose by the kilo as well as by the pack. The twin follows the
pattern proven by product 1060 (`DEMO Per-KG Test Food, By Weight or Pack`):

    pack variant   pricing_type fixed   price = Վաճառքի գին    product-weight = pack size
    twin variant   pricing_type per_kg  price_per_kg = Kg      product-weight = 1 kg
                                        weight = 1

`weight: 1` is what makes it a kilo: the storefront sells a `per_kg` variant as
units of `rate × weight`, so at 1 the customer buys one kilo at the register's
rate and can order several. At the pack weight it would quote more than the
whole bag.

The twin copies the pack variant's attributes and images verbatim and differs
only on `product-weight`, which is what keeps the API's uniqueness guard happy
and renders the two as a pack-size selector.

    scripts/make-perkg-twin.py                 # write the variant files
    scripts/make-perkg-twin.py --apply         # ...and add-variant.sh each one
"""
import argparse, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
PLAN = os.path.join(ROOT, "state/register/twin-plan.json")
ONE_KG_VALUE_ID = 7          # product-weight -> "1 kg"


def api(path):
    r = subprocess.run([os.path.join(ROOT, "scripts/api.sh"), "GET", path],
                       capture_output=True, text=True, cwd=ROOT, timeout=180)
    i = r.stdout.find("{")
    if i < 0:
        raise SystemExit(f"GET {path} failed: {r.stdout[:200]} {r.stderr[:200]}")
    return json.loads(r.stdout[i:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", help="comma-separated product ids")
    a = ap.parse_args()

    plan = json.load(open(PLAN))
    if a.only:
        keep = {int(x) for x in a.only.split(",")}
        plan = [p for p in plan if p["product_id"] in keep]

    made = []
    for x in plan:
        pid, sku = x["product_id"], x["pack_sku"]
        p = api(f"/products/{pid}")["data"]
        pack = next((v for v in p["variants"] if str(v["sku"]) == str(sku)), None)
        if not pack:
            print(f"! p{pid}: no variant with sku {sku} — skipped", file=sys.stderr)
            continue
        twin_sku = f"{sku}-KG"
        if any(str(v["sku"]) == twin_sku for v in p["variants"]):
            print(f"= p{pid}: {twin_sku} already there — skipped", file=sys.stderr)
            continue
        if pack.get("pricing_type") != "fixed":
            print(f"! p{pid}: pack variant is still {pack.get('pricing_type')} — "
                  f"flip it to fixed first", file=sys.stderr)
            continue

        attrs = dict(pack.get("attribute_value_ids") or {})
        attrs["product-weight"] = ONE_KG_VALUE_ID
        twin = {
            "name": "By weight, 1 kg",
            "pricing_type": "per_kg",
            "sku": twin_sku,
            "price_per_kg": x["kg_rate"],
            "weight": 1,
            "cost_price": int(round(x["cost_per_kg"])),
            "stock": pack.get("stock") or 0,
            "images": list(pack.get("images") or []),
            "attribute_value_ids": attrs,
        }
        out = os.path.join(CACHE, f"twin-{pid}.json")
        json.dump(twin, open(out, "w"), ensure_ascii=False, indent=1)
        made.append((pid, out, twin))
        print(f"p{pid:>5} {twin_sku:<14} {x['kg_rate']:>7.0f}/kg  cost {twin['cost_price']:>6}  "
              f"{len(twin['images'])} img  {p['name'][:38]}", file=sys.stderr)

    print(f"\n{len(made)} twin file(s) written", file=sys.stderr)
    if not a.apply:
        print("re-run with --apply to add them", file=sys.stderr)
        return
    for pid, path, _ in made:
        r = subprocess.run([os.path.join(ROOT, "scripts/add-variant.sh"), str(pid), path],
                           text=True, cwd=ROOT)
        if r.returncode:
            raise SystemExit(f"add-variant failed on p{pid}")


main()
