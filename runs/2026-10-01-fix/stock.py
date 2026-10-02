#!/usr/bin/env python3
"""Production fix 2026-10-01: stock placeholder 10 on every variant (user).

  pack variant           → on_hand 10
  weight variant         → on_hand 10000 g (10 kg)
  old 1 kg twin `-1KG`   → on_hand = allocated (0 unless an open order holds it),
                           so it can't be bought again but open orders still ship
Writes only through PUT /stock/variants/<id> (reason "correction"); a variant
already at its target is left alone. Reads every product live first.

    stock.py [--write]
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
os.environ.update(SIRUK_API="https://api.siruk.am/api/admin",
                  SIRUK_TOKEN_FILE=os.path.join(ROOT, ".siruk-token-prod"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import api  # noqa: E402

WRITE = "--write" in sys.argv
STATE = os.path.join(HERE, "stock-state.json")
state = json.load(open(STATE)) if os.path.exists(STATE) else {"done": {}, "failed": []}

ids, page = [], 1
while True:
    d = api("GET", f"/products?page={page}")
    ids += [p["id"] for p in d.get("data", [])]
    if page >= d["meta"]["last_page"]:
        break
    page += 1

plan = []
for pid in ids:
    p = api("GET", f"/products/{pid}")["data"]
    for v in p["variants"]:
        for lvl in v["stock_levels"] or [{"warehouse_id": 1, "on_hand": 0, "allocated": 0}]:
            if lvl["warehouse_id"] != 1:
                continue
            if v["sku"].endswith("-1KG") and v["sale_mode"] == "pack":
                target, why = lvl["allocated"], "retired 1 kg pack twin (replaced by the by-weight variant)"
            elif v["sale_mode"] == "weight":
                target, why = 10000, "placeholder stock 10 kg"
            else:
                target, why = 10, "placeholder stock 10"
            if lvl["on_hand"] != target:
                plan.append((pid, p["name"], v["id"], v["sku"], lvl["on_hand"], lvl["allocated"], target, why))

print(f"{len(ids)} products, {len(plan)} variants to change")
json.dump(plan, open(os.path.join(HERE, "stock-plan.json"), "w"), ensure_ascii=False, indent=1)
for pid, name, vid, sku, have, alloc, target, why in plan:
    if not WRITE:
        continue
    if str(vid) in state["done"]:
        continue
    r = api("PUT", f"/stock/variants/{vid}", {"warehouse_id": 1, "on_hand": target, "reason": "correction",
                                             "note": f"2026-10-01 catalogue fix: {why} (was {have})"})
    # error bodies carry "errors" / "error"; stock_verify (a re-run without --write) is the real check
    ok = not (r.get("errors") or r.get("error") or (isinstance(r.get("status"), int) and r["status"] >= 400))
    if ok:
        state["done"][str(vid)] = [have, target]
    else:
        state["failed"].append([vid, sku, json.dumps(r)[:300]])
        print("FAILED", pid, sku, json.dumps(r)[:300])
    json.dump(state, open(STATE, "w"), ensure_ascii=False, indent=1)
print("done", len(state["done"]), "failed", len(state["failed"]))
