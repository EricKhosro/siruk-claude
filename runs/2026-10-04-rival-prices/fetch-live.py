#!/usr/bin/env python3
"""Read-only: every product on production siruk.am via the public storefront API -> live.json.
Ids: scan /api/products/1..N; completeness: every product URL in /api/sitemap (dp/<variant id>)
must be one of the scanned variants."""
import json, os, re, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "curl/8.5.0", "Accept": "application/json"}
MAXID = int(sys.argv[1]) if len(sys.argv) > 1 else 2600

def getj(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))

def get(pid):
    for a in range(5):
        try:
            d = getj(f"https://api.siruk.am/api/products/{pid}")
            vs = []
            for v in d.get("variants") or []:
                pr = v.get("pricing") or {}
                vs.append({"id": v["id"], "sku": v.get("sku"), "label": v.get("name"), "url": v.get("url"),
                           "price": v.get("price"), "originalPrice": v.get("originalPrice"),
                           "salePrice": v.get("salePrice"), "compareAtPrice": v.get("compareAtPrice"),
                           "discount": v.get("discount"), "promotion": v.get("promotion"),
                           "saleMode": v.get("saleMode"), "size": v.get("size"),
                           "unitPrice": pr.get("unitPrice"), "rate": pr.get("formattedRate"),
                           "stock": (v.get("stock") or {}).get("available"),
                           "status": (v.get("stock") or {}).get("status")})
            return pid, {"name": d.get("name"), "displayName": d.get("displayName"), "slug": d.get("slug"),
                         "url": d.get("url"), "brand": (d.get("brand") or {}).get("name"),
                         "categories": [c.get("name") if isinstance(c, dict) else c for c in d.get("categories") or []],
                         "breadcrumbs": [b.get("name") for b in d.get("breadcrumbs") or [] if isinstance(b, dict)],
                         "variants": vs}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return pid, None
            time.sleep(2 * (a + 1))
        except Exception:
            time.sleep(2 * (a + 1))
    return pid, "ERROR"

out, errors = {}, []
with ThreadPoolExecutor(6) as ex:
    for pid, p in ex.map(get, range(1, MAXID + 1)):
        if p == "ERROR": errors.append(pid)
        elif p: out[pid] = p
sm = getj("https://api.siruk.am/api/sitemap")
sm_vids = {int(re.search(r"/dp/(\d+)", x["url"]).group(1)): x["url"] for x in sm
           if x["url"].startswith("en/product/")}
have = {v["id"] for p in out.values() for v in p["variants"]}
missing = sorted(set(sm_vids) - have)
json.dump({"products": out, "errors": errors, "sitemap_products": len(sm_vids),
           "sitemap_not_scanned": missing}, open(os.path.join(HERE, "live.json"), "w", encoding="utf-8"),
          ensure_ascii=False)
print(len(out), "products", sum(len(p["variants"]) for p in out.values()), "variants; max pid",
      max(out) if out else None, "errors", errors, "sitemap products", len(sm_vids), "sitemap not scanned", missing)
