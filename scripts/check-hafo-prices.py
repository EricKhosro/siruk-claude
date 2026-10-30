#!/usr/bin/env python3
"""Compare every Siruk variant's sale price with hafo.am and (optionally) fix it.

The logic — hafo's per-size rows, the /product/change cross-check, the Trixie
"Tx" forms, the sibling fallback and the guarded fix — lives in
siruk/pricecheck.py since 2026-10-26 (also: `siruk recheck-prices`, and the MCP
tools hafo_price_recheck / apply_hafo_prices).

    scripts/check-hafo-prices.py            # report only → runs/<date>/price-check.csv
    scripts/check-hafo-prices.py --apply    # also PUT the corrected sale prices
    scripts/check-hafo-prices.py --only 204,207
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SIRUK_NO_PACE"] = "1"  # as before
from siruk import pricecheck  # noqa: E402
from siruk.payload import PayloadError  # noqa: E402


def show(pid, p, rows):
    print(f"{pid:>4} {p.get('name', '')[:40]:<40} " + "  ".join(
        f"{r['sku']}:{r['siruk_price']}→{r['hafo_price'] or '?'} {r['status'][:9]}" for r in rows))


def main(argv):
    only = [int(x) for x in argv[argv.index("--only") + 1].split(",")] if "--only" in argv else None
    rows = pricecheck.check(only, progress=show)
    out = pricecheck.write_csv(rows)
    print("\n== summary ==", pricecheck.summary(rows), "\n→", out)
    fx = pricecheck.fixes(rows)
    if "--apply" not in argv:
        print(f"{sum(len(v) for v in fx.values())} variant(s) would be updated; run with --apply")
        return
    for pid, skus in fx.items():
        try:
            res = pricecheck.apply_prices(pid, skus)
            for w in res.warnings:
                print(f"  !! {pid}/{w}")
            print(f"ok  {pid} {res.body.get('name')}: " + ", ".join(
                f"{d['sku']}→{d['new']}" for d in res.diff if d["field"] == "price"))
        except PayloadError as e:
            print(f"  !! {e}")


if __name__ == "__main__":
    main(sys.argv[1:])
