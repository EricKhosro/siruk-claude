#!/usr/bin/env python3
"""Read-only: re-read, live from hafo.am's search API, the row of every variant matched by article code /
barcode in variants.json -> hafo-recheck.json {row_id: {price, kg_price, wholesale, qty, listing_discount}}.
Searches by the row's own sku (digits), falls back to its barcode."""
import json, os, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
API = ("https://hafo.am/products/filter?page=1&order_by=order-desc&min_price=0&max_price=50000000&animal=&brand="
       "&weight=&age=&type=&is_new=false&search=")

def search(q):
    for i in range(4):
        try:
            req = urllib.request.Request(API + urllib.parse.quote(q), headers={
                "User-Agent": UA, "Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
            d = json.load(urllib.request.urlopen(req, timeout=60))
            return (d.get("products") or d).get("data", [])
        except Exception:
            time.sleep(2 * (i + 1))
    return None

V = json.load(open(os.path.join(HERE, "variants.json"), encoding="utf-8"))
want = {}
for r in V:
    for h in r["hafo"]:
        want[h["row_id"]] = h

def one(h):
    for q in [re.sub(r"[^\dA-Za-z]", " ", h["sku"] or "").split()[-1] if h["sku"] else None, h.get("barcode")]:
        if not q:
            continue
        data = search(q)
        if data is None:
            return h["row_id"], {"error": "search failed"}
        for it in data:
            for a in it.get("product_additional_information") or []:
                if a["id"] == h["row_id"]:
                    time.sleep(0.3)
                    return h["row_id"], {"price": a.get("price"), "kg_price": a.get("kg_price"),
                                         "wholesale": a.get("wholesale_price"), "qty": a.get("qty_in_stock"),
                                         "listing_discount": it.get("discount"), "status": it.get("status"),
                                         "slug": it.get("slug"), "query": q}
    return h["row_id"], {"error": "row not returned by live search"}

out = {}
with ThreadPoolExecutor(4) as ex:
    for rid, res in ex.map(one, want.values()):
        out[rid] = res
json.dump(out, open(os.path.join(HERE, "hafo-recheck.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
changed = [(rid, want[rid]["price"], v.get("price")) for rid, v in out.items() if "price" in v and v["price"] != want[rid]["price"]]
kgch = [(rid, want[rid]["kg_price"], v.get("kg_price")) for rid, v in out.items() if "price" in v and v["kg_price"] != want[rid]["kg_price"]]
print(len(out), "rows rechecked; errors", sum(1 for v in out.values() if "error" in v),
      "; price changed since dump", changed[:20], len(changed), "; kg_price changed", kgch[:10])
