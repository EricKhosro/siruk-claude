"""ArmSoft goods / prices / stock vs the live Siruk catalogue, hafo's stock and Siruk Ops (2026-11-19).

  uv run --no-sync --with openpyxl python scripts/armsoft-vs-siruk.py Scale/armsoft-export-<d>.xml       Scale/armsoft-prices-<d>.xlsx Scale/armsoft-turnover-<d>.xlsx runs/<d>/siruk-export.json       .siruk-cache/hafo-watch/snapshot.json final/armsoft-<d>/armsoft-vs-siruk-<d>.xlsx [runs/<d>/ops-stock.json]

Inputs: the ArmSoft goods XML, price list and turnover exports (/armsoft-app → Export), `siruk export
--format json`, a fresh `hafo-watch.py crawl`, and optionally `siruk ops stock --json`.
Sheets: ArmSoft goods with no live Siruk variant, live variants with no ArmSoft good, price and barcode
differences, VAT on, negative stock, the Siruk 0 / 10 stock rule (knowledge/goods-setups.md 2026-11-06),
and Ops vs ArmSoft per code (a kg good: Ops bags × bag kg + loose grams). Read-only: it writes nothing.
"""
import sys, os, json, csv, re, importlib.util, collections
import xml.etree.ElementTree as ET
import openpyxl
from openpyxl.styles import Font, PatternFill

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
goods_xml, prices_xlsx, turnover, siruk_json, hafo_json, out = sys.argv[1:7]
ops_json = sys.argv[7] if len(sys.argv) > 7 else None

spec = importlib.util.spec_from_file_location('gp', os.path.join(ROOT, 'scripts', 'glovo-portal.py'))
gp = importlib.util.module_from_spec(spec); spec.loader.exec_module(gp)
stock = gp.armsoft_stock(turnover, goods_xml)

NS = {'a': 'http://www.armsoft.am/Accountant/6.0'}
goods = {}
for g in ET.parse(goods_xml).getroot().findall('a:Goods', NS):
    c = g.findtext('a:Code', '', NS)
    goods[c] = {'name': g.findtext('a:Name', '', NS), 'unit': g.findtext('a:Unit', '', NS),
                'alt': g.findtext('a:AltUnit', '', NS), 'weight': g.findtext('a:IsWeight', '', NS) == 'true',
                'vat': g.findtext('a:VAT', '', NS) == 'true',
                'units': {q.findtext('a:Unit', '', NS): float(q.findtext('a:Coef', '0', NS))
                          for q in g.findall('a:GoodQuantityUnits/a:QuantityUnitPart', NS)},
                'barcodes': {(b.findtext('a:Unit', '', NS), b.findtext('a:BarCode', '', NS))
                             for b in g.findall('a:GoodBarCodes/a:MTBarCode', NS)}}

# latest price per (code, unit) for price type 01
price = {}
wb = openpyxl.load_workbook(prices_xlsx, read_only=True)
for r in wb.active.iter_rows(min_row=3, values_only=True):
    if not r or not r[1] or r[5] != '01':
        continue
    k = (str(r[1]), str(r[7]))
    if k not in price or r[0] >= price[k][0]:
        price[k] = (r[0], r[10])

retired = {r['old_code'] for r in csv.DictReader(open(os.path.join(ROOT, 'state/armsoft-duplicate-codes.csv'), encoding='utf-8-sig'))}
retired |= {'0302', '1508', '1552', '1473'} | {f'{i:04d}' for i in range(1466, 1473)}

sir = json.load(open(siruk_json, encoding='utf-8'))
live = [v for v in sir if not v.get('is_discontinued')]
by_code = collections.defaultdict(list)
for v in sir:
    c = (v.get('accounting_code') or '').strip()
    if c:
        by_code[c].append(v)

# hafo snapshot: by EAN and by normalised article
hs = json.load(open(hafo_json, encoding='utf-8'))
hp = list(hs['rows'].values())
print('hafo snapshot', hs['fetched'], 'complete' if hs.get('complete') else 'INCOMPLETE')
h_ean, h_art = {}, {}
for p in hp:
    for e in re.findall(r'\d{8,14}', str(p.get('barcode') or '')):
        h_ean[e.lstrip('0')] = p
    s = re.sub(r'[\s\-]', '', str(p.get('sku') or '')).upper()
    if s:
        h_art[s] = p


def hafo_for(v):
    e = str(v.get('barcode') or '').lstrip('0')
    if e and e in h_ean:
        return h_ean[e]
    s = re.sub(r'[\s\-]', '', str(v.get('sku') or '')).upper()
    s = re.sub(r'-(KG|100G|\d)$', '', s)
    for k in (s, s + 'TX', s.replace('TX', '')):
        if k in h_art:
            return h_art[k]
    return None


sheets = collections.OrderedDict()
def add(sheet, header, row):
    sheets.setdefault(sheet, [header]).append(row)

# A. ArmSoft goods with no live Siruk variant
for c, g in sorted(goods.items()):
    if c in retired:
        continue
    vs = by_code.get(c, [])
    livevs = [v for v in vs if not v.get('is_discontinued')]
    if not livevs:
        st = stock.get(c, {}).get('stock', '')
        add('ArmSoft not on Siruk', ['Code', 'ArmSoft name', 'Unit', 'Stock', 'Sale price 01', 'Siruk (discontinued)', 'Barcodes'],
            [c, g['name'], g['unit'], st, (price.get((c, g['unit'])) or (None, ''))[1],
             ', '.join(f"{v['product_id']}/{v['sku']}" for v in vs), ' '.join(b for _, b in sorted(g['barcodes']))])

