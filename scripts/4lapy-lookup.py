#!/usr/bin/env python3
"""4lapy.ru (Четыре Лапы) — a Russian pet chain, EAN-keyed fallback for
images and texts (reference/image-sources.md, added 2026-09-23 on the user's
list of fallback sites).

Every product page lists its pack sizes as *offers*, and each offer carries
its own **manufacturer barcode** (`Штрихкод`), gallery, description, composition
(`состав`) and feeding guide. So an offer whose barcode equals our row's EAN is
**confirmed** — the same bar as the other EAN-keyed shops in rule 7. Anything
matched only by name is a candidate (`confirmed: false`), exactly like a
zoovet/nemo hit.

robots.txt disallows only `/search/`, so the site's search is NOT used:
products are found in the product sitemap (≈20,000 urls, cached), whose slugs
carry the brand and the Russian name transliterated
(`monge-adult-korm-dlya-koshek-…-1-5-kg-1142-1027896`).

    4lapy-lookup.py --search "monge adult koshek kuritsej"        # sitemap slug match
    4lapy-lookup.py --search "monge adult koshek" --ean 8009470004800   # fetch candidates, keep the barcode hit
    4lapy-lookup.py --url https://4lapy.ru/product/<slug>/        # every offer on the page
    4lapy-lookup.py --reindex                                      # refresh the sitemap cache
    4lapy-lookup.py --scan monge                                   # read every page whose slug has the word,
                                                                   # cache barcode -> offer (.siruk-cache/4lapy-barcodes.json)
    4lapy-lookup.py --ean 8009470004800                            # answer from that cache

Prices on this site are RUB retail — never a sale price for us (rule 2).
Texts are Russian: use them for the `ru` translation and as evidence, not as
the English copy.
"""
import argparse, json, os, re, sys, time, urllib.request

SITE = "https://4lapy.ru"
SITEMAPS = [SITE + "/sitemaps/sitemap-product.xml", SITE + "/sitemaps/sitemap-product.part1.xml"]
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, ".siruk-cache", "4lapy-index.json")
BARCODES = os.path.join(ROOT, ".siruk-cache", "4lapy-barcodes.json")
DELAY = 1.0


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xml"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def index(refresh=False):
    if not refresh and os.path.exists(INDEX):
        return json.load(open(INDEX))
    urls = []
    for sm in SITEMAPS:
        urls += re.findall(r"<loc>(https://4lapy\.ru/product/[^<]+)</loc>", fetch(sm))
        time.sleep(DELAY)
    urls = sorted(set(urls))
    os.makedirs(os.path.dirname(INDEX), exist_ok=True)
    json.dump(urls, open(INDEX, "w"), indent=0)
    print(f"indexed {len(urls)} product urls -> {INDEX}", file=sys.stderr)
    return urls


def slug_words(url):
    return set(url.rstrip("/").rsplit("/", 1)[-1].lower().split("-"))


def search(terms, limit):
    terms = [t.lower() for t in terms if t]
    scored = []
    for u in index():
        w = slug_words(u)
        s = sum(1 for t in terms if t in w or any(x.startswith(t) for x in w))
        if s:
            scored.append((s, u))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [{"url": u, "score": s} for s, u in scored[:limit]]


def clean(html):
    if not html:
        return None
    t = re.sub(r"<br\s*/?>|</p>|</h\d>", "\n", html)
    t = re.sub(r"<[^>]+>", "", t).replace("&nbsp;", " ")
    return re.sub(r"\n\s*\n+", "\n", t).strip() or None


