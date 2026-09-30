#!/usr/bin/env python3
"""Barcode lookup — what the world knows about our EAN (added 2026-09-25).

The step between "the brand site has nothing for this pack" and giving up
(CLAUDE.md rule 7, reference/image-sources.md → "Barcode lookup"). hafo stores
a manufacturer barcode for every variant; once hafo has **confirmed** our
article code, that barcode is a key the rest of the web shares, and shops that
print it identify the product and carry its name, photos and description.

    barcode-lookup.py --code 12207S --name "<register / CSV name>"   # barcode from hafo, then look it up
    barcode-lookup.py --ean 4048422122074                           # look up a barcode you already have
    barcode-lookup.py --ean 4048422122074 --no-net                  # local caches only

What it does, in order:
  1. The barcode: from `hafo-lookup.py`, only when hafo **confirms** the code
     AND the barcode is the one on the variant whose own sku/article IS our
     code. (A name-guessed hafo listing, or the barcode of a sibling variant,
     is not ours — both happened on 2026-09-25.) Check digit validated.
  2. Local EAN-keyed caches we already built: 4lapy.ru offers, monge.it pages
     (`ean2mit`), hornung/carrefour hits (`ean-images`).
  3. Free barcode databases: UPCitemdb (trial API, 100 lookups/day, slow down
     or it answers TOO_FAST) and Open Pet Food Facts.
  4. Prints the web search to run next: the exact EAN in quotes. That search
     is done with the agent's WebSearch tool, not from here — in the 2026-09-25
     test it identified 6 of 6 stuck barcodes, where the databases found 1.

Every hit is a **lead**, not a finished card: the confirmation and usage rules
are in reference/image-sources.md → "Barcode lookup". barcodelookup.com is not
used (403 bot wall; paid API).
"""
import argparse, json, os, re, subprocess, sys, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
UA = "SirukCatalog/1.0 (product import; contact via siruk.am)"
UPC_GAP = 12.0          # seconds between UPCitemdb calls; the trial tier throttles bursts
UPC_STAMP = os.path.join(CACHE, ".upcitemdb-last")


def ean_ok(b):
    b = re.sub(r"\D", "", str(b or ""))
    if len(b) not in (8, 12, 13, 14):
        return None
    d = [int(x) for x in b]
    s = sum(x * (3 if i % 2 == 0 else 1) for i, x in enumerate(reversed(d[:-1])))
    return b if (10 - s % 10) % 10 == d[-1] else None


def norm(code):
    """Brand-aware article key: hafo writes Trixie 23641 as 'TX 236411', Acana
    AC5301112 as 'AC 5301112', Monge 009517 as 'MS 009517'."""
    c = (code or "").strip().upper().replace("\xa0", " ")
    m = re.match(r"^TX\s*(\d{6})$", c)
    if m:
        return "T:" + m.group(1)[:5].lstrip("0")
    c = c.replace(" ", "")
    m = re.match(r"^(\d+)(TXN|TX)$", c)
    if m:
        return "T:" + m.group(1).lstrip("0")
    return c


def keys_of(sku):
    k = {norm(sku)}
    m = re.match(r"^([A-Z]{2})[\s\xa0]+(\d+)$", (sku or "").strip())
    if m and m.group(1) != "TX":
        k |= {m.group(1) + m.group(2), m.group(2)}
    return k


def barcode_from_hafo(code, name):
    cmd = [sys.executable, os.path.join(ROOT, "scripts/hafo-lookup.py"), "--code", code]
    if name:
        cmd += ["--name", name]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=180).stdout
    i = out.find("{")
    h = json.loads(out[i:]) if i >= 0 else {}
    if not h.get("confirmed"):
        return None, {"why": "hafo does not confirm this code", "hafo_url": h.get("url")}
    skus, bcs, arts = h.get("skus") or [], h.get("barcodes") or [], h.get("articles") or []
    if len(skus) != len(bcs):
        return None, {"why": "hafo sku/barcode lists don't line up — read the listing by hand",
                      "hafo_url": h.get("url")}
    want = norm(code)
    hits = set()
    for n, (s, b) in enumerate(zip(skus, bcs)):
        k = keys_of(s)
        if len(arts) == len(skus) and arts[n]:
            k.add(norm(arts[n]))
        if want in k and ean_ok(b):
            hits.add(ean_ok(b))
    if len(hits) != 1:
        return None, {"why": f"{len(hits)} barcodes pair with our code on the hafo listing",
                      "hafo_url": h.get("url"), "skus": skus, "barcodes": bcs}
    return hits.pop(), {"hafo_url": h.get("url"), "hafo_title": h.get("title_hy")}


