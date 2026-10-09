#!/usr/bin/env python3
"""Add species categories to the 17 approved multi-species products (2026-10-09).
Superset only: refuses any write that would drop a category or a variant."""
import json, os, subprocess, sys
ROOT = "/Users/conceptmacmini01/Documents/Projects/Siruk-claude"
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import put_body
SA_GROOM, SA_SUPPLIES, BIRD_GROOM, CAT_TOOLS = 104, 105, 106, 37
ADD = {475: [SA_GROOM, BIRD_GROOM], 478: [SA_GROOM, BIRD_GROOM], 479: [SA_GROOM, BIRD_GROOM],
       477: [SA_GROOM], 502: [SA_GROOM], 568: [SA_GROOM], 569: [SA_GROOM], 571: [SA_GROOM],
       581: [SA_GROOM], 588: [SA_GROOM], 589: [SA_GROOM], 614: [SA_GROOM], 615: [SA_GROOM],
       616: [SA_GROOM], 1202: [SA_SUPPLIES], 1023: [SA_SUPPLIES], 507: [CAT_TOOLS]}
def api(method, path, payload=None):
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(ROOT, ".siruk-cache", "_addcat.json")
        json.dump(payload, open(p, "w"), ensure_ascii=False); args.append(p)
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=180)
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:]) if i >= 0 else {"_err": r.stderr}
ok = bad = 0
for pid, add in ADD.items():
    cur = api("GET", f"/products/{pid}")["data"]
    want = sorted(set(cur["category_ids"]) | set(add))
    if want == sorted(cur["category_ids"]):
        print(f"  {pid} already {want}"); ok += 1; continue
    body = put_body(cur); body["category_ids"] = want
    res = api("PUT", f"/products/{pid}", body).get("data") or {}
    good = sorted(res.get("category_ids") or []) == want and len(res.get("variants", [])) == len(cur["variants"])
    ok += good; bad += not good
    print(f"  {pid} {cur['name'][:40]:<40} {sorted(cur['category_ids'])} -> {res.get('category_ids')} "
          f"variants {len(cur['variants'])}->{len(res.get('variants', []))} {'OK' if good else 'FAILED'}")
print(f"ok={ok} failed={bad}")
