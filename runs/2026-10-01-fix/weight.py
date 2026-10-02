#!/usr/bin/env python3
"""Production fix 2026-10-01: a by-weight twin for every bag of a loose-sold product.

Source: kg-rows.json (the register's `Kg` column, AllAngineProduct-FINAL-2026-09-28).
The row's demo link `/dp/<id>` is the bag variant id (same ids on production).

Per product, two PUTs (the sku `<bag>-KG` must be freed before it is reused):
  1. the old 1 kg *pack* twin `<bag>-KG` → sku `<bag>-1KG`, name "1 kg" (it can't be
     deleted or switched to weight: stock history; stock.py zeroes it later);
  2. a new `sale_mode: weight` variant per bag: sku `<bag>-KG`, price = Kg column,
     qty_min = qty_step = 1000 g, cost = bag cost ÷ bag kg, initial_stock 10000 g,
     same attributes / texts / images as the bag, placed right after the bag.
Then the bag's ru/hy variant texts are copied onto the new sku.

    weight.py [--write] [--only <product id> …]
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
os.environ.update(SIRUK_API="https://api.siruk.am/api/admin",
                  SIRUK_TOKEN_FILE=os.path.join(ROOT, ".siruk-token-prod"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import (api, product_type, product_body, to_variant_payload,  # noqa: E402
                           normalize_new, check_variants)

STATE = os.path.join(HERE, "weight-state.json")
WRITE = "--write" in sys.argv
ONLY = {int(a) for a in sys.argv[sys.argv.index("--only") + 1:]} if "--only" in sys.argv else None
VTEXT = ("about_this_item", "ingredient_information", "feeding_instructions")


def get(pid, lang=None):
    return api("GET", f"/products/{pid}", lang=lang).get("data")


def put(pid, body):
    r = api("PUT", f"/products/{pid}", body)
    if not (r.get("data") or {}).get("id"):
        raise SystemExit(f"product {pid}: PUT failed: {json.dumps(r)[:600]}")
    return r["data"]


def label(bag):
    base = re.sub(r",?\s*\d+(?:[.,]\d+)?\s*(?:kg|g)\s*$", "", bag["name"] or "", flags=re.I).strip(" ,")
    return f"{base}, by weight" if base else "By weight"


rows = [r for r in json.load(open(os.path.join(HERE, "kg-rows.json"))) if r["insiruk"] == "Yes"]
by_bag = {int(re.search(r"/dp/(\d+)", r["link"]).group(1)): r for r in rows}
state = json.load(open(STATE)) if os.path.exists(STATE) else {"done": {}, "skipped": []}

# product id per bag, from a live read of each bag's product (bag ids are variant ids)
pids = {}
snap = os.environ.get("SNAP")
if not snap:
    sys.exit("set SNAP=<dir of product GET json> (the read-only snapshot) to map bags to products")
for f in os.listdir(snap):
    if not f[0].isdigit():
        continue
    d = json.load(open(os.path.join(snap, f)))
    d = d.get("data", d)
    for v in d["variants"]:
        if v["id"] in by_bag:
            pids.setdefault(d["id"], []).append(v["id"])

for pid in sorted(pids):
    if ONLY and pid not in ONLY:
        continue
    if str(pid) in state["done"]:
        print(f"{pid}: done earlier"); continue
    p = get(pid)
    ptype = product_type(p["attribute_family_id"])
    allowed = {a["id"] for a in ptype.get("attributes") or []}
    vs = {v["sku"]: v for v in p["variants"]}
    bags = [v for v in p["variants"] if v["id"] in by_bag]
    if any(v["sale_mode"] == "weight" for v in p["variants"]):
        print(f"{pid}: already has a weight variant — skipping"); state["skipped"].append([pid, "has weight"]); continue

    # --- step 1: free the -KG skus
    renames = {}
    for b in bags:
        old = vs.get(f"{b['sku']}-KG")
        if old and old["sale_mode"] == "pack" and old["content"] == 1000:
            renames[old["sku"]] = f"{b['sku']}-1KG"
    body1 = product_body(p)
    body1["variants"] = []
    for v in p["variants"]:
        pv = to_variant_payload(v, allowed)
        if v["sku"] in renames:
            pv["sku"], pv["name"] = renames[v["sku"]], "1 kg"
        body1["variants"].append(pv)

    # --- step 2: add the weight twins after their bag
    new = []
    for b in bags:
        r = by_bag[b["id"]]
        kg = b["content"] / 1000 * (b.get("pack_count") or 1)
        price, cost = int(r["kg"]), round(float(r["cost"]) / kg)
        if price <= cost:
            sys.exit(f"{pid} {b['sku']}: kg price {price} not above cost/kg {cost} — stop")
        nv = {"sku": f"{b['sku']}-KG", "name": label(b), "sale_mode": "weight",
              "qty_min": 1000, "qty_step": 1000, "price": price, "cost_price": cost,
              "initial_stock": 10000, "images": list(b["images"]),
              "attribute_values": {k: ids for k, ids in (b["attribute_values"] or {}).items() if int(k) in allowed},
              **{f: b.get(f) or "" for f in VTEXT}}
        new.append((b["sku"], normalize_new(nv, ptype)))
    ordered = []
    for pv in body1["variants"]:
        ordered.append(pv)
        for bag_sku, nv in new:
            if pv["sku"] == bag_sku:
                ordered.append(dict(nv, is_default=False))
    for i, v in enumerate(ordered):
        v["sort_order"] = i
    errs, warns = check_variants(ordered, ptype, {nv["sku"] for _, nv in new})
    for w in warns:
        print(f"  ⚠ {w}")
    if errs:
        print(f"{pid} {p['name']}: REFUSED {errs}"); state["skipped"].append([pid, errs]); continue
    body2 = product_body(p)
    body2["variants"] = ordered

    print(f"{pid} {p['name']}: rename {renames}; add " +
          ", ".join(f"{nv['sku']} '{nv['name']}' {nv['price']}/kg cost {nv['cost_price']}" for _, nv in new))
    if not WRITE:
        continue
    if renames:
        put(pid, body1)
        # re-read so the renamed variants carry their ids into step 2
        p2 = get(pid)
        ids = {v["sku"]: v["id"] for v in p2["variants"]}
        for v in body2["variants"]:
            if v.get("id") is None and v["sku"] in renames.values():
                v["id"] = ids[v["sku"]]
    out = put(pid, body2)
    got = {v["sku"]: v for v in out["variants"]}
    for _, nv in new:
        g = got.get(nv["sku"])
        assert g and g["sale_mode"] == "weight" and g["price"] == nv["price"], f"{pid}: {nv['sku']} not read back"
    # ru / hy texts: copy the bag's own locale texts onto the twin
    tr = {}
    for lang in ("ru", "hy"):
        loc = get(pid, lang)
        lv = {v["sku"]: v for v in loc["variants"]}
        t = {"variants": {nv["sku"]: {f: lv[bag_sku].get(f) or "" for f in VTEXT} for bag_sku, nv in new}}
        f = os.path.join(HERE, "tr", f"w-{pid}-{lang}.json")
        os.makedirs(os.path.dirname(f), exist_ok=True)
        json.dump(t, open(f, "w"), ensure_ascii=False, indent=1)
        r = subprocess.run([os.path.join(ROOT, "scripts/set-translation.py"), str(pid), lang, f],
                           capture_output=True, text=True, cwd=ROOT)
        tr[lang] = (r.stdout.strip() or r.stderr.strip())[-160:]
        if r.returncode:
            print(f"  ! {lang} translation failed: {tr[lang]}")
    state["done"][str(pid)] = {"renamed": renames, "added": [nv["sku"] for _, nv in new], "tr": tr}
    json.dump(state, open(STATE, "w"), ensure_ascii=False, indent=1)
    print(f"  written, translations {tr}")
    subprocess.run([os.path.join(ROOT, "scripts/pace.sh"), "product"])
json.dump(state, open(STATE, "w"), ensure_ascii=False, indent=1)
