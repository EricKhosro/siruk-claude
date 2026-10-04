#!/usr/bin/env python3
"""Read-only helper for the rival-price agents (run from this folder, PYTHONUTF8=1).

  rival.py hafo "<terms>"        local search of today's hafo dump (every listing row): all terms must
                                  appear in title+row name+keywords (case-insensitive); prints sku, row
                                  name, price, wholesale, kg_price, stock, url
  rival.py hafo-live "<query>"   hafo.am's own search API (matches SKU, Armenian title, row name)
  rival.py hafo-sku "<text>"     hafo rows whose sku/article/barcode contains this text
  rival.py zoovet "<terms>"      local search of today's zoovet brand lists + zoovet's live search
  rival.py zoovet-page <url>     zoovet product page: name, price, old price, OPTIONS (size -> price), stock
  rival.py nemo "<terms>"        local search of today's nemo brand lists + nemo's live search
  rival.py nemo-page <url>       nemo product page: name, price, old price, stock, manufacturer
Terms: space-separated; a term with | means any-of (e.g. "royal maxi adult 15|15кг").
"""
import html as H, json, os, re, sys, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"


def fetch(url, js=False):
    h = {"User-Agent": UA}
    if js:
        h.update({"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
    p = urllib.parse.urlsplit(url)
    url = urllib.parse.urlunsplit((p.scheme, p.netloc, urllib.parse.quote(p.path, safe="/%"), p.query, p.fragment))
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=60).read().decode("utf-8", "replace")


def txt(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = H.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def amd(s):
    d = re.sub(r"[^\d]", "", txt(s or ""))
    return int(d) if d else None


def hit(name, terms):
    n = (name or "").lower().replace("\xa0", " ")
    return all(any(alt in n for alt in t.lower().split("|")) for t in terms)


def hafo_rows():
    for it in json.load(open(os.path.join(HERE, "hafo-all.json"), encoding="utf-8")):
        for a in it.get("product_additional_information") or []:
            yield it, a


def show_hafo(it, a):
    print(json.dumps({"sku": a.get("sku"), "row": a.get("name"), "title": it.get("title"), "price": a.get("price"),
                      "wholesale": a.get("wholesale_price"), "kg_price": a.get("kg_price"),
                      "barcode": a.get("barcode"), "in_stock": a.get("qty_in_stock"),
                      "url": "https://hafo.am/products/" + (it.get("slug") or "")}, ensure_ascii=False))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    cmd, arg = sys.argv[1], " ".join(sys.argv[2:])
    terms = [t for t in arg.split() if t]
    if cmd == "hafo":
        n = 0
        for it, a in hafo_rows():
            if hit((it.get("title") or "") + " " + (a.get("name") or "") + " " + (it.get("meta_keywords") or ""), terms):
                show_hafo(it, a)
                n += 1
                if n >= 60:
                    print("... (more)")
                    break
    elif cmd == "hafo-sku":
        q = arg.lower().replace(" ", "")
        for it, a in hafo_rows():
            if any(q in str(a.get(k) or "").lower().replace(" ", "").replace("\xa0", "") for k in ("sku", "article", "barcode")):
                show_hafo(it, a)
    elif cmd == "hafo-live":
        u = ("https://hafo.am/products/filter?page=1&order_by=order-desc&min_price=0&max_price=50000000&animal=&brand="
             "&weight=&age=&type=&is_new=false&search=" + urllib.parse.quote(arg))
        d = json.loads(fetch(u, js=True))
        box = d.get("products", d)
        for it in box.get("data", []):
            for a in it.get("product_additional_information") or []:
                show_hafo(it, a)
    elif cmd in ("zoovet", "nemo"):
        shops = json.load(open(os.path.join(HERE, "shops.json"), encoding="utf-8"))[cmd]
        seen = set()
        for brand, rows in shops.items():
            for r in rows:
                if hit(r["name"], terms) and r["url"] not in seen:
                    seen.add(r["url"])
                    print("LOCAL", json.dumps(r, ensure_ascii=False))
        try:
            if cmd == "zoovet":
                h = fetch("https://zoovet.am/search/?search=%s&description=true&limit=100" % urllib.parse.quote(arg))
                for b in re.split(r'<div class="product-thumb', h)[1:]:
                    u = re.search(r'<a href="(https://zoovet\.am/[^"]+)"', b)
                    if not u or u.group(1) in seen:
                        continue
                    seen.add(u.group(1))
                    names = sorted((txt(t) for t in re.findall(r'<a href="%s"[^>]*>(.*?)</a>' % re.escape(u.group(1)), b, re.S)), key=len)
                    p = re.search(r'price-new">([^<]+)<', b) or re.search(r'class="price">\s*<span[^>]*>([^<]+)<', b)
                    print("LIVE", json.dumps({"name": names[-1] if names else None, "url": u.group(1),
                                              "price": amd(p.group(1)) if p else None}, ensure_ascii=False))
            else:
                h = fetch("https://www.nemo.am/search?q=%s&pagesize=60" % urllib.parse.quote(arg))
                for b in re.split(r"<div class=product-item ", h)[1:]:
                    u = re.search(r'<a href=(/[^ >]+)', b)
                    if not u:
                        continue
                    url = "https://www.nemo.am" + urllib.parse.unquote(u.group(1))
                    if url in seen:
                        continue
                    seen.add(url)
                    t = re.search(r'class=product-title><a href=[^>]+>(.*?)</a>', b, re.S)
                    p = re.search(r'class="price actual-price">([^<]+)<', b)
                    print("LIVE", json.dumps({"name": txt(t.group(1)) if t else None, "url": url,
                                              "price": amd(p.group(1)) if p else None}, ensure_ascii=False))
        except Exception as e:
            print("live search failed:", e)
    elif cmd == "zoovet-page":
        h = fetch(arg)
        name = re.search(r'class="product-title">([^<]+)<', h)
        price = re.search(r'class="price">\s*([^<]+?)\s*</div>', h)
        blk = h[h.find('class="price-block"'):][:3000] if 'class="price-block"' in h else ""
        new = re.search(r'price-new[^"]*">\s*([^<]+)<', blk)   # main price block only (not related products)
        old = re.search(r'price-old[^"]*">\s*([^<]+)<', blk)
        opts = [(txt(n), amd(p)) for n, p in re.findall(
            r'class="option-name">(.*?)</span>\s*<span class="option-price">(.*?)</span>', h, re.S)]
        stock = re.search(r'class="stock">\s*<div class="([a-z]+)">\s*([^<]+?)\s*<', h)
        print(json.dumps({"url": arg, "name": txt(name.group(1)) if name else None,
                          "price": amd(price.group(1)) if price else None,
                          "price_new": amd(new.group(1)) if new else None,
                          "price_old": amd(old.group(1)) if old else None,
                          "options": opts, "stock": txt(stock.group(2)) if stock else None},
                         ensure_ascii=False, indent=1))
    elif cmd == "nemo-page":
        h = fetch(arg)
        name = re.search(r'<div class=product-name><h1[^>]*>([^<]+)<', h) or re.search(r'<h1[^>]*>([^<]+)<', h)
        price = re.search(r'itemprop=price content=([\d.]+)', h)
        # <div class=old-product-price><span>հին գինը:</span> <span>4200֏</span></div>: the amount is the
        # last span with digits (the first span is the label)
        old = re.search(r'class=old-product-price>(.*?)</div>', h, re.S)
        old = next((s for s in reversed(re.findall(r'<span>([^<]*\d[^<]*)<', old.group(1))) if amd(s)), None) if old else None
        old = re.match(r'(.*)', old) if old else None
        stock = re.search(r'property=product:availability content="([^"]+)"', h)
        manuf = re.search(r'class=manufacturers>.*?<a[^>]*>([^<]+)<', h, re.S)
        sd = re.search(r'class=short-description>(.*?)</div>', h, re.S)
        print(json.dumps({"url": arg, "name": txt(name.group(1)) if name else None,
                          "price": int(float(price.group(1))) if price else None,
                          "old_price": amd(old.group(1)) if old else None,
                          "stock": stock.group(1) if stock else None,
                          "manufacturer": txt(manuf.group(1)) if manuf else None,
                          "short": txt(sd.group(1))[:400] if sd else None}, ensure_ascii=False, indent=1))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
