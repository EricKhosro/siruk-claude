#!/usr/bin/env python3
"""Cache the live reference ids that prepare-run.py and validate-card.py check
against: brands, the category tree (with leaves), attribute families.

    scripts/live-ids.py            # -> .siruk-cache/live-ids.json (3 GETs)

Also importable: `load(max_age_h=12)` returns the cache, refetching when it is
missing or older than max_age_h.
"""
import json, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, ".siruk-cache", "live-ids.json")


def api(path):
    r = subprocess.run([os.path.join(ROOT, "scripts/api.sh"), "GET", path],
                       capture_output=True, text=True, cwd=ROOT, timeout=180)
    i = r.stdout.find("{")
    if i < 0:
        sys.exit(f"live-ids: GET {path} failed:\n{r.stdout[-400:]}{r.stderr[-400:]}")
    return json.loads(r.stdout[i:])


def fetch():
    brands = {str(b["id"]): b["name"] for b in api("/brands?forProducts=true")["data"]}
    cats = {}

    def walk(nodes, parent, root):
        for c in nodes:
            kids = c.get("children") or []
            r = root or c["id"]
            cats[str(c["id"])] = {"name": c["name"], "parent": parent, "species_root": r,
                                  "leaf": not kids}
            walk(kids, c["id"], r)
    walk(api("/categories?forProducts=true")["data"], None, None)
    fams = {str(f["id"]): {"code": f.get("code"), "name": f.get("name"),
                           "attrs": [a["code"] for a in f.get("attributes") or []]}
            for f in api("/attribute-families?forProducts=true")["data"]}
    d = {"fetched": time.strftime("%Y-%m-%d %H:%M"), "brands": brands,
         "categories": cats, "families": fams}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(d, open(OUT, "w"), ensure_ascii=False, indent=1)
    return d


def load(max_age_h=12):
    if os.path.exists(OUT) and time.time() - os.path.getmtime(OUT) < max_age_h * 3600:
        return json.load(open(OUT))
    return fetch()


if __name__ == "__main__":
    d = fetch()
    print(f"live-ids: {len(d['brands'])} brands, {len(d['categories'])} categories "
          f"({sum(c['leaf'] for c in d['categories'].values())} leaves), "
          f"{len(d['families'])} families -> {os.path.relpath(OUT, ROOT)}")
