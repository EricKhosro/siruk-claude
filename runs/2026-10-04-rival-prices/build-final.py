#!/usr/bin/env python3
"""siruk-vs-rivals-final.csv — EVERY live siruk.am variant (1,522) with the same item's price on hafo.am,
zoovet.am and nemo.am, and the HIGHEST rival price + its link right after the Siruk price and link.

Sources (all 2026-10-04):
  hafo    article-code / barcode match (variants.json; prices re-read live in hafo-recheck.json), or the
          name match of pass 1 (agent-results.json) for items with no hafo code
  zoovet / nemo  agent-results.json   pass 1: the 238 items without a hafo code match (all 3 shops searched)
                 agent-results2.json  pass 2: the 464 hafo-compared items that differed
                 agent-results3.json  pass 3: the 823 hafo-compared items at hafo's price
Every zoovet/nemo match: name match with every axis checked on the page, independently re-checked, and the
price re-fetched live. Ties for the highest: the link is the first of hafo, zoovet, nemo."""
import csv, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SHOPS = ("hafo", "zoovet", "nemo")
A_FILE = "AllAngineProduct-FINAL-2026-09-28.xlsx"
B_FILE = "Price Royal Canin Nor _ SIRUK.xlsx"


def load(name, key="final"):
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        return {}
    return {r["variant_id"]: (r[key] if key in r else r) for r in json.load(open(p, encoding="utf-8"))}


V = json.load(open(os.path.join(HERE, "variants.json"), encoding="utf-8"))
RE = json.load(open(os.path.join(HERE, "hafo-recheck.json"), encoding="utf-8"))
AG1, AG2, AG3 = load("agent-results.json"), load("agent-results2.json"), load("agent-results3.json")
RC = {(r["variant_id"], r["shop"]): r for r in json.load(open(os.path.join(HERE, "recheck3.json"), encoding="utf-8"))}
CHECK = {"live-ok": "page re-read live this evening", "saved-list": "zoovet unreachable this evening, equals today's saved zoovet list",
         "unconfirmed": "read on the zoovet page earlier today, zoovet unreachable this evening and this price is not in the saved list",
         "live-MISMATCH": "PAGE PRICE CHANGED"}


def check(vid, shop, x):
    """-> (how the price was confirmed, nemo old price); also refreshes in_stock from the evening re-read"""
    if shop == "hafo":
        return ("hafo page re-read live earlier on 2026-10-04" if vid in AG1 else "hafo API re-read live this evening"), ""
    r = RC.get((vid, shop))
    if not r:
        return "page re-read live earlier on 2026-10-04 (zoovet blocked us later)", x.get("old") or ""
    if r.get("in_stock") is not None:
        x["in_stock"] = r["in_stock"]
    note = CHECK[r["status"]]
    if r["status"] == "live-MISMATCH":
        note += f" (page now {r['page_prices']})"
    return note, r.get("old_price") or x.get("old") or ""


def from_agent(s):
    if not s or not s.get("found") or s.get("price") is None:
        return None
    return {"price": s["price"], "url": s.get("url", ""), "name": s.get("name", ""), "in_stock": s.get("in_stock"),
            "how": "name match, every axis checked on the page, independently verified", "old": s.get("old_price")}


def hafo_code(v):
    if v["variant_id"] in AG1 or len(v["hafo"]) != 1:
        return None
    h = v["hafo"][0]
    live = RE.get(str(h["row_id"])) or {}
    price = live.get("kg_price") if v["kind"] == "1 kg" else live.get("price")
    if not price:
        return None
    return {"price": price, "url": h["url"], "name": h["row_name"], "in_stock": (live.get("qty") or 0) > 0,
            "how": v["hafo_how"] + (" (per-kg price of the same bag)" if v["kind"] == "1 kg" else " + hafo wholesale = our cost")}


PM = {r["reg_no"]: r for r in csv.DictReader(open(os.path.join(HERE, "product-numbers.csv"), encoding="utf-8-sig"))}


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def source(v):
    """-> (file, Excel row, column, price in that cell, note). File/row only when that cell holds the live price."""
    p = float(v["price"])
    for b in v["xlsxB"]:
        col, val = ("C (Վաճառքի Գին)", b["sale"]) if b["col"] == "C" else ("D (Վաճառքի Գին կիլոգրամով)", b["kg"])
        if num(val) == p:
            return B_FILE, b["row"], col, int(val), ""
        return "", "", "", "", f"{B_FILE} row {b['row']} has {col} = {val}; the live price differs"
    for a in v["xlsxA"]:
        col, val = ("Kg", a["kg"]) if v["kind"] == "1 kg" else ("Վաճառքի գին", a["sale"])
        if num(val) == p:
            return A_FILE, a["row"], col, int(val), ""
        if val is not None:
            return "", "", "", "", f"{A_FILE} row {a['row']} has {col} = {int(val)}; the live price differs"
        note = f"{A_FILE} row {a['row']} (Կոդ {a['code']}) has no {col}: price not from either xlsx"
        pm = PM.get(a["code"])
        if pm and num(pm["kg"] if v["kind"] == "1 kg" else pm["sale_price"]) == p:
            note += f"; it equals csv/Product.numbers (Կոդ {a['code']})"
        return "", "", "", "", note
    return "", "", "", "", "In neither xlsx file (imported earlier from another supplier list)"