def local_hits(ean):
    hits = []
    def load(f):
        p = os.path.join(CACHE, f)
        return json.load(open(p)) if os.path.exists(p) else {}
    o = (load("4lapy-barcodes.json").get("barcodes") or {}).get(ean)
    if o:
        hits.append({"source": "4lapy.ru", "keyed": "barcode on the offer", "name": o.get("name"),
                     "url": o.get("url"), "images": o.get("images"),
                     "description": (o.get("description_ru") or "")[:400]})
    o = load("ean2mit.json").get(ean)
    if o:
        hits.append({"source": "monge.it", "keyed": "EAN in the pack-photo file name",
                     "name": o.get("name"), "url": o.get("url"), "images": o.get("images")})
    for art, o in load("ean-images.json").items():
        if o.get("ean") == ean:
            hits.append({"source": "ean-image-lookup", "keyed": "EAN in the file name",
                         "url": o.get("page"), "images": o.get("images"), "article": art})
    return hits


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def upcitemdb(ean):
    try:
        last = float(open(UPC_STAMP).read())
    except Exception:
        last = 0
    wait = UPC_GAP - (time.time() - last)
    if wait > 0:
        time.sleep(wait)
    try:
        d = get_json("https://api.upcitemdb.com/prod/trial/lookup?upc=" + ean)
    except Exception as e:
        return [], f"upcitemdb: {e}"
    finally:
        os.makedirs(CACHE, exist_ok=True)
        open(UPC_STAMP, "w").write(str(time.time()))
    if d.get("code") != "OK":
        return [], f"upcitemdb: {d.get('code')} {d.get('message', '')}".strip()
    return [{"source": "upcitemdb", "keyed": "EAN (database record)", "name": it.get("title"),
             "brand": it.get("brand"), "category": it.get("category"),
             "description": it.get("description"), "images": it.get("images"),
             "offers": [o.get("link") for o in it.get("offers") or []][:5]}
            for it in d.get("items") or []], None


def openpetfoodfacts(ean):
    try:
        d = get_json(f"https://world.openpetfoodfacts.org/api/v2/product/{ean}.json"
                     "?fields=product_name,brands,quantity,image_front_url,ingredients_text")
    except urllib.error.HTTPError as e:
        return [], None if e.code == 404 else f"openpetfoodfacts: {e}"   # 404 = no record
    except Exception as e:
        return [], f"openpetfoodfacts: {e}"
    p = d.get("product")
    if d.get("status") != 1 or not p:
        return [], None
    return [{"source": "openpetfoodfacts", "keyed": "EAN (database record)",
             "name": p.get("product_name"), "brand": p.get("brands"), "pack": p.get("quantity"),
             "composition": p.get("ingredients_text"),
             "images": [p["image_front_url"]] if p.get("image_front_url") else [],
             "note": "photos are CC-BY-SA — evidence only, not for upload"}], None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--code", help="our article code (barcode read from hafo)")
    g.add_argument("--ean", help="a barcode you already have")
    ap.add_argument("--name", help="row name, passed to hafo-lookup")
    ap.add_argument("--no-net", action="store_true", help="local caches only")
    a = ap.parse_args()

    out = {"code": a.code, "ean": None, "ean_from": None, "hits": [], "errors": []}
    if a.ean:
        out["ean"], out["ean_from"] = ean_ok(a.ean), "given"
        if not out["ean"]:
            sys.exit(f"{a.ean}: not a valid EAN/UPC (check digit)")
    else:
        ean, info = barcode_from_hafo(a.code, a.name)
        out.update(ean=ean, ean_from="hafo (confirmed, paired to our sku)" if ean else None, hafo=info)
        if not ean:
            print(json.dumps(out, ensure_ascii=False, indent=1))
            return
    ean = out["ean"]
    out["hits"] += local_hits(ean)
    if not a.no_net:
        for fn in (upcitemdb, openpetfoodfacts):
            hits, err = fn(ean)
            out["hits"] += hits
            if err:
                out["errors"].append(err)
    out["next"] = {
        "web_search": f'"{ean}"',
        "then": "open only pages that print this exact EAN and are not on the "
                "turned-down list (reference/image-sources.md); confirm identity on "
                "2+ independent pages; log in runs/<date>/barcode-sourced.csv",
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
