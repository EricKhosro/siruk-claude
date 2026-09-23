#!/usr/bin/env python3
"""Walk the whole image fallback ladder for every variant that has no usable photo.

Input is the gap worklist (variants with no image at all, or only a watermarked
hafo placeholder). For each one it tries the approved sources in CLAUDE.md rule 7
order and stops at the first that yields pictures:

    1 brand          scripts/trixie-image.sh  (trixie.de CDN + trixie.es)
    2 trixie.shop    Trixie's own Shopify store, cached index, article-keyed
    3 trixiecz.cz    official Czech distributor, cached index, `Kód` + EAN
    4 tiierisch.de   German shop, Shopify: variant sku = article, barcode = EAN,
                     and images are linked to the variant they belong to
    4 monge          monge.it / monge.shop pages, keyed by the EAN
    5 web search     scripts/image-search.py — Bing Images on the EAN, keeping
                     only files whose NAME carries the EAN/article (rule 7d)

Everything is downloaded to <out>/<article>/ with its provenance, measured, and
rendered into one contact sheet, because nothing may be attached before it has
been looked at (rule 7). Writing is a separate step:
`scripts/archive/_apply-recovered-images.py`.

    scripts/gap-images.py --worklist .siruk-cache/image-worklist.json \
                          --out runs/<date>/found --sheet [--only 25141,3435]
"""
import hashlib, html as htmllib, json, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
RANK = {"PHO_PRO_CLIP": 1, "PHO_PAC_CLIP": 2, "PHO_PRO_DET_CLIP": 3, "PHO_PRO_SET_CLIP": 4,
        "PHO_PRO_USE_CLIP": 5, "PHO_PRO_USE": 5, "PHO_PRO_DOG_CLIP": 6, "PHO_PRO_CAT_CLIP": 6,
        "PHO_PRO_GROUP_CLIP": 7, "GRA_PRO": 8}
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import importlib
isearch = importlib.import_module("image-search".replace("-", "_")) if False else None


def load(p, d):
    p = p if os.path.isabs(p) else os.path.join(CACHE, p)
    return json.load(open(p)) if os.path.exists(p) else d


def sh(args, t=180):
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=t)
    return r.stdout


def get(url, t=60):
    r = subprocess.run(["curl", "-sSL", "-A", UA, "--compressed", "--max-time", str(t), url],
                       capture_output=True)
    return r.stdout if r.returncode == 0 else b""


def dims(p):
    r = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", p], capture_output=True, text=True)
    w = re.search(r"pixelWidth:\s*(\d+)", r.stdout); h = re.search(r"pixelHeight:\s*(\d+)", r.stdout)
    return (int(w.group(1)), int(h.group(1))) if w and h else (0, 0)


def trixie_rank(url):
    f = url.rsplit("/", 1)[-1]
    for k in sorted(RANK, key=len, reverse=True):
        if f.startswith(k):
            return RANK[k]
    return 3


def ean_of(article, brand):
    a = re.sub(r"\D", "", article)
    def chk(b):
        s = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(b)); return b + str((10 - s % 10) % 10)
    if brand.lower().startswith("trixie") and len(a) <= 5:
        # Trixie ships two GS1 prefixes; the newer articles carry 4047974
        return chk("4011905" + a.zfill(5))
    if brand.lower().startswith("monge") and a.endswith("7") and len(a) <= 6:
        return chk("8009470" + a[:-1].zfill(5))
    return None


def eans_for(article, brand):
    """Every barcode this article can carry. Trixie ships two GS1 prefixes
    (4011905 and the newer 4047974) and both are in live use — 25141's photo is
    filed under 4047974251416 while 3435's is under 4011905034355 — so a lookup
    that tries only one misses half the catalogue."""
    a = re.sub(r"\D", "", article)
    def chk(b):
        s = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(b)); return b + str((10 - s % 10) % 10)
    if brand.lower().startswith("trixie") and len(a) <= 5:
        return [chk("4011905" + a.zfill(5)), chk("4047974" + a.zfill(5))]
    if brand.lower().startswith("monge") and a.endswith("7") and len(a) <= 6:
        return [chk("8009470" + a[:-1].zfill(5))]
    return []


def web_fallback(row, hafo_ean=None):
    """Rule 7d, the last resort: shops and catalogues that FILE THE PICTURE UNDER
    THE BARCODE, then a general image search kept to hits whose file name carries
    the number. Nothing here is a name match."""
    art, brand = row["article"], row.get("brand", "")
    eans = ([hafo_ean] if hafo_ean else []) + [e for e in eans_for(art, brand) if e != hafo_ean]
    found = []
    for e in eans:
        try:
            r = json.loads(sh([os.path.join(ROOT, "scripts/ean-image-lookup.py"), e], t=300))[0]
        except Exception:
            continue
        for u in r.get("carrefour", []):
            found.append((10, "carrefour-es", u, f"bucket keyed by EAN {e}"))
        for u in r.get("hornung", []):
            found.append((11, "hornung-baushop", u, f"file name carries EAN {e}"))
    if not found:
        try:
            out = sh([os.path.join(ROOT, "scripts/image-search.py"), "--article", art,
                      "--brand", brand, "--name", row.get("name", ""), "--limit", "6"], t=600)
            hits = json.loads(out[out.find("["):])[0]["kept"]
        except Exception:
            hits = []
        for h in hits:
            found.append((12 if h["evidence"] == "keyed-file" else 13, "web search",
                          h["image"], f'{h["evidence"]} {h["key"]} · {h["page"][:60]}'))
    return found


