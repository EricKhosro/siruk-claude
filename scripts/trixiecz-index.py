#!/usr/bin/env python3
"""Index trixiecz.cz — TRIXIE's official Czech distributor — by article number.

Why this site (approved 2026-09-11): it sells clearance stock, so it still lists
articles that trixie.de and its CDN have deleted, and every product page prints
our key in extractable markup:

    <h1>Unicorn, plush, 28 cm</h1>
    <strong data-code>35856</strong>   <strong data-ean>4011905358567</strong>

so nothing here rests on a name match (CLAUDE.md rule 7). `/en/` gives the
English name; images are clean 570x570 packshots with no watermark.

Two ways in, because **the sitemap is incomplete** — it omits most of the
discontinued stock (article 35510 is on the site but in no sitemap):

  --sitemap   walk the two product sitemaps (4,771 products, images included in
              the XML). Fast, but reaches only about half the catalogue.
  --sweep     walk the numeric product ids. The slug is ignored — /en/a_z8099/
              serves the same page as the full slug — so ids enumerate the whole
              shop. HEAD first (a live id answers 301, a dead one 404), then GET
              only what exists.

    scripts/trixiecz-index.py --sitemap
    scripts/trixiecz-index.py --sweep [--from 1] [--to 18000] [--refresh]
    scripts/trixiecz-index.py --lookup 35510 [...]

Result merges into .siruk-cache/trixiecz-index.json:

    {"35856": {"url":…, "ean":…, "name_en":…, "images":[…], "id":8099}}

Images are normalised to the 570x570 rendition (`_3`); the other renditions the
templates emit are 250 px thumbs or a 1200x630 social crop.
"""
import json, os, re, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
OUT = os.path.join(CACHE, "trixiecz-index.json")
STATE = os.path.join(CACHE, "trixiecz-sweep-state.json")
SITE = "https://www.trixiecz.cz"
SITEMAPS = [f"{SITE}/1/sitemap_products.xml", f"{SITE}/2/sitemap_products.xml"]
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
PARALLEL = 12           # polite: the shop is a small Czech host, not a CDN
HEAD_CHUNK = 600
GET_CHUNK = 120


def curl(args, timeout=900):
    return subprocess.run(["curl", "-sS", "--compressed", "-A", UA, "--max-time", "45"] + args,
                          capture_output=True, text=True, timeout=timeout)


def load(path, default):
    return json.load(open(path)) if os.path.exists(path) else default


def big(url, size="0"):
    """Normalise a /data/tmp rendition to the original (`_0`).

    The templates emit the same photo at several sizes — `_0` is the original the
    lightbox links to (1000-1920 px), `_3` a 570x570 square, `_2` 250 px, `_1` a
    50 px thumb, `_108` a 1200x630 social crop — and the path carries the size
    twice: /data/tmp/<size>/<last digit of image id>/<image id>_<size>.jpg."""
    u = url.split("?")[0]
    m = re.match(r"(.*/data/tmp)/\d+/\d/(\d+)_\d+\.jpg", u)
    if not m:
        return u
    base, img = m.groups()
    return f"{base}/{size}/{img[-1]}/{img}_{size}.jpg"


def parse(html, url):
    code = re.search(r"data-code>\s*(\d{3,7})", html) or re.search(r"[&?;]code=(\d{3,7})", html)
    if not code:
        return None
    ean = re.search(r"data-ean>\s*(\d{8,14})", html) or re.search(r"\b(40119\d{8})\b", html)
    name = re.search(r"<h1[^>]*>\s*([^<]{2,200}?)\s*</h1>", html)
    # Only the product's own gallery: the page also carries cross-sell thumbs and
    # a social-card crop, and the gallery urls are relative, so scope the scrape
    # to <div class="product-gallery"> … </div> and take the lightbox hrefs.
    g = re.search(r'class="product-gallery"(.*?)<div class="column-right"', html, re.S) or \
        re.search(r'class="product-gallery"(.*?)</form>', html, re.S)
    block = g.group(1) if g else ""
    imgs, seen = [], set()
    for u in (re.findall(r'href="(/data/tmp/[^"]+\.jpg)[^"]*"', block)
              or [big(x, "3") for x in re.findall(r'src="(/data/tmp/[^"]+\.jpg)[^"]*"', block)]
              or re.findall(r"https?://(?:www\.)?trixiecz\.cz/data/tmp/[^\"'\s>]+\.jpg", html)):
        b = big(u if u.startswith("http") else SITE + u)
        if b not in seen:
            seen.add(b)
            imgs.append(b)
    return {"url": url, "ean": ean.group(1) if ean else None,
            "name_en": name.group(1) if name else None, "images": imgs}


def merge(have, code, rec, replace=False):
    old = have.get(code) or {}
    imgs = (rec.get("images") or []) if replace else \
        list(dict.fromkeys((rec.get("images") or []) + (old.get("images") or [])))
    rec = {**old, **{k: v for k, v in rec.items() if v}, "images": imgs}
    have[code] = rec


def reparse(have):
    """Re-read every page already in the index (no id probing) — use after a
    change to what `parse` extracts."""
    urls = [v["url"] for v in have.values() if v.get("url")]
    print(f"re-reading {len(urls)} product pages", file=sys.stderr)
    for i in range(0, len(urls), GET_CHUNK):
        for u, rec in fetch(urls[i:i + GET_CHUNK]).items():
            merge(have, rec.pop("_code"), rec, replace=True)
        print(f"  {min(i + GET_CHUNK, len(urls))}/{len(urls)}", file=sys.stderr)
        save(have)
        time.sleep(1)


