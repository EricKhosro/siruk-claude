#!/usr/bin/env python3
"""Normalize the Vendors_Siruk price sheets into one canonical row list.

The five sheets exported from the vendor workbook each have a different column
layout, a different number format, and (in one case) rows whose columns are
shifted. This turns all of them into a single JSON array so the import does not
have to care which sheet a row came from.

    scripts/normalize-vendor-csv.py [csv-dir] [-o out.json]

Defaults: csv-dir = ./csv, out = .siruk-cache/vendor-rows.json

Each output row:
    sheet, line, brand, sku (or None), raw_name, cost, price,
    per_kg_hint, case_pack, unit_g, size_txt, skip_reason
Rows with no sale price get skip_reason="no-price" and are kept in the output so
the report can list them.
"""
import argparse
import csv
import json
import os
import re
import sys

# ---------------------------------------------------------------- numbers

CURRENCY = re.compile(r'(դր|դ\s*r|AMD|֏)', re.I)


def num(raw):
    """Parse a vendor price cell. Returns int AMD or None.

    Handles '  21,500 ', '24500', '20.900 դր' (dot-thousands!), '5,800 դր',
    the '6,100 դ r' typo, '-' and ''.
    """
    if raw is None:
        return None
    s = CURRENCY.sub('', str(raw)).strip()
    s = s.replace(' ', ' ').strip()
    if s in ('', '-', '—'):
        return None
    s = s.replace(' ', '')
    # dot used as a thousands separator: 20.900 / 1.760
    if re.fullmatch(r'\d{1,3}(\.\d{3})+', s):
        s = s.replace('.', '')
    # comma used as a thousands separator: 21,500 / 5,800
    elif re.fullmatch(r'\d{1,3}(,\d{3})+', s):
        s = s.replace(',', '')
    else:
        s = s.replace(',', '.')
    try:
        v = float(s)
    except ValueError:
        return None
    if v <= 0:
        return None
    return int(round(v))


# ---------------------------------------------------------------- names

ARM_PREFIX = {
    'Կատվի կեր': 'cat',
    'Շան կեր': 'dog',
    'Ձկան յուղ': 'supplement',
}

# Trailing pack spec: 12X70G, 8X6X15G, 6X1,5KG, 56x85 gr, 24x140 gr, 12*85g,
# 10kg, 0,5kg, 500ml. Multiplier groups are the vendor case pack.
SIZE_RE = re.compile(
    r'(?:(\d+)\s*[Xx*]\s*)?(?:(\d+)\s*[Xx*]\s*)?'
    r'(\d+(?:[.,]\d+)?)\s*(KG|կգ|GR|գր|G|գ|ML|L)?(?=\W|$)',
    re.I)

UNIT_G = {'KG': 1000, 'ԿԳ': 1000, 'L': 1000,
          'GR': 1, 'ԳՐ': 1, 'G': 1, 'Գ': 1, 'ML': 1}


def strip_species(name):
    for pfx, sp in ARM_PREFIX.items():
        if name.startswith(pfx):
            return name[len(pfx):].strip(), sp
    return name, None


def parse_size(name):
    """-> (case_pack, unit_g, size_txt). unit_g is the RETAIL unit in grams."""
    cands = [m for m in SIZE_RE.finditer(name) if (m.group(1) or m.group(4))]
    if not cands:
        return None, None, None
    m = cands[-1]
    a, b, q, u = m.group(1), m.group(2), m.group(3), (m.group(4) or '').upper()
    try:
        q = float(q.replace(',', '.'))
    except ValueError:
        return None, None, None
    if not u:
        # bare number after a multiplier, e.g. '12X85' or '6X800' -> grams
        u = 'G'
    grams = q * UNIT_G.get(u, 1)
    if a and b:
        # 8X6X50g -> case of 8, retail unit is the 6x50g multipack
        return int(a), grams * int(b), m.group(0).strip()
    if a:
        return int(a), grams, m.group(0).strip()
    return None, grams, m.group(0).strip()


def brand_of(name):
    u = name.upper()
    for key, brand in (
        ('SCHESIR', 'Schesir'), ('STUZZY', 'Stuzzy'), ('STZ ', 'Stuzzy'),
        ('SCH ', 'Schesir'),
        ('BELCANDO', 'Belcando'), ('LEONARDO', 'Leonardo'),
        ('BEWI DOG', 'Bewi Dog'), ('BEWI-LAC', 'Bewi Dog'),
        ('BEWI CAT', 'Bewi Cat'),
        ('DOGLAND', 'Dogland'), ('HAUSMARKE', 'Hausmarke'),
        ('MASTERCRAFT', 'Mastercraft'),
        ('CANVIT', 'Canvit'), ('BRIT', 'Brit'),
    ):
        if key in u:
            return brand
    return None


# ---------------------------------------------------------------- sheets

def rows_of(path):
    with open(path, newline='', encoding='utf-8-sig') as fh:
        return [r for r in csv.reader(fh) if any(c.strip() for c in r)]


def cell(r, i):
    return r[i].strip() if len(r) > i else ''


def sheet_vendor_coded(path, sheet):
    """Sheet 1: Կոդ | Անվանում | Unit H/S Cost | R/Price | PRICE/KG"""
    out = []
    for ln, r in enumerate(rows_of(path)[1:], start=2):
        raw = cell(r, 1)
        if not raw:
            continue
        sku = cell(r, 0).replace('W-', '').strip() or None
        out.append(dict(sheet=sheet, line=ln, sku=sku, raw_name=raw,
                        cost=num(cell(r, 2)), price=num(cell(r, 3)),
                        per_kg_hint=num(cell(r, 4))))
    return out


