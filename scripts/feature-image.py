#!/usr/bin/env python3
"""Feature-image audit: make sure variant.images[0] is a CLEAN product shot.

CLAUDE.md rule 7: the first image (storefront thumbnail + hero) must show the
product alone / in its own pack on a plain background — no animal, no hand, no
scene, no group of siblings. A lifestyle or group shot may lead only when the
product has nothing clean at all; those go to needs-packshot.csv for the user.

Classification is by the media FILENAME. Two conventions are known —
Trixie's CDN prefixes and Champion Petfoods' (Acana / Orijen) view-in-the-name:
    PHO_PRO_CLIP_*   packshot   rank 1   clean
    PHO_PAC_CLIP_*   pack       rank 2   clean
    PHO_PRO_GROUP*   group      rank 4   not clean
    GRA_*            drawing    rank 5   not clean
    PHO_PRO_<other>  lifestyle  rank 3   not clean (DOG/CAT/… = animal playing)
    *Front Right*    packshot   rank 1   clean    (Champion: bag alone on white)
    *Back*           pack       rank 2   clean    (Champion: back of the same bag)
    *Bowl/Features/New Look*    lifestyle  rank 3   not clean (Champion graphics)
    anything else    unknown    rank 3   must be checked by eye (--sheet)
Filenames are the ones the media library stores; nothing is guessed from a
product name. Reordering only moves ids around — no image is dropped or added.

    scripts/feature-image.py                      # audit, print a table, write CSVs
    scripts/feature-image.py --apply              # also PUT the reordered products
    scripts/feature-image.py --sheet              # also write an HTML contact sheet
                                                  # of every feature image (open it
                                                  # in the browser, screenshot, look)
    scripts/feature-image.py --only 315,316       # restrict to products
    scripts/feature-image.py --out runs/2026-09-10

Outputs (in --out, default runs/<today>/):
    feature-images.csv    every variant: order before/after, class of the leader
    needs-packshot.csv    variants whose leader is still not a clean shot
    feature-sheet.html    (--sheet) thumbnails of every leader, flagged ones red
Media filenames are cached in .siruk-cache/media-filenames.json (id → filename).
Writes go through the same GET → rebuild → PUT shape as add-all-images.py; PUT
replaces the whole variants array, so every variant key is carried over verbatim.
"""
import csv, datetime, html, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
NAMES = os.path.join(CACHE, "media-filenames.json")
VKEYS = ("id", "name", "about_this_item", "ingredient_information", "feeding_instructions", "pricing_type", "sku",
         "price", "price_per_kg", "min_allowed_price", "cost_price", "compare_at_price", "weight", "is_default",
         "stock", "vendor_stock", "sort_order", "images", "attribute_value_ids")
KEEP = ("name", "slug", "category_ids", "brand_id", "attribute_family_id", "is_best_seller", "is_on_sale", "is_discontinued")
CLEAN = {"packshot", "pack"}


def sh(args, timeout=300):
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=timeout)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def api(method, path, payload=None):
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "_feat.json"); json.dump(payload, open(p, "w"), ensure_ascii=False); args.append(p)
    rc, out, err = sh(args)
    i = out.find("{")
    return json.loads(out[i:]) if i >= 0 else {"_err": err[-300:]}


def classify(fname):
    f = fname or ""
    # Trixie CDN convention
    if re.match(r"PHO_PRO_CLIP_", f): return "packshot", 1
    if re.match(r"PHO_PAC_CLIP_", f): return "pack", 2
    if re.match(r"PHO_PRO_GROUP", f): return "group", 4
    if re.match(r"GRA_", f): return "drawing", 5
    if re.match(r"PHO_PRO_[A-Z]+_", f): return "lifestyle", 3
    # Champion Petfoods (Acana / Orijen, emea.*.com) name the view in the file:
    # "… Front Right 6kg EMEA APAC", "… Back 9.7kg …". Both are the bag alone on
    # white. "Bowl Image" / "Features" / "Key Features" / "New Look" are graphics.
    # Verified by eye 2026-09-11 across the 23-product Acana/Orijen import.
    if re.search(r"(?i)\bfront[-_ ]?(right|left)?\b", f): return "packshot", 1
    if re.search(r"(?i)\bback\b", f): return "pack", 2
    if re.search(r"(?i)\b(bowl|key[-_ ]?features?|features?|new[-_ ]?look|benefits|wholeprey|ingredients)\b", f):
        return "lifestyle", 3
    return "unknown", 3


