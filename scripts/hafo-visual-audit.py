#!/usr/bin/env python3
"""Find hafo photos on the live site by LOOKING, not by file name.

scripts/hafo-audit.py catches a hafo photo only while it keeps hafo's file name
(or its cache record). A hafo picture re-saved under another name — a renamed
upload, a crop, a re-encode — slips past it. This compares pixels: every media
used by any variant is perceptually hashed (pHash + dHash on our admin
thumbnail) and matched against hafo's own photo of every article we know
(.siruk-cache/hafo-all.json + every run's hafo.json). A match within --max-dist
on both hashes = the same photograph = a hafo placeholder.

Run with the venv that has Pillow + imagehash:

    SIRUK_API=https://api.siruk.am/api/admin SIRUK_TOKEN_FILE=$PWD/.siruk-token-prod \\
      .venv-scrapling/bin/python scripts/hafo-visual-audit.py --out runs/<date>/hafo-visual.csv

Read-only. Caches downloads in .siruk-cache/hafo-hash/ and hashes in hafo-hash.json.
Columns: product_id, product, variant_id, sku, variant, position, media_id,
media_file, hafo_article, hafo_image, phash_dist, dhash_dist, only_image, link.
Look at every row before acting on it (contact sheet): a brand packshot that
hafo itself copied will also match — the hafo copy carries the watermark, ours
may not.
"""
import argparse, csv, glob, hashlib, io, json, os, subprocess, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache", "hafo-hash")
HASHES = os.path.join(ROOT, ".siruk-cache", "hafo-hash-v2.json")  # v2 = hashed after trim()

from PIL import Image  # noqa: E402
import imagehash  # noqa: E402


def api(path):
    for _ in range(3):
        r = subprocess.run([os.path.join(ROOT, "scripts/api.sh"), "GET", path],
                           capture_output=True, text=True, cwd=ROOT, timeout=180)
        i = r.stdout.find("{")
        if i >= 0:
            try:
                return json.loads(r.stdout[i:])
            except json.JSONDecodeError:
                pass
        time.sleep(2)
    return {}


def fetch(url):
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest()[:20])
    if not os.path.exists(f):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            data = urllib.request.urlopen(req, timeout=60).read()
        except Exception:
            return None
        open(f, "wb").write(data)
    return f


def hashes(url, memo):
    if url in memo:
        return memo[url]
    f = fetch(url)
    h = None
    if f:
        try:
            im = trim(Image.open(f).convert("RGB"))
            h = [str(imagehash.phash(im)), str(imagehash.dhash(im))]
        except Exception:
            h = None
    memo[url] = h
    return h


def trim(im):
    """Crop away a plain (near-white) border: our upload pipeline pads a photo onto a
    canvas, which moves every pixel and defeats the hash (041887: 400x601 vs 762x984)."""
    from PIL import ImageChops
    bg = Image.new("RGB", im.size, (255, 255, 255))
    diff = ImageChops.difference(im, bg).convert("L").point(lambda x: 255 if x > 18 else 0)
    box = diff.getbbox()
    return im.crop(box) if box else im


def dist(a, b):
    return imagehash.hex_to_hash(a) - imagehash.hex_to_hash(b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-dist", type=int, default=10, help="pHash AND dHash distance (default 10)")
    ap.add_argument("--ids", help="comma-separated product ids (default: all)")
    a = ap.parse_args()
    memo = json.load(open(HASHES)) if os.path.exists(HASHES) else {}

    # hafo's photo per article
    hafo = {}
    srcs = [os.path.join(ROOT, ".siruk-cache", "hafo-all.json")] + glob.glob(os.path.join(ROOT, "runs", "*", "hafo.json"))
    for p in srcs:
        try:
            d = json.load(open(p))
        except Exception:
            continue
        for k, v in (d.items() if isinstance(d, dict) else []):
            if isinstance(v, dict) and v.get("image") and "cloudfront" in v["image"]:
                hafo.setdefault(v["image"], k)
    print(f"{len(hafo)} hafo photos", file=sys.stderr)
    hafo_h = []
    for i, (u, art) in enumerate(hafo.items()):
        h = hashes(u, memo)
        if h:
            hafo_h.append((u, art, h))
        if i % 100 == 0:
            json.dump(memo, open(HASHES, "w"))
    json.dump(memo, open(HASHES, "w"))
    print(f"{len(hafo_h)} hashed", file=sys.stderr)

    if a.ids:
        ids = [int(x) for x in a.ids.split(",")]
    else:
        ids, page = [], 1
        while True:
            d = api(f"/products?page={page}")
            ids += [p["id"] for p in d.get("data", [])]
            if page >= (d.get("meta") or {}).get("last_page", 1):
                break
            page += 1
    print(f"{len(ids)} products", file=sys.stderr)

    media = {}
    rows = []
    for n, pid in enumerate(ids):
        p = (api(f"/products/{pid}").get("data") or {})
        for v in p.get("variants") or []:
            imgs = v.get("images") or []
            for pos, mid in enumerate(imgs, 1):
                mid = mid.get("id") if isinstance(mid, dict) else mid
                if mid not in media:
                    m = (api(f"/medias/{mid}").get("data") or {})
                    media[mid] = (m.get("originalUrl") or m.get("url"), m.get("filename") or "")
                url, fn = media[mid]
                if not url:
                    continue
                h = hashes(url, memo)
                if not h:
                    continue
                best = None
                for hu, art, hh in hafo_h:
                    d1, d2 = dist(h[0], hh[0]), dist(h[1], hh[1])
                    if d1 <= a.max_dist and d2 <= a.max_dist and (best is None or d1 + d2 < best[2] + best[3]):
                        best = (hu, art, d1, d2)
                if best:
                    rows.append({"product_id": pid, "product": p.get("name"), "variant_id": v["id"],
                                 "sku": v.get("sku"), "variant": v.get("label") or v.get("name"),
                                 "position": pos, "media_id": mid, "media_file": fn,
                                 "hafo_article": best[1], "hafo_image": best[0],
                                 "phash_dist": best[2], "dhash_dist": best[3],
                                 "only_image": len(imgs) == 1,
                                 "link": f"https://siruk.am/product/{p.get('slug')}/dp/{v['id']}/"})
        if n % 50 == 0:
            json.dump(memo, open(HASHES, "w"))
            print(f"  {n}/{len(ids)}  {len(rows)} hafo matches", file=sys.stderr)
    json.dump(memo, open(HASHES, "w"))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    cols = list(rows[0].keys()) if rows else ["product_id"]
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print(f"{len(rows)} variant images look like hafo's photo -> {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
