#!/usr/bin/env python3
"""Build the deliverables from variants.json (live siruk.am + hafo code matches), hafo-recheck.json (live
hafo prices), agent-results.json (name matches on hafo / zoovet / nemo, adversarially verified) and xlsx.json.

  price-differences.csv  every live variant whose price differs from its rival (hafo first; else zoovet; else nemo)
  all-variants.csv       every live variant with its rival price and status (same / different / no rival has it)

Rival order: hafo.am; if hafo does not sell the exact item, zoovet.am; if zoovet does not either, nemo.am
(the user's final instruction). When zoovet and nemo both have it, nemo's price is shown in 'Other rival'.
Siruk price source: the xlsx file + Excel row + column, only when that cell holds the live price."""
import csv, json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
A_FILE = "AllAngineProduct-FINAL-2026-09-28.xlsx"
B_FILE = "Price Royal Canin Nor _ SIRUK.xlsx"

V = json.load(open(os.path.join(HERE, "variants.json"), encoding="utf-8"))
RE = json.load(open(os.path.join(HERE, "hafo-recheck.json"), encoding="utf-8"))
AG = {r["variant_id"]: r for r in json.load(open(os.path.join(HERE, "agent-results.json"), encoding="utf-8"))}
PM = {r["reg_no"]: r for r in csv.DictReader(open(os.path.join(HERE, "product-numbers.csv"), encoding="utf-8-sig"))}


def f(x):
    try:
        return float(x)
    except Exception:
        return None


def is_single_pouch(r):
    return bool(r["xlsxB"]) and r["xlsxB"][0]["col"] == "D" and r["kind"] == "pack"


def kind(r):
    return "1 kg (loose)" if r["kind"] == "1 kg" else ("single pouch" if is_single_pouch(r) else "pack")


def source(r):
    """-> (file, row, column, cell price, note)"""
    p = f(r["price"])
    for b in r["xlsxB"]:
        col, val = ("Վաճառքի Գին", b["sale"]) if b["col"] == "C" else ("Վաճառքի Գին կիլոգրամով", b["kg"])
        if val is not None and f(val) == p:
            return B_FILE, b["row"], col, int(val), ""
        return "", "", "", "", f"{B_FILE} row {b['row']} ({b['name']}) has {col} = {val} — live price differs"
    for a in r["xlsxA"]:
        col, val = ("Kg", a["kg"]) if r["kind"] == "1 kg" else ("Վաճառքի գին", a["sale"])
        if val is not None and f(val) == p:
            return A_FILE, a["row"], col, int(val), ""
        pm = PM.get(a["code"])
        pmv = f(pm["kg"] if r["kind"] == "1 kg" else pm["sale_price"]) if pm else None
        if val is None:
            note = f"{A_FILE} row {a['row']} (Կոդ {a['code']}) has no {col} — live price is not from either xlsx"
            if pmv == p:
                note += f"; it equals the PM register csv/Product.numbers (Կոդ {a['code']}, {'Kg' if r['kind'] == '1 kg' else 'Վաճառքի գին'} = {int(pmv)})"
        else:
            note = f"{A_FILE} row {a['row']} (Կոդ {a['code']}) has {col} = {int(val)} — live price differs"
        return "", "", "", "", note
    return "", "", "", "", "Not in either xlsx file (imported earlier from another supplier list)"


