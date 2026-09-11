#!/usr/bin/env python3
"""Index trixie.shop — TRIXIE's own Shopify storefront — by article number.

Why this site (approved 2026-09-11): it is Trixie's own shop and a *different*
catalogue from trixie.de, it keeps Trixie's own file names, and the whole thing
comes down in a dozen requests:

    https://trixie.shop/products.json?limit=250&page=N

Each variant's `sku` is the article number, and each image is still called
`PHO_PRO_CLIP_<article>-<n>_#SALL_#AWK_#V1.jpg`, so an image is attached only
when the file itself names our article (CLAUDE.md rule 7). It also reaches the
files the CDN probe cannot guess, because Trixie names one file for a whole set
of siblings: `PHO_PRO_CLIP_SilverReflect-12222-1`,
`PHO_PRO_CLIP_16248-16258-16268-16278-16288-1`.

    scripts/trixie-shop-index.py                # refresh the catalogue + index
    scripts/trixie-shop-index.py --lookup 12222 [...]

Writes .siruk-cache/trixie-shop-catalogue.json (raw) and
.siruk-cache/trixie-shop-art-images.json ({article: [url…]}, ranked packshot
first). Renders with `created-with-AI` in the file name are dropped: Trixie has
a handful of AI product renders in the shop and we do not ship those.
"""
import json, os, re, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
RAW = os.path.join(CACHE, "trixie-shop-catalogue.json")
OUT = os.path.join(CACHE, "trixie-shop-art-images.json")
NAMES = os.path.join(CACHE, "trixie-shop-names.json")
URL = "https://trixie.shop/products.json?limit=250&page={}"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
AI = "created-with-AI"
RANK = {"PHO_PRO_CLIP": 1, "PHO_PAC_CLIP": 2, "PHO_PRO_DET_CLIP": 3, "PHO_PRO_SET_CLIP": 4, "PHO_PRO": 3,
        "PHO_PRO_USE_CLIP": 5, "PHO_PRO_USE": 5, "PHO_PRO_DOG_CLIP": 6, "PHO_PRO_CAT_CLIP": 6,
        "PHO_PRO_DOG": 6, "PHO_PRO_CAT": 6, "PHO_PRO_GROUP_CLIP": 7, "PHO_PRO_GROUP": 7,
        "GRA_PRO": 8, "GRA_INFO": 8}
PREFIXES = sorted(RANK, key=len, reverse=True)


def prefix(fname):
    for p in PREFIXES:
        if fname.startswith(p + "_"):
            return p
    return ""


def rank(url):
    f = url.rsplit("/", 1)[-1]
    p = prefix(f)
    n = re.search(r"-(\d+)_", f[len(p):]) if p else None
    return (RANK.get(p, 6), int(n.group(1)) if n else 99, f)


def pull():
    out, page = [], 1
    while True:
        req = urllib.request.Request(URL.format(page), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            products = json.load(r).get("products", [])
        if not products:
            break
        out += products
        print(f"  page {page}: {len(products)} products ({len(out)} total)", file=sys.stderr)
        page += 1
        time.sleep(0.8)
    json.dump(out, open(RAW, "w"), ensure_ascii=False)
    return out


def index(products):
    """article -> ordered image urls, and article -> English product name.

    An image counts for an article when the file name carries that article
    number; a product whose whole page resolves to exactly one article keeps its
    pictures even if the files are named differently."""
    arts_img, names = {}, {}
    for p in products:
        arts = set()
        for v in p.get("variants", []):
            sku = (v.get("sku") or "").strip()
            m = re.match(r"^(\d{3,7})(?:-\d+)?$", sku)
            if m:
                arts.add(m.group(1))
            for a in re.findall(r"Art\.-Nr\.:\s*(\d{3,7})", v.get("title") or ""):
                arts.add(a)
        imgs = [i["src"] for i in p.get("images", []) if AI not in i.get("src", "")]
        in_files = set()
        for u in imgs:
            in_files |= set(re.findall(r"[_-](\d{3,7})(?=[-_])", u.rsplit("/", 1)[-1]))
        for a in arts | (in_files & arts if arts else in_files):
            names.setdefault(a, p.get("title"))
            keep = [u for u in imgs
                    if re.search(r"[_-]" + a + r"(?=[-_])", u.rsplit("/", 1)[-1])] or (imgs if len(arts | in_files) == 1 else [])
            if keep:
                arts_img.setdefault(a, [])
                for u in keep:
                    if u not in arts_img[a]:
                        arts_img[a].append(u)
    return {a: sorted(u, key=rank) for a, u in arts_img.items()}, names


def main():
    if "--lookup" in sys.argv:
        have = json.load(open(OUT)) if os.path.exists(OUT) else {}
        names = json.load(open(NAMES)) if os.path.exists(NAMES) else {}
        for a in sys.argv[sys.argv.index("--lookup") + 1:]:
            k = a if a in have else a.lstrip("0")
            print(json.dumps({k: {"name": names.get(k), "images": have.get(k, [])}}, ensure_ascii=False, indent=1))
        return
    products = pull() if "--cached" not in sys.argv else json.load(open(RAW))
    arts, names = index(products)
    json.dump(arts, open(OUT, "w"), ensure_ascii=False, indent=0)
    json.dump(names, open(NAMES, "w"), ensure_ascii=False, indent=0)
    packshot = sum(1 for u in arts.values() if u and prefix(u[0].rsplit("/", 1)[-1]) == "PHO_PRO_CLIP")
    print(f"{len(products)} products -> {len(arts)} article numbers with images "
          f"({packshot} lead with a PHO_PRO_CLIP packshot) -> {OUT}")


if __name__ == "__main__":
    main()
