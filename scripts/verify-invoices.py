#!/usr/bin/env python3
"""Reconcile transcribed invoice lines against each invoice's printed Итого.

Reads the raw line-item CSV and reports, per invoice, whether the sum of the
transcribed `Line Total (AMD)` matches the `Printed Total (AMD)` carried on
every row of that invoice. Any mismatch means a row was misread or missed.
"""
import csv, sys, collections

path = sys.argv[1] if len(sys.argv) > 1 else "csv/invoices/2026-09-lines-raw.csv"
rows = list(csv.DictReader(open(path)))

inv = collections.defaultdict(lambda: {"sum": 0.0, "printed": None, "n": 0, "bad": False})
for r in rows:
    k = r["Invoice ID"]
    e = inv[k]
    e["n"] += 1
    try:
        e["sum"] += float(r["Line Total (AMD)"] or 0)
    except ValueError:
        e["bad"] = True
    if r.get("Printed Total (AMD)"):
        e["printed"] = float(r["Printed Total (AMD)"])

ok = bad = unknown = 0
for k, e in sorted(inv.items()):
    if e["printed"] is None:
        unknown += 1
        print(f"?  {k:<28} {e['n']:>4} rows  sum {e['sum']:>12,.2f}  (no printed total)")
    elif abs(e["printed"] - e["sum"]) < 0.005:
        ok += 1
    else:
        bad += 1
        d = e["sum"] - e["printed"]
        print(f"!! {k:<28} {e['n']:>4} rows  sum {e['sum']:>12,.2f}  printed {e['printed']:>12,.2f}  diff {d:+,.2f}")

print(f"\n{len(rows)} lines across {len(inv)} invoices — {ok} reconcile, {bad} mismatch, {unknown} no printed total")
sys.exit(1 if bad else 0)
