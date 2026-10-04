#!/usr/bin/env python3
"""price-diff-report.csv: every live variant whose price differs from hafo.am (same pack confirmed),
with the siruk link, hafo link, both prices and where our price came from."""
import csv, json, os, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
P = list(csv.DictReader(open(os.path.join(HERE, "proposed-price-changes.csv"), encoding="utf-8-sig")))
A = {r["sku"]: r for r in csv.DictReader(open(os.path.join(HERE, "../2026-10-03-price-audit/A-register-prices.csv"), encoding="utf-8-sig"))}


def get(pid):
    req = urllib.request.Request(f"https://api.siruk.am/api/products/{pid}", headers={"User-Agent": "curl/8"})
    d = json.load(urllib.request.urlopen(req, timeout=60))
    return pid, {v["id"]: v.get("url") for v in d["variants"]}, d.get("url")


with ThreadPoolExecutor(4) as ex:
    urls = {pid: (vu, pu) for pid, vu, pu in ex.map(get, sorted({x["product_id"] for x in P}))}

EARLY = "Early import (Sept, before 2026-09-23); the run that set it was cleared, source not recorded. PM register price = our cost, so it was held and this price kept"
out = []
for x in P:
    sku, base = x["sku"], x["sku"].rsplit("-KG", 1)[0]
    reg = x["register row"] or A.get(base, {}).get("Կոդ", "")
    pm = x["PM price (register)"].split()
    if pm and float(pm[0]) == float(x["current live price"]):
        src = f"PM price list (csv/Product.numbers), register row {reg}"
    elif x["kind"] == "1 kg":
        src = f"PM register xlsx, Kg column (per-kg price), register row {reg}"
    elif sku == "42804":
        src = f"Early import (Sept), never updated: the 2026-10-02 import skipped it as already live. PM price is {pm[0]} (register row {reg})"
    else:
        src = EARLY + f" (PM price {pm[0] if pm else '-'}, register row {reg})"
    vu, pu = urls[x["product_id"]]
    link = "https://siruk.am" + (vu.get(int(x["variant_id"])) or pu)
    hafo = x["hafo url"]
    hafo = hafo[:len("https://hafo.am/products/")] + urllib.parse.quote(hafo[len("https://hafo.am/products/"):])
    out.append({"Product name": f"{x['brand']} {x['product']} — {x['variant']}",
                "Link in Siruk": link,
                "Link in hafo": hafo,
                "Price in Siruk": x["current live price"],
                "Price in hafo": x["hafo price"],
                "Source of the price": src,
                "Difference (Siruk - hafo)": int(x["current live price"]) - int(x["hafo price"]),
                "SKU / article": sku,
                "Our cost": x["our cost"]})
out.sort(key=lambda r: -abs(r["Difference (Siruk - hafo)"]) / float(r["Price in hafo"]))
with open(os.path.join(HERE, "price-diff-report.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
from collections import Counter
print(len(out), Counter(r["Source of the price"].split(",")[0].split(" (")[0][:40] for r in out))