def page(url):
    """Every offer (pack size) on a product page, with its own barcode."""
    html = fetch(url)
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return {"url": url, "error": "no __NEXT_DATA__ (page layout changed?)"}
    pp = json.loads(m.group(1))["props"]["pageProps"]
    prod = next((v for k, v in (pp.get("fallback") or {}).items()
                 if isinstance(v, dict) and v.get("offers")), None) or {}
    offers = prod.get("offers") or [pp.get("activeOffer") or {}]
    out = []
    for o in offers:
        attrs = {a.get("name"): (a.get("firstValue") or {}).get("value")
                 for a in (o.get("offerAttributes") or [])}
        barcodes = [v.get("value") for a in (o.get("offerAttributes") or [])
                    if a.get("code") == "bar_codes" for v in (a.get("values") or [])]
        out.append({
            "offer_id": o.get("offerId"),
            "name": (o.get("name") or "").strip(),
            "url": SITE + (o.get("url") or ""),
            "barcodes": [b for b in barcodes if b],
            "weight_kg": attrs.get("Вес"),
            "images": [i.get("media") for i in ((o.get("gallery") or {}).get("images") or []) if i.get("media")],
            "description_ru": clean(attrs.get("Детальное описание")),
            "composition_ru": clean(attrs.get("состав")),
            "feeding_ru": clean(attrs.get("рекомендации по питанию")),
        })
    return {"url": url, "product": (prod.get("name") or "").strip(),
            "brand": (prod.get("brand") or {}).get("name"), "offers": out}


def scan(word):
    """Read every product page whose slug carries `word` (a brand) once and
    cache barcode -> offer, so later --ean lookups need no network."""
    cache = json.load(open(BARCODES)) if os.path.exists(BARCODES) else {"pages": [], "barcodes": {}}
    done = set(cache["pages"])
    urls = [u for u in index() if word.lower() in u.rsplit("/", 2)[-2].split("-") and u not in done]
    print(f"{len(urls)} pages to read for '{word}'", file=sys.stderr)
    for n, u in enumerate(urls, 1):
        try:
            p = page(u)
        except Exception as e:
            print(f"  ! {u}: {e}", file=sys.stderr)
            continue
        for o in p.get("offers") or []:
            for b in o["barcodes"]:
                cache["barcodes"][b] = {**o, "product": p["product"], "brand": p["brand"]}
        cache["pages"].append(u)
        if n % 25 == 0:
            json.dump(cache, open(BARCODES, "w"), ensure_ascii=False)
            print(f"  {n}/{len(urls)}", file=sys.stderr)
        time.sleep(DELAY)
    json.dump(cache, open(BARCODES, "w"), ensure_ascii=False)
    print(f"{len(cache['barcodes'])} barcodes cached -> {BARCODES}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--search", help="latin / transliterated words matched against the url slug")
    ap.add_argument("--ean", help="keep only offers carrying this barcode (fetches the candidate pages)")
    ap.add_argument("--url", help="a 4lapy.ru product page")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--reindex", action="store_true")
    ap.add_argument("--scan", help="brand word: read every page whose slug has it, cache the barcodes")
    a = ap.parse_args()

    if a.reindex:
        index(refresh=True)
        if not (a.search or a.url):
            return
    if a.scan:
        scan(a.scan)
        return
    if a.url:
        print(json.dumps(page(a.url), ensure_ascii=False, indent=2))
        return
    if a.ean and not a.search:
        hit = (json.load(open(BARCODES))["barcodes"] if os.path.exists(BARCODES) else {}).get(a.ean)
        print(json.dumps({"ean": a.ean, "confirmed": bool(hit),
                          "note": "from the --scan cache" if hit else "not in the --scan cache (scan the brand first, or use --search)",
                          "hits": [hit] if hit else []}, ensure_ascii=False, indent=2))
        return
    if a.search:
        cands = search(re.split(r"\s+", a.search), a.limit)
        if not a.ean:
            print(json.dumps({"query": a.search, "confirmed": False,
                              "note": "slug matches only — open a page (--url) or pass --ean to confirm by barcode",
                              "candidates": cands}, ensure_ascii=False, indent=2))
            return
        hits = []
        for c in cands:
            p = page(c["url"])
            for o in p.get("offers") or []:
                if a.ean in o["barcodes"]:
                    hits.append({**o, "product": p["product"], "brand": p["brand"]})
            time.sleep(DELAY)
            if hits:
                break
        print(json.dumps({"query": a.search, "ean": a.ean, "confirmed": bool(hits),
                          "note": ("barcode printed on the offer equals the EAN — identity confirmed"
                                   if hits else f"no offer on the top {len(cands)} slug matches carries this barcode"),
                          "hits": hits}, ensure_ascii=False, indent=2))
        return
    ap.error("one of --search / --ean / --url / --scan / --reindex")


main()
