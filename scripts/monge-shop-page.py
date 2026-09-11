#!/usr/bin/env python3
"""Fetch + parse monge.shop (PrestaShop, /gb/ English) product pages.

Per page: name (h1), reference (EAN), images (thickbox renditions of THIS product,
from the product gallery), description (the intro paragraph), composition,
analytical constituents, additives, feeding, and the "Produkt card" attribute
table (Your pupil / Food type / Age / Type of food / Line / Main ingredient /
Weight / Size / Nutritional needs).

    scripts/monge-shop-page.py --url <page> | --from .siruk-cache/mongeshop-group.json --out pages.json
"""
import hashlib, html, json, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_CACHE = os.path.join(ROOT, ".siruk-cache", "mongeshop-html")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def get(url):
    os.makedirs(HTML_CACHE, exist_ok=True)
    p = os.path.join(HTML_CACHE, hashlib.sha1(url.encode()).hexdigest() + ".html")
    if os.path.exists(p):
        return open(p, encoding="utf-8", errors="ignore").read(), True
    for i in range(3):
        r = subprocess.run(["curl", "-sS", "-A", UA, "-L", "--max-time", "40", url], capture_output=True, text=True)
        if r.returncode == 0 and len(r.stdout) > 5000:
            open(p, "w", encoding="utf-8").write(r.stdout)
            return r.stdout, False
        time.sleep(2 * (i + 1))
    return "", False


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def parse(url, h):
    out = {"url": url}
    m = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
    out["name"] = clean(m.group(1)) if m else ""
    m = re.search(r"Reference\s*</[^>]+>\s*<[^>]+>\s*([0-9]{8,14})", h) or re.search(r"Reference\s+([0-9]{8,14})", clean(h))
    out["reference"] = m.group(1) if m else ""
    # gallery: the product's own image ids (data-image-large-src / thickbox in the product cover block)
    cover = re.search(r'class="[^"]*product-cover[^"]*".*?</div>\s*</div>', h, re.S)
    ids = []
    for blk in (cover.group(0) if cover else "", h):
        for u in re.findall(r"https://monge\.shop/(\d+)-(?:thickbox|large)_default/([^\"'\s]+\.jpg)", blk):
            if u not in ids:
                ids.append(u)
        if ids:
            break
    slug = url.rsplit("/", 1)[-1].split(".html")[0]
    slug = re.sub(r"^\d+-", "", slug)
    out["images"] = [f"https://monge.shop/{i}-thickbox_default/{f}" for i, f in ids if f.startswith(slug[:25])]
    txt = clean(h)
    for stop in ("Other products you may be interested in", "document.addEventListener", "Related products", "Reviews (0)"):
        i = txt.find(stop)
        if i > 0 and i > txt.find("COMPOSITION"):
            txt = txt[:i]
    m = re.search(r"Description\s+Product Details.*?Produkt card\s+Composition\s+(.*?)\s+YOUR PUPIL", txt, re.S)
    out["description"] = m.group(1).strip() if m else ""
    m = re.search(r"YOUR PUPIL\s+(.*?)\s+(?:Brand|Nutritional needs\s+(.*?)\s+(?:LIVING|Brand))", txt, re.S)
    card = {}
    for k, v in re.findall(r'"name":"([^"]+)","id_feature_value":"\d+","value":"([^"]*)"', h):
        k, v = html.unescape(k).strip(), html.unescape(v).strip()
        if k and v and k not in card:
            card[k] = v
    out["card"] = card
    m = re.search(r"COMPOSITION:\s*(.*?)(?:\s(?:ANALYTICAL|Analytical) (?:CONSTITUENTS|constituents|COMPONENTS|components):?\s*(.*?))?(?:\s(?:ADDITIVES|Additives|NUTRITIONAL ADDITIVES)[^:]*:\s*(.*?))?\s*(?:(?:FEEDING|Feeding|RECOMMENDED|Recommended|Instructions|INSTRUCTIONS|Add to basket|Data sheet|Reviews|Related)|$)", txt, re.S)
    if m:
        out["composition"] = (m.group(1) or "").strip()[:2000]
        out["analytical"] = (m.group(2) or "").strip()[:1000]
        out["additives"] = (m.group(3) or "").strip()[:1500]
    else:
        out["composition"] = out["analytical"] = out["additives"] = ""
    m = re.search(r"((?:FEEDING|Feeding) (?:RECOMMENDATION|recommendation|GUIDE|guide|instructions|INSTRUCTIONS)S?:?\s*.*?)(?:\sAdd to basket|Reviews|Related products|Data sheet|$)", txt, re.S)
    out["feeding"] = m.group(1).strip()[:1500] if m else ""
    return out


def main():
    if "--url" in sys.argv:
        u = sys.argv[sys.argv.index("--url") + 1]
        h, _ = get(u)
        print(json.dumps(parse(u, h), ensure_ascii=False, indent=1)); return
    src = json.load(open(sys.argv[sys.argv.index("--from") + 1]))
    outp = sys.argv[sys.argv.index("--out") + 1]
    out = json.load(open(outp)) if os.path.exists(outp) else {}
    for i, r in enumerate(src, 1):
        u = r.get("url")
        if not u or u in out:
            continue
        h, cached = get(u)
        if not h:
            print(f"[{i}] FETCH FAILED {u}", file=sys.stderr); continue
        out[u] = parse(u, h)
        print(f"[{i}/{len(src)}] {'cache' if cached else 'net'} {out[u]['name'][:60]} imgs={len(out[u]['images'])} card={len(out[u]['card'])}", file=sys.stderr)
        if not cached:
            time.sleep(0.8)
        if i % 10 == 0:
            json.dump(out, open(outp, "w"), ensure_ascii=False, indent=1)
    json.dump(out, open(outp, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
