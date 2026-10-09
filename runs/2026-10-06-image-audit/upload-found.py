#!/usr/bin/env python3
"""Upload accepted sourced photos (found/<group>.json, status found) to PRODUCTION media library,
into the folder the variant's current images live in (products/<brand>/<type>), and record
found-uploaded.json {sku: [media ids in gallery order]} for apply-plan.py.

    upload-found.py found/acana.json [...] [--only sku,sku] [--write]
"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
ENV = dict(os.environ, SIRUK_API="https://api.siruk.am/api/admin", SIRUK_TOKEN_FILE=os.path.join(ROOT, ".siruk-token-prod"))
WRITE = "--write" in sys.argv
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
files = [a for a in sys.argv[1:] if a.endswith(".json")]
snap = json.load(open(os.path.join(HERE, "products.json")))
media = {}
import csv
for r in csv.DictReader(open(os.path.join(HERE, "images.csv"))): media[r["media"]] = r["dir"]
SF = os.path.join(HERE, "found-uploaded.json")
state = json.load(open(SF)) if os.path.exists(SF) else {}
for f in files:
    for e in json.load(open(f)):
        if e.get("status") != "found" or (ONLY and e["sku"] not in ONLY): continue
        if e["sku"] in state: print("already", e["sku"], state[e["sku"]]); continue
        p = snap[str(e["product_id"])]
        v = next(v for v in p["variants"] if v["sku"] == e["sku"])
        folder = next((media.get(str(m)) for m in (v.get("images") or []) if media.get(str(m))), None) \
                 or next((media.get(str(m)) for vv in p["variants"] for m in (vv.get("images") or []) if media.get(str(m))), None)
        paths = [os.path.join(HERE, i["file"]) if not i["file"].startswith("/") else i["file"] for i in e["images"]]
        if not folder: sys.exit(f"no folder for {e['sku']}")
        if not WRITE:
            print(f"{e['product_id']} {e['sku']}: would upload {len(paths)} → {folder}"); continue
        ids = []
        for pth in paths:
            r = subprocess.run([os.path.join(ROOT, "scripts/upload-media.sh"), pth, folder], capture_output=True, text=True, cwd=ROOT, env=ENV)
            mid = (r.stdout.strip().splitlines() or [""])[-1]
            if r.returncode or not mid.isdigit(): sys.exit(f"upload failed {pth}: {r.stdout[-300:]} {r.stderr[-300:]}")
            ids.append(int(mid))
        state[e["sku"]] = ids; json.dump(state, open(SF, "w"), indent=1)
        print(f"{e['product_id']} {e['sku']}: uploaded {ids} → {folder}")
