#!/usr/bin/env python3
"""Index tiierisch.de — a German pet shop — by TRIXIE article number and EAN.

Found 2026-09-12 while hunting photos for the articles trixie.de, trixie.shop,
trixiecz.cz and zoovet all dropped. It is a Shopify store, so the whole
catalogue comes down in a few dozen requests, and — this is what makes it
usable under CLAUDE.md rule 7 — every variant carries **both keys**:

    "sku": "19904", "barcode": "4011905199047"

so a match is to the article number and its barcode, never to a name. Shopify
also records which images belong to which variant (`image.variant_ids`), so the
green 5 m lead does not inherit the black one's photo: variant-linked images
come first and are the only ones marked `variant`; the product-level shots are
returned separately as `family`, to be used only when the variant has none and
only after looking at them (a family shot can be a different colour).

    scripts/tiierisch-index.py                 # refresh (~2 min)
    scripts/tiierisch-index.py --lookup 19904 202720 [...]
    scripts/tiierisch-index.py --brand TRIXIE  # limit the index to one vendor

Writes .siruk-cache/tiierisch-index.json:
    {article: {"ean", "title", "variant", "url", "images": [...], "family": [...]}}
"""
import json, os, re, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
OUT = os.path.join(CACHE, "tiierisch-index.json")
SHOP = "https://www.tiierisch.de"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def crawl(vendor=None, pages=200):
    out, page = [], 1
    while page <= pages:
        d = get(f"{SHOP}/products.json?limit=250&page={page}").get("products", [])
        if not d:
            break
        out += [p for p in d if not vendor or p.get("vendor", "").upper() == vendor.upper()]
        print(f"  page {page}: {len(d)} products ({len(out)} kept)", file=sys.stderr)
        page += 1
        time.sleep(0.5)
    return out


def build(products):
    idx = {}
    for p in products:
        imgs = p.get("images") or []
        by_variant = {}
        family = []
        for im in imgs:
            src = im.get("src", "").split("?")[0]
            vids = im.get("variant_ids") or []
            if vids:
                for v in vids:
                    by_variant.setdefault(v, []).append(src)
            else:
                family.append(src)
        for v in p.get("variants") or []:
            sku = re.sub(r"\s", "", str(v.get("sku") or ""))
            if not sku.isdigit():
                continue
            rec = idx.setdefault(sku, {"ean": v.get("barcode"), "title": p.get("title", ""),
                                       "variant": v.get("title", ""),
                                       "url": f"{SHOP}/products/{p.get('handle')}",
                                       "images": [], "family": []})
            for u in by_variant.get(v.get("id"), []):
                if u not in rec["images"]:
                    rec["images"].append(u)
            for u in family:
                if u not in rec["family"]:
                    rec["family"].append(u)
    return idx


def main():
    a = sys.argv[1:]
    if "--lookup" in a:
        idx = json.load(open(OUT))
        for art in a[a.index("--lookup") + 1:]:
            r = idx.get(re.sub(r"\D", "", art))
            print(json.dumps({art: r}, indent=1, ensure_ascii=False))
        return
    vendor = a[a.index("--brand") + 1] if "--brand" in a else None
    prods = crawl(vendor)
    idx = build(prods)
    json.dump(idx, open(OUT, "w"), ensure_ascii=False, indent=1)
    withimg = sum(1 for r in idx.values() if r["images"])
    print(f"{len(prods)} products -> {len(idx)} articles ({withimg} with a variant-linked photo) -> {OUT}")


if __name__ == "__main__":
    main()
