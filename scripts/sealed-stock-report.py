#!/usr/bin/env python3
"""Sealed vs opened stock per ArmSoft good, and what to order — the sealed-stock sheet.

    uv run --with openpyxl python scripts/sealed-stock-report.py <turnover.xlsx> <goods.xml> --out sealed.xlsx

<turnover.xlsx>  ArmSoft "Ապրանքների շրջանառություն" (as for restock-report.py:
                 period from 01/01/01, "Բացված ըստ գործողությունների" ticked, Excel).
<goods.xml>      the goods export (Ապրանքներ և ծառայություններ → all → XML): the
                 pack size of every good is its alt unit's coefficient
                 (303 kg + 003 Պարկ ×12 = a 12 kg bag; 001 Հատ + 002 ×26 = a 26-pouch case).

The user's rule (2026-11-03): a bag that sold even 100 g loose is no longer a
sealed bag. ArmSoft counts a bag good in kg, so the stock splits into
sealed bags = whole multiples of the bag weight, and the open bag = the rest.
That assumes the shop opens one bag at a time; two half-sold bags of one good
would read as one sealed + one open — check the shelf if that is possible.
A good with no sealed pack left goes on the order list.
"""
import argparse, csv, json, math, os, re, xml.etree.ElementTree as ET
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = {"a": "http://www.armsoft.am/Accountant/6.0"}
UNIT_NAME = {"003": "bag", "001": "pack", "002": "case", "004": "pack"}
EPS = 1e-6


def load_goods(path):
    out = {}
    for g in ET.parse(path).getroot().findall("a:Goods", NS):
        code = g.findtext("a:Code", "", NS)
        unit, alt = g.findtext("a:Unit", "", NS), g.findtext("a:AltUnit", "", NS)
        coef = {q.findtext("a:Unit", "", NS): float(q.findtext("a:Coef", "0", NS))
                for q in g.findall("a:GoodQuantityUnits/a:QuantityUnitPart", NS)}
        pack = coef.get(alt, 0) if alt and alt != unit and coef.get(alt, 0) > 1 else 0
        out[code] = {"name": g.findtext("a:Name", "", NS), "long": g.findtext("a:LongName", "", NS),
                     "unit": unit, "alt": alt, "pack": pack}
    return out


def load_turnover(path):
    rows = list(openpyxl.load_workbook(path, read_only=True).active.iter_rows(values_only=True))
    # "Արտահանել Excel" puts a blank row under the title, "(մեծ տվյալներ)" doesn't: find the header
    hi = next(k for k, r in enumerate(rows[:6]) if r and r[0] == "Կոդ")
    h, rows = list(rows[hi]), rows[hi + 1:]
    i = lambda name: h.index(name)
    i_rec = [i("Պահեստի մուտքի օրդեր/Քանակ մուտք"), i("Ապրանքների մնացորդների մուտք/Քանակ մուտք")]
    i_ret, i_end = i("Վերադարձներ/Քանակ մուտք"), i("Վերջնական քանակ")
    i_sold = [i("Վաճառքներ/Քանակ ելք"), i("Վաճառք (Մանրածախ)/Քանակ ելք")]
    out = {}
    for r in rows:
        if not r or not r[0] or r[0] == "Ընդամենը":
            continue
        n = lambda j: float(r[j] or 0)
        out[str(r[0])] = {"name": r[1], "unit": r[2] or "",
                          "received": n(3) + sum(n(j) for j in i_rec),
                          "sold": sum(n(j) for j in i_sold) - n(i_ret),
                          "stock": n(i_end)}
    return out


def fold_duplicates(turn):
    """An old duplicate code's movements count on the code Siruk keeps."""
    path = os.path.join(ROOT, "state", "armsoft-duplicate-codes.csv")
    if not os.path.exists(path):
        return
    for r in csv.DictReader(open(path, encoding="utf-8")):
        old, keep = turn.pop(r["old_code"], None), turn.get(r["keep_code"])
        if old and keep:
            for k in ("received", "sold", "stock"):
                keep[k] += old[k]
            keep.setdefault("merged", []).append(r["old_code"])


def fmt_qty(x, kg):
    return f"{x:,.3f}".rstrip("0").rstrip(".") + (" kg" if kg else "")


def clean(name):
    """ArmSoft's long names lost a few characters to its code page."""
    for bad, good in ((" ճ ", " × "), ("PՉtռ", "Pâté"), ("ռ", "é"), ("/Ք ", " / Ø ")):
        name = name.replace(bad, good)
    return name