def sheet_new_price(path, sheet):
    """Sheet 2: Товар/Клиент | NEW H/S PRICE | NEW R/PRICE | NEW R/PRICE KG.

    The final rows are shifted: an article code lands in column 0 and the name
    in column 1. Detect that by column 0 being all digits.
    """
    out = []
    for ln, r in enumerate(rows_of(path)[1:], start=2):
        c0 = cell(r, 0)
        if re.fullmatch(r'\d{4,}', c0):          # shifted row
            raw, sku, off = cell(r, 1), c0, 1
        else:
            raw, sku, off = c0, None, 0
        if not raw:
            continue
        out.append(dict(sheet=sheet, line=ln, sku=sku, raw_name=raw,
                        cost=num(cell(r, 1 + off)), price=num(cell(r, 2 + off)),
                        per_kg_hint=num(cell(r, 3 + off))))
    return out


def sheet_royal_canin(path, sheet):
    """Sheet 3: Անվանում | Գնման Գին | Վաճառքի Գին | Վաճառքի Գին կիլոգրամով.

    Brand is implied (never written in the rows). The 4th column is per-kg for
    dry bags but per-unit for wet multipacks, so it is only a hint.
    """
    out = []
    for ln, r in enumerate(rows_of(path)[1:], start=2):
        raw = cell(r, 0)
        if not raw:
            continue
        out.append(dict(sheet=sheet, line=ln, sku=None, raw_name=raw,
                        cost=num(cell(r, 1)), price=num(cell(r, 2)),
                        per_kg_hint=num(cell(r, 3)), brand='Royal Canin'))
    return out


def sheet_joly_food(path, sheet):
    """Sheet 4: Ապրանք | Քանակ | Գնման գին -25% | Վաճառքի գին. All Brit."""
    out = []
    for ln, r in enumerate(rows_of(path)[1:], start=2):
        raw = cell(r, 0)
        if not raw:
            continue
        out.append(dict(sheet=sheet, line=ln, sku=None, raw_name=raw,
                        cost=num(cell(r, 2)), price=num(cell(r, 3)),
                        per_kg_hint=None, brand='Brit', qty_txt=cell(r, 1)))
    return out


def sheet_joly_vitamins(path, sheet):
    """Sheet 5: name | purchase | sale. All Canvit."""
    out = []
    for ln, r in enumerate(rows_of(path)[1:], start=2):
        raw = cell(r, 0)
        if not raw:
            continue
        out.append(dict(sheet=sheet, line=ln, sku=None, raw_name=raw,
                        cost=num(cell(r, 1)), price=num(cell(r, 2)),
                        per_kg_hint=None, brand='Canvit'))
    return out


HANDLERS = {
    'Vendors_Siruk - Royal Canin 1.csv': sheet_vendor_coded,
    'Vendors_Siruk - Royal Canin 2.csv': sheet_new_price,
    'Vendors_Siruk - Royal Canin 3.csv': sheet_royal_canin,
    'Vendors_Siruk - Joly food.csv': sheet_joly_food,
    'Vendors_Siruk - Joly Vitamins.csv': sheet_joly_vitamins,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv_dir', nargs='?', default='csv')
    ap.add_argument('-o', '--out', default='.siruk-cache/vendor-rows.json')
    args = ap.parse_args()

    rows = []
    for fname, handler in HANDLERS.items():
        path = os.path.join(args.csv_dir, fname)
        if not os.path.exists(path):
            print(f'!! missing sheet: {path}', file=sys.stderr)
            continue
        sheet = fname.replace('Vendors_Siruk - ', '').replace('.csv', '')
        rows.extend(handler(path, sheet))

    for r in rows:
        name, species = strip_species(r['raw_name'])
        r['name_clean'] = re.sub(r'\s+', ' ', name).strip()
        r['species_hint'] = species
        r['brand'] = r.get('brand') or brand_of(r['name_clean'])
        case, unit_g, stxt = parse_size(r['name_clean'])
        r['case_pack'], r['unit_g'], r['size_txt'] = case, unit_g, stxt
        reasons = []
        if not r['price']:
            reasons.append('no-price')
        if not r['brand']:
            reasons.append('no-brand')
        r['skip_reason'] = ','.join(reasons) or None

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)

    importable = [r for r in rows if not r['skip_reason']]
    print(f'sheets: {len(HANDLERS)}  rows: {len(rows)}  importable: {len(importable)}')
    from collections import Counter
    print('\nby brand (importable):')
    for b, c in Counter(r['brand'] for r in importable).most_common():
        print(f'  {c:4d}  {b}')
    skipped = Counter(r['skip_reason'] for r in rows if r['skip_reason'])
    print('\nskipped:')
    for reason, c in skipped.most_common():
        print(f'  {c:4d}  {reason}')
    nosize = [r for r in importable if not r['size_txt']]
    print(f'\nno pack size parsed: {len(nosize)}')
    for r in nosize[:25]:
        print(f'  [{r["sheet"]}:{r["line"]}] {r["raw_name"]}')
    print(f'\nwrote {args.out}')


if __name__ == '__main__':
    main()
