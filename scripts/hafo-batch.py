#!/usr/bin/env python3
"""Batch hafo lookup for every CSV row, resumable, keyed by article code.

    scripts/hafo-batch.py csv/products.csv .siruk-cache/hafo-all.json
"""
import csv, importlib.util, json, os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("hafo", os.path.join(ROOT, "scripts/hafo-lookup.py"))
hafo = importlib.util.module_from_spec(spec); spec.loader.exec_module(hafo)

src, out = sys.argv[1], sys.argv[2]
rows = list(csv.DictReader(open(src)))
res = json.load(open(out)) if os.path.exists(out) else {}
n = 0
for i, r in enumerate(rows, 1):
    code = r["Article Code"].strip()
    if code in res:
        continue
    x = hafo.lookup(code, r["Product Name (as printed)"])
    x["csv"] = {k: r[k] for k in r}
    res[code] = x
    n += 1
    tag = "OK  " + (x.get("brand") or "?") + " " + str(x.get("price_source")) + " " + str(x.get("price_amd")) if x.get("hafo_id") else "MISS"
    print(f"[{i}/{len(rows)}] {code:<10} {tag}  {(x.get('title_hy') or '')[:60]}", flush=True)
    if n % 10 == 0:
        json.dump(res, open(out, "w"), ensure_ascii=False)
    time.sleep(0.8)
json.dump(res, open(out, "w"), ensure_ascii=False)
print("DONE", len(res))
