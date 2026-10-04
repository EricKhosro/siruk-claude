#!/usr/bin/env python3
"""Read-only: every production product via the public storefront API -> live.json.
Ids: yesterday's admin snapshot (runs/2026-10-02-final/snapshot.json) + a scan past its max id."""
import json, os, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
snap = json.load(open(os.path.join(ROOT, "runs/2026-10-02-final/snapshot.json"), encoding="utf-8"))
ids = sorted(map(int, snap)) + list(range(max(map(int, snap)) + 1, max(map(int, snap)) + 151))

def get(pid):
    for a in range(4):
        try:
            req = urllib.request.Request(f"https://api.siruk.am/api/products/{pid}",
                                         headers={"User-Agent": "curl/8.5.0", "Accept": "application/json"})
            d = json.load(urllib.request.urlopen(req, timeout=60))
            return pid, {"name": d.get("name"), "brand": (d.get("brand") or {}).get("name"),
                         "variants": [{"id": v["id"], "sku": v.get("sku"), "label": v.get("name"),
                                       "price": v.get("price"), "originalPrice": v.get("originalPrice"),
                                       "salePrice": v.get("salePrice"), "compareAtPrice": v.get("compareAtPrice"),
                                       "discount": v.get("discount"), "promotion": v.get("promotion"),
                                       "saleMode": v.get("saleMode"), "size": (v.get("size") or {}).get("label"),
                                       "stock": (v.get("stock") or {}).get("available"),
                                       "status": (v.get("stock") or {}).get("status")}
                                      for v in d.get("variants") or []]}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return pid, None
            time.sleep(2 * (a + 1))
        except Exception:
            time.sleep(2 * (a + 1))
    return pid, "ERROR"

out, missing, errors = {}, [], []
with ThreadPoolExecutor(4) as ex:
    for pid, p in ex.map(get, ids):
        if p == "ERROR": errors.append(pid)
        elif p is None:
            if str(pid) in snap: missing.append(pid)
        else: out[pid] = p
json.dump({"products": out, "snapshot_ids_404": missing, "errors": errors},
          open(os.path.join(HERE, "live.json"), "w", encoding="utf-8"), ensure_ascii=False)
print(len(out), "products", sum(len(p["variants"]) for p in out.values()), "variants;",
      "snapshot ids now 404:", missing, "errors:", errors, "new ids:", [i for i in out if str(i) not in snap])
