#!/usr/bin/env python3
"""Image search of last resort — and the check that keeps it inside rule 7.

User instruction 2026-09-12: *"if you really cannot find picture anywhere try to
google it, just make sure it is the same product."* This is that step, run only
after the brand's own sites, the approved fallbacks and zoovet have all missed
(CLAUDE.md rule 7d).

A picture search returns pictures, so the identity check has to come from the
number rather than from the look of the thing. Every hit is classified by where
our key appears:

    keyed-file   the image FILE NAME carries our EAN or article
                 (…/4011905034355.jpg, …-4011905034355-hornung-baushop.jpg)
    keyed-page   the SOURCE PAGE url carries it (…/4011905034355, …--t3435)
    name-only    neither — a name match, which rule 7 forbids attaching

Only `keyed-*` hits are downloadable; `name-only` is reported so it can be seen
how thin the evidence is, never used. Even a keyed hit is a candidate: look at
the picture (--sheet) before it goes anywhere near upload-media.sh.

    scripts/image-search.py --article 3435 --brand Trixie --name "Fussball Vinyl 6 cm"
    scripts/image-search.py --article 041537 --ean 8009470041539 --brand "Gran Bonta"
    scripts/image-search.py --from gaps.json --out runs/2026-09-12/found --sheet

The EAN is computed for Trixie (4011905 + article padded to 5 + check digit) and
Monge/Gemon (8009470 + vendor code minus its trailing 7, padded to 5) unless
--ean says otherwise; both conventions are in reference/brand-sites.md.
"""
import hashlib, html as htmllib, json, os, re, subprocess, sys, time, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
BING = "https://www.bing.com/images/search?q={q}&first=1&count=35"
JUNK = re.compile(r"(sprite|logo|favicon|placeholder|banner|payment|paypal|visa|"
                  r"trustami|pixel|loader|spinner|1x1|blank|dummy|badge|social|"
                  r"youtube\.com|ytimg|facebook|instagram)", re.I)


def check(b):
    s = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(b))
    return b + str((10 - s % 10) % 10)


def guess_ean(article, brand=""):
    a = re.sub(r"\D", "", str(article))
    b = (brand or "").lower()
    if b.startswith("trixie") or not b:
        if len(a) <= 5:            # Trixie ships two GS1 prefixes, both in use
            return [check("4011905" + a.zfill(5)), check("4047974" + a.zfill(5))]
    if any(x in b for x in ("monge", "gemon", "gran bonta", "bwild", "simba")):
        if a.endswith("7") and len(a) <= 6:          # vendor code = EAN core + 7
            return [check("8009470" + a[:-1].zfill(5))]
    return []


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


def search(query):
    page = get(BING.format(q=urllib.parse.quote(query)))
    out = []
    for m in re.findall(r'\sm="([^"]+)"', page):
        try:
            d = json.loads(htmllib.unescape(m))
        except Exception:
            continue
        if d.get("murl"):
            out.append({"image": d["murl"], "page": d.get("purl", ""),
                        "title": (d.get("t") or "").strip()})
    return out


def delimited(k, s):
    """The key as its own number, not a fragment of a longer one (3435 must not
    match a 34350 file or a `...-3435xx` hash)."""
    return re.search(r"(?<![0-9])" + re.escape(k) + r"(?![0-9])", s) is not None


def classify(hit, keys):
    """EAN beats article, and a bare article is only evidence when it stands
    alone in the string: 3435 otherwise matches vinyl-sticker files all day."""
    name = hit["image"].split("?")[0].rsplit("/", 1)[-1]
    purl = hit["page"]
    for where, kind in ((name, "keyed-file"), (purl, "keyed-page")):
        for k in keys:
            if len(k) >= 12 and (k in where or k in re.sub(r"\D", "", where)):
                return kind, k                      # an EAN cannot collide
        for k in keys:
            if len(k) >= 5 and delimited(k, where):
                return kind, k
    return "name-only", ""


