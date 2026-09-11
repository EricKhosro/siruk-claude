#!/usr/bin/env python3
"""Fetch and parse trixie.de product pages.

Product pages are fully server-rendered (~100 KB), so curl is enough -- no
browser. Each page yields the English name, the bullet "Product information"
list, the prose description, and EVERY variant on it as
{item number -> contents}. That last part matters: the catalogue listing links
carry only one itemNo per product, so sibling pack sizes (e.g. 4020 next to
4026) are only discoverable here.

Usage:
    trixie-product.py --urls .siruk-cache/trixie-food-urls.json \
                      --out  .siruk-cache/trixie-food-pages.json
    trixie-product.py --url  "https://www.trixie.de/en/productworld/..."
"""
import argparse, hashlib, html, json, os, re, subprocess, sys, time

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_CACHE = os.path.join(ROOT, ".siruk-cache", "trixie-html")


def cached_get(url, refetch=False, **kw):
    """Fetch through an on-disk HTML cache, so tuning the parser never costs
    another 123 requests (and never re-trips trixie.de's throttle)."""
    os.makedirs(HTML_CACHE, exist_ok=True)
    path = os.path.join(HTML_CACHE, hashlib.sha1(url.encode()).hexdigest() + ".html")
    if os.path.exists(path) and not refetch:
        return open(path, encoding="utf-8", errors="ignore").read(), True
    htm = get(url, **kw)
    if htm:
        open(path, "w", encoding="utf-8").write(htm)
    return htm, False


def get(url, tries=3, timeout=25):
    """Short timeout + backoff. trixie.de briefly throttles after a burst (a
    17 MB catalogue fetch, or trixie-image.sh's 12 parallel CDN probes), and a
    long --max-time turns one throttled URL into minutes of dead wall-clock."""
    for i in range(tries):
        r = subprocess.run(["curl", "-sS", "-A", UA, "-L", "--max-time", str(timeout), url],
                           capture_output=True, text=True)
        if r.returncode == 0 and len(r.stdout) > 2000:
            return r.stdout
        time.sleep(3 * (i + 1))
    return ""


def text_of(htm):
    htm = re.sub(r"<(script|style).*?</\1>", " ", htm, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", htm)))


def parse(url, htm):
    txt = text_of(htm)
    title = ""
    m = re.search(r"<title[^>]*>(.*?)</title>", htm, re.S | re.I)
    if m:
        title = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip()
    name = ""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", htm, re.S | re.I)
    if m:
        name = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))).strip()
    # Some pages' <h1> is a stray fragment (one rendered as just "500"). The page
    # always prints the product name immediately before "Item no.:", doubled
    # (breadcrumb tail + heading), so recover it from there.
    if not name or name.isdigit() or len(name) < 4:
        m = re.search(r"([^|]{4,70}?)\s*Item no\.:", txt)
        if m:
            cand = m.group(1).strip()
            half = len(cand) // 2
            if cand[:half].strip() and cand[:half].strip() == cand[half:].strip():
                cand = cand[:half].strip()      # de-duplicate "X X"
            name = cand

    # Variant article numbers, in decreasing order of richness. A MULTI-variant
    # page prints "unique product number 4026 Contents 5 l" per variant; a
    # SINGLE-variant page prints only a bare "Item no.: 42681" with no Contents
    # and carries no itemNo= anywhere in its HTML -- so the bare form and the
    # request URL are both needed or those pages yield nothing.
    variants = {}
    for art, cont in re.findall(
            r"unique product number\s+(\d+)\s+Contents?\s+([0-9.,]+\s*[a-zA-Z]+)", txt):
        variants[art] = cont.strip()
    for art, cont in re.findall(r"Item no\.:\s*(\d+),\s*Contents?:\s*([0-9.,]+\s*\w+)", txt):
        variants.setdefault(art, cont.strip())
    for art in re.findall(r"unique product number\s+(\d+)", txt):
        variants.setdefault(art, "")
    for art in re.findall(r"Item no\.:\s*(\d+)", txt):
        variants.setdefault(art, "")
    for art in re.findall(r"itemNo=(\d+)", htm):
        variants.setdefault(art, "")
    m = re.search(r"[?&]itemNo=(\d+)", url)         # the URL we asked for
    if m:
        variants.setdefault(m.group(1), "")

    # bullet list under "Product information" -- the breadcrumb is also <li>s, so
    # keep only bullets that sit inside the Product-information span and are not
    # the product/section names themselves.
    bullets = []
    m = re.search(r"Product information(.*?)(?:Loading Data|Variant|product variant|Downloads|download links)", txt, re.S)
    if m:
        chunk = m.group(1).lower()
        skip = {name.lower(), title.lower()}
        for b in re.findall(r"<li[^>]*>(.*?)</li>", htm, re.S | re.I):
            b = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", b))).strip()
            if b and len(b) < 160 and b.lower() in chunk and b.lower() not in skip:
                if b not in bullets:
                    bullets.append(b)

    # prose description: the block after the bullets ("Loading Data" separates the
    # spec list from the marketing copy) and before Downloads.
    desc = ""
    m = re.search(r"Loading Data\s*(.*?)\s*(?:Downloads|download links)", txt, re.S)
    if m:
        desc = m.group(1).strip()
    if not desc:
        m = re.search(r"([A-Z][^.]{40,}?\.(?:\s+[^.]{20,}?\.){1,8})\s*Downloads", txt)
        desc = m.group(1).strip() if m else ""

    return {"url": url, "title": title, "name": name, "variants": variants,
            "bullets": bullets, "description": desc}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls"); ap.add_argument("--url")
    ap.add_argument("--out"); ap.add_argument("--delay", type=float, default=0.7)
    ap.add_argument("--reparse", action="store_true",
                    help="re-parse every url from the HTML cache (no network)")
    ap.add_argument("--refetch", action="store_true", help="ignore the HTML cache")
    a = ap.parse_args()

    urls = [a.url] if a.url else json.load(open(a.urls))
    # resume: keep whatever a previous run already parsed
    out = {}
    if a.out and os.path.exists(a.out) and not a.reparse:
        try:
            out = json.load(open(a.out))
        except ValueError:
            out = {}
    todo = [u for u in urls if u not in out]
    print(f"{len(out)} already done, {len(todo)} to fetch", file=sys.stderr)

    failed = []
    for i, u in enumerate(todo, 1):
        htm, from_cache = cached_get(u, refetch=a.refetch)
        if not htm:
            failed.append(u)
            print(f"[{i}/{len(todo)}] FETCH FAILED {u}", file=sys.stderr)
            continue
        rec = parse(u, htm)
        out[u] = rec
        print(f"[{i}/{len(todo)}] {'cache' if from_cache else 'net  '} "
              f"{rec['name'][:42]:<44} variants={list(rec['variants'])}", file=sys.stderr)
        if a.out and i % 10 == 0:          # checkpoint, so a kill loses ≤10 pages
            open(a.out, "w").write(json.dumps(out, ensure_ascii=False, indent=1))
        if not from_cache:
            time.sleep(a.delay)

    js = json.dumps(out, ensure_ascii=False, indent=1)
    if a.out:
        open(a.out, "w").write(js)
        print(f"wrote {a.out}  ({len(out)} pages, {len(failed)} failed)", file=sys.stderr)
    else:
        print(js)
    if failed:
        print("failed urls:\n  " + "\n  ".join(failed), file=sys.stderr)


if __name__ == "__main__":
    main()