# B. live Siruk variants with no ArmSoft good
for v in live:
    c = (v.get('accounting_code') or '').strip()
    if not c or c not in goods:
        add('Siruk not in ArmSoft', ['Product', 'Variant', 'SKU', 'Name', 'Size', 'Code on Siruk', 'Price', 'Barcode', 'Available'],
            [v['product_id'], v['variant_id'], v['sku'], f"{v['brand']} {v['product_name']}", v.get('size') or v.get('variant_name'),
             c, v['price'], v.get('barcode'), v.get('available')])

# C. prices and D. barcodes
for v in live:
    c = (v.get('accounting_code') or '').strip()
    g = goods.get(c)
    if not g:
        continue
    sku = str(v['sku'])
    if sku.endswith('-KG'):
        units = ['303']
    elif sku.endswith('-100G'):
        units = []
    elif g['unit'] == '303':
        units = [g['alt'] or '003']
    else:
        units = [g['unit']]
    for u in units:
        p = price.get((c, u))
        if p is None or float(p[1] or 0) != float(v['price']):
            add('Price differs', ['Code', 'Unit', 'ArmSoft price', 'Since', 'Siruk price', 'SKU', 'Name'],
                [c, u, p[1] if p else 'none', p[0].date().isoformat() if p else '', v['price'], sku, f"{v['brand']} {v['product_name']} {v.get('size') or ''}"])
    bc = str(v.get('barcode') or '').strip()
    if bc and bc not in {b for _, b in g['barcodes']}:
        add('Barcode not in ArmSoft', ['Code', 'SKU', 'Siruk barcode', 'ArmSoft barcodes', 'Name'],
            [c, sku, bc, ' '.join(f'{u}:{b}' for u, b in sorted(g['barcodes'])), f"{v['brand']} {v['product_name']} {v.get('size') or ''}"])
    if g['vat']:
        add('ArmSoft VAT on', ['Code', 'Name'], [c, g['name']])

# E. stock
for c, s in sorted(stock.items()):
    if s['stock'] < -1e-6:
        add('Negative stock', ['Code', 'Name', 'Stock', 'Unit'], [c, goods.get(c, {}).get('name', ''), s['stock'], 'kg' if s['kg'] else 'pcs'])

for v in live:
    c = (v.get('accounting_code') or '').strip()
    if not c or c not in goods:
        continue
    st = stock.get(c, {'kg': goods[c]['unit'] == '303', 'stock': 0, 'bag': goods[c]['units'].get(goods[c]['alt'], 0)})
    need, why = gp.variant_need(v, st)
    if need is None:
        continue
    have = st['stock'] >= need - 1e-6
    avail = float(v.get('available') or 0)
    h = hafo_for(v)
    hq = None if h is None else float(h.get('qty') or h.get('qty_in_stock') or 0)
    rc = (v.get('brand') or '').lower().startswith('royal canin')
    name = f"{v['brand']} {v['product_name']} {v.get('size') or v.get('variant_name') or ''}"
    row = [v['product_id'], v['variant_id'], v['sku'], c, name, st['stock'], 'kg' if st['kg'] else 'pcs', why,
           'yes' if have else 'no', avail, v.get('stock_status'), 'not sold' if h is None else hq, 'RC' if rc else '']
    hdr = ['Product', 'Variant', 'SKU', 'Code', 'Name', 'ArmSoft stock', 'Unit', 'Rule', 'We have', 'Siruk available',
           'Siruk status', 'hafo qty', 'Note']
    if avail <= 0 and have:
        add('Siruk 0 but we have it', hdr, row)
    elif avail <= 0 and not have and h is not None and hq and hq > 0 and not rc:
        add('Siruk 0, hafo has it', hdr, row)
    elif avail > 0 and not have and (rc or h is None or not hq):
        add('Siruk on, nobody has it', hdr, row)

# F. Siruk Ops vs ArmSoft, per ArmSoft code
if ops_json:
    pack = {c: g['units'].get(g['alt'], 0) if g['unit'] == '303' else 0 for c, g in goods.items()}
    tot, onames = collections.defaultdict(float), {}
    for r in json.load(open(ops_json, encoding='utf-8'))['rows']:
        c = (r.get('accountingCode') or '').strip()
        q = float(r['quantity'])
        kg = stock.get(c, {}).get('kg') or goods.get(c, {}).get('unit') == '303'
        tot[c] += q / 1000 if r['unit'] == 'g' else (q * pack.get(c, 0) if kg else q)
        onames.setdefault(c, f"{r['productName']} {r['label']}")
    for c in sorted(set(tot) | {k for k, s in stock.items() if abs(s['stock']) > 1e-6}):
        o, s_ = round(tot.get(c, 0), 3), stock.get(c, {}).get('stock', 0)
        if abs(o - s_) > 1e-3:
            add('Ops vs ArmSoft', ['Code', 'Name', 'ArmSoft', 'Ops', 'Ops − ArmSoft', 'Unit'],
                [c, onames.get(c) or goods.get(c, {}).get('name', ''), s_, o, round(o - s_, 3),
                 'kg' if stock.get(c, {}).get('kg') else 'pcs'])

wb = openpyxl.Workbook(); wb.remove(wb.active)
for name, rows in sheets.items():
    ws = wb.create_sheet(name[:31])
    for r in rows:
        ws.append(r)
    for cell in ws[1]:
        cell.font = Font(bold=True, color='FFFFFF'); cell.fill = PatternFill('solid', fgColor='1F4E78')
    ws.freeze_panes = 'A2'; ws.auto_filter.ref = ws.dimensions
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = min(60, max(8, max(len(str(c.value or '')) for c in col) + 2))
wb.save(out)
print(f'goods {len(goods)}, Siruk live variants {len(live)}, stock rows {len(stock)}, hafo rows {len(hp)}')
for name, rows in sheets.items():
    print(f'{name}: {len(rows) - 1}')
print('→', out)
