#!/usr/bin/env python3
"""Archive the 22 retired Royal Canin "12 × 85 g" case variants (user 2026-10-07).

The admin now archives (soft-removes, restorable) a variant with stock history
when it is left out of the product PUT — the form's "Archive this variant?"
(`will_archive` on the GET). Body rebuilt from a fresh GET via siruk_payload.put_body;
only a target that is stock 0, will_archive and pack_count 12 is dropped.

  SIRUK_API=https://api.siruk.am/api/admin SIRUK_TOKEN_FILE=$PWD/.siruk-token-prod \
    python3 runs/2026-10-07-archive-rc-cases/archive.py [--apply]
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "../../scripts"))
import siruk_payload as sp

TARGETS = {1259: [1859], 1254: [1841], 1252: [1835, 1837], 1257: [1853], 1255: [1843, 1845],
           1256: [1847, 1849, 1851], 1258: [1855, 1857], 1262: [1867, 1869], 1253: [1839],
           1266: [1877], 1264: [1873], 1265: [1875], 1260: [1861, 1863], 1263: [1871], 1261: [1865]}
apply = "--apply" in sys.argv
state_f = os.path.join(HERE, "state.json")
state = json.load(open(state_f)) if os.path.exists(state_f) else {}

ONLY = {int(x) for x in os.environ.get("ONLY", "").split(",") if x}
for pid, drop in TARGETS.items():
    if ONLY and pid not in ONLY:
        continue
    if state.get(str(pid)) == "done":
        continue
    p = sp.api("GET", f"/products/{pid}")["data"]
    json.dump(p, open(os.path.join(HERE, f"before-{pid}.json"), "w"), ensure_ascii=False)
    byid = {v["id"]: v for v in p["variants"]}
    bad = [d for d in drop if d not in byid or byid[d]["available_quantity"] != 0
           or not byid[d].get("will_archive") or byid[d].get("pack_count") != 12
           or (byid[d].get("stock_to_write_off") or 0) != 0]
    if bad:
        print(f"✗ {pid}: target(s) {bad} missing or not a stock-0 archivable case — skipped"); continue
    body = sp.put_body(p)
    drop_skus = {byid[d]["sku"] for d in drop}
    keep = [v for v in body["variants"] if v["sku"] not in drop_skus]
    if not keep or len(keep) != len(body["variants"]) - len(drop):
        print(f"✗ {pid}: unexpected variant count — skipped"); continue
    if not any(v.get("is_default") for v in keep):
        keep[0]["is_default"] = True
    for i, v in enumerate(keep):
        v["sort_order"] = i
    errs, warns = sp.check_variants(keep, sp.product_type(p["attribute_family_id"]))
    if errs:
        print(f"✗ {pid}: {'; '.join(errs)} — skipped"); continue
    body["variants"] = keep
    msg = f"{pid} {p['name']}: archive {[byid[d]['size_label'] or byid[d]['sku'] for d in drop]}, keep {[v['sku'] for v in keep]}"
    if not apply:
        print("dry:", msg); continue
    sp.api("PUT", f"/products/{pid}", body)
    after = sp.api("GET", f"/products/{pid}")["data"]
    left = {v["id"] for v in after["variants"]}
    ok = not (left & set(drop)) and {v["sku"] for v in after["variants"]} == {v["sku"] for v in keep}
    print(("✓ " if ok else "✗ VERIFY FAILED ") + msg)
    state[str(pid)] = "done" if ok else "check"
    json.dump(state, open(state_f, "w"), indent=1)
