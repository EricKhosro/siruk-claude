#!/usr/bin/env python3
"""Read the PM's stock register into rows.

The register is the shop's own goods-on-hand list. Unlike the invoice CSVs it
carries a **sale price** as well as a cost, but it has **no article codes** —
its `Կոդ` column is a sequential register number, not a supplier SKU.

Two file shapes are read: the `.xlsx` export (`csv/AllAngineProduct.xlsx`,
2026-09-15) and the Apple Numbers original (`csv/Product.numbers`, the copy the
PM re-sent on 2026-09-16 with `Վաճառքի գին` filled on every row — needs the
`numbers-parser` package). The default is the Numbers file.

    scripts/read-register.py [--src csv/Product.numbers] [--csv out.csv]
"""
import argparse, csv, os, re, sys, zipfile
from xml.etree import ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "csv/Product.numbers")
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
COLS = ["reg_no", "name_hy", "unit_code", "unit", "qty", "cost", "amount",
        "sale_price", "kg"]


def _col(ref):
    n = 0
    for ch in re.match(r"([A-Z]+)", ref).group(1):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def sheet_rows(path, sheet="xl/worksheets/sheet1.xml"):
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(f"{NS}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{NS}t")))
    for r in ET.fromstring(z.read(sheet)).iter(f"{NS}row"):
        cells, auto = {}, 0
        for c in r.findall(f"{NS}c"):
            v, t = c.find(f"{NS}v"), c.get("t")
            if t == "inlineStr":
                val = "".join(x.text or "" for x in c.iter(f"{NS}t"))
            elif v is None:
                val = ""
            elif t == "s":
                val = shared[int(v.text)]
            else:
                val = v.text or ""
            ref = c.get("ref")
            i = _col(ref) if ref else auto
            auto = i + 1
            cells[i] = (val or "").strip()
        if cells:
            yield [cells.get(i, "") for i in range(max(cells) + 1)]


def numbers_rows(path):
    """Every row of the first table of the first sheet, as strings."""
    from numbers_parser import Document
    t = Document(path).sheets[0].tables[0]
    for r in t.rows(values_only=True):
        cells = []
        for v in r:
            if isinstance(v, float) and v.is_integer():
                v = int(v)
            cells.append("" if v is None else str(v).strip())
        yield cells


def rows(path=SRC):
    """The data rows, as dicts, with the header and title lines dropped."""
    out, started = [], False
    reader = numbers_rows if path.endswith(".numbers") else sheet_rows
    for r in reader(path):
        r = r + [""] * (len(COLS) - len(r))
        if not started:
            # the header row is the one whose first cell is the literal `Կոդ`
            started = r[0] == "Կոդ"
            continue
        if not r[0] and not r[1]:
            continue
        out.append(dict(zip(COLS, r[:len(COLS)])))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv")
    ap.add_argument("--src", default=SRC)
    a = ap.parse_args()
    rs = rows(a.src)
    print(f"{len(rs)} register rows", file=sys.stderr)
    if a.csv:
        w = csv.DictWriter(open(a.csv, "w", newline=""), fieldnames=COLS)
        w.writeheader()
        w.writerows(rs)
        print(f"wrote {a.csv}", file=sys.stderr)
    else:
        for r in rs[:5]:
            print(r)


if __name__ == "__main__":
    main()
