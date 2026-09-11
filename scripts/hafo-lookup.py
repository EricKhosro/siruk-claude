#!/usr/bin/env python3
"""Look up a product on hafo.am by supplier article code, falling back to name.

hafo.am is a Laravel marketplace whose product grid is fed by a JSON endpoint:

    GET /products/filter?search=<q>&page=1&order_by=order-desc
        &min_price=0&max_price=200000&animal=&brand=&weight=&age=&type=&is_new=false

The `search` param matches the SKU held in each product's
`product_additional_information[].sku`, and hafo's SKUs are the same article
codes our supplier invoices use (`41116Tx`, `1101213`, `MG 013147`). So an
article-code lookup is an exact, language-independent match.

Note hafo has no English content — its ENG switch is a Google Translate widget.
Armenian titles come back as-is; `meta_keywords` usually carries hand-written
English terms, which is the best English hafo offers.

Usage:
    hafo-lookup.py --code 41116Tx [--name "..."]      # one lookup, JSON out
    hafo-lookup.py --csv csv/products.csv --limit 10  # batch, JSON array out
"""
import argparse, json, re, sys, time, urllib.parse, urllib.request

API = ("https://hafo.am/products/filter?page=1&order_by=order-desc"
       "&min_price=0&max_price=200000&animal=&brand=&weight=&age=&type=&is_new=false&search=")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
# Supplier suffixes that hafo may or may not carry on its own SKU.
SUFFIXES = ("Tx", "TXN", "MG", "IVS", "PCHL", "AQ", "K", "S", "V", "E", "J", "B", "M")


def norm_sku(s):
    """Normalise a SKU: lowercase, drop spaces/punctuation (incl. NBSP)."""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def sku_matches(hafo_sku, code):
    """True when hafo's SKU is our article code, allowing a brand prefix.

    hafo writes Monge SKUs as 'MG\xa0013147' (non-breaking space) and Trixie's
    as plain '41116Tx', so compare on the normalised form and tolerate a purely
    alphabetic prefix such as 'mg'.
    """
    h, c = norm_sku(hafo_sku), norm_sku(code)
    if not h or not c:
        return False
    if h == c:
        return True
    if h.endswith(c) and h[: -len(c)].isalpha():
        return True
    # our code may carry a supplier suffix hafo omits (013117 vs 013117Tx)
    cores = [c]
    for suf in SUFFIXES:
        if code.lower().endswith(suf.lower()):
            cores.append(norm_sku(code[: -len(suf)]))
    for cs in filter(None, cores):
        if h == cs or (h.endswith(cs) and h[: -len(cs)].isalpha()):
            return True
        # hafo also writes Trixie as 'TX 040201': a 'tx' prefix, a zero pad and a
        # trailing variant digit around the same article number. Verified only
        # for codes that actually carry the 'Tx' supplier suffix — a bare numeric
        # code (no suffix) has no such quirk, and applying this tolerance to it
        # produces false positives: our '15266' (a chicken treat, no suffix)
        # matched hafo's 'TX 152661' (a dog leash) on nothing but a shared
        # 5-digit prefix (found 2026-09-09, Trixie hafo-lookup batch).
        if code.lower().endswith("tx"):
            hd = re.sub(r"^[a-z]+", "", h)          # drop 'tx'/'mg' prefix
            cd = re.sub(r"^[a-z]+", "", cs)
            if hd.isdigit() and cd.isdigit():
                a, b = hd.lstrip("0"), cd.lstrip("0")
                if a == b or (a.startswith(b) and len(a) - len(b) == 1):
                    return True
    return False


def fetch(q, tries=3):
    url = API + urllib.parse.quote(q)
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            if i == tries - 1:
                return {"total": 0, "data": [], "_error": str(e)}
            time.sleep(1.5 * (i + 1))


def skus_of(item):
    return [a.get("sku") for a in (item.get("product_additional_information") or [])
            if a.get("sku")]


def barcodes_of(item):
    """EAN-13s hafo stores per variant. This is the join key to a brand's own
    shop — monge.shop's PrestaShop `reference` field is exactly this number —
    which is how we get an official image without any name matching."""
    out = []
    for a in item.get("product_additional_information") or []:
        b = str(a.get("barcode") or "").strip()
        if b.isdigit() and len(b) >= 8:
            out.append(b)
    return out


# Brands hafo lists in its own sidebar filter, longest first so "Monge Bwild"
# does not lose to "Monge".
HAFO_BRANDS = [
    "SmartBones", "Mr Buffalo", "ORIJEN", "ACANA", "BWILD", "VETSOLUTION",
    "GEMON", "SIMBA", "8 in 1", "TRIXIE", "BEAPHAR", "ECOPROM", "DOGGY DOLLY",
    "FLEXI", "FURminator", "MNYAMS", "Vitakraft", "LECHAT", "Tetra", "Tropical",
    "UNITABS", "ԳЕЛЬМИНТАЛ", "Inspector", "Чистотел", "Club4Paws",
    "Rolf Club", "Котоffeй", "Деревенские Лакомства", "Инсектал", "CitoDerm",
    "Cliny", "Mr.Fresh", "Зубочистики", "Perfect coat", "TAVELA", "Happy Jungle",
    "Alphen Hof", "Mr.Bruno", "Kaskad", "Versele Laga", "Eco-Premium", "GoSi",
    "AQUAEL", "Nature's Miracle", "Боспа", "Наша Марка", "Green Fort", "Tamachi",
    "Iv San Bernard", "Astrapharm", "Пчелодар", "Терра Кот", "INABA", "Терра Пес",
    "MEDMIL", "Polidex", "Блох Нет", "Rolls Rocky", "Pro Shape", "Perfeel+",
    "Aquaforest", "Ферма Кота Федра", "Monge", "ГАВ", "МЯУ", "SMART", "4 ԹԱԹ",
]
HAFO_BRANDS.sort(key=len, reverse=True)


