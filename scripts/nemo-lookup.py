#!/usr/bin/env python3
"""nemo.am — the third Armenian shop, a price/identity fallback alongside
zoovet.am (reference/pricing.md → "Second and third price sources").

nopCommerce, Armenian-language. Like zoovet, it has **no manufacturer article
code anywhere on the page** — no SKU, no barcode field — so a hit here is a
candidate, exactly like a hafo or zoovet name-search hit: `confirmed` is
always false. Confirm it yourself before using its price or picture, per
CLAUDE.md rule 6/2b:

  * brand + line + flavour + pack size must all match the row, and the pack
    photo should match the brand site's / hafo's photo of the same product;
  * no known code-collision trap has been found yet (unlike zoovet's
    `ME-…` numbers) — if one turns up, document it here and in
    reference/zoovet.md's sibling note.

Usage:
    nemo-lookup.py --search "roal canin bulldog adult"   # candidates
    nemo-lookup.py --search "bulldog" --brand royal-canin  # within one brand
    nemo-lookup.py --brand royal-canin                    # whole brand list
    nemo-lookup.py --url https://www.nemo.am/bulldog-adult-12kg  # full detail

Brand lists are cached in .siruk-cache/nemo-<slug>.json (--no-cache refetches).
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request

SITE = "https://www.nemo.am"
SEARCH = SITE + "/search?q={q}&pagesize={n}"
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
    s = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), s)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&quot;", '"'), ("&#039;", "'"),
                 ("&laquo;", "«"), ("&raquo;", "»"), ("&mdash;", "—")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def amd(s):
    """'42500&#x58F;' or '42 500 ֏' -> 42500 (None when there is no number).
    Decodes entities first — stripping non-digits from a raw '&#x58F;' leaves
    the '58' inside the hex code behind as a false digit run."""
    d = re.sub(r"[^\d]", "", text(s or ""))
    return int(d) if d else None


def full_size(thumb_url):
    """/images/thumbs/0000214_…-12_550.png -> …-12.png (the un-resized original,
    same file the product page's own `xoriginal` attribute points at)."""
    return re.sub(r"_(\d+)(\.(?:jpe?g|png|webp))$", r"\2", thumb_url)


def parse_list(html):
    """Product cards from a search / brand listing."""
    out, seen = [], set()
    for block in re.split(r"<div class=product-item ", html)[1:]:
        url = re.search(r'<a href=(/[^ >]+)', block)
        if not url or url.group(1) in seen:
            continue
        u = SITE + urllib.parse.unquote(url.group(1))
        title = re.search(r'class=product-title><a href=[^>]+>(.*?)</a>', block, re.S)
        price = re.search(r'class="price actual-price">([^<]+)<', block) or \
            re.search(r'class=product-price>.*?>([^<]+)<', block, re.S)
        img = re.search(r'<img alt="[^"]*" src=([^ >]+)', block)
        seen.add(url.group(1))
        out.append({"name": text(title.group(1)) if title else None,
                    "url": u,
                    "price": amd(price.group(1)) if price else None,
                    "image": full_size(img.group(1)) if img else None})
    return out


def product(url):
    """One product page: name, price, stock, image, manufacturer, description.
    No SKU/article field exists on this platform — confirm identity by hand."""
    html = fetch(url)
    name = re.search(r'<div class=product-name><h1[^>]*>([^<]+)<', html)
    price = re.search(r'itemprop=price content=([\d.]+)', html)
    stock = re.search(r'property=product:availability content="([^"]+)"', html)
    manuf = re.search(r'class=manufacturers>.*?<a[^>]*>([^<]+)<', html, re.S)
    img = re.search(r'xoriginal=([^ >]+)', html) or re.search(r'itemprop=image src=([^ >]+)', html)
    desc = re.search(r'class=short-description>([^<]*)<', html)
    return {"url": url, "name": text(name.group(1)) if name else None,
            "price": int(float(price.group(1))) if price else None,
            "in_stock": (stock.group(1) == "in stock") if stock else None,
            "manufacturer": text(manuf.group(1)) if manuf else None,
            "image": full_size(img.group(1)) if img else None,
            "description": text(desc.group(1)) if desc else None,
            "confirmed": False,
            "identity": "nemo has no manufacturer article code anywhere on the "
                        "page — confirm by brand+line+flavour+pack matching the "
                        "row, and the pack photo matching the brand site/hafo"}


def brand_list(slug, use_cache=True):
    path = os.path.join(CACHE_DIR, "nemo-%s.json" % slug)
    if use_cache and os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    out, page = [], 1
    while page <= 20:
        u = SITE + "/" + slug + (("?pagenumber=%d" % page) if page > 1 else "")
        rows = parse_list(fetch(u))
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


def score(name, terms):
    n = (name or "").lower()
    return sum(1 for t in terms if t and t.lower() in n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--search", help="free text (Armenian/transliterated); nemo has no article search")
    ap.add_argument("--brand", help="brand slug as it appears in the URL, e.g. royal-canin — filter or list")
    ap.add_argument("--url", help="a nemo.am product page")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args()

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
            rows = parse_list(fetch(SEARCH.format(q=urllib.parse.quote(a.search), n=max(18, a.limit))))
        out = {"query": a.search, "brand": a.brand, "confirmed": False,
               "note": "candidates only — nemo has no manufacturer article code "
                       "anywhere on the page; confirm identity (brand+line+flavour"
                       "+pack, pack photo matching) before using a price or picture",
               "candidates": rows[:a.limit]}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    if a.brand:
        rows = brand_list(a.brand, not a.no_cache)
        print(json.dumps({"brand": a.brand, "count": len(rows), "products": rows},
                         ensure_ascii=False, indent=2))
        return
    ap.error("one of --search / --brand / --url")


if __name__ == "__main__":
    main()