def main():
    argv = sys.argv[1:]
    apply = "--apply" in argv; sheet = "--sheet" in argv
    only = {int(x) for x in argv[argv.index("--only") + 1].split(",")} if "--only" in argv else None
    out = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(ROOT, "runs", datetime.date.today().isoformat())
    os.makedirs(out, exist_ok=True)
    names = json.load(open(NAMES)) if os.path.exists(NAMES) else {}

    def media(mid):
        k = str(mid)
        if k not in names:
            d = api("GET", f"/medias/{mid}").get("data") or {}
            names[k] = {"filename": d.get("filename") or "", "url": d.get("url") or ""}
            json.dump(names, open(NAMES, "w"), indent=1)
        return names[k]

    ids, page = [], 1
    while True:
        d = api("GET", f"/products?page={page}"); ids += [p["id"] for p in d.get("data", [])]
        if page >= (d.get("meta") or {}).get("last_page", 1): break
        page += 1

    rows, flagged, tiles, changed_products = [], [], [], 0
    for pid in sorted(set(ids)):
        if only and pid not in only: continue
        p = api("GET", f"/products/{pid}").get("data") or {}
        if not p: continue
        variants, changed = [], False
        for v in p.get("variants", []):
            nv = {k: v.get(k) for k in VKEYS if k in v}
            nv["attribute_value_ids"] = nv.get("attribute_value_ids") or {}
            before = list(nv.get("images") or [])
            info = [(mid, media(mid)) for mid in before]
            ranked = sorted(info, key=lambda t: classify(t[1]["filename"])[1])  # stable: ties keep source order
            after = [mid for mid, _ in ranked]
            lead = ranked[0][1] if ranked else {"filename": "", "url": ""}
            cls = classify(lead["filename"])[0] if ranked else "none"
            status = "ok" if cls in CLEAN else ("no-images" if not ranked else ("single-image" if len(after) == 1 else "needs-packshot"))
            if after != before:
                nv["images"] = after; changed = True
            rows.append({"product_id": pid, "product": p.get("name", ""), "variant_id": v.get("id"), "sku": v.get("sku"),
                         "images_before": " ".join(map(str, before)), "images_after": " ".join(map(str, after)),
                         "leader_file": lead["filename"], "leader_class": cls, "status": status,
                         "reordered": "yes" if after != before else "no"})
            if status != "ok":
                flagged.append({"product_id": pid, "product": p.get("name", ""), "variant_id": v.get("id"), "sku": v.get("sku"),
                                "leader_file": lead["filename"], "leader_class": cls, "image_count": len(after),
                                "all_files": " | ".join(m["filename"] for _, m in ranked), "reason": status})
            tiles.append((pid, p.get("name", ""), v.get("sku"), lead["url"], cls, status, len(after)))
            variants.append(nv)
        if changed:
            changed_products += 1
            if apply:
                body = {k: p.get(k) for k in KEEP}; body["variants"] = variants
                r = api("PUT", f"/products/{pid}", body)
                back = api("GET", f"/products/{pid}").get("data") or {}
                got = {x.get("id"): list(x.get("images") or []) for x in back.get("variants", [])}
                want = {x.get("id"): list(x.get("images") or []) for x in variants}
                mark = "applied ✓" if got == want else f"applied ✗ readback differs {r.get('_err','')}"
            else:
                mark = "would reorder"
        else:
            mark = ""
        bad = [r_ for r_ in rows if r_["product_id"] == pid and r_["status"] != "ok"]
        print(f"{pid:>4} {p.get('name','')[:34]:<34} {mark:<14} {'FLAG ' + bad[0]['leader_class'] if bad else ''}", flush=True)

    with open(os.path.join(out, "feature-images.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["product_id"]); w.writeheader(); w.writerows(rows)
    with open(os.path.join(out, "needs-packshot.csv"), "w", newline="") as f:
        cols = ["product_id", "product", "variant_id", "sku", "leader_file", "leader_class", "image_count", "all_files", "reason"]
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(flagged)
    if sheet:
        cells = []
        for pid, name, sku, url, cls, status, n in tiles:
            col = "#c00" if status != "ok" else "#2a7"
            cells.append(f'<figure style="border:3px solid {col}"><img src="{html.escape(url)}" loading="eager">'
                         f'<figcaption><b>{pid}</b> {html.escape(sku or "")} · {cls} · {n} img<br>{html.escape(name[:38])}</figcaption></figure>')
        doc = ('<!doctype html><meta charset="utf-8"><title>feature images</title><style>body{margin:8px;font:11px system-ui}'
               '.g{display:grid;grid-template-columns:repeat(6,1fr);gap:6px}figure{margin:0;background:#fff}'
               'img{width:100%;aspect-ratio:1;object-fit:contain;background:#fff;display:block}figcaption{padding:3px}</style>'
               f'<p>{len(tiles)} variants · {len(flagged)} flagged (red) · green = filename says clean shot</p><div class="g">{"".join(cells)}</div>')
        open(os.path.join(out, "feature-sheet.html"), "w").write(doc)
    print(f"\n{len(rows)} variants in {len(set(r['product_id'] for r in rows))} products · "
          f"{sum(r['reordered']=='yes' for r in rows)} variants / {changed_products} products {'reordered' if apply else 'to reorder'} · "
          f"{len(flagged)} flagged → {out}/needs-packshot.csv")


if __name__ == "__main__":
    main()
