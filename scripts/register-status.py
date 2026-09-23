#!/usr/bin/env python3
"""Decide, for every row of the PM's register, whether it is live on Siruk.

Three sources of an article code, in order of trust:
  1. the invoice CSV, matched by name (exact, or fuzzy with an equal buy price)
  2. hafo, matched by name + cost, accepted only when the names agree
  3. none — the row cannot be identified yet

"Live" is then decided against the catalogue SNAPSHOT (the article code is a
variant SKU), never against a run log, so a product imported from another CSV
still counts as live.

    scripts/register-status.py [--run state/register] [--out state/register/register-status.json]
"""
import argparse, csv, json, os, re, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(ROOT, "state/register")
SNAP = os.path.join(ROOT, ".siruk-cache/catalogue-snapshot.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=RUN, help="run folder holding register-match.json / hafo-recovered.json")
    ap.add_argument("--out", default=None)
    ap.add_argument("--overrides", default=None,
                    help="JSON {reg_no: code} for rows the fuzzy match got wrong (hand-checked)")
    a = ap.parse_args()
    ov_path = a.overrides or os.path.join(a.run, "match-overrides.json")
    overrides = json.load(open(ov_path)) if os.path.exists(ov_path) else {}
    a.out = a.out or os.path.join(a.run, "register-status.json")

    match = json.load(open(os.path.join(a.run, "register-match.json")))
    rec_path = os.path.join(a.run, "hafo-recovered.json")
    rec = json.load(open(rec_path)) if os.path.exists(rec_path) else {}
    snap = json.load(open(SNAP))

    by_sku = {}
    for p in snap.values():
        for v in p["variants"]:
            by_sku[re.sub(r"\s+", " ", str(v["sku"]).replace("\xa0", " ")).strip()] = (p, v)

    def find(code):
        if not code:
            return None
        # hafo writes some codes with a no-break space ("MG\xa0004807")
        code = re.sub(r"\s+", " ", code.replace("\xa0", " ")).strip()
        for c in (code, re.sub(r"(Tx|TXN)$", "", code), code.lstrip("0")):
            if c in by_sku:
                return by_sku[c]
        # hafo writes some SKUs zero-padded or with a brand prefix stripped
        for c in (code.zfill(6), code.zfill(5)):
            if c in by_sku:
                return by_sku[c]
        return None

    out = []
    for r in match:
        code, how = r.get("match"), r.get("how")
        h = rec.get(r["reg_no"])
        if not code and h and h.get("accepted"):
            code, how = h["sku"], "hafo name+cost"
        if r["reg_no"] in overrides:
            code, how = overrides[r["reg_no"]], "hand override"
        hit = find(code)
        out.append({**r, "code": code, "code_from": how,
                    "hafo": h,
                    "live": bool(hit),
                    "product_id": hit[0]["id"] if hit else None,
                    "product": hit[0]["name"] if hit else None,
                    "slug": hit[0]["slug"] if hit else None,
                    "variant_id": hit[1]["id"] if hit else None,
                    "variant": hit[1]["label"] if hit else None})
    json.dump(out, open(a.out, "w"), ensure_ascii=False, indent=1)

    print(f"{len(out)} register rows", file=sys.stderr)
    print(f"  live            : {sum(1 for r in out if r['live'])}", file=sys.stderr)
    print(f"  not live, coded : {sum(1 for r in out if not r['live'] and r['code'])}", file=sys.stderr)
    print(f"  no code         : {sum(1 for r in out if not r['code'])}", file=sys.stderr)
    print("  code source:", dict(collections.Counter(r["code_from"] or "-" for r in out)),
          file=sys.stderr)


main()
