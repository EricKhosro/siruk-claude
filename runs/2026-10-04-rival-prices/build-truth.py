#!/usr/bin/env python3
"""After the 2026-10-04 production price update.

1. siruk-vs-rivals-final.csv (the full audit) is refreshed in place: the 'Siruk price NOW' column comes from a
   fresh read of the public storefront, and no column cites csv/Product.numbers (user: never a price source).
2. siruk-source-of-truth.csv: one row per live variant. The columns are the product name on Siruk, the variant,
   the price, the source of the price, the Siruk link and the link to the source.
   Source of the price, in order:
     - the rival (hafo.am / zoovet.am / nemo.am) whose price for the exact item equals ours: the highest rival
       price, which is what every rival-sold variant was set to;
     - else the xlsx cell that holds our price (file, Excel row, column);
     - else none: no rival sells the exact item and neither xlsx file has a sale price for it."""
import csv, json, os, re, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
SHOPS = ("hafo", "zoovet", "nemo")
F = os.path.join(HERE, "siruk-vs-rivals-final.csv")
rows = list(csv.DictReader(open(F, encoding="utf-8-sig")))
head = list(rows[0].keys())


def storefront(pid):
    req = urllib.request.Request(f"https://api.siruk.am/api/products/{pid}",
                                 headers={"User-Agent": "curl/8.5.0", "Accept": "application/json"})
    for _ in range(4):
        try:
            return pid, json.load(urllib.request.urlopen(req, timeout=60))
        except Exception:
            pass
    raise SystemExit(f"storefront product {pid} unreadable")


V = {v["variant_id"]: v for v in json.load(open(os.path.join(HERE, "variants.json"), encoding="utf-8"))}
pids = sorted({V[int(r["Siruk variant id"])]["product_id"] for r in rows})
with ThreadPoolExecutor(6) as ex:
    live = dict(ex.map(storefront, pids))
NOW = {v["id"]: int(float(v["price"])) for d in live.values() for v in d.get("variants") or []}
UPDATED = {p["variant_id"] for n in ("plan.json", "plan-bony.json")
           for p in json.load(open(os.path.join(HERE, n), encoding="utf-8"))}

PM = re.compile(r";?\s*it equals csv/Product\.numbers \(Կոդ \d+\)")
truth, count = [], {}
for r in rows:
    vid = int(r["Siruk variant id"])
    now = NOW[vid]
    r["Siruk price NOW (AMD)"] = now
    r["Updated on 2026-10-04"] = "yes" if vid in UPDATED else ""
    hi = r["Highest rival price (AMD)"]
    r["Now vs highest rival"] = ("no rival sells this exact item" if not hi else
                                 "same" if now == int(float(hi)) else
                                 "Siruk dearer" if now > int(float(hi)) else "Siruk cheaper")
    r["Price source note"] = PM.sub("", r["Price source note"])
    if vid == 454:
        r["Remarks"] = ("hafo and nemo sell Bony Mix loose at 6300 per kg; this variant is the 1.8 kg pack, "
                        "set to zoovet's 1.8 kg price 11500 on 2026-10-04 (user)")
    shop = next((s for s in SHOPS if r[f"{s}.am price (AMD)"] and int(float(r[f"{s}.am price (AMD)"])) == now
                 and hi and now == int(float(hi))), None)
    if shop:
        src, link = f"{shop}.am (highest rival price for this exact item)", r[f"{shop}.am link"]
    elif r["Siruk price came from: file"] and r["Price in that cell (AMD)"] and int(r["Price in that cell (AMD)"]) == now:
        src = f"{r['Siruk price came from: file']}, Excel row {r['Excel row']}, column {r['Column']}"
        link = os.path.join("csv", r["Siruk price came from: file"])
    else:
        src, link = "NONE: no rival sells this exact item and neither xlsx file has a sale price for it", ""
    kind = src.split(" ")[0] if not src.startswith("NONE") else "NONE"
    count[kind] = count.get(kind, 0) + 1
    truth.append([r["Product on Siruk"], r["Variant"], now, src, r["Siruk link"], link])

with open(F, "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=head)
    w.writeheader()
    w.writerows(rows)
with open(os.path.join(HERE, "siruk-source-of-truth.csv"), "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["Product name on Siruk", "Variant", "Price (AMD)", "Source of price", "Siruk link", "Source link"])
    w.writerows(truth)
print(len(truth), "variants; source:", count)
print("now vs highest rival:", {k: sum(1 for r in rows if r["Now vs highest rival"] == k) for k in
                                ("same", "Siruk dearer", "Siruk cheaper", "no rival sells this exact item")})
print("Product.numbers still mentioned:", sum(1 for r in rows for v in r.values() if "Product.numbers" in str(v)))
