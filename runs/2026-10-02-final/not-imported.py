#!/usr/bin/env python3
"""Final check, 2026-10-02: which rows of the two PM files are NOT on production.

Register (csv/AllAngineProduct-FINAL-2026-09-28.xlsx): row → article code from, in order,
  today's found.csv codes, state/register/match-overrides.json, register-status.json;
  live = that code is a variant sku in snapshot.json (same normalisation as register-status.py).
  A row with no code is not imported; its reason comes from the 2026-10-01 not-found/not-added
  lists or today's holds.
Royal Canin (csv/Price Royal Canin Nor _ SIRUK.xlsx): the 52 rows with a quantity in column E were
  the import scope (2026-09-30); a row is live when its planned pack sku is a live variant.
  Rows with a price but no quantity, and rows with no price, are listed separately.
Writes not-imported-register.csv, not-imported-rc.csv and prints the counts.
Run with .venv-img/bin/python (openpyxl).
"""
import csv, json, os, re
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
snap = json.load(open(os.path.join(HERE, "snapshot.json")))


def norm(s):
    return re.sub(r"\s+", " ", str(s or "").replace("\xa0", " ")).strip()


by_sku = {}
for pid, p in snap.items():
    for v in p["variants"]:
        by_sku[norm(v["sku"])] = (pid, p, v)


def find(code):
    code = norm(code)
    if not code:
        return None
    for c in (code, re.sub(r"(Tx|TXN)$", "", code), code.lstrip("0"), code.replace(" ", ""),
              re.sub(r"^(MG|MM|GM|IN|BP|DL|CP|PG|PM|KF) ?", "", code),
              f"4{code}V", f"{code}V"):   # Versele-Laga skus: 4 + article + V (421620V)
        if c in by_sku:
            return by_sku[c]
    return None


# ---------------- register
wb = openpyxl.load_workbook(os.path.join(ROOT, "csv/AllAngineProduct-FINAL-2026-09-28.xlsx"), data_only=True)
rows = list(wb.worksheets[0].iter_rows(values_only=True))
hdr_i = next(i for i, r in enumerate(rows) if r and r[0] == "Կոդ")
reg = [r for r in rows[hdr_i + 1:] if r and r[0] and r[1]]   # the last line is the sheet total

status = {x["reg_no"]: x for x in json.load(open(os.path.join(ROOT, "state/register/register-status.json")))}
over = json.load(open(os.path.join(ROOT, "state/register/match-overrides.json")))
found = {x["Կոդ"]: x for x in csv.DictReader(open(os.path.join(ROOT, "runs/2026-10-01-register/found.csv"), encoding="utf-8-sig"))}
reasons = {}
for f, col in (("runs/2026-10-01-register/not-found.csv", "Why not"), ("runs/2026-10-01-register/not-added.csv", "Reason")):
    for x in csv.DictReader(open(os.path.join(ROOT, f), encoding="utf-8-sig")):
        reasons.setdefault(x["Կոդ"], (x.get("Category", ""), x.get(col, ""), x.get("Needed", "")))
holds = {}
for x in csv.DictReader(open(os.path.join(ROOT, "runs/2026-10-02-found/holds.csv"), encoding="utf-8-sig")):
    holds[x["Article Code"]] = x["Why held"]

out, live_n = [], 0
for r in reg:
    no, name, qty, cost, sale = str(r[0]), r[1], r[4], r[5], r[7]
    code = (found.get(no) or {}).get("Article code") or over.get(no) or (status.get(no) or {}).get("code")
    code = code or {"00030": "REG00030"}.get(no)   # imported today under a placeholder sku (no hafo code)
    if not code:   # the register often prints the supplier article after a slash: "…, 1 կգ/21620"
        m = re.findall(r"/\s*(\d{4,8})\s*$", str(name or ""))
        code = m[0] if m and find(m[0]) else None
    hit = find(code) if code else None
    if not hit and status.get(no, {}).get("live") and status[no].get("product_id") and str(status[no]["product_id"]) in snap:
        pid = str(status[no]["product_id"])
        hit = (pid, snap[pid], next((v for v in snap[pid]["variants"] if v["id"] == status[no].get("variant_id")), None))
        hit = hit if hit[2] else None
    if hit:
        live_n += 1
        continue
    cat, why, need = reasons.get(no, ("", "", ""))
    if code and code in holds:
        cat, why, need = "Held: price", holds[code], "the right sale price"
    elif not cat:
        cat = "No article code" if not code else "Not live"
        why = why or ("no article code recovered" if not code else f"code {code} is not a live sku")
    out.append({"Կոդ": no, "Անվանում": name, "Մնացորդ": qty, "Գնման գին": cost, "Վաճառքի գին": sale,
                "Article code": code or "", "Category": cat, "Why": why, "Needed": need})
with open(os.path.join(HERE, "not-imported-register.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
from collections import Counter
print(f"register: {len(reg)} rows, {live_n} live, {len(out)} not imported", Counter(x["Category"] for x in out))

# ---------------- Royal Canin
ws = openpyxl.load_workbook(os.path.join(ROOT, "csv/Price Royal Canin Nor _ SIRUK.xlsx"), data_only=True).worksheets[0]
rc = list(ws.iter_rows(values_only=True))
plan = json.load(open(os.path.join(ROOT, "runs/2026-09-30-rc/plan.json")))
skipped = {"82": "no cost / sale price in the file (Indoor 27 10+2 kg promo bag) — not imported (user, 2026-09-30)",
           "66": "Indoor 27 Home Life 10 kg — skipped on your instruction (2026-10-01)",
           "54": "Medium Starter 15 kg — skipped on your instruction (2026-10-01)",
           "144": "Cardiac dog 14 kg — skipped on your instruction (2026-10-01)",
           "155": "Mobility C2P+ 12 kg — skipped on your instruction (2026-10-01)",
           "158": "SKIN CARE 11 kg — skipped on your instruction (2026-10-01)"}
plan_skus = [v["sku"] for p in plan["products"] for v in p["variants"]]
rc_live = sum(1 for s in plan_skus if norm(s) in by_sku)
rc_out = []
for i, r in enumerate(rc[1:], 2):
    if not r[0]:
        continue
    has_q = isinstance(r[4], (int, float))
    if has_q and str(i) not in skipped:
        continue
    if str(i) in skipped:
        cat, why = "Skipped (in scope)", skipped[str(i)]
    elif r[1] or r[2]:
        cat, why = "No quantity in column E", "outside the import scope (not stocked)"
    else:
        cat, why = "No price, no quantity", "section heading or unpriced line"
    rc_out.append({"row": i, "name": norm(r[0]), "cost": r[1], "sale": r[2], "per_kg": r[3], "qty": r[4],
                   "Category": cat, "Why": why})
with open(os.path.join(HERE, "not-imported-rc.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rc_out[0].keys())); w.writeheader(); w.writerows(rc_out)
print(f"royal canin: plan skus live {rc_live}/{len(plan_skus)};", Counter(x["Category"] for x in rc_out))
