"""Full production image audit 2026-10-06 — read-only. Every product, every variant, every image.
Writes products.json (id → product with variants) and images.csv, downloads originals to img/."""
import json, os, subprocess, csv, hashlib, sys
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
ENV = dict(os.environ, SIRUK_API="https://api.siruk.am/api/admin", SIRUK_TOKEN_FILE=os.path.join(ROOT, ".siruk-token-prod"))
def api(path):
    for _ in range(3):
        r = subprocess.run([os.path.join(ROOT, "scripts/api.sh"), "GET", path], capture_output=True, text=True, env=ENV, cwd=ROOT)
        t = r.stdout
        if "{" in t:
            try: return json.loads(t[t.find("{"):])
            except Exception: pass
    raise SystemExit(f"failed {path}: {r.stderr[-300:]}")
media = {m["id"]: m for m in api("/medias?acceptTypes=image/jpeg,image/png,image/webp,image/gif,image/avif&per_page=10000")["data"]}
brands = {b["id"]: b["name"] for b in (api("/brands?per_page=1000").get("data") or [])}
ids, page = [], 1
while True:
    d = api(f"/products?per_page=100&page={page}")
    ids += [p["id"] for p in d["data"]]
    if page >= (d.get("meta") or d)["last_page"]: break
    page += 1
print(len(ids), "products", file=sys.stderr)
pf = os.path.join(HERE, "products.json")
prods = json.load(open(pf)) if os.path.exists(pf) else {}
for i, pid in enumerate(ids):
    if str(pid) in prods: continue
    prods[str(pid)] = api(f"/products/{pid}")["data"]
    if i % 50 == 0:
        json.dump(prods, open(pf, "w")); print(i, file=sys.stderr)
json.dump(prods, open(pf, "w"))
rows, need = [], {}
for pid, p in prods.items():
    for v in p["variants"]:
        for pos, mid in enumerate(v.get("images") or []):
            m = media.get(mid) or {}
            ext = m.get("extension") or "jpg"
            fn = os.path.join(HERE, "img", f"{mid}.{ext}")
            if m.get("originalUrl"): need[fn] = m["originalUrl"]
            rows.append({"product_id": pid, "product": p["name"], "brand": brands.get(p.get("brand_id"), p.get("brand_id")),
                         "variant_id": v["id"], "sku": v["sku"], "label": v["name"], "size_label": v.get("size_label"),
                         "options": "; ".join(f'{a.get("attributeName")}={a.get("label")}' for a in (v.get("attribute_value_labels") or []) if a.get("role") == "option"),
                         "pos": pos, "media": mid, "file": m.get("filename"), "dir": m.get("directory"), "dims": m.get("dimensions"),
                         "url": m.get("originalUrl"), "local": fn})
def dl(item):
    fn, url = item
    if not os.path.exists(fn) or os.path.getsize(fn) == 0:
        subprocess.run(["curl", "-sfL", "--max-time", "60", "-o", fn, url])
with ThreadPoolExecutor(4) as ex: list(ex.map(dl, need.items()))
for r in rows:
    r["md5"] = hashlib.md5(open(r["local"], "rb").read()).hexdigest() if os.path.exists(r["local"]) else "MISSING"
with open(os.path.join(HERE, "images.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
nov = [(pid, v["id"]) for pid, p in prods.items() for v in p["variants"] if not v.get("images")]
json.dump(nov, open(os.path.join(HERE, "no-image-variants.json"), "w"))
print(len(prods), "products", sum(len(p["variants"]) for p in prods.values()), "variants", len(rows), "image refs", len(need), "files", len(nov), "variants without images")
