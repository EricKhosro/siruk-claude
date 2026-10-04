#!/usr/bin/env python3
"""differences.csv: every register row whose live price is not confirmed by the register's own
`Վաճառքի գին`, grouped, plus the PM's Product.numbers price (state/register/register.csv) for context."""
import csv, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
reg = {r["reg_no"]: r for r in csv.DictReader(open(os.path.join(ROOT, "state/register/register.csv"), encoding="utf-8-sig"))}
A = list(csv.DictReader(open(os.path.join(HERE, "A-register-prices.csv"), encoding="utf-8-sig")))


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


out = []
for a in A:
    if a["verdict"] == "OK":
        continue
    lp, hp, np_ = f(a["live price"]), f(a["hafo"]), f(reg.get(a["Կոդ"], {}).get("sale_price"))
    if a["verdict"].startswith("DIFF") and np_ != lp:
        group = "1 FIX? live matches neither hafo nor the PM price"
    elif a["verdict"].startswith("DIFF"):
        group = "2 live = PM price (Product.numbers), hafo differs"
    elif a["verdict"].startswith("OK vs hafo") and np_ is not None and np_ != lp:
        group = "3 live = hafo, PM price differs (PM price held: at cost / typo)"
    elif a["verdict"].startswith("OK vs hafo"):
        continue
    else:
        group = "4 no price in xlsx, none on hafo" + (" - live = PM price" if np_ == lp else " - priced from another source")
    out.append({"group": group, "Կոդ": a["Կոդ"], "Անվանում": a["Անվանում"], "article": a["article"],
                "product_id": a["product_id"], "product": a["product"], "variant": a["variant"], "sku": a["sku"],
                "cost": a["cost"], "live price": a["live price"], "hafo price": a["hafo"],
                "PM price (Product.numbers)": "" if np_ is None else int(np_),
                "live - hafo": "" if hp is None else int(lp - hp),
                "live - hafo %": "" if not hp else f"{(lp - hp) / hp * 100:+.0f}%"})
out.sort(key=lambda r: (r["group"], r["Կոդ"]))
with open(os.path.join(HERE, "differences.csv"), "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
from collections import Counter
print(Counter(r["group"] for r in out))
