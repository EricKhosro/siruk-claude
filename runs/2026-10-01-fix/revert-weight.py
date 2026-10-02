#!/usr/bin/env python3
"""Production 2026-10-01 (PM decision): no by-weight sale until its UI is tested.
Every by-weight variant is replaced by a 1 kg PACK variant; the by-weight ones can't be
deleted through the API (stock history), so they go to stock 0 and a developer deletes them.

Per product with sale_mode=weight variants (bag = sku without "-KG"):
  PUT 1  weight sku `<bag>-KG` → `<bag>-W` (frees the sku)
  PUT 2  the 1 kg pack variant takes `<bag>-KG`:
           register products: the retired `<bag>-1KG` twin is re-used (label "1 kg")
           Royal Canin: a new one is added (initial_stock 10)
         price = the weight variant's per-kg price, cost = its cost, photos / texts /
         attributes = the bag's; order: bag, its 1 kg, … , weight variants last
  ru/hy  the bag's texts copied onto the 1 kg sku (set-translation.py)
  stock  1 kg → 10 (re-used ones), weight → 0   (/stock/variants, reason correction)

    revert-weight.py [--write] [--only <pid> …]
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
SF = os.path.join(HERE, "revert-state.json")
state = json.load(open(SF)) if os.path.exists(SF) else {"done": {}}

pids = []
for f in os.listdir(os.path.join(HERE, "snapshot")):
    d = json.load(open(os.path.join(HERE, "snapshot", f)))
    if not d["is_discontinued"] and any(v["sale_mode"] == "weight" for v in d["variants"]):
        pids.append(d["id"])


def put(pid, body, what):
    r = api("PUT", f"/products/{pid}", body)
    if not (r.get("data") or {}).get("id"):
        sys.exit(f"{pid} {what} PUT failed: {json.dumps(r)[:500]}")
    return r["data"]


def stock(vid, on_hand, why):
    r = api("PUT", f"/stock/variants/{vid}", {"warehouse_id": 1, "on_hand": on_hand, "reason": "correction",
                                             "note": f"2026-10-01 PM: {why}"})
    if r.get("errors") or r.get("error"):
        sys.exit(f"stock {vid}: {json.dumps(r)[:300]}")


for pid in sorted(pids):
    if (ONLY and pid not in ONLY) or str(pid) in state["done"]:
        continue
    p = api("GET", f"/products/{pid}")["data"]
    ptype = product_type(p["attribute_family_id"])
    allowed = {a["id"] for a in ptype.get("attributes") or []}
    by = {v["sku"]: v for v in p["variants"]}
    pairs = []                                       # (weight, bag, old 1 kg or None)
    for w in [v for v in p["variants"] if v["sale_mode"] == "weight"]:
        assert w["sku"].endswith("-KG"), f"{pid}: unexpected weight sku {w['sku']}"
        bag = by[w["sku"][:-3]]
        pairs.append((w, bag, by.get(bag["sku"] + "-1KG")))

    # PUT 1: weight skus → -W
    vs1 = [to_variant_payload(v, allowed) for v in p["variants"]]
    for v in vs1:
        if v["sale_mode"] == "weight":
            v["sku"] = v["sku"][:-3] + "-W"
    # PUT 2: 1 kg pack variants take -KG, sorted after their bag, weight last
    vs2 = [dict(v) for v in vs1]
    news, plan = [], []
    for w, bag, old in pairs:
        common = {"name": "1 kg", "price": w["price"], "cost_price": w["cost_price"], "images": list(bag["images"]),
                  "attribute_values": {k: ids for k, ids in (bag["attribute_values"] or {}).items() if int(k) in allowed},
                  **{f: bag.get(f) or "" for f in VTEXT}}
        if old:
            v = next(x for x in vs2 if x["sku"] == old["sku"])
            v.update(common, sku=bag["sku"] + "-KG")
            plan.append(f"re-use {old['sku']}→{bag['sku']}-KG {w['price']}/1 kg (was {old['price']})")
        else:
            nv = normalize_new(dict(common, sku=bag["sku"] + "-KG", sale_mode="pack", measure_type="mass",
                                    content=1000, pack_count=1, initial_stock=10), ptype)
            nv["is_default"] = False
            news.append((bag["sku"], nv))
            plan.append(f"add {bag['sku']}-KG 1 kg {w['price']}")
    ordered = []
    rest = [v for v in vs2 if v["sale_mode"] != "weight"]
    one_kg = {v["sku"] for v in rest if v["sku"].endswith("-KG")}
    for v in rest:
        if v["sku"] in one_kg:
            continue
        ordered.append(v)
        for x in rest:
            if x["sku"] == v["sku"] + "-KG":
                ordered.append(x)
        for bag_sku, nv in news:
            if bag_sku == v["sku"]:
                ordered.append(nv)
    ordered += [v for v in vs2 if v["sale_mode"] == "weight"]
    assert len(ordered) == len(vs2) + len(news), f"{pid}: ordering lost a variant"
    for i, v in enumerate(ordered):
        v["sort_order"] = i
    errs, warns = check_variants(ordered, ptype, {nv["sku"] for _, nv in news})
    if errs:
        sys.exit(f"{pid}: refused {errs}")
    print(f"{pid} {p['name']}: " + "; ".join(plan))
    if not WRITE:
        continue
    b1 = product_body(p); b1["variants"] = vs1
    put(pid, b1, "rename weight")
    b2 = product_body(p); b2["variants"] = ordered
    out = put(pid, b2, "1 kg")
    got = {v["sku"]: v for v in out["variants"]}
    for w, bag, old in pairs:
        k = got[bag["sku"] + "-KG"]
        assert k["sale_mode"] == "pack" and k["content"] == 1000 and k["price"] == w["price"], f"{pid}: 1 kg read back {k}"
    # translations
    for lang in ("ru", "hy"):
        loc = {v["sku"]: v for v in api("GET", f"/products/{pid}", lang=lang)["data"]["variants"]}
        t = {"variants": {bag["sku"] + "-KG": {f: loc[bag["sku"]].get(f) or "" for f in VTEXT} for _, bag, _ in pairs}}
        fn = os.path.join(HERE, "tr", f"rv-{pid}-{lang}.json")
        json.dump(t, open(fn, "w"), ensure_ascii=False, indent=1)
        r = subprocess.run([os.path.join(ROOT, "scripts/set-translation.py"), str(pid), lang, fn],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode:
            sys.exit(f"{pid} {lang}: {r.stderr[-300:]}")
    # stock
    for w, bag, old in pairs:
        if old:
            stock(old["id"], 10, "1 kg pack variant back in sale (by-weight sale paused)")
        stock(w["id"], 0, "by-weight sale paused — variant to be deleted by the developers")
    state["done"][str(pid)] = {"weight_ids": [w["id"] for w, _, _ in pairs], "plan": plan}
    json.dump(state, open(SF, "w"), ensure_ascii=False, indent=1)
    print("  written")
    subprocess.run([os.path.join(ROOT, "scripts/pace.sh"), "product"])
