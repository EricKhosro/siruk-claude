"""Final read-only check on production: for every product with a non-ok verdict, fetch live galleries and
report (1) variants with no image, (2) media judged wrong/unclear for that variant still attached,
(3) purchasable vs not. Writes verify-live.json."""
import json, glob, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
ENV = dict(os.environ, SIRUK_API="https://api.siruk.am/api/admin", SIRUK_TOKEN_FILE=os.path.join(ROOT, ".siruk-token-prod"))
rows = []
for f in glob.glob(os.path.join(HERE, "verdicts/batch-*.json")): rows += json.load(open(f))
V = {(str(r["variant_id"]), int(r["media"])): r for r in rows}
pids = sorted({str(r["product_id"]) for r in rows if r["verdict"] != "ok"}, key=int)
plan = {}
for f in glob.glob(os.path.join(HERE, "plan-out/*.json")): plan.update(json.load(open(f)))
out = {"empty": [], "still_bad": [], "products": len(pids)}
for pid in pids:
    t = subprocess.run([os.path.join(ROOT, "scripts/api.sh"), "GET", f"/products/{pid}"], capture_output=True, text=True, env=ENV, cwd=ROOT).stdout
    p = json.loads(t[t.find("{"):])["data"]
    for v in p["variants"]:
        ims = [int(m) for m in v.get("images") or []]
        d = (plan.get(pid) or {}).get(v["sku"]) or {}
        tag = d.get("hold") or ""
        if not ims: out["empty"].append([pid, v["sku"], v["name"], v.get("is_purchasable"), tag])
        for i, m in enumerate(ims):
            r = V.get((str(v["id"]), m))
            if r and r["verdict"] not in ("ok",):
                out["still_bad"].append([pid, p["name"], v["sku"], v["name"], i, m, r["verdict"], (r.get("seen") or "")[:90], v.get("is_purchasable"), tag])
json.dump(out, open(os.path.join(HERE, "verify-live.json"), "w"), ensure_ascii=False, indent=1)
print("products", len(pids), "empty", len(out["empty"]), "still-flagged placements", len(out["still_bad"]))
