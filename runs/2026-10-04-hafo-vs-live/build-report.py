#!/usr/bin/env python3
"""price-differences.csv — every live siruk.am variant whose price differs from the reference shop:
hafo.am (matched by article code, same pack confirmed by cost = hafo wholesale); when hafo does not
price it, zoovet.am / nemo.am (matched by name, every axis — alt/out-*.json).
Also not-priced-anywhere.csv: variants none of the three shops sells."""
import csv, glob, json, os, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
R = list(csv.DictReader(open(os.path.join(HERE, "all-variants-vs-hafo.csv"), encoding="utf-8-sig")))
urls = json.load(open(os.path.join(HERE, "siruk-urls.json"), encoding="utf-8"))
reg = {r["reg_no"]: r for r in csv.DictReader(open(os.path.join(HERE, "../../state/register/register.csv"), encoding="utf-8-sig"))}
A = {}
for r in csv.DictReader(open(os.path.join(HERE, "../2026-10-03-price-audit/A-register-prices.csv"), encoding="utf-8-sig")):
    A.setdefault(r["sku"], r)
alt = {}
for f in glob.glob(os.path.join(HERE, "alt/out-*.json")):
    for x in json.load(open(f, encoding="utf-8")):
        alt[x["sku"]] = x
inp = {x["sku"]: x for f in glob.glob(os.path.join(HERE, "alt/in-*.json")) for x in json.load(open(f, encoding="utf-8"))}


def siruk_link(r):
    u = urls[r["product_id"]]
    return "https://siruk.am" + (u["by_sku"].get(r["sku"]) or u["product_url"])


def origin(r):
    """Where the siruk price itself came from."""
    sku = r["sku"]; base = sku.rsplit("-KG", 1)[0]
    a = A.get(sku) or {}
    if a:
        pm = reg.get(a["Կոդ"], {}).get("sale_price")
        if pm and float(pm) == float(r["live price"]):
            return f"PM price list (Product.numbers), register row {a['Կոդ']}"
        if a.get("Վաճառքի գին") and float(a["Վաճառքի գին"]) == float(r["live price"]):
            return f"PM register xlsx sale price, row {a['Կոդ']}"
        return f"other (register row {a['Կոդ']}, PM price {pm or '-'})"
    if sku.endswith("-KG") and A.get(base):
        return f"PM register xlsx Kg column, row {A[base]['Կոդ']}"
    if r["brand"] == "Royal Canin":
        return "Royal Canin price list (Price Royal Canin Nor _ SIRUK.xlsx)"
    return "not in the PM register"


def hafo_url(u):
    p = "https://hafo.am/products/"
    return p + urllib.parse.quote(u[len(p):]) if u.startswith(p) else u


def pct(a, b):
    return f"{(a - b) / b * 100:+.1f}%" if b else ""


out, none = [], []
for r in R:
    lp = int(r["live price"])
    name = f"{r['brand']} {r['product']} — {r['variant']}"
    base = {"Product name": name, "Link in Siruk": siruk_link(r)}
    hafo_ok = r["group"] in ("SAME as hafo", "DIFFERENT") or (r["group"].startswith("DIFFERENT - cost") and r["sku"] in ("073252", "072022"))
    if hafo_ok:
        hp = int(float(r["hafo price"]))
        if hp != lp:
            out.append(dict(base, **{"Link in hafo / zoovet / nemo": hafo_url(r["hafo url"]), "Price in Siruk": lp,
                                     "Price in hafo / zoovet / nemo": hp, "Source of the price": "hafo.am",
                                     "Difference (Siruk - shop)": lp - hp, "Difference %": pct(lp, hp),
                                     "How matched": "article code" + (" + cost = hafo wholesale" if r["same pack?"].startswith("yes") else f" ({r['same pack?']})"),
                                     "Shop sale price (if discounted)": "", "Second shop": "", "Siruk price came from": origin(r), "SKU": r["sku"]}))
        continue
    x = alt.get(r["sku"])
    if x is None:
        none.append(dict(base, **{"Price in Siruk": lp, "Why": "zoovet/nemo search not run", "SKU": r["sku"], "Siruk price came from": origin(r)}))
        continue
    hits = [(s, x[s]) for s in ("zoovet", "nemo") if x.get(s) and x[s].get("price_regular")]
    if not hits:
        none.append(dict(base, **{"Price in Siruk": lp, "Why": f"hafo: no; zoovet: {x.get('zoovet_reason','')}; nemo: {x.get('nemo_reason','')}",
                                  "SKU": r["sku"], "Siruk price came from": origin(r)}))
        continue
    hits.sort(key=lambda t: int(float(t[1]["price_regular"])) == lp)   # the shop that differs first
    (s1, h1), rest = hits[0], hits[1:]
    p1 = int(float(h1["price_regular"]))
    second = "; ".join(f"{s}.am {int(float(h['price_regular']))} {h.get('url','')}" for s, h in rest)
    if p1 != lp or any(int(float(h["price_regular"])) != lp for _, h in rest):
        out.append(dict(base, **{"Link in hafo / zoovet / nemo": h1.get("url", ""), "Price in Siruk": lp,
                                 "Price in hafo / zoovet / nemo": p1, "Source of the price": f"{s1}.am (not on hafo)",
                                 "Difference (Siruk - shop)": lp - p1, "Difference %": pct(lp, p1),
                                 "How matched": "by name: " + (h1.get("evidence") or h1.get("name", ""))[:200],
                                 "Shop sale price (if discounted)": h1.get("price_sale") or "",
                                 "Second shop": second, "Siruk price came from": origin(r), "SKU": r["sku"]}))

order = {"hafo.am": 0}
out.sort(key=lambda o: (order.get(o["Source of the price"], 1), -abs(float(o["Difference %"].rstrip("%") or 0))))
for fn, rows in (("price-differences.csv", out), ("not-priced-anywhere.csv", none)):
    with open(os.path.join(HERE, fn), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for o in rows for k in o))); w.writeheader(); w.writerows(rows)
from collections import Counter
print("differences:", len(out), Counter(o["Source of the price"] for o in out))
print("not priced anywhere:", len(none))
print("Siruk dearer:", sum(o["Difference (Siruk - shop)"] > 0 for o in out), "cheaper:", sum(o["Difference (Siruk - shop)"] < 0 for o in out))