# --------------------------------------------------------------- sitemap mode
def from_sitemap(have):
    for sm in SITEMAPS:
        xml = curl([sm]).stdout
        blocks = re.findall(r"<url>(.*?)</url>", xml, re.S)
        print(f"{sm}: {len(blocks)} products", file=sys.stderr)
        urls = []
        for b in blocks:
            loc = re.search(r"<loc>([^<]+)</loc>", b)
            imgs = [big(u) for u in re.findall(r"<image:loc>([^<]+)</image:loc>", b)]
            if loc:
                urls.append((loc.group(1), imgs))
        for i in range(0, len(urls), GET_CHUNK):
            batch = urls[i:i + GET_CHUNK]
            for u, rec in fetch([u for u, _ in batch]).items():
                sitemap_imgs = dict(batch).get(u, [])
                rec["images"] = list(dict.fromkeys(rec["images"] + sitemap_imgs))
                merge(have, rec.pop("_code"), rec)
            print(f"  {min(i + GET_CHUNK, len(urls))}/{len(urls)} pages, {len(have)} codes", file=sys.stderr)
            save(have)
            time.sleep(1)


# ------------------------------------------------------------------ id sweep
def head(ids):
    """HEAD a batch of ids. A live product answers 301 to its canonical slug."""
    with tempfile.NamedTemporaryFile("w", suffix=".curl", delete=False) as f:
        for i in ids:
            f.write(f"url = {SITE}/en/a_z{i}/\n")
        cfg = f.name
    r = curl(["--head", "-Z", "--parallel-max", str(PARALLEL), "-K", cfg,
              "-o", "/dev/null", "-w", "%{http_code} %{redirect_url} %{url}\n"])
    os.unlink(cfg)
    live = {}
    for line in r.stdout.splitlines():
        p = line.split()
        if len(p) < 3 or p[0] not in ("200", "301", "302"):
            continue
        target = p[1] if p[1].startswith("http") else p[2]
        m = re.search(r"_z(\d+)/?$", target)
        if m:
            live[int(m.group(1))] = target
    return live


def fetch(urls):
    """GET pages in parallel into a temp dir, parse each."""
    out = {}
    with tempfile.TemporaryDirectory() as d:
        with tempfile.NamedTemporaryFile("w", suffix=".curl", delete=False) as f:
            for n, u in enumerate(urls):
                f.write(f"url = {u}\noutput = {d}/{n}.html\n")
            cfg = f.name
        curl(["-Z", "--parallel-max", str(PARALLEL), "-L", "-K", cfg])
        os.unlink(cfg)
        for n, u in enumerate(urls):
            p = f"{d}/{n}.html"
            if not os.path.exists(p):
                continue
            rec = parse(open(p, encoding="utf-8", errors="replace").read(), u)
            if rec:
                code = re.search(r"data-code>\s*(\d{3,7})|[&?;]code=(\d{3,7})",
                                 open(p, encoding="utf-8", errors="replace").read())
                rec["_code"] = code.group(1) or code.group(2)
                out[u] = rec
    return out


def sweep(have, lo, hi, refresh):
    st = load(STATE, {"done": [], "live": {}})
    done = set(st["done"])
    todo = [i for i in range(lo, hi + 1) if refresh or i not in done]
    print(f"ids {lo}-{hi}: {len(todo)} to probe", file=sys.stderr)
    for i in range(0, len(todo), HEAD_CHUNK):
        batch = todo[i:i + HEAD_CHUNK]
        live = head(batch)
        if not live:            # an empty band is usually throttling rather than a gap,
            time.sleep(10)      # so confirm before believing it (the id space does have
            live = head(batch)  # real holes: 12022-12700 are all 404)
            if not live:
                print(f"  ids {batch[0]}-{batch[-1]}: empty twice — treating it as a gap "
                      f"in the id space", file=sys.stderr)
        urls = list(live.values())
        for j in range(0, len(urls), GET_CHUNK):
            for u, rec in fetch(urls[j:j + GET_CHUNK]).items():
                code = rec.pop("_code")
                m = re.search(r"_z(\d+)/?$", u)
                if m:
                    rec["id"] = int(m.group(1))
                merge(have, code, rec)
            time.sleep(1)
        done |= set(batch)
        st["done"] = sorted(done)
        json.dump(st, open(STATE, "w"))
        save(have)
        print(f"  ids {batch[0]}-{batch[-1]}: {len(live)} live, {len(have)} codes total", file=sys.stderr)
        time.sleep(1)


def save(have):
    json.dump(have, open(OUT, "w"), ensure_ascii=False, indent=0)


def main():
    argv = sys.argv[1:]
    have = load(OUT, {})
    if "--lookup" in argv:
        for a in argv[argv.index("--lookup") + 1:]:
            print(json.dumps({a: have.get(a) or have.get(a.lstrip("0"))}, ensure_ascii=False, indent=1))
        return
    refresh = "--refresh" in argv
    if "--reparse" in argv:
        reparse(have)
    if "--sitemap" in argv:
        from_sitemap(have)
    if "--sweep" in argv:
        lo = int(argv[argv.index("--from") + 1]) if "--from" in argv else 1
        hi = int(argv[argv.index("--to") + 1]) if "--to" in argv else 18000
        sweep(have, lo, hi, refresh)
    save(have)
    withimg = sum(1 for v in have.values() if v.get("images"))
    print(f"{len(have)} article codes indexed, {withimg} with at least one image -> {OUT}")


if __name__ == "__main__":
    main()
