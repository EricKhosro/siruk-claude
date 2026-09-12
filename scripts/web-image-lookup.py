#!/usr/bin/env python3
"""Last resort: verify a page found by a general web/image search, and pull its photos.

CLAUDE.md rule 7 lets a general web search close the gap when the brand's own
sites, the approved fallbacks and zoovet all have nothing (rule 7d, user
instruction 2026-09-12: *"if you really cannot find picture anywhere try to
google it, just make sure it is the same product"*). The search itself is done
by hand (the WebSearch tool / Google Images); this script is the **verification**
half, so a hit is still keyed to a number and never to a name:

  * it fetches each candidate page and reports which of our keys it prints —
    the article code, the EAN, the trailing-1 trimmed article (29411 -> 2941);
  * it keeps images whose file name carries a key, then the og:image of a page
    that prints one, then the rest of the gallery;
  * it downloads every candidate so it can be LOOKED AT before anything is
    uploaded, and reports pixel size (sips) so a thumbnail can be rejected.

A page that prints none of the keys is reported with `keys: []` — that is a name
match, and rule 7 forbids attaching it.

    scripts/web-image-lookup.py --article 29411 --ean 4011905294117 URL [URL...]
    scripts/web-image-lookup.py --article 25141 --alt 2514 --out .siruk-cache/webimg URL
    scripts/web-image-lookup.py --ean-of 29411          # just print the Trixie EAN

Trixie EAN = 4011905 + article padded to 5 + check digit (only for <=5-digit
articles; the 6-digit lead/collar numbers are not encodable and take --ean).
"""
import hashlib, html as htmllib, json, os, re, subprocess, sys, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
SKIP = re.compile(r"(sprite|logo|icon|favicon|placeholder|banner|flag|payment|"
                  r"paypal|visa|mastercard|trustami|bewertung|pixel|loader|spinner|"
                  r"1x1|blank|dummy|/ui/|/icons?/|badge|social)", re.I)


def trixie_ean(article):
    a = re.sub(r"\D", "", str(article))
    if len(a) > 5:
        return None
    b = "4011905" + a.zfill(5)
    s = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(b))
    return b + str((10 - s % 10) % 10)


def get(url, timeout=45, binary=False):
    r = subprocess.run(["curl", "-sSL", "-A", UA, "--compressed", "--max-time", str(timeout), url],
                       capture_output=True)
    if r.returncode != 0:
        return b"" if binary else ""
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def dims(path):
    r = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
                       capture_output=True, text=True)
    w = re.search(r"pixelWidth:\s*(\d+)", r.stdout)
    h = re.search(r"pixelHeight:\s*(\d+)", r.stdout)
    return (int(w.group(1)), int(h.group(1))) if w and h else (0, 0)


def page_keys(text, keys):
    """Which of our keys the page itself prints (digits only, word-ish boundaries)."""
    flat = re.sub(r"[\s ]+", " ", text)
    found = []
    for k in keys:
        if re.search(r"(?<!\d)" + re.escape(k) + r"(?!\d)", flat):
            found.append(k)
    return found


def images_from(page, base, keys):
    out, seen = [], set()

    def add(u, why):
        u = urllib.parse.urljoin(base, htmllib.unescape(u.strip()))
        u = u.split("#")[0]
        if not u.lower().startswith("http") or SKIP.search(u) or u in seen:
            return
        seen.add(u)
        out.append({"url": u, "why": why})

    srcs = re.findall(r'(?:src|data-src|data-original|data-zoom-image|data-large_image|'
                      r'data-image|href|content)\s*=\s*"([^"]+?\.(?:jpe?g|png|webp))[^"]*"', page, re.I)
    for u in srcs:
        name = u.rsplit("/", 1)[-1]
        hit = [k for k in keys if k in re.sub(r"\D", "", name) or k in name]
        if hit:
            add(u, "file name carries " + "/".join(hit))
    for pat in (r'property="og:image"[^>]*content="([^"]+)"',
                r'content="([^"]+)"[^>]*property="og:image"',
                r'"image"\s*:\s*"([^"]+)"'):
        for m in re.findall(pat, page, re.I):
            add(m, "og:image / schema image of a page that prints the key")
    for u in srcs:
        add(u, "other image on that page")
    return out


def fetch_images(cands, outdir, limit):
    os.makedirs(outdir, exist_ok=True)
    kept = []
    for c in cands[:limit]:
        ext = re.sub(r"[^a-z]", "", c["url"].rsplit(".", 1)[-1].lower())[:4] or "jpg"
        p = os.path.join(outdir, hashlib.sha1(c["url"].encode()).hexdigest()[:12] + "." + ext)
        if not os.path.exists(p):
            data = get(c["url"], binary=True)
            if len(data) < 3000:
                continue
            open(p, "wb").write(data)
        w, h = dims(p)
        if w < 400 or h < 400:
            continue
        kept.append(dict(c, file=p, w=w, h=h, bytes=os.path.getsize(p)))
    return kept


def main():
    a = sys.argv[1:]
    if "--ean-of" in a:
        for x in a[a.index("--ean-of") + 1:]:
            print(x, trixie_ean(x))
        return
    def opt(name, default=None):
        return a[a.index(name) + 1] if name in a else default
    article = opt("--article", "")
    ean = opt("--ean") or (trixie_ean(article) if article else None)
    alts = [x for x in (opt("--alt") or "").split(",") if x]
    outdir = opt("--out", os.path.join(ROOT, ".siruk-cache/webimg", article or "misc"))
    limit = int(opt("--limit", "8"))
    urls = [x for x in a if x.startswith("http")]
    keys = [k for k in ([article, ean] + alts) if k]

    res = []
    for u in urls:
        page = get(u)
        if not page:
            res.append({"page": u, "error": "fetch failed"}); continue
        text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", page, flags=re.S | re.I)
        text = htmllib.unescape(re.sub(r"<[^>]+>", " ", text))
        found = page_keys(text, keys) or page_keys(page, keys)
        title = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
        imgs = images_from(page, u, found) if found else []
        res.append({"page": u, "host": urllib.parse.urlparse(u).netloc,
                    "title": htmllib.unescape(title.group(1)).strip()[:120] if title else "",
                    "keys": found,
                    "images": fetch_images(imgs, outdir, limit) if found else [],
                    "note": "" if found else "page prints none of " + ",".join(keys) +
                            " — name match only, rule 7 forbids it"})
    print(json.dumps({"article": article, "ean": ean, "keys": keys, "results": res},
                     indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