def rival(r):
    """-> dict(shop, url, price, old, name, stock, how, other) or None"""
    vid = r["variant_id"]
    ag = AG.get(vid)
    if ag:
        fin = ag["final"]
        for shop in ("hafo", "zoovet", "nemo"):
            s = fin.get(shop) or {}
            if s.get("found") and s.get("price") is not None:
                other = []
                for o in ("zoovet", "nemo"):
                    so = fin.get(o) or {}
                    if o != shop and so.get("found") and so.get("price") is not None and shop != "hafo":
                        other.append(f"{o}.am {so['price']} ({so.get('url', '')})")
                verified = {"verifier-agreed": "matched by an agent, confirmed by an independent verifier",
                            "tiebreak": "matcher and verifier disagreed; settled by a third check",
                            "matcher-only": "matched by an agent (verifier unavailable)"}[ag["source"]]
                how = ("hafo row " + (s.get("sku") or "") + " — " if shop == "hafo" else "") + \
                      "name match, every axis checked on the page (" + verified + ")"
                return {"shop": shop + ".am", "url": s.get("url", ""), "price": s["price"], "old": s.get("old_price"),
                        "name": s.get("name", ""), "stock": s.get("in_stock"), "how": how,
                        "evidence": s.get("evidence", ""), "other": "; ".join(other)}
        return None
    if len(r["hafo"]) == 1:
        h = r["hafo"][0]
        live = RE.get(str(h["row_id"])) or RE.get(h["row_id"]) or {}
        price = live.get("kg_price") if r["kind"] == "1 kg" else live.get("price")
        if price is None and "error" in live:
            price = h["kg_price"] if r["kind"] == "1 kg" else h["price"]
        if r["kind"] == "1 kg" and not price:
            return None
        cost = r["cost_xlsx"] if r["cost_xlsx"] is not None else r["cost_snapshot"]
        how = r["hafo_how"]
        if r["kind"] == "1 kg":
            how += " — hafo's per-kg price of the same bag"
        elif cost is not None and h["wholesale"] is not None and abs(float(cost) - float(h["wholesale"])) < 1:
            how += " + hafo wholesale = our cost"
        else:
            how += f" (hafo wholesale {h['wholesale']} vs our cost {cost})"
        return {"shop": "hafo.am", "url": h["url"], "price": price, "old": None, "name": h["row_name"],
                "stock": (live.get("qty", h["qty"]) or 0) > 0, "how": how, "evidence": "", "other": ""}
    return None


HEAD = ["Product on Siruk", "Variant", "Kind", "SKU", "Siruk link", "Siruk price (AMD)",
        "Rival shop", "Rival link", "Rival price (AMD)", "Difference (Siruk - rival)", "Difference %",
        "Rival's product name", "Rival in stock", "How matched",
        "Siruk price came from: file", "Siruk price came from: Excel row", "Siruk price came from: column",
        "Price in that row (AMD)", "Note on Siruk price", "Other rival (zoovet/nemo) price", "Siruk variant id"]

diff_rows, all_rows = [], []
for r in sorted(V, key=lambda r: (r["brand"] or "", r["display"] or "", r["variant_id"])):
    rv = rival(r)
    src = source(r)
    base = [r["display"], r["label"], kind(r), r["sku"], r["siruk_url"], r["price"]]
    if rv:
        d = r["price"] - rv["price"]
        pct = f"{d / rv['price'] * 100:+.1f}%" if rv["price"] else ""
        row = base + [rv["shop"], rv["url"], rv["price"], d, pct, rv["name"],
                      "" if rv["stock"] is None else ("yes" if rv["stock"] else "no"), rv["how"],
                      *src, rv["other"], r["variant_id"]]
        status = "same price" if d == 0 else "DIFFERENT"
    else:
        row = base + ["", "", "", "", "", "", "", "", *src, "", r["variant_id"]]
        status = "no rival sells this exact item"
    all_rows.append([status] + row)
    if rv and rv["price"] != r["price"]:
        diff_rows.append(row)

with open(os.path.join(HERE, "price-differences.csv"), "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(HEAD)
    w.writerows(diff_rows)
with open(os.path.join(HERE, "all-variants.csv"), "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["Status"] + HEAD)
    w.writerows(all_rows)
from collections import Counter
print(Counter(r[0] for r in all_rows))
print("differences by shop", Counter(r[6] for r in diff_rows))
print("differences with an xlsx source", sum(1 for r in diff_rows if r[14]), "of", len(diff_rows))
