#!/usr/bin/env python3
"""Attach the reviewed gap images to their variants.

Input is one or more `found.json` files written by `scripts/gap-images.py`, or a
hand-written file of the same shape:

    [{"product_id": 810, "sku": "24428", "article": "24428",
      "images": [{"url": "...", "source": "trixiecz", "why": "page Kód 24428"}]}]

Order in the list is the gallery order, so images[0] is the feature image and
must already be a clean product shot — look at the contact sheet first
(`scripts/contact-sheet.py`), that is rule 7, not a formality. Each url goes through
`scripts/upload-media.sh` (which verifies the file is readable and caches
url -> media id), then ONE PUT per product rebuilt from a fresh GET, so the
other variants are untouched. Any hafo placeholder on the variant is dropped:
a real photo has replaced it.

    scripts/apply-gap-images.py runs/<date>/found/found.json [more.json ...]
    scripts/apply-gap-images.py --dry-run found.json
    scripts/apply-gap-images.py --only 24428,17592 found.json
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
VKEYS = ("id", "name", "about_this_item", "ingredient_information", "feeding_instructions",
         "pricing_type", "sku", "price", "price_per_kg", "min_allowed_price", "cost_price",
         "compare_at_price", "weight", "is_default", "stock", "vendor_stock", "sort_order",
         "images", "attribute_value_ids")
KEEP = ("name", "slug", "category_ids", "brand_id", "attribute_family_id",
        "is_best_seller", "is_on_sale", "is_discontinued")


def sh(a, t=900):
    r = subprocess.run(a, capture_output=True, text=True, cwd=ROOT, timeout=t)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def api(method, path, payload=None):
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "_applygap.json")
        json.dump(payload, open(p, "w"), ensure_ascii=False)
        args.append(p)
    rc, out, err = sh(args)
    i = out.find("{")
    return json.loads(out[i:]) if i >= 0 else {"_err": (err or out)[-300:]}


def hafo_ids():
    """Media that came from hafo.am — by source url, and by the bare-timestamp
    file names hafo serves (1643034845-25189.jpg, 164381185448408127.jpg)."""
    def load(p, d):
        return json.load(open(os.path.join(CACHE, p))) if os.path.exists(os.path.join(CACHE, p)) else d
    mc = load("media-cache.json", {})
    st = load("enrich-images.state.json", {"media": {}})
    ids = {v for u, v in list(mc.items()) + list(st.get("media", {}).items())
           if "d1b3l6j8a0ngef.cloudfront.net" in u and isinstance(v, int) and v}
    for mid, fn in load("media-filenames.json", {}).items():
        base = str(fn).rsplit("/", 1)[-1]
        stem = base.split(".")[0]
        if base.startswith("hafo") or (stem.split("-")[0].isdigit() and len(stem.split("-")[0]) >= 10):
            ids.add(int(mid))
    return ids


def main():
    a = sys.argv[1:]
    dry = "--dry-run" in a
    only = set((a[a.index("--only") + 1] if "--only" in a else "").split(",")) - {""}
    rows = []
    for f in [x for x in a if x.endswith(".json")]:
        rows += json.load(open(f))
    bad = hafo_ids()
    done = 0
    for r in rows:
        urls = [i["url"] for i in (r.get("images") or [])]
        if not urls or (only and r["article"] not in only and str(r.get("product_id")) not in only):
            continue
        pid, sku = r["product_id"], str(r["sku"])
        if dry:
            print(f'{r["article"]:>8} p{pid} {sku}: would set {len(urls)} image(s)')
            continue
        ids = []
        for u in urls:
            rc, out, err = sh([os.path.join(ROOT, "scripts/upload-media.sh"), u])
            last = out.splitlines()[-1] if out else ""
            if re.fullmatch(r"\d+", last):
                ids.append(int(last))
            else:
                print(f'{r["article"]}: upload failed {u} :: {(err or out)[-140:]}')
        if not ids:
            continue
        p = api("GET", f"/products/{pid}").get("data") or {}
        variants, changed = [], False
        for v in p.get("variants", []):
            nv = {k: v.get(k) for k in VKEYS if k in v}
            nv["attribute_value_ids"] = nv.get("attribute_value_ids") or {}
            if str(v.get("sku")) == sku:
                keep = [i for i in (nv.get("images") or []) if i not in bad and i not in ids]
                new = ids + keep
                if new != (nv.get("images") or []):
                    nv["images"] = new
                    changed = True
            variants.append(nv)
        if not changed:
            print(f'{r["article"]:>8} p{pid}: unchanged')
            continue
        body = {k: p.get(k) for k in KEEP if p.get(k) is not None}
        body["variants"] = variants
        api("PUT", f"/products/{pid}", body)
        back = api("GET", f"/products/{pid}").get("data") or {}
        got = [x.get("images") for x in back.get("variants", []) if str(x.get("sku")) == sku]
        print(f'{r["article"]:>8} p{pid}: {got}')
        done += 1
    print(f"{done} variant(s) updated")


if __name__ == "__main__":
    main()
