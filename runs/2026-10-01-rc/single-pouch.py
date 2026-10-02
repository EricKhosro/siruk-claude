#!/usr/bin/env python3
"""Production 2026-10-01 (user): the Royal Canin wet rows with 12 in column E are cases of 12
from the distributor, sold ONE BY ONE — no variant may be "12 × …".

  85 g products 1252–1266: each "12 × 85 g" variant already has a single-pouch twin
    (`<sku>-1` or its own EAN, 85 g, price = column D 750, cost 625). The case variant has
    stock history (delete_locked), so it is retired: moved last, never default, stock → 0;
    the developers delete it. The single pouch takes its place and default flag.
  1267 Mother & Babycat (no single twin): the variant itself becomes 1 × 195 g, label
    "Mousse 195 g"; price 2,300 / cost 2,000 (column C / B are per can).

    single-pouch.py [--write]
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
os.environ.update(SIRUK_API="https://api.siruk.am/api/admin",
                  SIRUK_TOKEN_FILE=os.path.join(ROOT, ".siruk-token-prod"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import api, product_type, product_body, to_variant_payload, check_variants  # noqa

WRITE = "--write" in sys.argv
PIDS = range(1252, 1268)
SF = os.path.join(HERE, "single-pouch-state.json")
state = json.load(open(SF)) if os.path.exists(SF) else {"done": {}}
os.makedirs(os.path.join(HERE, "backup"), exist_ok=True)


def is_case(v):
    return v["sale_mode"] == "pack" and (v.get("pack_count") or 1) > 1


for pid in PIDS:
    if str(pid) in state["done"]:
        continue
    p = api("GET", f"/products/{pid}")["data"]
    assert p["brand"]["name"] if isinstance(p.get("brand"), dict) else True
    ptype = product_type(p["attribute_family_id"])
    allowed = {a["id"] for a in ptype.get("attributes") or []}
    cases = [v for v in p["variants"] if is_case(v)]
    if not cases:
        print(f"{pid} {p['name']}: nothing to do"); continue
    vs = [to_variant_payload(v, allowed) for v in p["variants"]]
    singles = [v for v in vs if not is_case(v)]
    plan, retire = [], []
    if singles:
        # every case must have its 85 g twin with the same options
        def opts(v):
            return {k: sorted(i) for k, i in (v.get("attribute_values") or {}).items()
                    if any(a["id"] == int(k) and a["role"] == "option" for a in ptype["attributes"])}
        for c in cases:
            twin = [s for s in singles if s["content"] == c["content"] and opts(s) == opts(c)]
            assert len(twin) == 1, f"{pid}: case {c['sku']} has {len(twin)} single twins"
            retire.append(c)
            plan.append(f"retire {c['sku']} '{c['name']}' {c['price']} → single {twin[0]['sku']} '{twin[0]['name']}' {twin[0]['price']}")
        ordered = [v for v in vs if not is_case(v)] + [v for v in vs if is_case(v)]
        for v in ordered:
            v["is_default"] = False
        ordered[0]["is_default"] = True
    else:
        assert len(vs) == 1 and pid == 1267, f"{pid}: unexpected shape"
        v = vs[0]
        old = (v["name"], v["pack_count"])
        v.update(pack_count=1, name=v["name"].replace(f"{v['pack_count']} × ", ""))
        plan.append(f"{v['sku']} '{old[0]}' → '{v['name']}', pack_count {old[1]} → 1, price {v['price']} cost {v['cost_price']}")
        ordered = vs
    for i, v in enumerate(ordered):
        v["sort_order"] = i
    errs, warns = check_variants(ordered, ptype)
    if errs:
        sys.exit(f"{pid}: refused {errs}")
    print(f"{pid} {p['name']}: " + "; ".join(plan) + (f"  [warn {warns}]" if warns else ""))
    if not WRITE:
        continue
    json.dump(p, open(os.path.join(HERE, "backup", f"{pid}.json"), "w"), ensure_ascii=False, indent=1)
    body = product_body(p); body["variants"] = ordered
    r = api("PUT", f"/products/{pid}", body)
    out = (r.get("data") or {})
    if not out.get("id"):
        sys.exit(f"{pid} PUT failed: {json.dumps(r)[:500]}")
    got = {v["sku"]: v for v in out["variants"]}
    assert len(got) == len(p["variants"]), f"{pid}: variant count changed"
    assert not got[ordered[0]["sku"]]["pack_count"] > 1 and got[ordered[0]["sku"]]["is_default"], f"{pid}: read-back {got[ordered[0]['sku']]}"
    for c in retire:
        vid = got[c["sku"]]["id"]
        s = api("PUT", f"/stock/variants/{vid}", {"warehouse_id": 1, "on_hand": 0, "reason": "correction",
                                                  "note": "2026-10-01 user: cases of 12 are sold one by one — case variant to be deleted by the developers"})
        if s.get("errors") or s.get("error"):
            sys.exit(f"stock {vid}: {json.dumps(s)[:300]}")
    state["done"][str(pid)] = {"plan": plan, "retired_ids": [got[c["sku"]]["id"] for c in retire]}
    json.dump(state, open(SF, "w"), ensure_ascii=False, indent=1)
    print("  written")
    subprocess.run([os.path.join(ROOT, "scripts/pace.sh"), "product"])
