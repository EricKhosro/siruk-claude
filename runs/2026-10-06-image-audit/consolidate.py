"""Merge verdicts/*.json → findings.csv (non-ok only) + summary; classify the fix each needs."""
import json, glob, csv, collections, os
HERE = os.path.dirname(os.path.abspath(__file__))
rows = []
for f in sorted(glob.glob(os.path.join(HERE, "verdicts/batch-*.json"))):
    for r in json.load(open(f)):
        r["batch"] = os.path.basename(f)[6:-5]; rows.append(r)
cnt = collections.Counter(r["verdict"] for r in rows)
bad = [r for r in rows if r["verdict"] != "ok"]
for r in bad:
    v, pos = r["verdict"], int(r["pos"])
    if v.startswith("wrong") and pos == 0: r["fix"] = "REPLACE-LEAD"
    elif v.startswith("wrong"): r["fix"] = "drop-secondary"
    elif v == "not-packshot-lead": r["fix"] = "reorder-or-replace-lead"
    elif v == "hafo-placeholder": r["fix"] = "source-real-photo"
    elif v == "broken": r["fix"] = "reupload"
    elif v == "unclear" and pos == 0: r["fix"] = "check-lead"
    else: r["fix"] = "check-secondary"
with open(os.path.join(HERE, "findings.csv"), "w", newline="") as f:
    keys = ["batch","product_id","variant_id","sku","label","pos","media","verdict","fix","seen"]
    w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore"); w.writeheader(); w.writerows(bad)
done = sorted({r["batch"] for r in rows})
print("batches:", len(done), done); print("placements:", len(rows), dict(cnt))
print("fix:", dict(collections.Counter(r["fix"] for r in bad)))
print("products affected:", len({r["product_id"] for r in bad}))
