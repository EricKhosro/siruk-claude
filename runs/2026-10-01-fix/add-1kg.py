#!/usr/bin/env python3
"""Production 2026-10-01 (PM): a 1 kg PACK variant for every product that was sold by weight.
The by-weight variants were deleted by the developers; their per-kg price / cost / bag come
from the snapshot taken before (snapshot/).

  existing `<bag>-1KG` (register products): sku → `<bag>-KG`, label "1 kg", the bag's photos
      and texts, stock set to 10 (/stock/variants, correction)
  none (Royal Canin): new variant `<bag>-KG`, 1 kg, price = per-kg price, cost = per-kg cost,
      the bag's photos / texts / attributes, initial_stock 10
  sorted right after its bag; ru/hy texts copied from the bag (set-translation.py)

    add-1kg.py [--write] [--only <pid> …]
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
os.environ.update(SIRUK_API="https://api.siruk.am/api/admin",
                  SIRUK_TOKEN_FILE=os.path.join(ROOT, ".siruk-token-prod"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import api, product_type, product_body, to_variant_payload, normalize_new, check_variants  # noqa

WRITE = "--write" in sys.argv
ONLY = {int(a) for a in sys.argv[sys.argv.index("--only") + 1:]} if "--only" in sys.argv else None
VTEXT = ("about_this_item", "ingredient_information", "feeding_instructions")
SF = os.path.join(HERE, "add-1kg-state.json")
state = json.load(open(SF)) if os.path.exists(SF) else {"done": {}}

# per product: [(bag sku, per-kg price, per-kg cost)] from the pre-delete snapshot
want = {}
for f in os.listdir(os.path.join(HERE, "snapshot")):
    d = json.load(open(os.path.join(HERE, "snapshot", f)))
    if d["is_discontinued"]:
        continue
    for v in d["variants"]:
        if v["sale_mode"] == "weight":
            want.setdefault(d["id"], []).append((v["sku"][:-3], v["price"], v["cost_price"]))

for pid in sorted(want):
    if (ONLY and pid not in ONLY) or str(pid) in state["done"]:
        continue
    p = api("GET", f"/products/{pid}")["data"]
    assert not any(v["sale_mode"] == "weight" for v in p["variants"]), f"{pid}: still has a weight variant"
    ptype = product_type(p["attribute_family_id"])
    allowed = {a["id"] for a in ptype.get("attributes") or []}
    by = {v["sku"]: v for v in p["variants"]}
    vs = [to_variant_payload(v, allowed) for v in p["variants"]]
    vby = {v["sku"]: v for v in vs}
    news, plan, restock = [], [], []
    for bag_sku, price, cost in want[pid]:
        bag = by[bag_sku]
        common = {"name": "1 kg", "images": list(bag["images"]),
                  "attribute_values": {k: ids for k, ids in (bag["attribute_values"] or {}).items() if int(k) in allowed},
                  **{f: bag.get(f) or "" for f in VTEXT}}
        old = by.get(bag_sku + "-1KG") or (by.get(bag_sku + "-KG") if (by.get(bag_sku + "-KG") or {}).get("sale_mode") == "pack" else None)
        if old:
            vby[old["sku"]].update(common, sku=bag_sku + "-KG")
            if not old["stock_levels"] or old["stock_levels"][0]["on_hand"] != 10:
                restock.append(old["id"])
            plan.append(f"{old['sku']}→{bag_sku}-KG {old['price']} (stock {old['stock_levels'][0]['on_hand'] if old['stock_levels'] else 0}→10)")
            if old["price"] != price:
                plan[-1] += f" !! price {old['price']} vs per-kg {price}"
        else:
            nv = normalize_new(dict(common, sku=bag_sku + "-KG", sale_mode="pack", measure_type="mass", content=1000,
                                    pack_count=1, price=price, cost_price=cost, initial_stock=10), ptype)
            nv["is_default"] = False
            news.append((bag_sku, nv))
            plan.append(f"add {bag_sku}-KG 1 kg {price} cost {cost}")
    # order: each 1 kg right after its bag
    kg = {bag + "-KG" for bag, _, _ in want[pid]}
    ordered = []
    for v in vs:
        if v["sku"] in kg:
            continue
        ordered.append(v)
        ordered += [x for x in vs if x["sku"] == v["sku"] + "-KG"]
        ordered += [nv for b, nv in news if b == v["sku"]]
    assert len(ordered) == len(vs) + len(news), f"{pid}: ordering lost a variant"
    for i, v in enumerate(ordered):
        v["sort_order"] = i
    errs, _ = check_variants(ordered, ptype, {nv["sku"] for _, nv in news})
    if errs:
        sys.exit(f"{pid}: refused {errs}")
    print(f"{pid} {p['name']}: " + "; ".join(plan))
    if not WRITE:
        continue
    body = product_body(p)
    body["variants"] = ordered
    r = api("PUT", f"/products/{pid}", body)
    out = r.get("data") or {}
    if not out.get("id"):
        sys.exit(f"{pid}: PUT failed {json.dumps(r)[:500]}")
    got = {v["sku"]: v for v in out["variants"]}
    for bag_sku, price, _ in want[pid]:
        k = got.get(bag_sku + "-KG")
        assert k and k["sale_mode"] == "pack" and k["content"] == 1000, f"{pid}: {bag_sku}-KG not read back"
    for lang in ("ru", "hy"):
        loc = {v["sku"]: v for v in api("GET", f"/products/{pid}", lang=lang)["data"]["variants"]}
        t = {"variants": {b + "-KG": {f: loc[b].get(f) or "" for f in VTEXT} for b, _, _ in want[pid]}}
        fn = os.path.join(HERE, "tr", f"kg-{pid}-{lang}.json")
        os.makedirs(os.path.dirname(fn), exist_ok=True)
        json.dump(t, open(fn, "w"), ensure_ascii=False, indent=1)
        rr = subprocess.run([os.path.join(ROOT, "scripts/set-translation.py"), str(pid), lang, fn],
                            capture_output=True, text=True, cwd=ROOT)
        if rr.returncode:
            sys.exit(f"{pid} {lang}: {rr.stderr[-300:]}")
    for vid in restock:
        rs = api("PUT", f"/stock/variants/{vid}", {"warehouse_id": 1, "on_hand": 10, "reason": "correction",
                                                  "note": "2026-10-01 PM: 1 kg pack variant back in sale (by-weight removed)"})
        if rs.get("errors") or rs.get("error"):
            sys.exit(f"stock {vid}: {json.dumps(rs)[:300]}")
    state["done"][str(pid)] = plan
    json.dump(state, open(SF, "w"), ensure_ascii=False, indent=1)
    print("  written")
    subprocess.run([os.path.join(ROOT, "scripts/pace.sh"), "product"])
