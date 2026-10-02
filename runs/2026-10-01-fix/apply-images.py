#!/usr/bin/env python3
"""Upload approved replacement photos and set them as the variant's gallery.

upload-<g>.json: [{product, variant, sku, folder, files:[local], replaces:[media ids]}]
The bag's by-weight twin `<sku>-KG` gets the same gallery (the one allowed share).
Uploads go through scripts/upload-media.sh (verified, into the folder the old picture
lived in); the gallery write through galleries.py. State in applied-<g>.json (resumable).

    apply-images.py <g> [--write]
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ENV = dict(os.environ, SIRUK_API="https://api.siruk.am/api/admin",
           SIRUK_TOKEN_FILE=os.path.join(ROOT, ".siruk-token-prod"))
g = sys.argv[1]
WRITE = "--write" in sys.argv
items = json.load(open(os.path.join(HERE, f"upload-{g}.json")))
SF = os.path.join(HERE, f"applied-{g}.json")
state = json.load(open(SF)) if os.path.exists(SF) else {}
snap = {}
for f in os.listdir(os.path.join(HERE, "snapshot")):
    d = json.load(open(os.path.join(HERE, "snapshot", f)))
    snap[d["id"]] = d
plan = {}
for it in items:
    key = str(it["variant"])
    ids = state.get(key)
    if ids is None:
        if not WRITE:
            print("would upload", it["files"], "→", it["folder"]); continue
        ids = []
        for f in it.get("files", []):
            r = subprocess.run([os.path.join(ROOT, "scripts/upload-media.sh"), os.path.join(HERE, f), it["folder"]],
                               capture_output=True, text=True, cwd=ROOT, env=ENV)
            mid = (r.stdout.strip().splitlines() or [""])[-1]
            if r.returncode or not mid.isdigit():
                sys.exit(f"upload failed {f}: {r.stderr[-400:]}")
            ids.append(int(mid))
        state[key] = ids
        json.dump(state, open(SF, "w"), indent=1)
    pl = plan.setdefault(str(it["product"]), {})
    pl[it["sku"]] = ids + [m for m in it.get("keep", []) if m not in ids]   # keep = existing ids after the new ones
    twin = f"{it['sku']}-KG"
    if any(v["sku"] == twin for v in snap[it["product"]]["variants"]):
        pl[twin] = pl[it["sku"]]
pf = os.path.join(HERE, f"plan-images-{g}.json")
json.dump(plan, open(pf, "w"), indent=1)
if WRITE:
    r = subprocess.run([sys.executable, os.path.join(HERE, "galleries.py"), pf, "--write"], env=ENV, cwd=ROOT)
    sys.exit(r.returncode)