def siruk_names(path):
    """ArmSoft code -> "Brand Product, flavour" from a `siruk export --format json` file (bag variant, size dropped)."""
    names = {}
    if not path:
        return names
    for v in json.load(open(path, encoding="utf-8")):
        code, sku = (v.get("accounting_code") or "").strip(), v.get("sku") or ""
        if not code or sku.endswith(("-KG", "-100G", "-1")) or code in names:
            continue
        label = re.sub(r"[\s,]*\d+(?:[.,]\d+)?\s*(?:kg|g|l)(?:\s*\(.*\))?$", "", v.get("variant_name") or "").strip()
        names[code] = f"{v.get('brand') or ''} {v['product_name']}".strip() + (f", {label}" if label else "")
    return names


def write_simple(packed, out, names):
    """One sheet for the shop: per bag good, sealed bags + what is left in the open one."""
    for r in packed:
        r["product"] = names.get(r["code"]) or r["product"]
    def order(r):
        return 0 if r["status"].startswith("only") else 1 if r["status"].startswith("OUT") else 2
    data = sorted((r for r in packed if r["pack_n"]), key=lambda r: (order(r), clean(r["product"]).lower()))
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "What's left"
    ws.append([f"What's left — sealed bags and open bags (ArmSoft, {os.path.basename(out)[-15:-5]})"])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append(["Order = no sealed bag left. Yellow: only an open bag is left. Red: nothing left."])
    ws["A2"].font = Font(italic=True, color="595959")
    ws.append([])
    ws.append(["Product", "Bag size", "Sealed bags", "Open bag: left", "Total left", "Order?"])
    for c in ws[4]:
        c.font = Font(bold=True, color="FFFFFF", size=12)
        c.fill = PatternFill("solid", fgColor="1F4E78")
        c.alignment = Alignment(horizontal="center", vertical="center")
    kg = lambda x: (f"{x:.2f}".rstrip("0").rstrip(".") + " kg") if x else "—"
    fill = {0: PatternFill("solid", fgColor="FFE699"), 1: PatternFill("solid", fgColor="F8CBAD")}
    for r in data:
        o = order(r)
        open_txt = f"{kg(r['open'])} ({r['open_pct']:.0%})" if r["open"] else "—"
        ws.append([clean(r["product"]), kg(r["pack_n"]), r["sealed"], open_txt,
                   kg(max(r["stock"], 0)), "ORDER" if o < 2 else ""])
        row = ws.max_row
        for c in ws[row]:
            c.font = Font(size=12, bold=(c.column == 6))
            if c.column > 1:
                c.alignment = Alignment(horizontal="center")
            if o < 2:
                c.fill = fill[o]
    for j, w in enumerate([62, 12, 13, 18, 13, 10], start=1):
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = "A5"
    ws.auto_filter.ref = f"A4:F{ws.max_row}"
    ws.page_setup.orientation = "portrait"
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToHeight = 0
    ws.print_title_rows = "4:4"
    wb.save(out)
    print(f"{len(data)} bag goods, {sum(1 for r in data if order(r) < 2)} to order -> {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("turnover")
    ap.add_argument("goods")
    ap.add_argument("--out", required=True)
    ap.add_argument("--simple", action="store_true", help="one sheet: what is left of each bag good")
    ap.add_argument("--siruk", help="`siruk export --format json` file, for brand + product names")
    a = ap.parse_args()
    goods, turn = load_goods(a.goods), load_turnover(a.turnover)
    fold_duplicates(turn)

    rows = []
    for code, t in turn.items():
        if t["received"] <= 0 and abs(t["sold"]) < EPS and abs(t["stock"]) < EPS:
            continue                                  # never stocked
        g = goods.get(code, {})
        kg = t["unit"] == "կգ"
        pack = g.get("pack", 0) if kg else 0    # pouches / pads sell one by one: a case is not a sealed pack
        stock = round(t["stock"], 3)
        notes = []
        if not kg and g.get("pack"):
            notes.append(f"received in {UNIT_NAME.get(g['alt'], 'pack')}s of {g['pack']:g}, sold one by one")
        if t.get("merged"):
            notes.append("incl. old duplicate code " + ", ".join(t["merged"]))
        if pack:
            sealed = math.floor(stock / pack + EPS) if stock > 0 else 0
            open_left = round(stock - sealed * pack, 3) if stock > 0 else 0
            if open_left < 0.001:
                open_left = 0
            pack_txt = f"{fmt_qty(pack, kg)} {UNIT_NAME.get(g['alt'], 'pack')}"
        else:
            sealed, open_left, pack_txt = (max(stock, 0), 0, "piece")
            if kg:
                pack_txt, sealed = "kg (pack size unknown)", None
                notes.append("sold by kg but no bag unit in ArmSoft — can't tell sealed from open")
        if stock < -EPS:
            notes.append("negative stock: more sold than received — a receipt is missing")
        if sealed is None:
            status = "check"
        elif stock <= EPS:
            status = "OUT — order"
        elif sealed == 0:
            status = "only open " + ("bag" if kg else "pack") + " — order"
        else:
            status = "sealed in stock"
        rows.append({"code": code, "product": g.get("long") or g.get("name") or t["name"],
                     "aname": t["name"], "kg": kg, "pack": pack_txt, "pack_n": pack,
                     "received": round(t["received"], 3), "sold": round(t["sold"], 3),
                     "other": round(stock - t["received"] + t["sold"], 3), "stock": stock,
                     "sealed": sealed, "open": open_left,
                     "open_pct": open_left / pack if pack and open_left else None,
                     "status": status, "note": "; ".join(notes)})

    packed = [r for r in rows if r["pack_n"] or r["kg"]]
    pieces = [r for r in rows if not (r["pack_n"] or r["kg"])]
    order = [r for r in rows if r["status"].endswith("order") and r["sold"] > 0]
    order.sort(key=lambda r: (not r["status"].startswith("only"), -r["sold"], r["code"]))
    packed.sort(key=lambda r: ({"OUT — order": 1, "check": 3, "sealed in stock": 2}.get(r["status"], 0), r["code"]))
    pieces.sort(key=lambda r: (r["stock"] > 0, r["code"]))

    if a.simple:
        write_simple(packed, a.out, siruk_names(a.siruk))
        return

    head = ["ArmSoft code", "Product", "ArmSoft name", "Pack", "Received", "Sold", "Other moves",
            "Stock now", "Sealed packs", "Open pack left", "Open pack % left", "Status", "Note"]
    keys = ["code", "product", "aname", "pack", "received", "sold", "other", "stock",
            "sealed", "open", "open_pct", "status", "note"]
    fills = {"OUT": "F8CBAD", "only": "FFE699", "sealed": "C6EFCE", "check": "D9D9D9"}

    wb = openpyxl.Workbook()
    for title, data in (("Order list", order), ("Bags & packs", packed), ("Piece goods", pieces)):
        ws = wb.active if title == "Order list" else wb.create_sheet(title)
        ws.title = title
        ws.append(head)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1F4E78")
            c.alignment = Alignment(vertical="center", wrap_text=True)
        for i, r in enumerate(data, start=2):
            ws.append([r[k] for k in keys])
            f = next((v for k, v in fills.items() if r["status"].startswith(k)), None)
            if f:
                ws.cell(i, 12).fill = PatternFill("solid", fgColor=f)
                ws.cell(i, 9).fill = PatternFill("solid", fgColor=f)
            for j in (5, 6, 7, 8, 10):
                ws.cell(i, j).number_format = '#,##0.###" kg"' if r["kg"] else "#,##0.###"
            ws.cell(i, 11).number_format = "0%"
        for j, w in enumerate([9, 52, 40, 16, 10, 10, 10, 11, 9, 11, 9, 22, 40], start=1):
            ws.column_dimensions[get_column_letter(j)].width = w
        ws.freeze_panes = "C2"
        ws.auto_filter.ref = ws.dimensions

    ws = wb.create_sheet("How to read")
    for line in [
        "Source: ArmSoft goods turnover 01/01/01 – today (receipts from the supplier e-invoices, till sales, returns) + the goods export for pack sizes.",
        "Received = warehouse receipts. Sold = till sales minus customer returns. Other moves = stock corrections (issue orders, fix receipts).",
        "Bags are counted in kg in ArmSoft. Sealed packs = how many whole bags fit in the stock; Open pack left = what is left in the opened bag.",
        "Example: 1 × 12 kg bag received, 100 g sold loose → stock 11.9 kg → 0 sealed, 11.9 kg open → 'only open bag — order'.",
        "This assumes one bag of a good is open at a time. If two bags of the same good were opened, the sheet shows one sealed bag too many.",
        "Order list = goods that sold at least once and have no sealed pack left: yellow = only an open bag/pack left, red = nothing left.",
        "Piece goods (one unit = one item) are sealed by nature: stock = sealed count. Pouches and pads come in cases but sell one by one, so they are piece goods here.",
    ]:
        ws.append([line])
    ws.column_dimensions["A"].width = 140
    wb.move_sheet("How to read", offset=-3)
    wb.active = 1
    wb.save(a.out)
    c = lambda s: sum(1 for r in rows if r["status"].startswith(s))
    print(f"{len(rows)} goods: {c('sealed')} sealed in stock, {c('only')} only open, {c('OUT')} out, {c('check')} check")
    print(f"order list {len(order)} -> {a.out}")


if __name__ == "__main__":
    main()
