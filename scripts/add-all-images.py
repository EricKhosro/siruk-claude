#!/usr/bin/env python3
"""Give every Trixie variant ALL of its official gallery images.

For each product of brand 8 (Trixie) and each variant: resolve every gallery
image for the variant's article number (`scripts/trixie-image.sh`, page-based),
upload each through `scripts/upload-media.sh` (which slugifies, flattens alpha,
verifies the file is readable and caches URL→id, so an image already on the
server is not uploaded twice), then set `images` to the full ordered id list in
gallery order — packshot first (feature image rule, CLAUDE.md 7). Run
`scripts/feature-image.py` afterwards to confirm every first image is clean.
One PUT per product, body rebuilt from a fresh GET. Resumable via a state file.

    scripts/add-all-images.py [--only id,id] [--dry-run] [--limit N]
"""
import json, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
URLS = os.path.join(CACHE, "trixie-gallery-urls.json")
STATE = os.path.join(CACHE, "add-all-images-state.json")
TRIXIE = 8
VKEYS = ("id", "name", "about_this_item", "ingredient_information", "feeding_instructions", "pricing_type", "sku",
         "price", "price_per_kg", "min_allowed_price", "cost_price", "compare_at_price", "weight", "is_default",
         "stock", "vendor_stock", "sort_order", "images", "attribute_value_ids")
KEEP = ("name", "slug", "category_ids", "brand_id", "attribute_family_id", "is_best_seller", "is_on_sale", "is_discontinued")


def sh(args, timeout=300):
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=timeout, env=dict(os.environ, SIRUK_NO_PACE=os.environ.get("SIRUK_NO_PACE", "")))
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def api(method, path, payload=None):
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "_imgs.json"); json.dump(payload, open(p, "w"), ensure_ascii=False); args.append(p)
    rc, out, err = sh(args)
    i = out.find("{")
    return json.loads(out[i:]) if i >= 0 else {"_err": err[-300:]}


def load(p, d):
    return json.load(open(p)) if os.path.exists(p) else d


def gallery(article, cache):
    if article in cache:
        return cache[article]
    rc, out, _ = sh([os.path.join(ROOT, "scripts/trixie-image.sh"), article])
    urls = [u for u in out.splitlines() if u.startswith("http")]
    cache[article] = urls; json.dump(cache, open(URLS, "w"), indent=1)
    time.sleep(0.8)
    return urls


def upload(url):
    rc, out, err = sh([os.path.join(ROOT, "scripts/upload-media.sh"), url], timeout=600)
    last = out.splitlines()[-1] if out else ""
    return int(last) if re.fullmatch(r"\d+", last) else None


def main():
    dry = "--dry-run" in sys.argv
    only = {int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")} if "--only" in sys.argv else None
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    urlcache, state = load(URLS, {}), load(STATE, {"done": [], "problems": []})
    ids, page = [], 1
    while True:
        d = api("GET", f"/products?page={page}"); ids += [p["id"] for p in d.get("data", [])]
        if page >= (d.get("meta") or {}).get("last_page", 1): break
        page += 1
    n = 0
    for pid in sorted(set(ids)):
        if only and pid not in only: continue
        if not dry and pid in state["done"]: continue
        p = api("GET", f"/products/{pid}").get("data") or {}
        if p.get("brand_id") != TRIXIE: continue
        variants, changed, report = [], False, []
        for v in p.get("variants", []):
            nv = {k: v.get(k) for k in VKEYS if k in v}
            nv["images"] = list(nv.get("images") or []); nv["attribute_value_ids"] = nv.get("attribute_value_ids") or {}
            art = re.sub(r"tx$", "", v["sku"], flags=re.I)
            urls = gallery(art, urlcache)
            if not urls:
                report.append(f"{v['sku']}: no gallery"); variants.append(nv); continue
            if dry:
                report.append(f"{v['sku']}: {len(nv['images'])} → {len(urls)} imgs"); variants.append(nv); continue
            new_ids = []
            for u in urls:
                mid = upload(u)
                if mid: new_ids.append(mid)
                else: state["problems"].append((pid, v["sku"], u, "upload failed"))
            existing = nv["images"]
            # gallery order wins (trixie-image.sh ranks the packshot first): the
            # feature image must be a clean product shot (CLAUDE.md rule 7). The old
            # "keep the existing first image first" rule left a cat-playing photo as
            # the thumbnail of product 315 (2026-09-10). Existing images that are
            # not in the gallery go last; scripts/feature-image.py re-ranks by
            # filename afterwards if needed.
            ordered = list(new_ids) + [i for i in existing if i not in new_ids]
            if ordered != existing:
                nv["images"] = ordered; changed = True
            report.append(f"{v['sku']}: {len(existing)} → {len(ordered)} imgs")
            variants.append(nv)
        if changed and not dry:
            body = {k: p.get(k) for k in KEEP}; body["variants"] = variants
            api("PUT", f"/products/{pid}", body)
            back = api("GET", f"/products/{pid}").get("data") or {}
            ok = [len(x.get("images") or []) for x in back.get("variants", [])] == [len(x["images"]) for x in variants]
            if not ok: state["problems"].append((pid, "verify", "image counts differ after PUT"))
        if not dry:
            state["done"].append(pid); json.dump(state, open(STATE, "w"), indent=1)
        print(f"{pid:>4} {p.get('name','')[:36]:<36} {'; '.join(report)}", flush=True)
        n += 1
        if limit and n >= limit: break
    print("problems:", state["problems"] if state["problems"] else "none")


if __name__ == "__main__":
    main()