def kind(v):
    if v["kind"] == "1 kg":
        return "1 kg (loose)"
    return "single pouch" if v["xlsxB"] and v["xlsxB"][0]["col"] == "D" else "pack"


REMARKS = {
    454: "Siruk mislabel: hafo and nemo sell Bony Mix loose at 6300 PER KG (hafo row '... կգ', fractional stock); "
         "Siruk labels this variant 1,800 g but charges the per-kg 6300. zoovet's 1.8 kg bag is 11500.",
    1722: "AllAngine row 31 Kg = 6600 is hafo's per-kg price for the CAT Wild Prairie; zoovet and nemo sell the dog "
          "food loose at 4700.",
    513: "Product 406's gallery holds zoovet's photo of a different (pink) Trixie rope ball (media 7951).",
}

HEAD = ["Product on Siruk", "Variant", "Kind", "SKU", "Siruk price (AMD)", "Siruk link",
        "Highest rival price (AMD)", "Highest rival link", "Difference (Siruk - highest)", "Difference %", "Status",
        "hafo.am price (AMD)", "hafo.am link", "zoovet.am price (AMD)", "zoovet.am link",
        "nemo.am price (AMD)", "nemo.am link", "nemo.am old (struck-through) price",
        "Highest rival's product name", "Rival in stock", "How matched", "Rival price confirmed",
        "Siruk price came from: file", "Excel row", "Column", "Price in that cell (AMD)", "Price source note",
        "Remarks", "Siruk variant id"]

rows, missing, stat = [], [], {}
for v in sorted(V, key=lambda r: (r["brand"] or "", r["display"] or "", r["variant_id"])):
    vid = v["variant_id"]
    found = {}
    h = hafo_code(v)
    if h:
        found["hafo"] = h
    covered = vid in AG1 or vid in AG2 or vid in AG3
    for ag, shops in ((AG1, SHOPS), (AG2, ("zoovet", "nemo")), (AG3, ("zoovet", "nemo"))):
        if vid in ag:
            for s in shops:
                x = from_agent(ag[vid].get(s))
                if x:
                    found[s] = x
                elif s in found and s != "hafo":
                    found.pop(s)
    if not covered:
        missing.append(vid)
    if found:
        best_price = max(x["price"] for x in found.values())
        bs = next(s for s in SHOPS if s in found and found[s]["price"] == best_price)
        best = found[bs]
        d = v["price"] - best_price
        status = "same as highest rival" if d == 0 else ("Siruk dearer" if d > 0 else "Siruk cheaper")
        best_cells = [best_price, best["url"], d, f"{d / best_price * 100:+.1f}%", status]
    else:
        best, status = None, "no rival sells this exact item"
        best_cells = ["", "", "", "", status]
    stat[status] = stat.get(status, 0) + 1
    src = source(v)
    checks = {sh: check(vid, sh, found[sh]) for sh in SHOPS if sh in found}
    rows.append([v["display"], v["label"], kind(v), v["sku"], v["price"], v["siruk_url"], *best_cells,
                 found.get("hafo", {}).get("price", ""), found.get("hafo", {}).get("url", ""),
                 found.get("zoovet", {}).get("price", ""), found.get("zoovet", {}).get("url", ""),
                 found.get("nemo", {}).get("price", ""), found.get("nemo", {}).get("url", ""),
                 checks.get("nemo", ("", ""))[1],
                 best["name"] if best else "",
                 "; ".join(f"{s}: {'' if found[s]['in_stock'] is None else ('yes' if found[s]['in_stock'] else 'no')}" for s in SHOPS if s in found),
                 "; ".join(f"{s}: {found[s]['how']}" for s in SHOPS if s in found),
                 "; ".join(f"{s}: {checks[s][0]}" for s in SHOPS if s in found),
                 *src, REMARKS.get(vid, ""), vid])

with open(os.path.join(HERE, "siruk-vs-rivals-final.csv"), "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(HEAD)
    w.writerows(rows)
print(len(rows), "variants;", stat)
print("variants with no zoovet/nemo search on record:", len(missing), missing[:30])
