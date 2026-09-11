#!/usr/bin/env python3
"""zoovet.am — the second Armenian shop: unwatermarked photos and a second price.

Added 2026-09-11 on the user's instruction ("zoovet.am can be our source of
truth just like hafo.am, and it doesn't have a watermark"). It is an OpenCart
shop, Russian-language, 212 brands including 18 of our 19.

What it is good for                      | What it can NOT do
-----------------------------------------|-------------------------------------
photos: the ORIGINAL behind each cached   | identity by article code. Its
thumbnail is the brand's own 1500x1500    | "Артикул: ME-00008447" is an
packshot, with no watermark — unlike      | internal sequential code that
every image hafo serves                   | COLLIDES with brand article
a second Armenian retail price (AMD),     | numbers: searching "3503" (a
stock and a Russian name/description      | Trixie article) returns a Monge
that helps the `ru` translation           | bag whose zoovet code is ME-00003503

So a zoovet hit is a **candidate**, exactly like a hafo name-search hit:
`confirmed` is always false here. Confirm it yourself before anything is
written, per CLAUDE.md rule 6/7 — see reference/zoovet.md:

  * Trixie and most European brands print the article number on the pack
    ("Art.-Nr. 42703", "#31501"). Open the full-size image and read it.
  * Otherwise: brand + line + flavour + pack size must all match the row, and
    the pack artwork must match the brand site's photo of the same product.
  * A size/colour that differs in the Russian name (zoovet "Carlo серый
    37x15x47" vs our "Classic mint green/white 37x15x47") is a different
    product, not a match.

Usage:
    zoovet-lookup.py --search "шампунь сухой 450"          # candidates
    zoovet-lookup.py --search "шампунь" --brand trixie     # within one brand
    zoovet-lookup.py --brand trixie                        # whole brand list
    zoovet-lookup.py --url https://zoovet.am/…/trixie-…    # full detail
    zoovet-lookup.py --brands                              # brand → slug table

Brand lists are cached in .siruk-cache/zoovet-<slug>.json (--no-cache refetches).
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request

SITE = "https://zoovet.am"
SEARCH = SITE + "/search/?search={q}&description=true&limit=100"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         ".siruk-cache")
DELAY = 0.5


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", "replace")


def text(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&quot;", '"'), ("&#039;", "'"),
                 ("&laquo;", "«"), ("&raquo;", "»"), ("&mdash;", "—")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def amd(s):
    """'1 250 ֏' → 1250 (None when there is no number)."""
    d = re.sub(r"[^\d]", "", (s or "").replace(" ", " "))
    return int(d) if d else None


def full_size(url):
    """Cached thumbnail → the original file, which is the unwatermarked
    1500x1500 packshot: /image/cache/catalog/x/y-800x800.png → /image/catalog/x/y.png"""
    u = url.replace("/image/cache/catalog/", "/image/catalog/")
    return re.sub(r"-\d+x\d+(\.(?:jpe?g|png|webp))$", r"\1", u)


def parse_list(html):
    """Product cards from a search / brand / category listing."""
    out, seen = [], set()
    for block in re.split(r'<div class="product-thumb', html)[1:]:
        url = re.search(r'<a href="(https://zoovet\.am/[^"]+)"', block)
        if not url or url.group(1) in seen:
            continue
        # the card repeats its own href for image, brand and title — the title is
        # the longest of those anchors, which also ignores page furniture that
        # trails the last card
        u = url.group(1)
        names = [text(t) for t in re.findall(
            r'<a href="%s"[^>]*>(.*?)</a>' % re.escape(u), block, re.S)]
        names = sorted((n for n in names if n), key=len)
        brand = re.search(r'class="brand-link[^"]*">\s*<a[^>]*>([^<]+)<', block)
        price = re.search(r'price-new">([^<]+)<', block) or \
            re.search(r'class="price">\s*<span[^>]*>([^<]+)<', block)
        old = re.search(r'price-old(?: [^"]*)?">([^<]+)<', block)
        img = re.search(r'<img src="([^"]+)"', block)
        stock = re.search(r'class="stock ([a-z]+)">([^<]*)<', block)
        seen.add(u)
        out.append({"name": names[-1] if names else None,
                    "brand": text(brand.group(1)) if brand else None,
                    "url": u,
                    "price": amd(price.group(1)) if price else None,
                    "old_price": amd(old.group(1)) if old else None,
                    "image": full_size(img.group(1)) if img else None,
                    "in_stock": (stock.group(1) == "green") if stock else None})
    return out


def product(url):
    """One product page: name, zoovet code, price, stock, full-size gallery,
    Russian description and the shop's own attribute rows."""
    html = fetch(url)
    name = re.search(r'class="product-title">([^<]+)<', html)
    sku = re.search(r'class="sku">[^:<]*:\s*([^<]+)<', html)
    price = re.search(r'class="price">\s*([^<]+?)\s*</div>', html)
    stock = re.search(r'class="stock">\s*<div class="([a-z]+)">\s*([^<]+?)\s*<', html)
    gallery = []
    g = re.search(r'class="swiper photo-large".*?</div>\s*</div>\s*</div>', html, re.S)
    if g:
        for m in re.finditer(r'href="(https://zoovet\.am/image/[^"]+)"', g.group(0)):
            u = full_size(m.group(1))
            if u not in gallery:
                gallery.append(u)
    attrs = {}
    for k, v in re.findall(r'attr-item__k">(.*?)</div>\s*<div class="attr-item__v">(.*?)</div>',
                           html, re.S):
        attrs[text(k)] = text(v)
    desc = None
    d = re.search(r'(?:Описание)</span>.*?<div class="acc-body">(.*?)</div>\s*</div>',
                  html, re.S)
    if d:
        desc = text(d.group(1))
    return {"url": url, "name": text(name.group(1)) if name else None,
            "zoovet_code": text(sku.group(1)) if sku else None,
            "price": amd(price.group(1)) if price else None,
            "in_stock": (stock.group(1) == "green") if stock else None,
            "stock_text": text(stock.group(2)) if stock else None,
            "images": gallery, "attributes": attrs, "description": desc,
            "confirmed": False,
            "identity": "zoovet has no brand article code — confirm by the article "
                        "printed on the pack in the photo, or by brand+line+flavour+pack"}


