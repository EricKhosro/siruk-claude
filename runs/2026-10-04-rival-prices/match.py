#!/usr/bin/env python3
"""Stage 1 — deterministic: every live siruk.am variant -> its xlsx row (if any) and its hafo.am row by
article code / barcode. Output: variants.json (one record per live variant) + match-summary.txt.

xlsx A (AllAngine FINAL 09-28): row -> live variant by the row's 'Link on demo.siruk.am' dp id (demo
and production share variant ids). A '-KG' variant takes its bag's row, priced from the `Kg` column.
xlsx B (Royal Canin): rows -> live variants via rc-map.json (built separately, by name + size).
hafo: our sku (or the bag sku for '-KG') vs the hafo row sku (scripts/hafo-lookup.py sku_matches, Trixie
'Tx' form, Versele-Laga 4<art>V) or vs the hafo row barcode (Royal Canin EAN skus; the xlsx EAN).
"""
import csv, importlib.util, json, os, re
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location("hl", os.path.join(ROOT, "scripts/hafo-lookup.py"))
hl = importlib.util.module_from_spec(spec); spec.loader.exec_module(hl)

live = json.load(open(os.path.join(HERE, "live.json"), encoding="utf-8"))["products"]
hafo = json.load(open(os.path.join(HERE, "hafo-all.json"), encoding="utf-8"))
X = json.load(open(os.path.join(HERE, "xlsx.json"), encoding="utf-8"))
rcmap = json.load(open(os.path.join(HERE, "rc-map.json"), encoding="utf-8"))["map"]
pm = {r["reg_no"]: r for r in csv.DictReader(open(os.path.join(HERE, "product-numbers.csv"), encoding="utf-8-sig"))}
snapf = os.path.join(ROOT, "runs/2026-10-02-final/snapshot.json")   # cost only, as identity evidence
snapcost = {}
if os.path.exists(snapf):
    for p in json.load(open(snapf, encoding="utf-8")).values():
        for v in p["variants"]:
            snapcost[v["id"]] = v.get("cost")

A_by_vid = defaultdict(list)
for r in X["A"]:
    if r["vid"]: A_by_vid[r["vid"]].append(dict(r, link="xlsx 'Link on demo.siruk.am'"))
# rows the xlsx did not link (marked 'No' on 09-28, imported later): register number -> article code / live
# variant, from state/register/register-status.json (the register audit's code mapping)
A_by_code_row = {r["code"]: r for r in X["A"]}
RS = json.load(open(os.path.join(ROOT, "state/register/register-status.json"), encoding="utf-8"))
reg_by_vid, reg_by_sku = defaultdict(list), defaultdict(list)
for s_ in RS:
    a_ = A_by_code_row.get(s_["reg_no"])
    if not a_: continue
    if s_.get("code"): reg_by_sku[re.sub(r"[^a-z0-9]", "", str(s_["code"]).lower())].append(dict(a_, link="register code = our sku (state/register)"))
    if a_["vid"]: continue
    if s_.get("variant_id"): reg_by_vid[int(s_["variant_id"])].append(dict(a_, link="register code -> live variant (state/register)"))
B_by_row = {r["row"]: r for r in X["B"]}

rows = []
for it in hafo:
    for a in it.get("product_additional_information") or []:
        rows.append({"listing_id": it["id"], "title": it.get("title"), "slug": it.get("slug"),
                     "listing_discount": it.get("discount"), "max_discount": it.get("max_discount"),
                     "listing_status": it.get("status"), "maker": (it.get("product_maker") or {}).get("name")
                     if isinstance(it.get("product_maker"), dict) else it.get("product_maker"), **a})

def digits(s): return re.sub(r"\D", "", str(s or "")).lstrip("0")
idx, bc = defaultdict(list), defaultdict(list)
for r in rows:
    d = digits(r.get("sku"))
    if d:
        idx[d].append(r); idx[d[:-1]].append(r)
    for b in re.split(r"[,;\s]+", str(r.get("barcode") or "")):
        if b.strip(): bc[b.strip().lstrip("0")].append(r)

def hafo_match(base, brand, ean=None):
    keys = {digits(base), digits(re.sub(r"^4(\d+)V$", r"\1", base))}
    cands = {id(r): r for k in keys if k for r in idx.get(k, [])}.values()
    forms = [base] + ([base + "Tx"] if brand == "Trixie" and not base.lower().endswith("tx") else []) \
        + ([re.sub(r"^4(\d+)V$", r"\1", base)] if re.match(r"^4\d+V$", base) else [])
    hits = [r for r in cands if any(hl.sku_matches(r.get("sku") or "", f) for f in forms)]
    if brand == "Trixie":
        # the Tx tolerance (zero pad + trailing digit) is only valid against a hafo Trixie code
        # ('TX 040201', '41116Tx', 'TX 40531Trx'); a bare/other-prefix number is another brand
        hits = [r for r in hits if "tx" in hl.norm_sku(r.get("sku")) or hl.norm_sku(r.get("sku")) == hl.norm_sku(base)]
    how = "article code"
    if not hits and re.fullmatch(r"\d{8,14}", base):
        hits, how = list(bc.get(base.lstrip("0"), [])), "barcode = our sku"
    if not hits and ean:
        hits, how = list(bc.get(str(ean).strip().lstrip("0"), [])), "barcode = xlsx EAN"
    return how, list({r["id"]: r for r in hits}.values())

