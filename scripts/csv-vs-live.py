#!/usr/bin/env python3
"""Diff csv/ALL_SIRUK_PRODUCTS.csv against the live catalogue by article code.

Live variants carry the article code as their SKU — verbatim for every brand
except Trixie, whose codes lose the `Tx`/`TXN` suffix. A row counts as imported
when either spelling is a live SKU.

    scripts/csv-vs-live.py            # -> runs/<date>/csv-vs-live.json
"""
import csv, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP = os.path.join(ROOT, ".siruk-cache", "catalogue-snapshot.json")
SRC = os.path.join(ROOT, "csv/ALL_SIRUK_PRODUCTS.csv")


def variants_of(snap):
    for p in snap.values():
        for v in p["variants"]:
            yield p, v


def main():
    snap = json.load(open(SNAP))
    by_sku = {}
    for p, v in variants_of(snap):
        by_sku.setdefault(str(v["sku"]).strip(), (p, v))
    rows = list(csv.DictReader(open(SRC)))
    live, missing = [], []
    for r in rows:
        code = r["Article Code"].strip()
        art = re.sub(r"(Tx|TXN)$", "", code)
        hit = next((by_sku[c] for c in (code, art) if c in by_sku), None)
        if hit is None and len(art) >= 5 and art[:-1] in by_sku:
            # Trixie also sells an article under a trailing vendor digit
            # (29411 -> 2941). Only accept it when the live variant was bought
            # at this row's cost, so a real sibling article is never absorbed.
            cand = by_sku[art[:-1]]
            try:
                same_cost = float(cand[1]["cost_price"] or 0) == float(r["Buy Price (AMD)"] or -1)
            except ValueError:
                same_cost = False
            if same_cost:
                hit = cand
        (live if hit else missing).append((r, hit))
    print(f"{len(rows)} CSV rows: {len(live)} live, {len(missing)} missing", file=sys.stderr)
    out = {
        "live": [{**r, "_product_id": h[0]["id"], "_product": h[0]["name"],
                  "_slug": h[0]["slug"], "_brand": h[0]["brand"],
                  "_variant": h[1]["label"], "_sku": h[1]["sku"],
                  "_variant_id": h[1].get("id"),
                  "_price": h[1]["price"], "_price_per_kg": h[1]["price_per_kg"],
                  "_cost": h[1]["cost_price"], "_images": h[1]["images"]}
                 for r, h in live],
        "missing": [r for r, _ in missing],
    }
    d = os.path.join(ROOT, "runs", "2026-09-15")
    os.makedirs(d, exist_ok=True)
    json.dump(out, open(os.path.join(d, "csv-vs-live.json"), "w"), indent=1, ensure_ascii=False)
    import collections
    print("missing by brand:", collections.Counter(r["Brand"] for r in out["missing"]).most_common(), file=sys.stderr)


main()
