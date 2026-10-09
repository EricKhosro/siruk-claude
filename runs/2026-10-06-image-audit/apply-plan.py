#!/usr/bin/env python3
"""Apply plan-out/*.json gallery decisions to PRODUCTION.

Per variant: new gallery = plan "gallery" (+ new uploads from found.json put first, when present).
Skips a variant whose plan gallery is empty and has no new upload (needs a photo — never leave a
variant imageless). Skips a variant whose LIVE gallery differs from today's snapshot (products.json),
so a concurrent hand edit is never overwritten. -KG twins follow their bag.
Writes go through runs/2026-10-01-fix/galleries.py (one PUT per product, siruk_payload, read back).

    apply-plan.py              # dry run: prints every change
    apply-plan.py --write [--only pid,pid]
"""
import json, glob, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
ENV = dict(os.environ, SIRUK_API="https://api.siruk.am/api/admin", SIRUK_TOKEN_FILE=os.path.join(ROOT, ".siruk-token-prod"))
os.environ.update(ENV); sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import api  # noqa: E402
WRITE = "--write" in sys.argv
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
plan = {}
for f in sorted(glob.glob(os.path.join(HERE, "plan-out/*.json"))):
    plan.update(json.load(open(f)))
found = {}  # sku -> [new media ids] (filled by the sourcing step)
ff = os.path.join(HERE, "found-uploaded.json")
if os.path.exists(ff): found = json.load(open(ff))
snap = json.load(open(os.path.join(HERE, "products.json")))
out, skipped, changed = {}, [], 0
for pid, by_sku in plan.items():
    if ONLY and pid not in ONLY: continue
    live = api("GET", f"/products/{pid}")["data"]
    lv = {v["sku"]: [int(m) for m in v.get("images") or []] for v in live["variants"]}
    sv = {v["sku"]: [int(m) for m in v.get("images") or []] for v in snap[pid]["variants"]}
    for sku, d in by_sku.items():
        base = sku[:-3] if sku.endswith("-KG") else sku
        src = by_sku.get(base, d) if sku.endswith("-KG") else d
        gal = [int(m) for m in (found.get(base) or [])] + [int(m) for m in src.get("gallery") or [] if int(m) not in (found.get(base) or [])]
        if sku not in lv: skipped.append((pid, sku, "sku gone")); continue
        if src.get("hold"): skipped.append((pid, sku, "held: " + src["hold"])); continue
        planned = [int(m) for m in src.get("gallery") or []]
        if lv[sku] != sv.get(sku) and lv[sku] != planned: skipped.append((pid, sku, "changed since snapshot")); continue
        if not gal: skipped.append((pid, sku, "needs photo: " + (src.get("need") or "?"))); continue
        if gal == lv[sku]: continue
        out.setdefault(pid, {})[sku] = gal; changed += 1
        print(f"{pid} {sku}: {lv[sku]} -> {gal}   # {(src.get('why') or '')[:110]}")
pf = os.path.join(HERE, "gallery-plan.json"); json.dump(out, open(pf, "w"), indent=1)
print(f"\nvariants to change: {changed} in {len(out)} products; skipped {len(skipped)}")
for s in skipped: print("  skip", *s)
if WRITE and out:
    sys.exit(subprocess.run([sys.executable, os.path.join(ROOT, "runs/2026-10-01-fix/galleries.py"), pf, "--write"], env=ENV, cwd=ROOT).returncode)
