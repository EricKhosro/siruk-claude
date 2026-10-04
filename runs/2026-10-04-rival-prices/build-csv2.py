#!/usr/bin/env python3
"""price-differences-highest.csv — the 497 variants reported in price-differences.csv, now with the price
of the same item on ALL three rivals (hafo.am, zoovet.am, nemo.am) and the HIGHEST of them chosen.

Sources (all fetched 2026-10-04):
  hafo    article-code / barcode match (variants.json, prices re-read live: hafo-recheck.json), or the
          name match of the first agent pass (agent-results.json) for the items hafo has no code for
  zoovet, nemo  agent-results2.json (the 464 hafo-compared items, matched + adversarially verified)
                agent-results.json  (the 33 items hafo does not sell, matched + verified in the first pass)
Ties for the highest price: the chosen link is the first of hafo, zoovet, nemo."""
import csv, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SHOPS = ("hafo", "zoovet", "nemo")

V = {r["variant_id"]: r for r in json.load(open(os.path.join(HERE, "variants.json"), encoding="utf-8"))}
RE = json.load(open(os.path.join(HERE, "hafo-recheck.json"), encoding="utf-8"))
AG1 = {r["variant_id"]: r["final"] for r in json.load(open(os.path.join(HERE, "agent-results.json"), encoding="utf-8"))}
AG2 = {r["variant_id"]: r for r in json.load(open(os.path.join(HERE, "agent-results2.json"), encoding="utf-8"))}
OLD = list(csv.DictReader(open(os.path.join(HERE, "price-differences.csv"), encoding="utf-8-sig")))


def hafo_code(v):
    """hafo by article code: (price, url, name, in_stock) or None"""
    if v["variant_id"] in AG1 or len(v["hafo"]) != 1:
        return None
    h = v["hafo"][0]
    live = RE.get(str(h["row_id"])) or {}
    price = live.get("kg_price") if v["kind"] == "1 kg" else live.get("price")
    if not price:
        return None
    return {"price": price, "url": h["url"], "name": h["row_name"], "in_stock": (live.get("qty") or 0) > 0,
            "how": v["hafo_how"] + (" — per-kg price of the same bag" if v["kind"] == "1 kg" else " + hafo wholesale = our cost"),
            "old": None}


def from_agent(s, how):
    if not s or not s.get("found") or s.get("price") is None:
        return None
    return {"price": s["price"], "url": s.get("url", ""), "name": s.get("name", ""), "in_stock": s.get("in_stock"),
            "how": how, "old": s.get("old_price")}


HEAD = ["Product on Siruk", "Variant", "Kind", "SKU", "Siruk link", "Siruk price (AMD)",
        "hafo.am price (AMD)", "hafo.am link", "zoovet.am price (AMD)", "zoovet.am link",
        "nemo.am price (AMD)", "nemo.am link",
        "Chosen price - highest rival (AMD)", "Rival link", "Difference (Siruk - chosen)", "Difference %",
        "Rival's product name", "Rival in stock", "How matched",
        "Siruk price came from: file", "Price in that row (AMD)", "Siruk variant id"]

rows, stats = [], {"rivals": {1: 0, 2: 0, 3: 0}, "zero": 0, "changed_vs_first": 0, "discounted": []}
for o in OLD:
    vid = int(o["Siruk variant id"])
    v = V[vid]
    found = {}
    h = hafo_code(v)
    if h:
        found["hafo"] = h
    if vid in AG1:                                    # the 33 hafo does not sell (first pass searched all 3)
        f = AG1[vid]
        for s in SHOPS:
            x = from_agent(f.get(s), "name match, every axis checked on the page, independently verified")
            if x:
                found[s] = x
    if vid in AG2:
        f = AG2[vid]["final"]
        for s in ("zoovet", "nemo"):
            x = from_agent(f.get(s), "name match, every axis checked on the page, independently verified")
            if x:
                found[s] = x
    if not found:
        raise SystemExit(f"variant {vid}: no rival price at all")
    best = max(found.values(), key=lambda x: x["price"])
    best_shop = next(s for s in SHOPS if s in found and found[s]["price"] == best["price"])
    best = found[best_shop]
    stats["rivals"][len(found)] += 1
    d = v["price"] - best["price"]
    if d == 0:
        stats["zero"] += 1
    if best["price"] != int(o["Rival price (AMD)"]):
        stats["changed_vs_first"] += 1
    for s, x in found.items():
        if x.get("old"):
            stats["discounted"].append((vid, s, x["price"], x["old"]))
    stock = "; ".join(f"{s}: {'' if found[s]['in_stock'] is None else ('yes' if found[s]['in_stock'] else 'no')}"
                      for s in SHOPS if s in found)
    how = "; ".join(f"{s}: {found[s]['how']}" for s in SHOPS if s in found)
    rows.append([o["Product on Siruk"], o["Variant"], o["Kind"], o["SKU"], o["Siruk link"], v["price"],
                 found.get("hafo", {}).get("price", ""), found.get("hafo", {}).get("url", ""),
                 found.get("zoovet", {}).get("price", ""), found.get("zoovet", {}).get("url", ""),
                 found.get("nemo", {}).get("price", ""), found.get("nemo", {}).get("url", ""),
                 best["price"], best["url"], d, f"{d / best['price'] * 100:+.1f}%",
                 best["name"], stock, how,
                 o["Siruk price came from: file"], o["Price in that row (AMD)"], vid])

with open(os.path.join(HERE, "price-differences-highest.csv"), "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(HEAD)
    w.writerows(rows)
print(len(rows), "rows; rivals found per item", stats["rivals"], "; chosen = siruk price already:", stats["zero"],
      "; chosen price differs from the first-pass rival price:", stats["changed_vs_first"])
print("discounted rival prices:", stats["discounted"])
