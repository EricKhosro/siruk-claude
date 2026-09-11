#!/usr/bin/env python3
"""Crawl every monge.it product page and index it by the EAN in its image names.

monge.it (the Monge group's own site: Monge, BWILD, Grill, Fresh, Gran Bonta,
Gemon, Simba, Lechat, Special Dog, Leo's) names each pack photo
`…_<pack>_<EAN-13>.jpg`, so the EAN hafo stores per variant (`barcode`) joins our
article code straight to the brand's own picture with no name matching.
Earlier runs fetched only the ~390 pages that a name guess suggested; this walks
all three product sitemaps (~2,080 URLs) so the join can be exact everywhere.

    scripts/monge-it-crawl.py [--limit N] [--refresh]

Writes .siruk-cache/mongeit-all.json  {url: {name, images, ean:[…]}}
   and .siruk-cache/ean2mit.json      {ean: {url, name, images}}
"""
import concurrent.futures, json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
ALL = os.path.join(CACHE, "mongeit-all.json")
IDX = os.path.join(CACHE, "ean2mit.json")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
EAN = re.compile(r"(80094\d{8})")


def get(url, tries=2):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception:
            if i == tries - 1:
                return ""
    return ""


def sitemap_urls():
    out = []
    for n in ("", "2", "3"):
        x = get(f"https://www.monge.it/product-sitemap{n}.xml")
        out += re.findall(r"<loc>([^<]+)</loc>", x)
    return sorted(set(out))


def parse(url):
    h = get(url)
    if not h:
        return url, None
    name = ""
    m = re.search(r'<meta property="og:title" content="([^"]+)"', h) or re.search(r"<title>(.*?)</title>", h, re.S)
    if m:
        name = re.sub(r"\s*[|–-]\s*Monge.*$", "", m.group(1)).strip()
    imgs = []
    for u in re.findall(r'https://www\.monge\.it/wp-content/uploads/[^"\' )]+?\.(?:jpg|jpeg|png|webp)', h):
        u = re.sub(r"-\d+x\d+(\.\w+)$", r"\1", u)       # drop WordPress thumbnail sizes
        if "logo" in u.lower() or "icon" in u.lower() or "placeholder" in u.lower():
            continue
        if u not in imgs:
            imgs.append(u)
    return url, {"url": url, "name": name, "images": imgs,
                 "ean": sorted({e for u in imgs for e in EAN.findall(u)})}


def main():
    refresh = "--refresh" in sys.argv
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    have = json.load(open(ALL)) if os.path.exists(ALL) and not refresh else {}
    urls = [u for u in sitemap_urls() if "/product" in u or "/prodotto" in u or "/producto" in u]
    todo = [u for u in urls if u not in have][:limit]
    print(f"{len(urls)} product urls, {len(todo)} to fetch", file=sys.stderr)
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        for i, (u, d) in enumerate(ex.map(parse, todo), 1):
            if d:
                have[u] = d
            if i % 100 == 0:
                print(f"  {i}/{len(todo)}", file=sys.stderr)
                json.dump(have, open(ALL, "w"), ensure_ascii=False, indent=0)
    json.dump(have, open(ALL, "w"), ensure_ascii=False, indent=0)
    idx = {}
    for d in have.values():
        for e in d["ean"]:
            cur = idx.get(e)
            if not cur or len(d["images"]) > len(cur["images"]):
                idx[e] = d
    json.dump(idx, open(IDX, "w"), ensure_ascii=False, indent=0)
    print(f"{len(have)} pages, {len(idx)} EANs indexed")


if __name__ == "__main__":
    main()
