#!/usr/bin/env python3
"""List every live variant that has no image, or an image that came from hafo.am.

hafo pictures are watermarked stand-ins (CLAUDE.md rule 7a); this is the worklist
for replacing them with the brand's own photo.

    scripts/_scan-image-gaps.py            -> .siruk-cache/image-gaps.json
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")


def api(path):
    r = subprocess.run([os.path.join(ROOT, "scripts/api.sh"), "GET", path],
                       capture_output=True, text=True, cwd=ROOT, timeout=180)
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:]) if i >= 0 else {}


def load(p, d):
    return json.load(open(p)) if os.path.exists(p) else d


def main():
    mc = load(os.path.join(CACHE, "media-cache.json"), {})
    st = load(os.path.join(CACHE, "enrich-images.state.json"), {"media": {}})
    hafo_ids = {v for u, v in list(mc.items()) + list(st.get("media", {}).items())
                if "d1b3l6j8a0ngef.cloudfront.net" in u and isinstance(v, int) and v}
    names = load(os.path.join(CACHE, "media-filenames.json"), {})
    # a media whose stored file name is a bare hafo timestamp is a hafo upload too
    for mid, fn in names.items():
        base = str(fn).rsplit("/", 1)[-1]
        if base.startswith("hafo") or (base.split(".")[0].isdigit() and len(base.split(".")[0]) >= 15):
            hafo_ids.add(int(mid))
    print(f"{len(hafo_ids)} media id(s) known to be hafo uploads", file=sys.stderr)

    ids, page = [], 1
    while True:
        d = api(f"/products?page={page}")
        ids += [p["id"] for p in d.get("data", [])]
        if page >= (d.get("meta") or {}).get("last_page", 1):
            break
        page += 1
    print(f"{len(ids)} products", file=sys.stderr)

    gaps = []
    for n, pid in enumerate(sorted(set(ids)), 1):
        p = api(f"/products/{pid}").get("data") or {}
        for v in p.get("variants", []):
            imgs = v.get("images") or []
            bad = [i for i in imgs if i in hafo_ids]
            if not imgs or bad:
                gaps.append({"product_id": pid, "name": p.get("name", ""), "slug": p.get("slug", ""),
                             "brand_id": p.get("brand_id"), "sku": str(v.get("sku")), "label": v.get("name", ""),
                             "images": imgs, "hafo": bad, "kind": "empty" if not imgs else
                             ("hafo only" if len(bad) == len(imgs) else "hafo among others")})
        if n % 100 == 0:
            print(f"  {n}/{len(set(ids))}", file=sys.stderr)
    json.dump(gaps, open(os.path.join(CACHE, "image-gaps.json"), "w"), ensure_ascii=False, indent=1)
    import collections
    print("gaps:", collections.Counter(g["kind"] for g in gaps), "->", os.path.join(CACHE, "image-gaps.json"))


if __name__ == "__main__":
    main()
