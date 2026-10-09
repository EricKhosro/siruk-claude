#!/usr/bin/env python3
"""Fill the ArmSoft import workbook `csv/Siruk-hx.xlsx` from the Scale XML.

Four sheets, all built from `csv/all-xml-scale.xml` — the same file we hand the
ArmSoft scale program — so the workbook and the XML can never drift apart:

  MATERIALS   one row per <Goods>, column for column (see FIELDS below).
  PRICES      one row per (good, quantity unit). Price type is always "01",
              currency AMD, date = today (--date). The price is the live Siruk
              sale price, taken from runs/2026-10-04-rival-prices/
              final/siruk-source-of-truth.csv through Scale/scale-codes-per-kg.csv,
              which already joins each source-of-truth variant to its good.
              A good sold loose has two rows under one code: 303 carries its
              "1 kg" variant price, 003 the bag variant price.
              Goods with no Siruk variant are priced from
              state/armsoft-extra-prices.csv where we have a sourced price,
              and skipped (listed on stderr) where we do not — never guessed.
  MTQUNIT     one row per <QuantityUnitPart>, with its conversion coefficient;
              the good's <AltUnit> is flagged IsAltUnit.
  MTBARCODES  one row per <MTBarCode> (good + unit + barcode).

Usage:
    build-armsoft-import.py [--date 2026-10-05] [--sheets PRICES,MATERIALS] [--dry-run]
"""
import argparse, csv, datetime, pathlib, re, sys
from collections import defaultdict
from copy import copy

import openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
XML = ROOT / 'csv/all-xml-scale.xml'
MAP = ROOT / 'Scale/scale-codes-per-kg.csv'
EXTRA = ROOT / 'state/armsoft-extra-prices.csv'
XLSX = ROOT / 'csv/Siruk-hx.xlsx'

# MATERIALS column -> the <Goods> child element that fills it, in sheet order.
# `None` means the sheet column has no XML counterpart.
FIELDS = [
    ('Կոդ', 'Code'), ('Անվանում', 'Name'), ('Տեսակ', 'Type'), ('Խումբ', 'Group'),
    ('ԱԴԳՏ դասակարգիչ', 'CPACode'), ('Հիմնական չափման միավոր', 'Unit'),
    ('Բնութագիր', 'Description'), ('Հաշվառման մեթոդ', 'ExpMethod'),
    ('Գծիկավոր կոդ', 'BarCode'), ('ԱԱՀ', 'VAT'),
    ('Ցույց տալ գնացուցակներում', 'ShowInPriceList'), ('Քաշային', 'IsWeight'),
    ('PLU կոդ', 'PLUCode'), ('Ստուգել դրոշմանիշները', 'CheckMarking'),
    ('Երկիր', 'Country'), ('Արտադրող', 'Producer'),
    ('Հատկություն 1', 'Property1'), ('Հատկություն 2', 'Property2'),
    ('Լրիվ անվանում', 'LongName'), ('Նվազագույն քանակ', 'MinQTY'),
    ('Առավելագույն քանակ', 'MaxQTY'), ('Բոնուս %', 'Bonus'),
    ('Բոնուս չհաշվարկել', 'IgnoreBonus'), ('Բոնուս միավոր', 'Point'),
    ('Հավելագին %', 'Extra'), ('ՀԾԲ գործակից', 'Coeff'), ('Զեղչի %', 'Discount'),
    ('Անվանում (en)', 'CaptionEN'), ('Անվանում (ru)', 'CaptionRU'),
    ('Լրացուցիչ բնութագիր 1', 'AdditionalDescr1'),
    ('Լրացուցիչ բնութագիր 2', 'AdditionalDescr2'),
    ('Բնապահպանական հարկի %', 'EnvironmentalFeePercent'),
    ('Արտաքին կոդ', 'ExternalCode'),
    ('Փոխարկելի ապրանքի խումբ', 'SubstituteItemsGroup'),
    ('Հիմնական մատակարար', 'MainSupplier'), ('Գնապիտակի չափման միավոր', 'LabelUnit'),
    ('Վերահաշվարկի գործակից', 'LabelCoeff'), ('Նկար', 'Image'),
    ('սխալ', None),
]
# Columns ArmSoft reads as 0/1 flags; the XML writes them as true/false.
BOOLS = {'VAT', 'ShowInPriceList', 'IsWeight', 'CheckMarking', 'IgnoreBonus'}
# Columns that are numbers, not text.
NUMS = {'Type', 'ExpMethod', 'MinQTY', 'MaxQTY', 'Bonus', 'Point', 'Extra',
        'Coeff', 'Discount', 'EnvironmentalFeePercent', 'LabelCoeff'}


def text(el, tag):
    """The element's text, or None when absent / xsi:nil / empty."""
    m = re.search(rf'<{tag}\b[^>]*/>|<{tag}>(.*?)</{tag}>', el, re.S)
    if not m or m.group(0).endswith('/>'):
        return None
    v = (m.group(1) or '').strip()
    v = (v.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
          .replace('&quot;', '"').replace('&apos;', "'"))
    return v or None


