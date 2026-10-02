#!/usr/bin/env python3
"""Replace hafo photos on live production variants with the picks in image-plan.json.

For every variant with verdict "replace": upload its picked files (scripts/upload-media.sh,
verified readable) into the folder its hafo photo lives in, then set the gallery to
  new ids + the variant's other current images minus every hafo media id.
Twins (<sku>-KG) get the bag's new gallery. The gallery write goes through
runs/2026-10-01-fix/galleries.py (one PUT per product via siruk_payload, read back).

    apply.py            # dry run: uploads nothing, prints the plan
    apply.py --write
"""
import csv, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ENV = dict(os.environ, SIRUK_API="https://api.siruk.am/api/admin",
           SIRUK_TOKEN_FILE=os.path.join(ROOT, ".siruk-token-prod"))
os.environ.update(ENV)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import api  # noqa: E402

WRITE = "--write" in sys.argv
plan = json.load(open(os.path.join(HERE, "image-plan.json")))
hafo_rows = list(csv.DictReader(open(os.path.join(ROOT, "runs/2026-10-01-fix/still-hafo-images.csv"))))
hafo_media = {int(r["hafo_media"].split()[0]) for r in
              csv.DictReader(open(os.path.join(ROOT, "runs/2026-10-01-fix/hafo-images.csv"))) if r["hafo_media"]}
SF = os.path.join(HERE, "uploaded.json")
state = json.load(open(SF)) if os.path.exists(SF) else {}

prod_of = {}
for r in hafo_rows:
    prod_of[r["sku"]] = int(r["product_id"])

out = {}
for vid, e in plan.items():
    if e["verdict"] != "replace":
        print(f"{vid} {e['sku']}: {e['verdict']} — left as is ({e.get('note','')[:80]})")
        continue
    # the plan's variant id → product via the csv's variant link; a 1 kg twin (re-created
    # 2026-10-01, so not in the csv) is skipped here and copies its bag's gallery below
    pid = next((int(r["product_id"]) for r in hafo_rows if r["siruk_link"].rstrip("/").endswith(f"/{vid}")), None)
    if pid is None:
        print(f"{vid} {e['sku']}: twin — takes its bag's gallery")
        continue
    p = api("GET", f"/products/{pid}")["data"]
    v = next(x for x in p["variants"] if str(x["id"]) == str(vid))
    cur = [m["id"] if isinstance(m, dict) else m for m in v.get("images") or []]
    hafo_here = [m for m in cur if m in hafo_media]
    folder = None
    if hafo_here:
        folder = (api("GET", f"/medias/{hafo_here[0]}").get("data") or {}).get("directory")
    if not folder and cur:
        folder = (api("GET", f"/medias/{cur[0]}").get("data") or {}).get("directory")
    files = [i["file"] for i in e["images"]]
    key = "|".join(files)
    ids = state.get(key)
    if ids is None:
        if not WRITE:
            print(f"{pid}/{vid} {v['sku']}: would upload {files} → {folder}; current {cur}, drop hafo {hafo_here}")
            continue
        ids = []
        for f in files:
            r = subprocess.run([os.path.join(ROOT, "scripts/upload-media.sh"), os.path.join(ROOT, f), folder],
                               capture_output=True, text=True, cwd=ROOT, env=ENV)
            mid = (r.stdout.strip().splitlines() or [""])[-1]
            if r.returncode or not mid.isdigit():
                sys.exit(f"upload failed {f}: {r.stdout[-300:]} {r.stderr[-300:]}")
            ids.append(int(mid))
        state[key] = ids
        json.dump(state, open(SF, "w"), indent=1)
    gallery = ids + [m for m in cur if m not in hafo_media and m not in ids]
    out.setdefault(str(pid), {})[v["sku"]] = gallery
    print(f"{pid}/{vid} {v['sku']}: {cur} → {gallery}")
    twin = next((x for x in p["variants"] if x["sku"] == f"{v['sku']}-KG"), None)
    if twin:
        out[str(pid)][twin["sku"]] = gallery
        print(f"   twin {twin['id']} {twin['sku']} → {gallery}")

pf = os.path.join(HERE, "gallery-plan.json")
json.dump(out, open(pf, "w"), indent=1)
if WRITE and out:
    r = subprocess.run([sys.executable, os.path.join(ROOT, "runs/2026-10-01-fix/galleries.py"), pf, "--write"],
                       env=ENV, cwd=ROOT)
    sys.exit(r.returncode)
