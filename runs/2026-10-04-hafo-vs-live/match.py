#!/usr/bin/env python3
"""Every live siruk.am variant vs hafo.am's REGULAR shelf price (variant row `price`, not a discount).

Match: our sku -> hafo row sku (scripts/hafo-lookup.py sku_matches, also with the Trixie `Tx` suffix,
Versele-Laga `4<art>V`) or our sku = hafo row barcode (Royal Canin EAN skus).
Identity check per match: hafo `wholesale_price` vs our cost (admin snapshot 2026-10-02) — equal cost
means the same pack; a different cost usually means a different pack (3 pipettes vs 1) or a cost change.
`-KG` variants (1 kg of a bag) are compared with the bag row's `kg_price`.
hafo discount: listing `discount` % (the page then strikes the price through) — reported, never used.
"""
import csv, importlib.util, json, os, re, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location("hl", os.path.join(ROOT, "scripts/hafo-lookup.py"))
hl = importlib.util.module_from_spec(spec); spec.loader.exec_module(hl)

live = json.load(open(os.path.join(HERE, "live.json"), encoding="utf-8"))["products"]
hafo = json.load(open(os.path.join(HERE, "hafo-all.json"), encoding="utf-8"))
snap = json.load(open(os.path.join(ROOT, "runs/2026-10-02-final/snapshot.json"), encoding="utf-8"))
cost = {v["sku"]: v["cost"] for p in snap.values() for v in p["variants"]}
# register context: sku -> (row, PM price)
regctx = {}
prev = os.path.join(ROOT, "runs/2026-10-03-price-audit/differences.csv")
for r in csv.DictReader(open(os.path.join(ROOT, "runs/2026-10-03-price-audit/A-register-prices.csv"), encoding="utf-8-sig")):
    regctx.setdefault(r["sku"], []).append(r["Կոդ"])
pm = {r["reg_no"]: r["sale_price"] for r in csv.DictReader(open(os.path.join(ROOT, "state/register/register.csv"), encoding="utf-8-sig"))}

rows = []
for it in hafo:
    for a in it.get("product_additional_information") or []:
        rows.append({"listing": it["id"], "title": it.get("title"), "slug": it.get("slug"),
                     "discount": it.get("discount"), "max_discount": it.get("max_discount"),
                     "status": it.get("status"), **a})


def digits(s):
    return re.sub(r"\D", "", str(s or "")).lstrip("0")


idx = defaultdict(list)
bc = defaultdict(list)
for r in rows:
    d = digits(r.get("sku"))
    if d:
        idx[d].append(r)
        idx[d[:-1]].append(r)       # Trixie trailing variant digit
    b = str(r.get("barcode") or "").strip()
    if b:
        bc[b].append(r)


def match(sku, brand=""):
    base = re.sub(r"-(KG|1KG|1)$", "", sku)
    cands = {id(r): r for k in {digits(base), digits(re.sub(r"^4(\d+)V$", r"\1", base))} if k for r in idx.get(k, [])}.values()
    hits = []
    for r in cands:
        h = r.get("sku") or ""
        forms = [base] + ([base + "Tx"] if brand == "Trixie" else []) \
            + ([re.sub(r"^4(\d+)V$", r"\1", base)] if re.match(r"^4\d+V$", base) else [])
        if any(hl.sku_matches(h, f) for f in forms):
            hits.append(r)
    if not hits:
        hits = list(bc.get(base, []))
    # one row per hafo row id
    return base, list({r["id"]: r for r in hits}.values())


out = []
for pid, p in live.items():
    for v in p["variants"]:
        sku = str(v["sku"]).strip()
        kind = "1 kg" if re.search(r"-(KG|1KG)$", sku) else ("single pouch" if sku.endswith("-1") else "pack")
        base, hits = match(sku, p["brand"])
        c = cost.get(sku)
        rec = {"product_id": pid, "brand": p["brand"], "product": p["name"], "variant": v["label"], "sku": sku,
               "kind": kind, "our cost": c if c is not None else "", "live price": v["price"],
               "register row": " ".join(regctx.get(sku, [])),
               "PM price": " ".join(pm.get(x, "") for x in regctx.get(sku, []))}
        if not hits:
            out.append(dict(rec, group="no hafo row")); continue
        if len(hits) > 1:
            # prefer the row whose wholesale equals our cost
            same = [h for h in hits if c is not None and h.get("wholesale_price") is not None and abs(float(h["wholesale_price"]) - float(c)) < 1]
            hits = same if len(same) == 1 else hits
        h = hits[0]
        multi = len(hits) > 1
        hp = h.get("price")
        if kind == "1 kg":
            hp = h.get("kg_price")
        disc = h.get("discount")
        rec.update({"hafo sku": h.get("sku"), "hafo name": h.get("name"), "hafo url": f"https://hafo.am/products/{h.get('slug')}",
                    "hafo price": hp if hp is not None else "", "hafo wholesale": h.get("wholesale_price"),
                    "hafo stock": h.get("qty_in_stock"),
                    "hafo discount %": disc or "",
                    "hafo discounted price": round(float(h['price']) * (1 - float(disc) / 100)) if disc and h.get("discount_price") == 1 else "",
                    "other hafo rows": " ; ".join(f"{x.get('sku')} {x.get('price')}" for x in hits[1:]) if multi else ""})
        if kind == "1 kg":
            same_pack = "n/a (1 kg)"
        elif c is None or h.get("wholesale_price") is None:
            same_pack = "unknown (no cost)"
        elif abs(float(h["wholesale_price"]) - float(c)) < 1:
            same_pack = "yes (cost = hafo wholesale)"
        else:
            same_pack = f"NO: our cost {c} vs hafo wholesale {h['wholesale_price']}"
        rec["same pack?"] = same_pack
        if hp in (None, ""):
            g = "hafo row has no price" + (" (no kg_price)" if kind == "1 kg" else "")
        else:
            diff = float(v["price"]) - float(hp)
            rec["live - hafo"] = round(diff)
            rec["live - hafo %"] = f"{diff / float(hp) * 100:+.1f}%" if float(hp) else ""
            if diff == 0:
                g = "SAME as hafo"
            elif same_pack.startswith("NO"):
                g = "DIFFERENT - cost differs (check pack)"
            else:
                g = "DIFFERENT"
        if multi:
            g += " [several hafo rows]"
        out.append(dict(rec, group=g))


def pctkey(r):
    try:
        return -abs(float(str(r.get("live - hafo %", "0")).rstrip("%")))
    except ValueError:
        return 0


out.sort(key=lambda r: (r["group"], pctkey(r)))
keys = list(dict.fromkeys(k for r in out for k in ["group", "brand", "product", "variant", "sku", "kind", "live price",
                                                     "hafo price", "live - hafo", "live - hafo %", "same pack?", "our cost",
                                                     "hafo wholesale", "hafo sku", "hafo name", "hafo discount %",
                                                     "hafo discounted price", "hafo stock", "PM price", "register row",
                                                     "product_id", "other hafo rows", "hafo url"]))
with open(os.path.join(HERE, "all-variants-vs-hafo.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore"); w.writeheader(); w.writerows(out)
print(len(out), "live variants")
for k, n in sorted(Counter(r["group"] for r in out).items()):
    print(f"  {n:5}  {k}")
print("hafo listings with an active discount:", sum(1 for it in hafo if it.get("discount")))
