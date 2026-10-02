#!/usr/bin/env python3
"""Production fix 2026-10-01: set variant galleries from a plan (rule 7 — one gallery per size).

plan.json: {"<product id>": {"<sku>": [media id, …], …}, …}
Every media id must exist in the media library (checked live, GET /medias/<id>).
One PUT per product through siruk_payload (everything else re-sent unchanged), read back.

    galleries.py <plan.json> [--write]
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
os.environ.update(SIRUK_API="https://api.siruk.am/api/admin",
                  SIRUK_TOKEN_FILE=os.path.join(ROOT, ".siruk-token-prod"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import api, product_type, product_body, to_variant_payload, check_variants  # noqa: E402

plan = json.load(open(sys.argv[1]))
WRITE = "--write" in sys.argv
log = []
for pid, by_sku in plan.items():
    p = api("GET", f"/products/{pid}")["data"]
    ptype = product_type(p["attribute_family_id"])
    allowed = {a["id"] for a in ptype.get("attributes") or []}
    vs = [to_variant_payload(v, allowed) for v in p["variants"]]
    for sku, ids in by_sku.items():
        hit = [v for v in vs if v["sku"] == sku]
        assert hit, f"{pid}: no sku {sku}"
        for m in ids:
            r = api("GET", f"/medias/{m}")
            assert (r.get("data") or {}).get("id") == m, f"media {m} missing"
        print(f"{pid} {sku}: {hit[0]['images']} → {ids}")
        hit[0]["images"] = ids
    errs, _ = check_variants(vs, ptype)
    assert not errs, f"{pid}: {errs}"
    if not WRITE:
        continue
    body = product_body(p)
    body["variants"] = vs
    out = api("PUT", f"/products/{pid}", body)["data"]
    got = {v["sku"]: v["images"] for v in out["variants"]}
    for sku, ids in by_sku.items():
        assert got[sku] == ids, f"{pid} {sku}: read back {got[sku]}"
    log.append(pid)
    print(f"  written {pid}")
print("products written:", len(log))