def brand_of(item):
    """hafo fills product_maker only sometimes; otherwise scan title/meta."""
    if item.get("product_maker"):
        return item["product_maker"].strip(), "product_maker"
    hay = " ".join(str(item.get(k) or "") for k in ("title", "meta_title", "slug"))
    for b in HAFO_BRANDS:
        if re.search(re.escape(b), hay, re.I):
            return b, "title/meta match"
    return "", ""


def variant_of(item, code):
    """The product_additional_information[] row for OUR article code.

    ⚠️ This is where the real price lives. hafo's TOP-LEVEL `price` is only the
    cheapest variant of the listing -- for the knotted-rope listing it is 400
    (the 15 cm), while the 60 cm in the same listing is 2750. Pricing a row from
    the top-level field therefore under-prices every larger size, silently and
    sometimes below our own cost. Always price from this row.
    """
    if not code:
        return None
    for a in item.get("product_additional_information") or []:
        for field in ("sku", "article", "code", "additional_code", "unique_code"):
            if sku_matches(a.get(field), code):
                return a
    return None


def slim(item, how, code=None):
    b, bhow = brand_of(item)
    var = variant_of(item, code)
    return {
        "hafo_id": item.get("id"),
        "matched_by": how,
        "brand": b,
        "brand_source": bhow,
        "title_hy": item.get("title"),
        "slug": item.get("slug"),
        "url": f"https://hafo.am/products/{item.get('slug')}" if item.get("slug") else None,
        "skus": skus_of(item),
        "barcodes": barcodes_of(item),
        "articles": [a.get("article") for a in (item.get("product_additional_information") or []) if a.get("article")],
        "image": item.get("image_main_url") or item.get("image"),
        # per-variant price when we could identify our row, else nothing --
        # never fall back to the listing price, which belongs to another size.
        "price_amd": (var or {}).get("price"),
        "wholesale_price_amd": (var or {}).get("wholesale_price"),
        "price_source": "variant" if var else "UNRESOLVED",
        "variant_name_hy": (var or {}).get("name"),
        "variant_sku": (var or {}).get("sku"),
        "variant_in_stock": (var or {}).get("in_stock"),
        "variant_qty": (var or {}).get("qty_in_stock"),
        "variant_kg_price": (var or {}).get("kg_price"),
        # kept for audit only -- do NOT price from these
        "listing_price_amd": item.get("price"),
        "listing_wholesale_amd": item.get("wholesale_price"),
        "variant_count": len(item.get("product_additional_information") or []),
        "meta_title": item.get("meta_title"),
        "meta_description": item.get("meta_description"),
        "meta_keywords": item.get("meta_keywords"),
        "content_html": item.get("content"),
        "confirmed": True,
    }


def lookup(code, name=""):
    code = (code or "").strip()
    tried = []

    # 1. exact article code
    for q in [code] + ([code[:-len(s)] for s in SUFFIXES if code.endswith(s)] or []):
        if not q or q in tried:
            continue
        tried.append(q)
        d = fetch(q)
        for it in d.get("data", []):
            if any(sku_matches(s, code) or sku_matches(s, q) for s in skus_of(it)):
                return slim(it, f"article code (search='{q}')", code)

    # 2. name search — strip our Armenian boilerplate, keep the distinctive words
    if name:
        cleaned = re.sub(r"(Պահածո|Պաուչ|Պաշտետ|Կեր|Հյուրասիրություն|Ձողիկներ|Խաղալիք|"
                         r"Վզնոց|Զգեստիկ|Շլեյկա|Կերաման|Լցանյութ|Ավազ|շն\.?|շների|"
                         r"կատ\.?|կատուների|համար|`|՝)", " ", name)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        for q in [cleaned, " ".join(cleaned.split()[:4]), " ".join(cleaned.split()[:2])]:
            if not q or q in tried:
                continue
            tried.append(q)
            d = fetch(q)
            if d.get("total"):
                r = slim(d["data"][0], f"NAME-GUESS (search='{q}', {d['total']} hits)", code)
                r["confirmed"] = False
                r["candidates"] = [{"title": x.get("title"), "skus": skus_of(x)}
                                   for x in d["data"][:5]]
                return r

    return {"hafo_id": None, "matched_by": None, "tried": tried,
            "brand": "", "title_hy": None, "skus": []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code"); ap.add_argument("--name", default="")
    ap.add_argument("--csv"); ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--out")
    a = ap.parse_args()

    if a.code:
        print(json.dumps(lookup(a.code, a.name), ensure_ascii=False, indent=2))
        return

    import csv as _csv
    rows = list(_csv.DictReader(open(a.csv)))[:a.limit]
    out = []
    for i, r in enumerate(rows, 1):
        res = lookup(r["Article Code"], r["Product Name (as printed)"])
        res["csv"] = {k: r[k] for k in ("Article Code", "Brand",
                                        "Product Name (as printed)", "Species",
                                        "Category", "Buy Price (AMD)", "Qty Received")}
        out.append(res)
        print(f"[{i}/{len(rows)}] {r['Article Code']:<10} "
              f"{'OK  ' + (res['brand'] or '?') if res['hafo_id'] else 'MISS'}"
              f"  {res.get('title_hy') or ''}"[:110], file=sys.stderr)
        time.sleep(0.8)
    js = json.dumps(out, ensure_ascii=False, indent=2)
    if a.out:
        open(a.out, "w").write(js); print(f"\nwrote {a.out}", file=sys.stderr)
    else:
        print(js)


if __name__ == "__main__":
    main()
