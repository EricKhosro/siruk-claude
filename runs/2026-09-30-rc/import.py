#!/usr/bin/env python3
"""Import the Royal Canin plan to PRODUCTION, one product at a time (run only on the user's go).

    runs/2026-09-30-rc/import.py                 # dry run: builds + checks every body, writes nothing
    runs/2026-09-30-rc/import.py --write [--only key,key]

Per product: exists? (slug) -> upload each variant's gallery into products/royal-canin/<type>
-> create-product.sh -> set-translation.py ru + hy (if tr/<key>-<lang>.json exists) -> record in
state.json. Resumable: finished keys are skipped. All writes go through scripts/ (rule 10) with
SIRUK_API / SIRUK_TOKEN_FILE pointed at production.
"""
import json, os, subprocess, sys, urllib.parse

R = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(R))
ENV = dict(os.environ, SIRUK_API="https://api.siruk.am/api/admin",
           SIRUK_TOKEN_FILE=os.path.join(ROOT, ".siruk-token-prod"))
STATE = os.path.join(R, "state.json")
TYPE_DIR = {1: "dry-food", 2: "wet-food"}
write = "--write" in sys.argv
only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.update({k: ENV[k] for k in ("SIRUK_API", "SIRUK_TOKEN_FILE")})
from siruk_payload import PayloadError, api, post_body  # noqa: E402


def sh(*args):
    return subprocess.run(args, capture_output=True, text=True, cwd=ROOT, env=ENV)


state = json.load(open(STATE)) if os.path.exists(STATE) else {"done": {}, "problems": []}
plan = json.load(open(os.path.join(R, "plan.json")))["products"]
for p in plan:
    key = p["key"]
    if (only and key not in only) or key in state["done"]:
        continue
    body = json.load(open(os.path.join(R, "payloads", f"{key}.json")))
    try:
        post_body(dict(body, variants=[dict(v, images=[1]) for v in body["variants"]]))
    except PayloadError as e:
        print(f"{key}: REFUSED {e}"); state["problems"].append([key, str(e)]); continue
    if not write:
        print(f"{key}: ok ({len(body['variants'])} variants, {sum(len(v['_image_urls']) for v in p['variants'] if not v.get('_twin_of'))} images)")
        continue
    found = api("GET", "/products?search=" + urllib.parse.quote(p["name"])).get("data") or []
    if any(x.get("slug") == body["slug"] or x.get("brand") == "Royal Canin" for x in found):
        print(f"{key}: a Royal Canin product with this name/slug is live — skipped"); state["problems"].append([key, "already live"]); continue
    # name matches of OTHER brands (Monge "Maxi Adult") are fine: brand-less names repeat across brands
    other = [f"{x['id']} {x['name']} ({x.get('brand')})" for x in found]
    by_sku = {}
    for v, pv in zip(body["variants"], p["variants"]):
        if pv.get("_twin_of") in by_sku:          # loose / single-pouch variant: the pack's own photos
            v["images"] = by_sku[pv["_twin_of"]]
            continue
        ids = []
        for url in [u for u in pv["_image_urls"] if u]:     # royalcanin.com lists some empty entries
            if url in state.setdefault("media", {}):       # uploaded on an earlier attempt
                ids.append(state["media"][url]); continue
            r = sh("scripts/upload-media.sh", url, f"products/royal-canin/{TYPE_DIR[body['attribute_family_id']]}")
            mid = (r.stdout.strip().splitlines() or [""])[-1]
            if r.returncode == 0 and mid.isdigit():
                ids.append(int(mid)); state["media"][url] = int(mid)
                json.dump(state, open(STATE, "w"), ensure_ascii=False, indent=1)
            else:
                state["problems"].append([key, f"image failed {url}: {r.stderr.strip()[-200:]}"])
        if not ids:
            raise SystemExit(f"{key}: variant {v['sku']} got no image — stopping")
        v["images"] = ids
        by_sku[v["sku"]] = ids
    path = os.path.join(ROOT, ".siruk-cache", f"prod-rc-{key}.json")
    json.dump(body, open(path, "w"), ensure_ascii=False, indent=1)
    if other:
        print(f"{key}: same name under other brands, creating anyway: {other}")
    r = subprocess.run(["scripts/create-product.sh", path], capture_output=True, text=True, cwd=ROOT,
                       env=dict(ENV, FORCE="1") if other else ENV)
    print(r.stdout[-600:], r.stderr[-600:])
    if r.returncode:
        raise SystemExit(f"{key}: create failed — stopping")
    pid = next(int(l.split()[-1]) for l in r.stderr.splitlines() if l.startswith("created product"))
    tr = {}
    for lang in ("ru", "hy"):
        f = os.path.join(R, "tr", f"{key}-{lang}.json")
        if os.path.exists(f):
            t = sh("scripts/set-translation.py", str(pid), lang, f)
            tr[lang] = t.stdout.strip()[-200:] or t.stderr.strip()[-200:]
    state["done"][key] = {"product_id": pid, "translations": tr}
    json.dump(state, open(STATE, "w"), ensure_ascii=False, indent=1)
    print(f"{key}: product {pid} {tr}")
    sh("scripts/pace.sh", "product")
json.dump(state, open(STATE, "w"), ensure_ascii=False, indent=1) if write else None
print("problems:", state["problems"] or "none")
