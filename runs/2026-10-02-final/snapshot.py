#!/usr/bin/env python3
"""Read-only: every production product with its variants (sku, label, price, cost) → snapshot.json."""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ENV = dict(os.environ, SIRUK_API="https://api.siruk.am/api/admin",
           SIRUK_TOKEN_FILE=os.path.join(ROOT, ".siruk-token-prod"))


def api(path):
    for _ in range(3):
        r = subprocess.run([os.path.join(ROOT, "scripts/api.sh"), "GET", path],
                           capture_output=True, text=True, cwd=ROOT, env=ENV, timeout=180)
        i = r.stdout.find("{")
        if i >= 0:
            try:
                return json.loads(r.stdout[i:])
            except json.JSONDecodeError:
                pass
    return {}


ids, page = [], 1
while True:
    d = api(f"/products?page={page}")
    ids += [p["id"] for p in d.get("data", [])]
    if page >= (d.get("meta") or {}).get("last_page", 1):
        break
    page += 1
out = {}
for n, pid in enumerate(ids):
    p = api(f"/products/{pid}").get("data") or {}
    out[pid] = {"name": p.get("name"), "slug": p.get("slug"), "brand_id": p.get("brand_id"),
                "variants": [{"id": v["id"], "sku": v["sku"], "label": v.get("name"), "price": v.get("price"),
                              "cost": v.get("cost_price"), "images": len(v.get("images") or [])}
                             for v in p.get("variants") or []]}
    if n % 100 == 0:
        print(n, len(ids), file=sys.stderr, flush=True)
json.dump(out, open(os.path.join(HERE, "snapshot.json"), "w"), ensure_ascii=False)
print(len(out), "products", sum(len(p["variants"]) for p in out.values()), "variants")
