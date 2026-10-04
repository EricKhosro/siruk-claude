#!/usr/bin/env python3
"""Read-only: hafo.am's whole catalogue, raw (every listing + every variant row, all fields) -> hafo-all.json."""
import json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
API = ("https://hafo.am/products/filter?page={p}&order_by=order-desc"
       "&min_price=0&max_price=50000000&animal=&brand=&weight=&age=&type=&is_new=false&search=")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"


def page(p):
    for i in range(5):
        try:
            req = urllib.request.Request(API.format(p=p), headers={"User-Agent": UA, "Accept": "application/json",
                                                                   "X-Requested-With": "XMLHttpRequest"})
            return json.load(urllib.request.urlopen(req, timeout=60))
        except Exception as e:
            print(f"page {p}: {e}", file=sys.stderr)
            time.sleep(3 * (i + 1))
    raise SystemExit(f"page {p} failed")


first = page(1)
box = first["products"] if "products" in first else first
last = box.get("last_page", 1)
items = list(box["data"])
for p in range(2, last + 1):
    d = page(p)
    items += (d["products"] if "products" in d else d)["data"]
    if p % 20 == 0:
        print(p, last, len(items), file=sys.stderr, flush=True)
    time.sleep(0.4)
for it in items:
    it.pop("content", None)
json.dump(items, open(os.path.join(HERE, "hafo-all.json"), "w", encoding="utf-8"), ensure_ascii=False)
print(len(items), "listings", sum(len(i.get("product_additional_information") or []) for i in items), "rows; last_page", last)