def parse_goods():
    """Every <Goods> block, in XML order, as a dict of its scalar fields plus
    its quantity units and barcodes."""
    xml = XML.read_text(encoding='utf-8-sig')
    out = []
    for g in re.findall(r'<Goods[ >].*?</Goods>', xml, re.S):
        head = g.split('<GoodQuantityUnits', 1)[0]
        tail = g.split('</GoodBarCodes>', 1)[-1]
        d = {tag: text(head, tag) or text(tail, tag)
             for _, tag in FIELDS if tag}
        d['units'] = [{'Unit': text(p, 'Unit'), 'Coef': text(p, 'Coef'),
                       'IsDefault': text(p, 'IsDefault'), 'Image': text(p, 'Image')}
                      for p in re.findall(r'<QuantityUnitPart>.*?</QuantityUnitPart>', g, re.S)]
        d['barcodes'] = [{'Unit': text(b, 'Unit'), 'BarCode': text(b, 'BarCode')}
                         for b in re.findall(r'<MTBarCode>.*?</MTBarCode>', g, re.S)]
        d['AltUnit'] = text(head, 'AltUnit')
        out.append(d)
    return out


def materials_rows(goods):
    rows = []
    for g in goods:
        row = []
        for _, tag in FIELDS:
            if tag is None:
                row.append(None)
            elif tag in BOOLS:
                v = g.get(tag)
                row.append(None if v is None else (1 if v == 'true' else 0))
            elif tag in NUMS:
                v = g.get(tag)
                row.append(None if v is None else float(v))
            else:
                row.append(g.get(tag))
        rows.append(row)
    return rows


def mtqunit_rows(goods):
    rows = []
    for g in goods:
        for u in g['units']:
            is_alt = 1 if (u['Unit'] == g['AltUnit'] and u['IsDefault'] != 'true') else 0
            rows.append([g['Code'], u['Unit'], float(u['Coef']), is_alt,
                         u['Image'], None])
    return rows


def mtbarcodes_rows(goods):
    return [[g['Code'], b['Unit'], b['BarCode'], None]
            for g in goods for b in g['barcodes'] if b['BarCode']]


def prices_rows(goods, day, problems):
    variants = defaultdict(list)
    for r in csv.DictReader(MAP.open(encoding='utf-8-sig')):
        variants[r['good_code']].append(r)
    extra = defaultdict(dict)
    if EXTRA.exists():
        for r in csv.DictReader(EXTRA.open(encoding='utf-8-sig')):
            extra[r['good_code']][r['unit']] = float(r['price_amd'])

    rows = []
    for g in goods:
        code, units = g['Code'], [u['Unit'] for u in g['units']]
        vs = variants.get(code)
        if not vs:
            if code in extra:
                for u in units:
                    if u in extra[code]:
                        rows.append([code, u, extra[code][u]])
                    else:
                        problems.append(f'{code}/{u}: no Siruk variant and no sourced price')
            else:
                problems.append(f'{code}: not on Siruk yet, no sourced price')
            continue
        # the loose "1 kg" variant is the one that got a scale code
        per_kg = [v for v in vs if v['scale_code']]
        bag = [v for v in vs if not v['scale_code']]
        groups = {}
        if '303' in units:
            if per_kg:
                groups['303'] = per_kg
            else:
                problems.append(f'{code}: unit 303 but no "1 kg" variant')
        elif per_kg:
            problems.append(f'{code}: has a "1 kg" variant but no unit 303')
        for u in units:
            if u != '303':
                groups[u] = bag or vs
        for u in units:
            group = groups.get(u)
            if not group:
                continue
            seen = {v['price_amd'] for v in group}
            if len(seen) > 1:
                problems.append(f'{code}/{u}: variants disagree on price {sorted(seen)}')
                continue
            rows.append([code, u, float(group[0]['price_amd'])])
    return [['01', c, u, day, 'AMD', p, None] for c, u, p in rows]


def write(ws, rows, first_row=3):
    """Replace the sheet's data rows, keeping row `first_row`'s cell styles."""
    style = [copy(c._style) for c in ws[first_row]]
    for row in ws.iter_rows(min_row=first_row, max_row=ws.max_row):
        for c in row:
            c.value = None
    for i, vals in enumerate(rows):
        for col, val in enumerate(vals, start=1):
            c = ws.cell(row=first_row + i, column=col, value=val)
            if col - 1 < len(style):
                c._style = copy(style[col - 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--sheets', default='MATERIALS,PRICES,MTQUNIT,MTBARCODES')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    day = datetime.datetime.fromisoformat(args.date)
    want = [s.strip().upper() for s in args.sheets.split(',') if s.strip()]

    goods = parse_goods()
    problems = []
    built = {
        'MATERIALS': materials_rows(goods),
        'PRICES': prices_rows(goods, day, problems),
        'MTQUNIT': mtqunit_rows(goods),
        'MTBARCODES': mtbarcodes_rows(goods),
    }
    for p in problems:
        print('SKIP/WARN', p, file=sys.stderr)
    print(f'{len(goods)} goods parsed', file=sys.stderr)
    for s in want:
        print(f'  {s}: {len(built[s])} rows', file=sys.stderr)
    if args.dry_run:
        for s in want:
            print(f'--- {s}', file=sys.stderr)
            for r in built[s][:3]:
                print('   ', r, file=sys.stderr)
        return

    wb = openpyxl.load_workbook(XLSX)
    for s in want:
        write(wb[s], built[s])
    wb.save(XLSX)
    print(f'wrote {", ".join(want)} in {XLSX}', file=sys.stderr)


if __name__ == '__main__':
    main()
