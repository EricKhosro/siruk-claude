#!/usr/bin/env python3
"""Apply reference/complement-categories.json to the live categories ("Goes well with categories").

    scripts/set-complements.py              # dry run: resolve every path, show what would change
    scripts/set-complements.py --apply      # PUT the changed categories, read each back

The map is keyed by category path ("Dog > Food > Dry Food"); every path must resolve against the
live tree or nothing is written. A category not in the map is left alone (its list is never
cleared), so a list the PM set by hand on another category survives.

The category PUT (CategoryController::update) validates name + slug as required and fills only the
keys a request carries — EXCEPT list_as_products, which it reads with $request->boolean() and so
resets to false when absent. The body is therefore exactly
  {name, slug, parent_id, list_as_products, complement_category_ids}
copied from a fresh GET (en; no Content-Language → the en name is rewritten unchanged). No
description, image, meta or pinned_product_ids is sent, so those stay as they are (SEO only syncs
when meta is in the request; pins only when pinned_product_ids is).
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import api  # noqa: E402

MAP = os.path.join(ROOT, "reference", "complement-categories.json")


def tree():
    by_path, by_id = {}, {}

    def walk(n, trail):
        path = " > ".join(trail + [n["name"]])
        by_path[path] = n["id"]
        by_id[n["id"]] = {"path": path, "complements": n.get("complement_category_ids") or [],
                          "count": n.get("productsCount")}
        for c in n.get("children") or []:
            walk(c, trail + [n["name"]])
    for n in api("GET", "/categories")["data"]:
        walk(n, [])
    return by_path, by_id


def main(argv):
    by_path, by_id = tree()
    spec = json.load(open(MAP))["map"]
    errs, plan = [], []
    for src, targets in spec.items():
        if src not in by_path:
            errs.append(f"unknown category '{src}'")
            continue
        ids = []
        for t in targets:
            if t not in by_path:
                errs.append(f"{src}: unknown target '{t}'")
            elif by_path[t] == by_path[src]:
                errs.append(f"{src}: points at itself")
            elif t.split(" > ")[0] != src.split(" > ")[0]:
                errs.append(f"{src}: target '{t}' is another pet — the cart only searches the cart's own pet trees")
            else:
                ids.append(by_path[t])
        cid = by_path[src]
        if by_id[cid]["complements"] != ids:
            plan.append((cid, src, by_id[cid]["complements"], ids))
    if errs:
        sys.exit("refusing to write:\n  " + "\n  ".join(errs))
    unmapped = [p for p, i in by_path.items() if i not in {by_path[s] for s in spec}
                and not any(q.startswith(p + " > ") for q in by_path) and p.count(" > ") >= 1]
    for cid, src, old, new in plan:
        names = ", ".join(f"{by_id[i]['path'].split(' > ', 1)[1]} ({by_id[i]['count']})" for i in new)
        print(f"{cid:>4} {src}: {old or '—'} → {new}  [{names}]")
    print(f"\n{len(plan)} categories to change, {len(spec) - len(plan)} already as mapped.")
    if unmapped:
        print(f"leaves with no row in the map (left alone): {unmapped}")
    if "--apply" not in argv:
        print("dry run — nothing written (--apply to write)")
        return
    failed = 0
    for cid, src, old, new in plan:
        c = api("GET", f"/categories/{cid}")["data"]
        body = {"name": c["name"], "slug": c["slug"], "parent_id": c.get("parent_id"),
                "list_as_products": bool(c.get("list_as_products")), "complement_category_ids": new}
        api("PUT", f"/categories/{cid}", body)
        back = api("GET", f"/categories/{cid}")["data"]
        same = all(back.get(k) == c.get(k) for k in ("name", "slug", "parent_id", "list_as_products",
                                                    "image", "featured_image", "meta", "pinned_product_ids"))
        if back.get("complement_category_ids") != new or not same:
            failed += 1
            print(f"  {cid} {src}: READ-BACK MISMATCH", file=sys.stderr)
        subprocess.run([os.path.join(ROOT, "scripts/pace.sh"), "api"], cwd=ROOT)
    print(f"applied {len(plan) - failed}, {failed} mismatches", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
