"""Image audit 2026-10-02: every variant whose photos were written by runs/2026-10-02-found,
runs/2026-10-02-images or runs/2026-10-01-fix (applied-A/B/C). Read-only against production."""
import json, os, subprocess, hashlib, csv, time
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "runs/2026-10-02-audit")
env = dict(os.environ, SIRUK_API="https://api.siruk.am/api/admin", SIRUK_TOKEN_FILE=os.path.join(ROOT, ".siruk-token-prod"))
def api(path):
    r = subprocess.run([os.path.join(ROOT, "scripts/api.sh"), "GET", path], capture_output=True, text=True, env=env, cwd=ROOT)
    t = r.stdout; return json.loads(t[t.find("{"):])
# scope: product ids (whole product, so siblings are compared too) + the variant ids actually written
pids, vids, why = set(), set(), {}
for l in open(os.path.join(ROOT, "runs/2026-10-02-found/created.tsv")):
    f = l.rstrip("\n").split("\t"); pids.add(int(f[0])); vids.add(int(f[3])); why[int(f[3])] = "found-import"
for p, m in json.load(open(os.path.join(ROOT, "runs/2026-10-02-images/gallery-plan.json"))).items():
    pids.add(int(p)); why.setdefault(("p", int(p)), "lens-run")
fix_v = {}
for k in "ABC":
    for v in json.load(open(os.path.join(ROOT, f"runs/2026-10-01-fix/applied-{k}.json"))):
        fix_v[int(v)] = "fix-" + k
media = {}
def med(mid):
    if mid not in media:
        d = api(f"/medias/{mid}")["data"]; media[mid] = d
    return media[mid]
rows = []
# resolve 2026-10-01-fix variant ids to products via the snapshot
snap = json.load(open(os.path.join(ROOT, "runs/2026-10-02-final/snapshot.json")))
for pid, p in (snap.items() if isinstance(snap, dict) else []):
    for v in p.get("variants", []):
        if v.get("id") in fix_v: pids.add(int(pid))
for pid in sorted(pids):
    p = api(f"/products/{pid}")["data"]
    for v in p["variants"]:
        labels = v.get("attribute_value_labels") or {}
        for i, mid in enumerate(v.get("images") or []):
            m = med(mid); fn = os.path.join(OUT, "img", f"{mid}.{m.get('extension') or 'jpg'}")
            if not os.path.exists(fn):
                subprocess.run(["curl", "-sL", "-o", fn, m["originalUrl"]])
            h = hashlib.md5(open(fn, "rb").read()).hexdigest() if os.path.exists(fn) else ""
            rows.append({"product_id": pid, "product": p["name"], "variant_id": v["id"], "sku": v["sku"], "label": v["name"],
                         "attrs": json.dumps(labels, ensure_ascii=False), "pos": i, "media": mid, "file": m["filename"],
                         "dims": m.get("dimensions"), "md5": h, "local": fn,
                         "source": why.get(v["id"]) or fix_v.get(v["id"]) or ("lens-run" if ("p", pid) in why else "sibling")})
with open(os.path.join(OUT, "images.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(pids), "products", len({r['variant_id'] for r in rows}), "variants", len(rows), "image refs", len(media), "media")
