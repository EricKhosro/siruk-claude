"""Ops goods vs ArmSoft goods, both ways (2026-11-24): every Ops variant reaches an ArmSoft good by accounting code, its barcodes sit on that good, a loose variant has unit 303; ArmSoft goods no Ops variant uses.

  python scripts/ops-vs-armsoft-goods.py Scale/armsoft-export-<d>.xml <out.json> "runs/<d>/ops-goods-p*.json"

Ops pages: siruk ops goods list --json --page N --page-size 200. Read-only."""
import sys, json, glob, collections
import xml.etree.ElementTree as ET
NS = {'a': 'http://www.armsoft.am/Accountant/6.0'}
xmlp = sys.argv[1]
goods = {}
for g in ET.parse(xmlp).getroot().findall('a:Goods', NS):
    c = g.findtext('a:Code', '', NS)
    goods[c] = {'name': g.findtext('a:Name', '', NS), 'long': g.findtext('a:LongName', '', NS),
                'unit': g.findtext('a:Unit', '', NS), 'weight': g.findtext('a:IsWeight', '', NS) == 'true',
                'units': {q.findtext('a:Unit', '', NS) for q in g.findall('a:GoodQuantityUnits/a:QuantityUnitPart', NS)},
                'bc': {b.findtext('a:BarCode', '', NS) for b in g.findall('a:GoodBarCodes/a:MTBarCode', NS)} | {g.findtext('a:BarCode', '', NS)}}
bc_index = collections.defaultdict(set)
for c, g in goods.items():
    for b in g['bc']:
        if b: bc_index[b].add(c)
ops = []
for f in sorted(glob.glob(sys.argv[3])):
    ops += json.load(open(f, encoding='utf-8'))['items']
print('ArmSoft goods', len(goods), '| Ops variants', len(ops))
by_code = collections.defaultdict(list)
no_code, bad_code, bc_miss, unit_miss = [], [], [], []
for v in ops:
    c = (v.get('accountingCode') or '').strip()
    q = sum((s.get('quantity') or 0) for s in v['stock'] if s['kind'] == 'shop')
    row = dict(sku=v['sku'], name=f"{v['brand']} {v['productName']['en']} — {v['label']}", code=c, barcode=v.get('barcode') or '',
               active=v['isActive'], disc=v['isDiscontinued'], stock=q, unit=v['stockUnit'], sid=v.get('sirukVariantId'))
    if not c:
        row['armsoft_by_barcode'] = ','.join(sorted(bc_index.get(row['barcode'], [])))
        no_code.append(row); continue
    if c not in goods:
        row['armsoft_by_barcode'] = ','.join(sorted(bc_index.get(row['barcode'], [])))
        bad_code.append(row); continue
    by_code[c].append(row)
    g = goods[c]
    for b in [row['barcode']] + list(v.get('extraBarcodes') or []):
        b = b if isinstance(b, str) else (b.get('barcode') or '')
        if b and b not in g['bc']:
            bc_miss.append(dict(row, missing=b, armsoft_bc=' '.join(sorted(x for x in g['bc'] if x)), armsoft_name=g['name']))
    if row['unit'] == 'loose' and '303' not in g['units']:
        unit_miss.append(dict(row, armsoft_units=' '.join(sorted(g['units']))))
as_only = [dict(code=c, name=g['name'], long=g['long'], bc=' '.join(sorted(x for x in g['bc'] if x))) for c, g in sorted(goods.items()) if c not in by_code]
out = dict(no_code=no_code, code_not_in_armsoft=bad_code, barcode_not_on_good=bc_miss, loose_without_303=unit_miss, armsoft_only=as_only)
json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for k, rows in out.items():
    print(f'\n## {k}: {len(rows)}')
    for r in rows[:400]: print(' |', ' | '.join(str(x) for x in r.values()))
