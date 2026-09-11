#!/usr/bin/env python3
"""Parse a cached trixie.de product page into everything the import needs.

Reads the HTML cache written by scripts/trixie-product.py (.siruk-cache/trixie-html/
<sha1(url)>.html) and returns, per page:
  name, breadcrumb (list), species, gallery (1600mx1200m urls, in page order),
  info_heading, bullets, prose (the marketing paragraph(s) under Product
  information), variants {article: {dt: dd, ...}} from the "product variant"
  section, composition [..], analytical {k: v}, additives {k: v}.

    scripts/trixie-parse.py --url "<page url>"            # one page, JSON
    scripts/trixie-parse.py --urls list.json --out out.json
"""
import argparse, hashlib, html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_CACHE = os.path.join(ROOT, ".siruk-cache", "trixie-html")


def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()


def cached_html(url):
    p = os.path.join(HTML_CACHE, hashlib.sha1(url.encode()).hexdigest() + ".html")
    return open(p, encoding="utf-8", errors="ignore").read() if os.path.exists(p) else ""


def parse(url, htm):
    out = {"url": url}
    m = re.search(r"<h1[^>]*>(.*?)</h1>", htm, re.S | re.I)
    out["name"] = clean(m.group(1)) if m else ""
    m = re.search(r"Item no\.:\s*(\d+)", clean(htm))
    out["item_no"] = m.group(1) if m else ""
    crumbs = re.findall(r'<li class="breadcrumb-item[^"]*">.*?<span>(.*?)</span>', htm, re.S)
    out["breadcrumb"] = [clean(c) for c in crumbs][2:]      # drop "TRIXIE Heimtierbedarf", "Productworld"
    out["species"] = (out["breadcrumb"][0].lower() if out["breadcrumb"] else "")
    # breadcrumb slugs from the url
    try:
        out["path"] = url.split("/en/productworld/")[1].split("?")[0].split("/")[:-1]
    except IndexError:
        out["path"] = []
    # gallery (page order); 280x280 thumbs are the gallery, 1600 rendition is the same file
    thumbs = re.findall(r'class="galleryItem"><img[^>]+src="https://cdn\.trixie\.de/assets/img/280x280/([^"]+)"', htm)
    big = re.findall(r"https://cdn\.trixie\.de/assets/img/1600mx1200m/[^\"' )]*\.(?:jpg|jpeg|png|webp)", htm)
    seen, gal = set(), []
    for f in thumbs:                      # page order, 1600 rendition when the page lists it
        u = "https://cdn.trixie.de/assets/img/1600mx1200m/" + f
        if u not in seen:
            seen.add(u); gal.append(u)
    for u in big:
        if u not in seen:
            seen.add(u); gal.append(u)
    out["gallery"] = gal
    # product information block
    m = re.search(r'<div class="description">(.*?)</div>\s*</div>\s*</div>', htm, re.S)
    info = m.group(1) if m else ""
    m = re.search(r"<h2>\s*<strong>(.*?)</strong>\s*</h2>", info, re.S)
    out["info_heading"] = clean(m.group(1)) if m else ""
    out["bullets"] = [clean(b) for b in re.findall(r"<li[^>]*>(.*?)</li>", info, re.S) if clean(b)]
    paras = [clean(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", info, re.S)]
    out["prose"] = [p for p in paras if p]
    # the marketing text (between "Loading Data" and Composition/Downloads) when not inside description
    if not out["prose"]:
        txt = clean(htm)
        m = re.search(r"Loading Data\s*(.*?)\s*(?:Composition & Labelling|Downloads|Product detail for a product)", txt, re.S)
        if m and len(m.group(1)) > 30:
            out["prose"] = [m.group(1).strip()]
    # variants (accessible section)
    variants = {}
    for art, body in re.findall(r"product variant: unique product number (\d+)</h4>\s*<dl>(.*?)</dl>", htm, re.S):
        d = {}
        for dt, dd in re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", body, re.S):
            k, v = clean(dt), clean(dd)
            v = clean(html.unescape(v)) if "&lt;" in v else v
            if k:
                d[k] = v
        variants[art] = d
    if not variants and out["item_no"]:
        variants[out["item_no"]] = {}
    out["variants"] = variants
    # composition & labelling
    m = re.search(r"<h3>Composition &amp; Labelling</h3>\s*<ul>(.*?)</ul>", htm, re.S)
    out["composition"] = [clean(x) for x in re.findall(r"<li>(.*?)</li>", m.group(1), re.S)] if m else []
    m = re.search(r'<h3 id="analytic-headline">.*?</h3>(.*?)</dl>', htm, re.S)
    out["analytical"] = {clean(a): clean(b) for a, b in re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", m.group(1), re.S)} if m else {}
    m = re.search(r'<h3 id="additives-heading">.*?</h3>(.*?)</dl>', htm, re.S)
    out["additives"] = {clean(a): clean(b) for a, b in re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", m.group(1), re.S) if clean(a)} if m else {}
    # feeding recommendation, if the page has one
    txt = clean(htm)
    m = re.search(r"(Feeding recommendation|Feeding guide|Recommended daily amount)[:\s]*(.*?)(?:Composition|Downloads|Analytical|$)", txt, re.S | re.I)
    out["feeding"] = m.group(2).strip()[:1500] if m else ""
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url"); ap.add_argument("--urls"); ap.add_argument("--out")
    a = ap.parse_args()
    urls = [a.url] if a.url else json.load(open(a.urls))
    out, missing = {}, []
    for u in urls:
        htm = cached_html(u)
        if not htm:
            missing.append(u); continue
        out[u] = parse(u, htm)
    if a.out:
        json.dump(out, open(a.out, "w"), ensure_ascii=False, indent=1)
        print(f"parsed {len(out)}, {len(missing)} not in cache", file=sys.stderr)
    else:
        print(json.dumps(out if len(out) > 1 else next(iter(out.values()), {}), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
