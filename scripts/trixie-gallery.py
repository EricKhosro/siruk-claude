#!/usr/bin/env python3
"""Every official gallery image for a Trixie article, packshot first — from the
cached page (scripts/trixie-parse.py) plus a CDN probe, cached per article in
.siruk-cache/trixie-gallery-urls.json (same file scripts/trixie-image.sh uses).

Ranking = scripts/trixie-image.sh: PHO_PRO_CLIP (packshot) 1, PHO_PAC_CLIP 2,
other article-keyed shots 3, group shots naming the article 4, GRA_ drawings 5.
Only file names carrying THIS article number count. When the page has no
PHO_PRO_CLIP (or there is no page) the CDN is probed for PHO_PRO_CLIP/PHO_PAC_CLIP
_<art>-1..8 and hits are merged.

    scripts/trixie-gallery.py <article> [<article>...]           # print urls
    scripts/trixie-gallery.py --batch articles.json [--pages pages.json]
"""
import concurrent.futures, json, os, re, subprocess, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
GAL = os.path.join(CACHE, "trixie-gallery-urls.json")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def rank(u):
    f = u.rsplit("/", 1)[-1]
    if f.startswith("PHO_PRO_CLIP_"): return 1
    if f.startswith("PHO_PAC_CLIP_"): return 2
    if f.startswith("PHO_PRO_GROUP"): return 4
    if f.startswith("GRA_"): return 5
    return 3


def keyed(f, art):
    return re.search(rf"_({art}|[0-9-]*-{art}|{art}-[0-9-]*|[0-9-]*-{art}-[0-9-]*)-[0-9]+_", f) is not None


def head_ok(u):
    try:
        req = urllib.request.Request(u, method="HEAD", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status == 200
    except Exception:
        return False


def probe(art):
    urls = [f"https://cdn.trixie.de/assets/img/1600mx1200m/{p}_{art}-{i}_%23SALL_%23AWK_%23V1.jpg"
            for p in ("PHO_PRO_CLIP", "PHO_PAC_CLIP") for i in range(1, 9)]
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        ok = list(ex.map(head_ok, urls))
    return [u for u, o in zip(urls, ok) if o]


def resolve(art, page_gallery, cache):
    if art in cache:
        return cache[art]
    urls = [u for u in page_gallery if keyed(u.rsplit("/", 1)[-1], art)]
    if not any(rank(u) == 1 for u in urls):
        urls += [u for u in probe(art) if u not in urls]
        time.sleep(0.5)
    urls = sorted(dict.fromkeys(urls), key=lambda u: (rank(u), u))
    cache[art] = urls
    return urls


def main():
    cache = json.load(open(GAL)) if os.path.exists(GAL) else {}
    if "--batch" in sys.argv:
        arts = json.load(open(sys.argv[sys.argv.index("--batch") + 1]))
        pages = json.load(open(sys.argv[sys.argv.index("--pages") + 1])) if "--pages" in sys.argv else {}
        art2gal = {}
        for u, p in pages.items():
            for a in p.get("variants", {}):
                art2gal.setdefault(a, p.get("gallery", []))
            if p.get("item_no"):
                art2gal.setdefault(p["item_no"], p.get("gallery", []))
        for i, a in enumerate(arts, 1):
            if a in cache:
                continue
            g = resolve(a, art2gal.get(a, []), cache)
            print(f"[{i}/{len(arts)}] {a:<8} {len(g)} images" + ("" if g else "  NONE"), flush=True)
            if i % 10 == 0:
                json.dump(cache, open(GAL, "w"), indent=0)
        json.dump(cache, open(GAL, "w"), indent=0)
    else:
        for a in sys.argv[1:]:
            print("\n".join(resolve(a, [], cache)))
        json.dump(cache, open(GAL, "w"), indent=0)


if __name__ == "__main__":
    main()
