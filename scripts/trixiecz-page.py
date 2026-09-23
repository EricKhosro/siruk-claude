#!/usr/bin/env python3
"""Read one trixiecz.cz product page: the article it prints, its EAN, the
English name, the breadcrumb, the description bullets and the full-size images.

trixiecz is the official Czech distributor (CLAUDE.md rule 7c). Every page
prints `Code:` and `EAN:`, so a hit is keyed to the article, never to a name.

    scripts/trixiecz-page.py <url> [<url> ...]
"""
import html, json, re, subprocess, sys

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def text(x):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", x)).split())


def page(url):
    raw = subprocess.run(["curl", "-sL", "-A", UA, url], capture_output=True,
                         text=True, timeout=90).stdout
    t = re.sub(r"<script.*?</script>", "", raw, flags=re.S)
    code = re.search(r"data-code>([^<]+)<", t)
    ean = re.search(r"data-ean>([^<]+)<", t)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", t, flags=re.S)
    crumbs = [text(m) for m in re.findall(r'itemprop="name"[^>]*>(.*?)<', t, flags=re.S)]
    if not crumbs:
        crumbs = [text(m) for m in re.findall(r'<li[^>]*class="[^"]*breadcrumb[^"]*"[^>]*>(.*?)</li>', t, flags=re.S)]
    i = t.find("Product description")
    desc = text(t[i:i + 2000])[:900] if i >= 0 else ""
    imgs, seen = [], set()
    for m in re.finditer(r'data-src="(/data/tmp/\d+/\d+/(\d+)_\d+\.jpg)[^"]*"[^>]*alt="([^"]*)"', t):
        n = m.group(2)
        if n in seen:
            continue
        seen.add(n)
        imgs.append({"url": f"https://www.trixiecz.cz/data/tmp/0/{n[-1]}/{n}_0.jpg",
                     "alt": m.group(3)})
    art = code and code.group(1).strip()
    # Keep only the product's own photos: trixiecz serves them under Trixie's
    # file names, which carry the article (PHO_PRO_CLIP_24165-1.jpg). Every
    # other <img> on the page is a category-menu icon.
    if art:
        imgs = [i for i in imgs if art in i["alt"]]
    return {"url": url, "code": art,
            "ean": ean and ean.group(1).strip(),
            "name_en": text(h1.group(1)) if h1 else "",
            "breadcrumb": crumbs, "description": desc, "images": imgs}


for u in sys.argv[1:]:
    print(json.dumps(page(u), ensure_ascii=False, indent=1))