def lookup(article, brand="", name="", ean=None, outdir=None, limit=10, queries=None):
    eans = ([ean] if ean else []) or guess_ean(article, brand)
    keys = [k for k in list(eans) + [str(article)] if k and len(str(k)) >= 4]
    qs = queries or ([f'"{e}"' for e in eans] +
                     [f'{brand} {article} {name}'.strip()])
    seen, hits = set(), []
    for q in [x for x in qs if x]:
        for h in search(q):
            if h["image"] in seen or JUNK.search(h["image"]):
                continue
            seen.add(h["image"])
            kind, key = classify(h, keys)
            h.update(evidence=kind, key=key, query=q)
            hits.append(h)
        time.sleep(1.2)
    hits.sort(key=lambda h: {"keyed-file": 0, "keyed-page": 1, "name-only": 2}[h["evidence"]])

    outdir = outdir or os.path.join(ROOT, ".siruk-cache/imgsearch", str(article))
    os.makedirs(outdir, exist_ok=True)
    kept, md5s, n = [], set(), 0
    for h in hits:
        if h["evidence"] == "name-only" or n >= limit:
            continue
        data = get(h["image"], binary=True)
        if len(data) < 4000:
            continue
        d5 = hashlib.md5(data).hexdigest()
        if d5 in md5s:
            continue
        ext = re.sub(r"[^a-z]", "", h["image"].split("?")[0].rsplit(".", 1)[-1].lower())[:4] or "jpg"
        p = os.path.join(outdir, f"{article}-{len(kept)+1}.{ext}")
        open(p, "wb").write(data)
        w, hh = dims(p)
        if max(w, hh) < 600 or min(w, hh) < 100:
            os.remove(p); continue
        md5s.add(d5); n += 1
        kept.append(dict(h, file=p, w=w, h=hh, bytes=len(data)))
    return {"article": str(article), "brand": brand, "name": name, "ean": eans, "keys": keys,
            "queries": [x for x in qs if x], "kept": kept,
            "rejected_name_only": [h for h in hits if h["evidence"] == "name-only"][:6]}


def sheet(results, path):
    cells = []
    for r in results:
        for k in r["kept"]:
            cells.append(
                f'<figure><img src="file://{k["file"]}"><figcaption><b>{r["article"]}</b> '
                f'{htmllib.escape(r["name"])[:40]}<br>{k["w"]}×{k["h"]} · {k["evidence"]}'
                f' {k["key"]}<br><span>{htmllib.escape(k["page"][:70])}</span></figcaption></figure>')
    open(path, "w").write(
        "<!doctype html><meta charset=utf-8><style>body{font:12px -apple-system;background:#fff;"
        "margin:12px;display:flex;flex-wrap:wrap;gap:10px}figure{margin:0;width:210px}"
        "img{width:210px;height:210px;object-fit:contain;background:#f4f4f4;border:1px solid #ddd}"
        "figcaption{font-size:10px;line-height:1.3}span{color:#888}</style>" + "".join(cells))
    return path


def main():
    a = sys.argv[1:]
    def opt(n, d=None):
        return a[a.index(n) + 1] if n in a else d
    outdir = opt("--out")
    limit = int(opt("--limit", "10"))
    if "--from" in a:
        rows = json.load(open(opt("--from")))
    else:
        rows = [{"article": opt("--article"), "brand": opt("--brand", ""),
                 "name": opt("--name", ""), "ean": opt("--ean")}]
    res = []
    for r in rows:
        d = lookup(r["article"], r.get("brand", ""), r.get("name", ""), r.get("ean"),
                   os.path.join(outdir, str(r["article"])) if outdir else None, limit)
        d["product_id"] = r.get("product_id"); d["sku"] = r.get("sku")
        res.append(d)
        print(f'{r["article"]:>8}  {len(d["kept"])} keyed  ean={d["ean"]}', file=sys.stderr)
    if outdir:
        os.makedirs(outdir, exist_ok=True)
        json.dump(res, open(os.path.join(outdir, "found.json"), "w"), indent=1, ensure_ascii=False)
        if "--sheet" in a:
            print(sheet(res, os.path.join(outdir, "sheet.html")), file=sys.stderr)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
