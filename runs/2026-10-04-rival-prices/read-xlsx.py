#!/usr/bin/env python3
"""Both price spreadsheets -> xlsx.json with the exact Excel row numbers.
A = csv/AllAngineProduct-FINAL-2026-09-28.xlsx (header row 3, data from row 4)
B = csv/Price Royal Canin Nor _ SIRUK.xlsx (header row 1; imported rows = column E has a number)"""
import json, os, re, openpyxl
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
A = "AllAngineProduct-FINAL-2026-09-28.xlsx"
B = "Price Royal Canin Nor _ SIRUK.xlsx"

def num(x):
    if x in (None, ""): return None
    if isinstance(x, (int, float)): return x
    d = re.sub(r"[^\d.]", "", str(x)); return float(d) if d else None

out = {"A": [], "B": []}
ws = openpyxl.load_workbook(os.path.join(ROOT, "csv", A), data_only=True).worksheets[0]
for i, r in enumerate(ws.iter_rows(min_row=4, values_only=True), start=4):
    if all(c in (None, "") for c in r): continue
    link = r[12] or ""
    m = re.search(r"/dp/(\d+)", str(link))
    out["A"].append({"file": A, "row": i, "code": r[0], "name_hy": r[1], "unit": r[3], "qty": r[4],
                     "cost": num(r[5]), "sale": num(r[7]), "kg": num(r[8]), "in_siruk": r[9],
                     "why_not": r[10], "name_en": r[11], "link": link,
                     "vid": int(m.group(1)) if m else None, "ean": r[13], "ean_note": r[14]})
ws = openpyxl.load_workbook(os.path.join(ROOT, "csv", B), data_only=True).worksheets[0]
for i, r in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
    if all(c in (None, "") for c in r): continue
    out["B"].append({"file": B, "row": i, "name": (r[0] or "").strip() if isinstance(r[0], str) else r[0],
                     "cost": num(r[1]), "sale": num(r[2]), "kg": num(r[3]), "E": r[4],
                     "imported": r[4] not in (None, "")})
json.dump(out, open(os.path.join(HERE, "xlsx.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("A rows", len(out["A"]), "with sale", sum(1 for x in out["A"] if x["sale"]), "with kg",
      sum(1 for x in out["A"] if x["kg"]), "linked", sum(1 for x in out["A"] if x["vid"]))
print("B rows", len(out["B"]), "imported", sum(1 for x in out["B"] if x["imported"]),
      "imported with kg", sum(1 for x in out["B"] if x["imported"] and x["kg"]))