def brand_list(slug, use_cache=True):
    path = os.path.join(CACHE_DIR, "zoovet-%s.json" % slug)
    if use_cache and os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    out, page = [], 1
    while page <= 20:
        html = fetch("%s/%s?limit=100&page=%d" % (SITE, slug, page))
        rows = parse_list(html)
        new = [r for r in rows if r["url"] not in {o["url"] for o in out}]
        out += new
        if not new:
            break
        page += 1
        time.sleep(DELAY)
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(path, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return out


def brands():
    html = fetch(SITE + "/brands")
    seen = {}
    # the A–Z grid: <div class="col-sm-3"><a href="…/trixie">Trixie</a></div>.
    # Matching the whole page would drag in the footer's "О компании" links.
    for u, n in re.findall(
            r'<div class="col-sm-\d+"><a href="(https://zoovet\.am/[a-z0-9\-]+)"[^>]*>([^<]+)</a>',
            html):
        n = text(n)
        if n and n not in seen:
            seen[n] = u
    return seen


def score(name, terms):
    n = (name or "").lower()
    return sum(1 for t in terms if t and t.lower() in n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--search", help="free text (Russian); zoovet has no article search")
    ap.add_argument("--brand", help="brand slug, e.g. trixie — filter or list")
    ap.add_argument("--url", help="a zoovet product page")
    ap.add_argument("--brands", action="store_true", help="brand → slug table")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args()

    if a.brands:
        print(json.dumps(brands(), ensure_ascii=False, indent=2))
        return
    if a.url:
        print(json.dumps(product(a.url), ensure_ascii=False, indent=2))
        return
    if a.search:
        terms = [t for t in re.split(r"\s+", a.search) if t]
        if a.brand:
            rows = brand_list(a.brand, not a.no_cache)
            rows = sorted(rows, key=lambda r: -score(r["name"], terms))
            rows = [r for r in rows if score(r["name"], terms)]
        else:
            rows = parse_list(fetch(SEARCH.format(q=urllib.parse.quote(a.search))))
        out = {"query": a.search, "brand": a.brand, "confirmed": False,
               "note": "candidates only — zoovet cannot be searched by article code "
                       "(its ME-… code collides with brand articles); confirm identity "
                       "before using a price or a picture",
               "candidates": rows[:a.limit]}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    if a.brand:
        rows = brand_list(a.brand, not a.no_cache)
        print(json.dumps({"brand": a.brand, "count": len(rows), "products": rows},
                         ensure_ascii=False, indent=2))
        return
    ap.error("one of --search / --brand / --url / --brands")


if __name__ == "__main__":
    main()
