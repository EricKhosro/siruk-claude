#!/usr/bin/env python3
"""Give every product its attribute family, decided by the categories it is in.

A product with `attribute_family_id: null` serves **no attribute facets at
all** on the storefront, even for attributes its own variants carry
(`reference/product-rules.md`). Grooming, Accessories and Litter products had
none because those three families did not exist until 2026-09-15.

`PUT /products/<id>` replaces the whole record, so this rebuilds the body from a
fresh `GET` and changes exactly one key — the same shape and guards as
`set-variant.sh`. It refuses to write if a variant would be lost.

    scripts/set-attribute-family.py --dry-run
    scripts/set-attribute-family.py --apply [--only 199,329]
"""
import argparse, collections, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")

# leaf category -> family. Ranges follow the tree in reference/admin-api.md.
RULES = [
    (set(range(27, 41)), 7, "Grooming"),
    (set(range(59, 66)), 9, "Litter"),
    (set(range(66, 82)), 8, "Accessories"),
    (set(range(17, 27)), 5, "Toys"),            # dog toys 17-22, cat toys 23-26
]


def api(method, path, payload=None):
    cmd = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "family-put.json")
        json.dump(payload, open(p, "w"), ensure_ascii=False)
        cmd.append(p)
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=180)
    i = r.stdout.find("{")
    if i < 0:
        raise SystemExit(f"{method} {path} failed:\n{r.stdout[-500:]}\n{r.stderr[-500:]}")
    return json.loads(r.stdout[i:])


def family_for(cats):
    for leaves, fid, name in RULES:
        if set(cats or []) & leaves:
            return fid, name
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", help="comma-separated product ids")
    a = ap.parse_args()

    snap = json.load(open(os.path.join(CACHE, "catalogue-snapshot.json")))
    todo, skipped = [], []
    for p in snap.values():
        if p.get("attribute_family_id"):
            continue
        fid, fname = family_for(p.get("category_ids"))
        if not fid:
            skipped.append(p)
            continue
        todo.append((int(p["id"]), fid, fname, p["name"], p["category_ids"]))
    todo.sort()
    if a.only:
        keep = {int(x) for x in a.only.split(",")}
        todo = [t for t in todo if t[0] in keep]

    print(f"{len(todo)} product(s) to set:", file=sys.stderr)
    for fid, n in collections.Counter((t[1], t[2]) for t in todo).items():
        print(f"   family {fid[0]} {fid[1]:<12} {n}", file=sys.stderr)
    for p in skipped:
        print(f"   ! no rule for p{p['id']} {p['name'][:40]} cats={p['category_ids']}",
              file=sys.stderr)
    if not a.apply:
        print("\ndry run — re-run with --apply", file=sys.stderr)
        return

    done = 0
    for pid, fid, fname, name, _cats in todo:
        cur = api("GET", f"/products/{pid}")["data"]
        body = {
            "name": cur["name"], "slug": cur["slug"],
            "category_ids": cur["category_ids"], "brand_id": cur.get("brand_id"),
            "attribute_family_id": fid,
            "is_best_seller": cur.get("is_best_seller", False),
            "is_on_sale": cur.get("is_on_sale", False),
            "is_discontinued": cur.get("is_discontinued", False),
            "variants": cur["variants"],
        }
        before_ids = sorted(v["id"] for v in cur["variants"])
        out = api("PUT", f"/products/{pid}", body)["data"]
        after_ids = sorted(v["id"] for v in out["variants"])
        if before_ids != after_ids:
            raise SystemExit(f"p{pid}: variants changed {before_ids} -> {after_ids} — STOPPING")
        if out.get("attribute_family_id") != fid:
            raise SystemExit(f"p{pid}: family did not stick ({out.get('attribute_family_id')})")
        done += 1
        print(f"  p{pid:>5} -> {fname:<12} ({len(after_ids)} variants kept)  {name[:40]}",
              file=sys.stderr)
    print(f"\n{done} product(s) updated", file=sys.stderr)


main()
