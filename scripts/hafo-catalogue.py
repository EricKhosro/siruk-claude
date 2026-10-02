#!/usr/bin/env python3
"""Download hafo.am's whole catalogue (every product, every
`product_additional_information[]` row) into one cached JSON file.

Why: hafo's search box matches some products only in one script — the Мяу
bags come up for "Мяу" but not for "ՄՅԱՈՒ", though their row names are
Armenian — so a codeless register row can miss its exact twin however the
query is worded. Matching against the full list (cost + pack + word stems,
`identify-by-name.py --catalogue`) has no such blind spot.

    scripts/hafo-catalogue.py [--out .siruk-cache/hafo-catalogue.json] [--max-age-h 24]

~170 pages of 40, paced; a fresh-enough cache is reused.
"""
import argparse, json, os, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, ".siruk-cache/hafo-catalogue.json")
API = ("https://hafo.am/products/filter?page={p}&order_by=order-desc"
       "&min_price=0&max_price=2000000&animal=&brand=&weight=&age=&type=&is_new=false&search=")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def page(p, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(API.format(p=p), headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            if i == tries - 1:
                raise
            print(f"  page {p}: {e}; retry", file=sys.stderr)
            time.sleep(2 * (i + 1))


def rows(item):
    maker = item.get("product_maker")
    maker = maker.get("title") if isinstance(maker, dict) else maker
    for r in item.get("product_additional_information") or []:
        try:
            wp = float(r.get("wholesale_price") or 0)
        except (TypeError, ValueError):
            wp = 0.0
        yield {"sku": (r.get("sku") or "").replace(" ", ""), "raw_sku": r.get("sku"),
               "name": r.get("name"), "title": item.get("title"), "maker": maker,
               "url": f"https://hafo.am/products/{item.get('slug')}",
               "price": r.get("price"), "wholesale": wp, "barcode": r.get("barcode")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--max-age-h", type=float, default=24)
    ap.add_argument("--sleep", type=float, default=0.7)
    a = ap.parse_args()
    if os.path.exists(a.out) and time.time() - os.path.getmtime(a.out) < a.max_age_h * 3600:
        print(f"cache fresh: {a.out}", file=sys.stderr)
        return
    first = page(1)
    last = first["last_page"]
    out = [r for it in first["data"] for r in rows(it)]
    for p in range(2, last + 1):
        time.sleep(a.sleep)
        out += [r for it in page(p)["data"] for r in rows(it)]
        if p % 20 == 0:
            print(f"  {p}/{last}", file=sys.stderr)
    json.dump({"fetched": time.strftime("%Y-%m-%d %H:%M"), "products": first["total"], "rows": out},
              open(a.out, "w"), ensure_ascii=False)
    print(f"{first['total']} products, {len(out)} rows -> {a.out}", file=sys.stderr)


main()
