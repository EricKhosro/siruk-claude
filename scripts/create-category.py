#!/usr/bin/env python3
"""Create admin categories from a spec file, idempotently.

Categories are created ONLY on an explicit user ask (CLAUDE.md rule 8) — this
script is the mechanism, not the permission. It dedupes on (parent_id, name):
an existing category with that name under that parent is reused, never
duplicated. Slugs follow the live convention `<pet>-<parent>-<leaf>`.

    scripts/create-category.py spec.json [--dry-run]

spec.json: [{"parent": null | 1 | "Dog > Supplies", "name": "...", "slug": "...",
             "meta_title": "..."}, ...]  — parents are created before children
when listed first, and a later entry may name an earlier one by path.

After creating, add the ru/hy pair to scripts/translate-categories.py and run
it (CLAUDE.md rule 13).
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = os.path.join(ROOT, "scripts", "api.sh")


def api(method, path, payload=None):
    cmd = [API, method, path]
    inp = None
    if payload is not None:
        cmd.append("-")
        inp = json.dumps(payload)
    r = subprocess.run(cmd, input=inp, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"API {method} {path} failed:\n{r.stderr}\n{r.stdout}")
    return json.loads(r.stdout)


def tree():
    """Flat {id: {...}} plus {'Dog > Supplies': id} path index."""
    data = api("GET", "/categories?forProducts=true")["data"]
    flat, paths = {}, {}

    def walk(nodes, prefix):
        for n in nodes:
            path = f"{prefix} > {n['name']}" if prefix else n["name"]
            flat[n["id"]] = {"name": n["name"], "parent_id": n.get("parent_id"), "path": path}
            paths[path] = n["id"]
            walk(n.get("children") or [], path)

    walk(data, "")
    return flat, paths


def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry = "--dry-run" in sys.argv
    if len(args) != 1:
        sys.exit(__doc__)
    spec = json.load(open(args[0]))
    flat, paths = tree()
    fake = 0

    for e in spec:
        p = e["parent"]
        if p is None:  # a new top-level pet (Bird, Small Animal — 2026-09-28)
            parent_id, full = None, e["name"]
        else:
            parent_id = p if isinstance(p, int) else paths.get(p)
            if parent_id is None:
                sys.exit(f"parent not found: {p!r} (for {e['name']!r})")
            full = f"{flat[parent_id]['path']} > {e['name']}"
        if full in paths:
            print(f"  exists  {paths[full]:>3}  {full}")
            continue
        body = {
            "parent_id": parent_id,
            "name": e["name"],
            "slug": e["slug"],
            "description": "",
            "quick_links": [],
            "meta": {"title": e.get("meta_title", e["name"]),
                     "description": e.get("meta_title", e["name"])},
        }
        if dry:
            print(f"  DRY     ---  {full}   slug={e['slug']}")
            fake -= 1
            paths[full] = fake
            flat[fake] = {"name": e["name"], "parent_id": parent_id, "path": full}
            continue
        res = api("POST", "/categories", body)
        new = res.get("data", res)
        nid = new["id"]
        paths[full] = nid
        flat[nid] = {"name": e["name"], "parent_id": parent_id, "path": full}
        print(f"  created {nid:>3}  {full}   slug={e['slug']}")


if __name__ == "__main__":
    main()