def num(x):
    try: return float(x)
    except Exception: return None

out = []
for pid, p in live.items():
    skus = {v["sku"]: v for v in p["variants"]}
    for v in p["variants"]:
        sku = str(v["sku"] or "").strip()
        is_kg = bool(re.search(r"-(KG|1KG)$", sku, re.I))
        base = re.sub(r"-(KG|1KG)$", "", sku, flags=re.I)
        bag = skus.get(base) if is_kg else None
        # xlsx A row
        tgt = bag if (is_kg and bag) else v
        arows = A_by_vid.get(tgt["id"], [])
        if not arows:
            arows = reg_by_vid.get(tgt["id"], []) or reg_by_sku.get(re.sub(r"[^a-z0-9]", "", base.lower()), [])
        if not arows and re.fullmatch(r"REG\d{5}", base) and base[3:] in A_by_code_row:
            arows = [dict(A_by_code_row[base[3:]], link="our sku REG<register no.>")]
        if not arows:
            arows = [dict(r_, link="our sku printed at the end of the register name") for r_ in X["A"]
                     if re.search(r"/\s*" + re.escape(base) + r"\s*$", r_["name_hy"] or "")]
        # xlsx B row(s)
        brows = [dict(B_by_row[int(r)], col=c) for r, c in rcmap.get(str(v["id"]), [])]
        ean = next((r["ean"] for r in arows if r.get("ean")), None)
        how, hits = hafo_match(base, p["brand"], ean)
        cost0 = (arows[0]["cost"] if arows and arows[0]["cost"] else snapcost.get(v["id"]))
        if len(hits) > 1 and cost0 and not is_kg:
            same = [h for h in hits if h.get("wholesale_price") is not None and abs(float(h["wholesale_price"]) - float(cost0)) < 1]
            if len(same) == 1: hits, how = same, how + " (one of several, wholesale = our cost)"
        cost = None
        if arows and arows[0]["cost"]: cost = arows[0]["cost"] / ((bag and (bag["size"] or {}).get("netContent", 0) / 1e6) or 1) if is_kg else arows[0]["cost"]
        sc = snapcost.get(v["id"])
        rec = {"product_id": int(pid), "variant_id": v["id"], "brand": p["brand"], "product": p["name"],
               "display": p["displayName"], "label": v["label"], "sku": sku, "kind": "1 kg" if is_kg else "pack",
               "bag_sku": base if is_kg else None, "bag_label": bag["label"] if bag else None,
               "size": v["size"], "saleMode": v["saleMode"],
               "siruk_url": "https://siruk.am" + (v.get("url") or "").rstrip("/") + "/",
               "price": v["price"], "originalPrice": v["originalPrice"], "salePrice": v["salePrice"],
               "compareAtPrice": v["compareAtPrice"], "discount": v["discount"], "stock": v["stock"],
               "cost_xlsx": cost, "cost_snapshot": sc,
               "xlsxA": [{k: r.get(k) for k in ("row", "code", "name_hy", "name_en", "cost", "sale", "kg", "ean", "link")} for r in arows],
               "xlsxB": [{k: r[k] for k in ("row", "name", "cost", "sale", "kg", "E", "col")} for r in brows],
               "pm": [{"reg_no": r["code"], "sale": num(pm[r["code"]]["sale_price"]) if r["code"] in pm else None,
                       "kg": num(pm[r["code"]]["kg"]) if r["code"] in pm else None} for r in arows],
               "hafo_how": how if hits else None,
               "hafo": [{"row_id": h["id"], "listing_id": h["listing_id"], "url": "https://hafo.am/products/" + (h["slug"] or ""),
                         "title": h["title"], "row_name": h.get("name"), "sku": h.get("sku"), "barcode": h.get("barcode"),
                         "price": h.get("price"), "wholesale": h.get("wholesale_price"), "kg_price": h.get("kg_price"),
                         "discount_price": h.get("discount_price"), "unique_price": h.get("unique_price"),
                         "listing_discount": h.get("listing_discount"), "max_discount": h.get("max_discount"),
                         "qty": h.get("qty_in_stock"), "status": h.get("listing_status"), "maker": h.get("maker")}
                        for h in hits]}
        out.append(rec)
json.dump(out, open(os.path.join(HERE, "variants.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
n = len(out); m = sum(1 for r in out if r["hafo"]); amb = sum(1 for r in out if len(r["hafo"]) > 1)
print(f"{n} variants; hafo code/barcode hits {m} (ambiguous {amb}); no hafo hit {n - m}; "
      f"xlsxA linked {sum(1 for r in out if r['xlsxA'])}; xlsxB linked {sum(1 for r in out if r['xlsxB'])}")
