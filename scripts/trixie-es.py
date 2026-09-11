#!/usr/bin/env python3
"""trixie.es — the Spanish TRIXIE shop, second source for an article's gallery.

Why a second TLD at all (found 2026-09-11): trixie.de drops a discontinued
article from both the catalogue and the CDN — 149 of our articles have no page
there — and even a live article often keeps a single photo on the .de page while
the country shop hosts the whole set. trixie.es is Trixie's own Spanish shop
(ePages, `/WebRoot/StoreWeb/Shops/Trixie/…`); it keeps its own copies of the
official photos at 1500x1500 and, crucially, prints the **article number** on
every product page, so a hit here is keyed to the article, not to a name.

    article 3503  (Longies, 18 cm)  .de CDN: 1 image      .es: 3 images
    article 31501 (Chew Bites 150g) .de: gone completely   .es: 4 images

Two article-keyed facts on a page:

  * the variations table — `<td data-title="ref">31501</td>`, printed as
    "Ref.31501" in search results. This is Trixie's own article → product
    mapping and it is what `confirmed` below means.
  * the file names — `PHO_PRO_CLIP_<article>-<n>.jpg`, same convention as the
    .de CDN, so a file is self-verifying (the article is printed on the pack).

A page may also carry a **sibling's** photo (article 24183's page shows only
`PHO_PRO_CLIP_24181-1.jpg`): only files whose name carries our article are
returned. Its bullet text can be stale — 31501's bullets say "with lamb" while
the pack in its own photo reads "with parsley & peppermint" — so the text here
is a candidate, never evidence; the photo and the `ref` are the reliable parts.

Usage:
    trixie-es.py --images 31501          # one URL per line, packshot first
    trixie-es.py --article 31501         # JSON: name, refs, specs, images
    trixie-es.py --article 3503 --locale es_ES
    trixie-es.py --images 33445 --no-cache

`--images` prints nothing unless the page's `ref` equals the article asked for.
When only a **trailing-1 trim** matches (our sheets carry the vendor form
`35031` for Trixie article `3503`, the same +1 hafo writes as `TX 040201`), the
candidate is reported on stderr and you confirm it by name before re-running
with that article — an unverified trim must never become an image.
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request

SHOP = "https://www.trixie.es"
SEARCH = (SHOP + "/epages/Trixie.sf/{loc}/?ObjectPath=/Shops/Trixie"
                 "&ViewAction=FacetedSearchProducts&SearchString={q}")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     ".siruk-cache", "trixie-es.json")
DELAY = 0.4          # the shop is small; keep the crawl polite
MAX_CANDIDATES = 4   # search hits to open per article
NAV = {"whatsapp", "see product", "ver producto", "find outlets", "see document"}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", "replace")


def load_cache():
    try:
        with open(CACHE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(c):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    tmp = CACHE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(c, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, CACHE)


def unescape(s):
    for a, b in (("&amp;", "&"), ("&quot;", '"'), ("&#39;", "'"),
                 ("&oacute;", "ó"), ("&nbsp;", " "), ("&ntilde;", "ñ")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def search(article, loc):
    """Search results as [{ref, name, url}] — the listing already prints Ref.<n>."""
    html = fetch(SEARCH.format(loc=loc, q=urllib.parse.quote(article)))
    out = []
    for block in re.split(r'<div class="HotDeal">', html)[1:]:
        url = re.search(r'class="ProductName"[^>]*href="([^"]+)"', block) \
            or re.search(r'href="(https://www\.trixie\.es/[^"?#]+)"', block)
        name = re.search(r'class="ProductName"[^>]*>([^<]+)<', block)
        ref = re.search(r"Ref\.(\d+)", block) or re.search(r'class="qa_(\d+)', block)
        if url:
            out.append({"ref": ref.group(1) if ref else None,
                        "name": unescape(name.group(1)) if name else None,
                        "url": unescape(url.group(1))})
    return out


def rank(url):
    """packshot, pack, other photo, group shot, drawing — same order as the CDN."""
    f = url.rsplit("/", 1)[-1]
    if f.startswith("PHO_PRO_CLIP"):
        return 1
    if f.startswith("PHO_PAC_CLIP"):
        return 2
    if f.startswith("PHO_PRO_GROUP"):
        return 4
    if f.startswith("GRA_"):
        return 5
    return 3


def file_articles(fname):
    """Articles a gallery file name is keyed to, per Trixie's convention
    `<PREFIX>_<article>[-<article>…]-<n>.jpg` — the last number is the index."""
    m = re.search(r"_(\d+(?:-\d+)*)(?:_(?:xs|s|m|h))?\.(?:jpg|jpeg|png)$", fname)
    if not m:
        return []
    nums = m.group(1).split("-")
    return nums[:-1] if len(nums) > 1 else nums


def images_for(html, article):
    """Full-size gallery files whose name carries THIS article (or a group shot
    naming it among several). `_xs/_s/_m/_h` are the shop's thumbnails."""
    urls = set()
    for m in re.finditer(r'(?:href|src|data-src-l)="(/WebRoot/StoreWeb/[^"]+?\.(?:jpg|jpeg|png))"', html):
        u = m.group(1)
        if article.lstrip("0") not in [a.lstrip("0") for a in file_articles(u.rsplit("/", 1)[-1])]:
            continue
        urls.add(SHOP + re.sub(r"_(?:xs|s|m|h)\.(jpg|jpeg|png)$", r".\1", u))
    return sorted(urls, key=lambda u: (rank(u), u))


