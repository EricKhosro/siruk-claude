#!/usr/bin/env python3
"""Move every product image into `products/<brand-slug>/<type>/`, brand logos
into `logos/` and category tiles into `categories/` (CLAUDE.md rule 7, layout
set by the user 2026-09-23). Page banners go in `banners/` by hand — nothing in
the API says which root file is a banner.

    scripts/organize-media.py                 # dry run: prints the plan
    scripts/organize-media.py --apply         # create folders + move
    scripts/organize-media.py --apply --only products/trixie/toys   # one folder (pilot)

Reads the catalogue from .siruk-cache/catalogue-snapshot.json (refresh it first
with scripts/catalogue-snapshot.py if products changed since). Type = the
product's attribute family code (dry-food, wet-food, treats, supplements, toys,
grooming, accessories, litter).

Moves go through `POST /medias-move {ids, directory}` — the admin's own bulk
move (siruk-web backend MediaController::move, route `medias-move`). The media id stays the
same, so products keep their images; only the original's storage url changes
(the webp and admin thumbnail live in webp/ and thumbnails/ and do not move).
Idempotent: each target folder is listed first and what is already there is
skipped, so a re-run only moves the rest (a text/html-typed file never shows in
the listing, so it is simply moved again into the same folder).

An image shared by products of two brands/types goes where most of its products
are, and is logged. Anything else in the root (site content: blog, landing,
about-us) is reported, never moved. Output: runs/<date>/media-reorg/.
"""
import collections, datetime, importlib.util, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("mf", os.path.join(ROOT, "scripts/media-folder.py"))
mf = importlib.util.module_from_spec(spec); spec.loader.exec_module(mf)

SNAP = os.path.join(ROOT, ".siruk-cache/catalogue-snapshot.json")
OUT = os.path.join(ROOT, "runs", datetime.date.today().isoformat(), "media-reorg")
CHUNK = 50


def main():
    apply = "--apply" in sys.argv
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    os.makedirs(OUT, exist_ok=True)

    snap = json.load(open(SNAP))
    fams = {f["id"]: f.get("code") or mf.slugify(f["name"])
            for f in mf.api("GET", "/attribute-families?forProducts=true")["data"]}
    brands = mf.api("GET", "/brands?forProducts=true")["data"]
    bslug = {b["id"]: mf.slugify(b["name"]) for b in brands}

    # media id -> Counter(target dir) over every product using it
    votes = collections.defaultdict(collections.Counter)
    problems = []
    for p in snap.values():
        b, t = bslug.get(p.get("brand_id")), fams.get(p.get("attribute_family_id"))
        if not b or not t:
            problems.append({"product": p["id"], "why": f"brand {p.get('brand_id')} / family {p.get('attribute_family_id')} unmapped"})
            continue
        for v in p["variants"]:
            for mid in v["image_ids"]:
                if mid:
                    votes[mid][f"products/{b}/{t}"] += 1

    target = {mid: c.most_common(1)[0][0] for mid, c in votes.items()}
    shared = [{"media": mid, "to": target[mid], "also": sorted(set(c) - {target[mid]})}
              for mid, c in votes.items() if len(c) > 1]

    for b in brands:
        if b.get("image"):
            target.setdefault(b["image"], "logos")
    cats = json.dumps(mf.api("GET", "/categories"))
    for mid in {int(x) for x in re.findall(r'"(?:image|icon|banner|meta_image)"\s*:\s*(\d+)', cats)}:
        target.setdefault(mid, "categories")

    by_dir = collections.defaultdict(list)
    for mid, d in target.items():
        by_dir[d].append(mid)
    if only:
        by_dir = {only: by_dir.get(only, [])}

    root = mf.list_dir("")
    leftover = [{"id": m["id"], "filename": m.get("filename"), "isUsed": m.get("isUsed")}
                for m in root if m["id"] not in target]

    print(f"{sum(len(v) for v in by_dir.values())} media → {len(by_dir)} folders; "
          f"{len(shared)} shared across folders; {len(leftover)} root files not product/logo/category "
          f"(left alone); {len(problems)} unmapped products", file=sys.stderr)
    json.dump({"folders": {d: sorted(v) for d, v in sorted(by_dir.items())}, "shared": shared,
               "problems": problems, "left_in_root": leftover},
              open(os.path.join(OUT, "plan.json"), "w"), indent=1)
    if not apply:
        for d, v in sorted(by_dir.items()):
            print(f"{len(v):5d}  {d}")
        return

    log = open(os.path.join(OUT, "moves.jsonl"), "a")
    idx = mf.folder_index()
    moved = failed = skipped = 0
    for d, ids in sorted(by_dir.items()):
        idx = mf.ensure(d, idx)
        there = {m["id"] for m in mf.list_dir(d)}
        todo = [i for i in ids if i not in there]
        skipped += len(ids) - len(todo)
        for k in range(0, len(todo), CHUNK):
            chunk = todo[k:k + CHUNK]
            try:
                res = mf.api("POST", "/medias-move", {"ids": chunk, "directory": d})
                ok = {m["id"] for m in res.get("data", []) if m.get("directory") == d}
            except RuntimeError as e:
                print(f"  ! chunk into {d} failed ({e}); moving one by one", file=sys.stderr)
                ok = set()
                for i in chunk:
                    try:
                        r = mf.api("POST", "/medias-move", {"ids": [i], "directory": d})
                        ok |= {m["id"] for m in r.get("data", []) if m.get("directory") == d}
                    except RuntimeError as e1:
                        log.write(json.dumps({"media": i, "to": d, "error": str(e1)[-300:]}) + "\n")
            for i in chunk:
                log.write(json.dumps({"media": i, "to": d, "ok": i in ok}) + "\n")
            moved += len(ok); failed += len(chunk) - len(ok)
        log.flush()
        print(f"  {d}: {len(todo)} to move, {len(ids) - len(todo)} already there", file=sys.stderr)
    print(f"moved {moved}, already in place {skipped}, failed {failed} — log {OUT}/moves.jsonl",
          file=sys.stderr)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
