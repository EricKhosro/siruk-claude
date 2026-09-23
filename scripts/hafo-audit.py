#!/usr/bin/env python3
"""Find every variant in the catalogue that still shows a hafo.am photo.

hafo serves every picture with a repeating "Hafo" watermark, so one must never
survive to production (CLAUDE.md rule 7a): it is a placeholder the PM replaces
by hand, it goes last in the gallery, and the variant belongs on
`runs/<date>/needs-image.csv`.

A media is hafo if either is true:

  * the url it was uploaded FROM is on hafo's CDN (`d1b3l6j8a0ngef.cloudfront.net`,
    recorded in .siruk-cache/media-cache.json), or
  * the stored file name is one of hafo's own — a bare upload timestamp
    (`164381185448408127.jpg`), a timestamp plus the article
    (`1643034845-25189.jpg`), or anything starting `hafo`.

The second test is what catches the ones the caches lost: a media uploaded in a
run whose url→id mapping was never written still keeps hafo's file name.

    scripts/hafo-audit.py                       # -> .siruk-cache/hafo-audit.json
    scripts/hafo-audit.py --csv runs/<date>/hafo-images.csv
"""
import csv, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
OUT = os.path.join(CACHE, "hafo-audit.json")
HAFO_CDN = "d1b3l6j8a0ngef.cloudfront.net"


def load(p, d):
    p = p if os.path.isabs(p) else os.path.join(CACHE, p)
    return json.load(open(p)) if os.path.exists(p) else d


def api(path):
    r = subprocess.run([os.path.join(ROOT, "scripts/api.sh"), "GET", path],
                       capture_output=True, text=True, cwd=ROOT, timeout=180)
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:]) if i >= 0 else {}


def looks_like_hafo(filename):
    base = str(filename or "").rsplit("/", 1)[-1]
    if base.lower().startswith("hafo"):
        return True
    stem = base.split(".")[0]
    stem = re.sub(r"-adminThumbnail$", "", stem)
    head = stem.split("-")[0]
    # hafo names files after the upload timestamp: 17 bare digits, or
    # "<10-digit epoch>-<article>"
    return head.isdigit() and len(head) >= 10


def main():
    names = load("media-filenames.json", {})
    mc = load("media-cache.json", {})
    from_hafo = {v for u, v in mc.items() if HAFO_CDN in u and isinstance(v, int)}
    murl = load("media-urls.json", {})

    ids, page = [], 1
    while True:
        d = api(f"/products?page={page}")
        ids += [p["id"] for p in d.get("data", [])]
        if page >= (d.get("meta") or {}).get("last_page", 1):
            break
        page += 1
    print(f"{len(ids)} products", file=sys.stderr)

    def filename_of(mid):
        rec = names.get(str(mid))
        if isinstance(rec, dict) and rec.get("filename"):
            return rec["filename"]
        u = murl.get(str(mid))
        if u is None:
            u = ((api(f"/medias/{mid}").get("data") or {}).get("url") or "")
            murl[str(mid)] = u
        return u.rsplit("/", 1)[-1]

    rows = []
    for n, pid in enumerate(sorted(set(ids)), 1):
        p = api(f"/products/{pid}").get("data") or {}
        for v in p.get("variants", []):
            imgs = v.get("images") or []
            bad = []
            for mid in imgs:
                if mid in from_hafo or looks_like_hafo(filename_of(mid)):
                    bad.append(mid)
            if bad:
                rows.append({"product_id": pid, "name": p.get("name", ""), "slug": p.get("slug", ""),
                             "brand_id": p.get("brand_id"), "category_ids": p.get("category_ids"),
                             "sku": str(v.get("sku")), "label": v.get("name", ""),
                             "images": imgs, "hafo": bad,
                             "kind": "hafo only" if len(bad) == len(imgs) else "hafo among others",
                             "files": [filename_of(m) for m in bad]})
        if n % 100 == 0:
            print(f"  {n}/{len(set(ids))}", file=sys.stderr)

    json.dump(murl, open(os.path.join(CACHE, "media-urls.json"), "w"))
    json.dump(rows, open(OUT, "w"), ensure_ascii=False, indent=1)
    import collections
    print("hafo images still live:", collections.Counter(r["kind"] for r in rows),
          f"-> {OUT}", file=sys.stderr)
    if "--csv" in sys.argv:
        path = sys.argv[sys.argv.index("--csv") + 1]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Article Code", "Product (admin id)", "Product", "Variant SKU",
                        "Variant", "Total images", "hafo images", "hafo file(s)"])
            for r in rows:
                w.writerow([r["sku"], r["product_id"], r["name"], r["sku"], r["label"],
                            len(r["images"]), len(r["hafo"]), "; ".join(r["files"])])
        print(f"{len(rows)} row(s) -> {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