def page(url, article):
    html = fetch(url)
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    name = unescape(title.group(1)) if title else None
    if name:
        name = re.sub(r"\s*[-–]\s*TRIXIE\s*$", "", name)
    rows = []
    for tr in re.split(r"<tr", html):
        cells = re.findall(r'data-title="([^"]+)"[^>]*>([^<]*)<', tr)
        if cells:
            rows.append({unescape(k): unescape(v) for k, v in cells})
    refs = [r["ref"] for r in rows if r.get("ref")]
    bullets = []
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    det = re.search(r'class="ProductDetails.*?class="VariationsTable"', body, re.S)
    if det:
        for li in re.findall(r"<li[^>]*>(.*?)</li>", det.group(0), re.S):
            t = unescape(re.sub(r"<[^>]+>", " ", li))
            if (t and len(t) < 120 and t not in bullets and t.lower() not in NAV
                    and not (t.isupper() and len(t) > 3)):
                bullets.append(t)
    return {"url": url, "name": name, "refs": refs, "rows": rows,
            "bullets": bullets[:12], "images": images_for(html, article)}


def lookup(article, loc="en_GB", use_cache=True, cache=None):
    """{article, confirmed, url, name, spec, images[], candidates[]}."""
    cache = load_cache() if cache is None else cache
    key = "%s:%s" % (article, loc)
    if use_cache and key in cache:
        return cache[key]
    res = {"article": article, "confirmed": False, "url": None, "name": None,
           "spec": {}, "images": [], "candidates": []}
    try:
        hits = search(article, loc)
    except Exception as e:
        res["error"] = str(e)[:120]
        return res
    res["candidates"] = [{k: h[k] for k in ("ref", "name", "url")} for h in hits][:8]
    ordered = [h for h in hits if h.get("ref") == article] + \
              [h for h in hits if h.get("ref") != article]
    for h in ordered[:MAX_CANDIDATES]:
        time.sleep(DELAY)
        try:
            p = page(h["url"], article)
        except Exception:
            continue
        if article in p["refs"]:
            res.update(confirmed=True, url=p["url"], name=p["name"],
                       images=p["images"], bullets=p["bullets"])
            for row in p["rows"]:
                if row.get("ref") == article:
                    res["spec"] = {k: v for k, v in row.items() if k != "ref"}
            break
    cache[key] = res
    save_cache(cache)
    return res


def trim_candidates(article):
    """Vendor forms of a Trixie article: '35031' is article 3503 with hafo's
    trailing 1, '040201' is 4020 zero-padded and +1. Never auto-accepted."""
    out = []
    a = article.lstrip("0") or article
    if a != article:
        out.append(a)
    if len(a) > 4 and a.endswith("1"):
        t = a[:-1].lstrip("0")
        if t:
            out.append(t)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--article", help="lookup, JSON out")
    ap.add_argument("--images", help="lookup, image URLs only (one per line)")
    ap.add_argument("--locale", default="en_GB", help="en_GB (default) or es_ES")
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args()
    art = a.article or a.images
    if not art:
        ap.error("--article or --images")
    art = art.strip().lstrip("0") or art.strip()
    cache = load_cache()
    res = lookup(art, a.locale, not a.no_cache, cache)
    if not res.get("confirmed"):
        for t in trim_candidates(art):
            alt = lookup(t, a.locale, not a.no_cache, cache)
            if alt.get("confirmed"):
                res["trim_candidate"] = {"article": t, "name": alt["name"],
                                         "url": alt["url"], "images": len(alt["images"])}
                print("trixie.es: no page for %s; trailing-digit trim %s is '%s' (%d images) "
                      "— confirm the name matches before using it: "
                      "scripts/trixie-es.py --images %s"
                      % (art, t, alt["name"], len(alt["images"]), t), file=sys.stderr)
                break
    if a.images:
        for u in res.get("images", []):
            print(u)
    else:
        print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
