#!/usr/bin/env python3
"""Build a local article-number -> product index for trixie.de.

trixie.de's /en/search page has no server-side query: the form's fields carry no
`name`, so `?q=` is ignored and filtering happens in the browser. The upside is
that the page ships the ENTIRE catalogue -- ~3,250 product links of the form

    /en/productworld/<tree>/<english-slug>-<ids>?itemNo=<article>

so one fetch gives every article number, its English name and its page URL. That
replaces driving the browser once per product.

Usage:
    trixie-catalogue.py --build [--out .siruk-cache/trixie-catalogue.json]
    trixie-catalogue.py --lookup 4020 [4026 ...]
"""
import argparse, html, json, os, re, subprocess, sys

SEARCH_URL = "https://www.trixie.de/en/search"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
PAGE = os.path.join(CACHE, "trixie-search-page.html")
INDEX = os.path.join(CACHE, "trixie-catalogue.json")

LINK = re.compile(r'href="(/en/productworld/[^"]*?\?itemNo=(\d+))"')


def fetch_page(path=PAGE, force=False):
    if os.path.exists(path) and not force:
        return path
    subprocess.run(["curl", "-sS", "-A", UA, "-L", "--max-time", "180",
                    SEARCH_URL, "-o", path], check=True)
    return path


def slug_to_name(url):
    """The slug segment carries the English product name; trailing numeric ids
    are the CMS node ids, not part of the name."""
    seg = url.split("?")[0].rstrip("/").rsplit("/", 1)[-1]
    seg = re.sub(r"(-\d{6,})+$", "", seg)
    return seg.replace("-", " ").strip()


def build(path=PAGE, out=INDEX):
    htm = open(path, encoding="utf-8", errors="ignore").read()
    idx = {}
    for href, art in LINK.findall(htm):
        href = html.unescape(href)
        # one page can list several articles (pack sizes); keep them all
        idx.setdefault(art, {"article": art,
                             "url": "https://www.trixie.de" + href,
                             "name": slug_to_name(href)})
    json.dump(idx, open(out, "w"), ensure_ascii=False, indent=1, sort_keys=True)
    return idx


def load(out=INDEX):
    return json.load(open(out)) if os.path.exists(out) else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--force", action="store_true", help="re-download the page")
    ap.add_argument("--out", default=INDEX)
    ap.add_argument("--lookup", nargs="*")
    a = ap.parse_args()

    if a.build:
        fetch_page(force=a.force)
        idx = build(out=a.out)
        print(f"indexed {len(idx)} article numbers -> {a.out}", file=sys.stderr)
        return

    idx = load(a.out)
    if not idx:
        sys.exit("no index yet — run with --build")
    for art in (a.lookup or []):
        art = re.sub(r"[^0-9]", "", art)          # strip the 'Tx' suffix
        hit = idx.get(art) or idx.get(art.lstrip("0"))
        print(json.dumps(hit or {"article": art, "miss": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
