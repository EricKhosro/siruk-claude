#!/usr/bin/env python3
"""Resolve a Monge-group product on monge.shop by EAN-13.

monge.shop is Monge's own PrestaShop storefront (`/gb/` is English) and it
covers the wet lines that monge.it's English catalogue omits — Grill, Fresh,
Jelly, Delicate — as well as Gemon and Simba.

Its search returns JSON whose `products[].reference` **is the EAN-13**, and hafo
stores that same EAN per variant as `barcode`. So:

    our article code -> hafo (barcode) -> monge.shop (reference) -> image + EN name

is an exact chain with no name matching anywhere in it.

Usage: monge-shop-lookup.py <ean> [<ean> ...]
       monge-shop-lookup.py --from-hafo <hafo.json> [--out out.json]
"""
import json, sys, time, urllib.parse, urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
URL = "https://monge.shop/gb/module/iqitsearch/searchiqit?ajax=1&s="


def biggest(cover):
    """PrestaShop hands back several sizes; take the widest."""
    if not cover:
        return None
    sizes = (cover.get("bySize") or {}).values()
    best = max(sizes, key=lambda s: int(s.get("width") or 0), default=None)
    return (best or {}).get("url") or cover.get("large", {}).get("url")


def lookup(ean, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(URL + urllib.parse.quote(str(ean)),
                                         headers={"User-Agent": UA,
                                                  "X-Requested-With": "XMLHttpRequest"})
            with urllib.request.urlopen(req, timeout=45) as r:
                d = json.load(r)
            break
        except Exception as e:
            if i == tries - 1:
                return {"ean": ean, "error": str(e)}
            time.sleep(1.5 * (i + 1))
    for p in d.get("products") or []:
        if str(p.get("reference") or "").strip() == str(ean).strip():
            return {"ean": ean, "matched": True, "name_en": p.get("name"),
                    "url": p.get("link"), "image": biggest(p.get("cover")),
                    "description_html": p.get("description_short"),
                    "id_product": p.get("id_product")}
    return {"ean": ean, "matched": False,
            "near": [(p.get("reference"), p.get("name")) for p in (d.get("products") or [])[:3]]}


def main():
    if "--from-hafo" in sys.argv:
        src = json.load(open(sys.argv[sys.argv.index("--from-hafo") + 1]))
        out = []
        for r in src:
            code = r["csv"]["Article Code"]
            eans = r.get("barcodes") or []
            if not r.get("confirmed") or not eans:
                out.append({"article": code, "ean": None, "matched": False,
                            "reason": "no confirmed hafo match" if not r.get("confirmed")
                                      else "hafo has no barcode"})
                print(f"{code:<9} --   no ean", file=sys.stderr)
                continue
            res = lookup(eans[0]); res["article"] = code
            out.append(res)
            print(f"{code:<9} {'OK ' if res.get('matched') else 'no '} {eans[0]}  "
                  f"{(res.get('name_en') or '')[:58]}", file=sys.stderr)
            time.sleep(0.6)
        o = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
        js = json.dumps(out, ensure_ascii=False, indent=1)
        open(o, "w").write(js) if o else print(js)
    else:
        for e in sys.argv[1:]:
            print(json.dumps(lookup(e), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
