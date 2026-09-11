#!/usr/bin/env python3
"""Last-resort image lookup for an article the brand's own sites do not picture.

CLAUDE.md's fallback ladder ends with "a general web/image search for the exact
product", flagged as fallback. This walks European pet shops that print TRIXIE's
article number in the product URL, so a hit is still keyed to the article and
never to a name:

    zoo4you.de      …-<article>.html
    gundogstore.eu  page markup carries "<article>"
    miscota.com     page markup carries "<article>"

    scripts/find-article-image.py <article> [...]      # JSON per article

For each candidate page it keeps images whose file name carries the article, and
otherwise the page's own og:image — which is that page's single product photo.
Nothing is uploaded here: look at the file first (rule 7).
"""
import json, re, subprocess, sys, urllib.parse

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def get(url, timeout=60):
    r = subprocess.run(["curl", "-sSL", "-A", UA, "--max-time", str(timeout), url],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def bing(q):
    """A plain search-engine query; returns candidate urls."""
    h = get("https://duckduckgo.com/html/?q=" + urllib.parse.quote(q))
    out = []
    for m in re.findall(r'href="(https?://[^"]+)"', h):
        u = urllib.parse.unquote(m)
        if "duckduckgo" in u or "/y.js" in u:
            continue
        out.append(u.split("&rut=")[0])
    seen, res = set(), []
    for u in out:
        k = u.split("?")[0]
        if k not in seen:
            seen.add(k); res.append(k)
    return res[:12]


def images_from(page_html, article, base):
    imgs = []
    for u in re.findall(r'(?:src|data-src|content|href)="([^"]+\.(?:jpg|jpeg|png|webp))"', page_html, re.I):
        full = urllib.parse.urljoin(base, u)
        name = full.rsplit("/", 1)[-1]
        if article in name:
            imgs.append(("article in file name", full))
    m = re.search(r'property="og:image"\s+content="([^"]+)"', page_html) or \
        re.search(r'content="([^"]+)"\s+property="og:image"', page_html)
    if m:
        imgs.append(("og:image of a page that names the article", urllib.parse.urljoin(base, m.group(1))))
    seen, out = set(), []
    for why, u in imgs:
        if u not in seen:
            seen.add(u); out.append({"why": why, "url": u})
    return out


def lookup(article, name=""):
    res = {"article": article, "candidates": []}
    urls = bing(f"Trixie {article} {name}".strip())
    for u in urls:
        host = urllib.parse.urlparse(u).netloc
        if not re.search(r"zoo4you|gundogstore|miscota|zoohit|zooplus|petmarket|arcaplanet|maxizoo|kramar|fera\.pl|zooplanet", host):
            continue
        h = get(u)
        if not h or article not in h:
            continue
        imgs = images_from(h, article, u)
        if imgs:
            res["candidates"].append({"page": u, "host": host, "images": imgs[:4]})
        if len(res["candidates"]) >= 3:
            break
    return res


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = [lookup(a) for a in args]
    print(json.dumps(out, indent=1))