def collect(row, shop, cz, monge, tii=None):
    tii = tii or {}
    art, brand = row["article"], row.get("brand", "")
    ean = ean_of(art, brand)
    found = []          # (rank, source, url, note)

    if brand.lower().startswith("trixie"):
        for u in [x for x in sh([os.path.join(ROOT, "scripts/trixie-image.sh"), art]).splitlines() if x.strip()]:
            found.append((trixie_rank(u), "brand site", u, "file name carries " + art))
        if not found:
            for u in shop.get(art, []):
                found.append((trixie_rank(u), "trixie.shop", u, "Trixie file name, article " + art))
        if not found and art in tii:
            rec = tii[art]
            for i, u in enumerate(rec.get("images") or []):
                found.append((4 if i == 0 else 5, "tiierisch", u,
                              f'sku {art} ({rec.get("variant","")[:40]}), EAN {rec.get("ean")}'))
        if not found and art in cz:
            # the page's own `Kód` IS our article number, which is the key rule 7
            # asks for; the EAN is only recorded. (Trixie's barcodes are not a
            # formula: 3435 is 4011905034355 but 2345 is 4011905234519, and the
            # newer articles sit on a second GS1 prefix, 4047974.)
            rec = cz[art]
            for i, u in enumerate(rec.get("images") or []):
                found.append((4 if i == 0 else 5, "trixiecz", u,
                              f"page Kód {art}, EAN {rec.get('ean')}"))
    if brand.lower().startswith("monge") and ean:
        for v in monge.values():
            if str(v.get("reference") or "").strip() == ean:
                for i, u in enumerate(v.get("images") or []):
                    found.append((1 if i == 0 else 3, "monge.shop", u, "page reference = EAN " + ean))
    return [f for f in found if f[2]], ean


def download(cands, outdir, article, limit=10):
    os.makedirs(outdir, exist_ok=True)
    kept, seen = [], set()
    for rank, src, url, note in sorted(cands, key=lambda c: c[0])[:limit * 2]:
        if len(kept) >= limit:
            break
        data = get(url)
        if len(data) < 4000:
            continue
        d5 = hashlib.md5(data).hexdigest()
        if d5 in seen:
            continue
        ext = re.sub(r"[^a-z]", "", url.split("?")[0].rsplit(".", 1)[-1].lower())[:4] or "jpg"
        p = os.path.join(outdir, f"{article}-{len(kept)+1}.{ext}")
        open(p, "wb").write(data)
        w, h = dims(p)
        # a lead, a collar or a 50 cm rope is photographed laid out straight —
        # Trixie's own file for lead 201301 is 1600x118 — so judge by the long
        # edge and only reject what is genuinely a thumbnail
        if max(w, h) < 600 or min(w, h) < 100:
            os.remove(p); continue
        seen.add(d5)
        kept.append({"file": p, "url": url, "source": src, "why": note, "rank": rank, "w": w, "h": h})
    return kept


def sheet(rows, path):
    cells = []
    for r in rows:
        for i, k in enumerate(r["images"]):
            cells.append(
                f'<figure class="{"lead" if i == 0 else ""}"><img src="file://{k["file"]}">'
                f'<figcaption><b>{r["article"]}</b> p{r.get("product_id","")} '
                f'{htmllib.escape(r["name"])[:38]}<br>{k["w"]}×{k["h"]} · {k["source"]}'
                f'<br><span>{htmllib.escape(k["why"])[:64]}</span></figcaption></figure>')
    open(path, "w").write(
        "<!doctype html><meta charset=utf-8><style>body{font:12px -apple-system;background:#fff;margin:10px;"
        "display:flex;flex-wrap:wrap;gap:8px}figure{margin:0;width:200px}figure.lead img{border:3px solid #1a7}"
        "img{width:200px;height:200px;object-fit:contain;background:#f5f5f5;border:1px solid #ddd}"
        "figcaption{font-size:10px;line-height:1.25}span{color:#888}</style>" + "".join(cells))
    return path


def main():
    a = sys.argv[1:]
    def opt(n, d=None): return a[a.index(n) + 1] if n in a else d
    wl = json.load(open(opt("--worklist", os.path.join(CACHE, "image-worklist.json"))))
    only = set((opt("--only") or "").split(",")) - {""}
    if only:
        wl = [r for r in wl if r["article"] in only or str(r.get("product_id")) in only]
    out = opt("--out", os.path.join(CACHE, "gap-images"))
    os.makedirs(out, exist_ok=True)
    shop = load("trixie-shop-art-images.json", {})
    cz = load("trixiecz-index.json", {})
    monge = load("mongeshop-pages.json", {})
    tii = load("tiierisch-index.json", {})
    barcodes = load("hafo-variant-barcode.json", {})
    web = "--web" in a
    res = []
    for r in wl:
        cands, ean = collect(r, shop, cz, monge, tii)
        imgs = download(cands, os.path.join(out, r["article"]), r["article"])
        if not imgs and web:            # a source that had the article but no usable file
            cands = web_fallback(r, (barcodes.get(r["sku"]) or {}).get("barcode")) or cands
            imgs = download(cands, os.path.join(out, r["article"]), r["article"])
        res.append(dict(r, ean=ean, images=imgs,
                        sources=sorted({c[1] for c in cands}),
                        note="" if imgs else "no approved source has this article"))
        print(f'{r["article"]:>8} {len(imgs):>2} img  {",".join(sorted({c[1] for c in cands})) or "-"}', file=sys.stderr)
    json.dump(res, open(os.path.join(out, "found.json"), "w"), indent=1, ensure_ascii=False)
    if "--sheet" in a:
        print(sheet(res, os.path.join(out, "sheet.html")), file=sys.stderr)
    print(f'{sum(1 for r in res if r["images"])}/{len(res)} variants got pictures', file=sys.stderr)


if __name__ == "__main__":
    main()
