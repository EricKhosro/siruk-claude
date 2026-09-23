#!/usr/bin/env python3
"""Rename products that outgrew a single variant.

A product imported from one row often carries the row's axis in its Name
("Flash USB Light Collar, nylon, M–L: 40–50 cm/25 mm, red", "Mini Adult Chicken
& Rice 800 g"). Once a sibling is added the Name must be the LINE name and the
axis lives in the labels (reference/product-rules.md → Name, slug, label).

Two sources of the new name, in order:
  1. `rename_to` on a plan product (scripts/archive/plan-register-food.py wrote it
     next to `existing_id`), passed with --plan;
  2. the Name minus its own first variant's label when the Name ends with
     that label (the same cut scripts/find-duplicate-products.py makes).
Products with one variant are never touched. ru/hy names are re-cut the same
way (drop the same trailing comma segments) and written with
scripts/set-translation.py; a translated name that cannot be cut cleanly is
listed for a hand-written one.

    scripts/fix-outgrown-names.py [--plan plan.json …] [--ids …] [--apply]
"""
import argparse, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")


def api(method, path, payload=None, lang=None):
    env = dict(os.environ)
    if lang:
        env["SIRUK_LANG"] = lang
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "_rename.json")
        json.dump(payload, open(p, "w"), ensure_ascii=False)
        args.append(p)
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=120, env=env)
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:]) if i >= 0 else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", nargs="*", default=[])
    ap.add_argument("--ids", nargs="*", default=[])
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    snap = json.load(open(os.path.join(CACHE, "catalogue-snapshot.json")))
    wanted = {}
    for pf in a.plan:
        for p in json.load(open(pf))["products"]:
            if p.get("existing_id") and p.get("rename_to"):
                wanted[int(p["existing_id"])] = p["rename_to"]
    ids = {int(x) for x in a.ids} | set(wanted)
    todo = []
    for pid, p in snap.items():
        pid = int(pid)
        if ids and pid not in ids:
            continue
        if len(p["variants"]) < 2:
            continue
        name = p["name"]
        new = wanted.get(pid)
        if not new:
            lbl = (p["variants"][0].get("label") or "").strip()
            if lbl and name.endswith(lbl) and len(name) > len(lbl):
                new = name[: len(name) - len(lbl)].rstrip(" ,–-:")
        if new and new != name:
            todo.append((pid, name, new, p))
    print(f"{len(todo)} product(s) to rename", file=sys.stderr)
    for pid, old, new, p in todo:
        print(f"  {pid}: {old!r} -> {new!r}", file=sys.stderr)
    if not a.apply:
        return
    for pid, old, new, p in todo:
        r = subprocess.run([os.path.join(ROOT, "scripts/rename-product.sh"), str(pid), new],
                           capture_output=True, text=True, cwd=ROOT, timeout=300)
        print(f"  {'ok ' if r.returncode == 0 else 'BAD'} en {pid}: {new}" + ("" if r.returncode == 0 else (r.stderr or r.stdout)[-160:]), file=sys.stderr)
        # translated names: drop as many trailing comma segments as the English lost
        drop = len([x for x in old[len(new):].split(",") if x.strip()])
        for lang in ("ru", "hy"):
            cur = (api("GET", f"/products/{pid}", lang=lang).get("data") or {}).get("name") or ""
            parts = cur.split(",")
            if drop and len(parts) > drop and cur != new:
                cut = ",".join(parts[:-drop]).strip(" ,–-:")
                tf = os.path.join(CACHE, f"_rename-{pid}-{lang}.json")
                json.dump({"name": cut}, open(tf, "w"), ensure_ascii=False)
                r = subprocess.run([os.path.join(ROOT, "scripts/set-translation.py"), str(pid), lang, tf],
                                   capture_output=True, text=True, cwd=ROOT, timeout=300)
                print(f"  {'ok ' if r.returncode == 0 else 'BAD'} {lang} {pid}: {cur!r} -> {cut!r}", file=sys.stderr)
            else:
                print(f"  ?? {lang} {pid}: {cur!r} — write the {lang} line name by hand", file=sys.stderr)


if __name__ == "__main__":
    main()
