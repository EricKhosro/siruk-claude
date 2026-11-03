#!/usr/bin/env python3
"""Build the Yandex price proposal: every Siruk variant, its cost, its Siruk price,
the rival's Yandex price where a checked match exists, and a suggested Yandex price.

Reads
  final/siruk-source-of-truth.xlsx                 price + buying price per variant (dp/<variant id> link)
  .siruk-cache/yandex/<slug>-matches.json          scripts/yandex-price-compare.py
  .siruk-cache/yandex/<slug>-verdicts.json         {variant_id: {verdict, note}} — the hand / agent check
Writes
  final/yandex/siruk-yandex-prices.xlsx

The pricing rule lives in Excel formulas driven by the Settings sheet, so the
user can change commission / undercut / minimum margin and see every row move:
  matched (verdict "same"):  max(floor(rival × (1 − undercut)), floor price)
  no rival price:            max(ceiling(Siruk price × (1 + uplift)), floor price)
  floor price = ceiling(cost ÷ (1 − commission − minimum margin))
Rounded to 50 ֏.

  uv run --no-sync --with openpyxl python scripts/yandex-price-sheet.py zoovetam
"""
import json, os, re, sys
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.formatting.rule import FormulaRule

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, '.siruk-cache', 'yandex')
OUT = os.path.join(ROOT, 'final', 'yandex', 'siruk-yandex-prices.xlsx')


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else 'zoovetam'
    data = json.load(open(os.path.join(CACHE, f'{slug}-matches.json'), encoding='utf-8'))
    vpath = os.path.join(CACHE, f'{slug}-verdicts.json')
    verdicts = json.load(open(vpath, encoding='utf-8')) if os.path.exists(vpath) else {}

    sot = {}
    ws = openpyxl.load_workbook(os.path.join(ROOT, 'final', 'siruk-source-of-truth.xlsx'), read_only=True, data_only=True).worksheets[0]
    for r in list(ws.iter_rows(values_only=True))[1:]:
        m = re.search(r'/dp/(\d+)', r[7] or '')
        if m:
            sot[int(m.group(1))] = {'price': r[2], 'cost': r[3]}

    wb = openpyxl.Workbook()
    st = wb.active
    st.title = 'Settings'
    head = Font(bold=True)
    inp = PatternFill('solid', fgColor='FFF2CC')
    rows = [
        ('Yandex commission (share of the shelf price Yandex keeps)', 0.20,
         'PLACEHOLDER — replace with the rate in your Yandex contract'),
        ('Undercut vs Zoovet on Yandex', 0.05, 'how much cheaper than Zoovet we want to be'),
        ('Minimum net margin after commission', 0.15, 'never price below cost ÷ (1 − commission − this)'),
        ('Uplift on the Siruk price when Zoovet has no such item', 0.14,
         'Zoovet sells on Yandex at a median 1.20× our Siruk price; 1.20 × (1 − 5%) ≈ +14%'),
        ('Round to (֏)', 50, ''),
    ]
    st['A1'], st['B1'], st['C1'] = 'Setting', 'Value', 'Note'
    for c in 'ABC':
        st[f'{c}1'].font = head
    for i, (k, v, n) in enumerate(rows, start=2):
        st[f'A{i}'], st[f'B{i}'], st[f'C{i}'] = k, v, n
        st[f'B{i}'].fill = inp
        st[f'B{i}'].number_format = '0%' if isinstance(v, float) else '0'
    st.column_dimensions['A'].width = 58
    st.column_dimensions['B'].width = 10
    st.column_dimensions['C'].width = 80
    COMM, UNDER, MINM, UPL, RND = 'Settings!$B$2', 'Settings!$B$3', 'Settings!$B$4', 'Settings!$B$5', 'Settings!$B$6'

    ps = wb.create_sheet('Prices')
    cols = ['Brand', 'Product', 'Variant', 'SKU', 'Barcode', 'Category', 'In stock',
            'Cost (֏)', 'Siruk price (֏)', 'Siruk margin %',
            'Zoovet Yandex item', 'Zoovet Yandex price (֏)', 'Match check', 'Match note',
            'Floor price (֏)', 'Suggested Yandex price (֏)', 'Price basis',
            'Net after commission (֏)', 'Net margin %', 'vs Zoovet %', 'vs Siruk price %']
    ps.append(cols)
    for c in range(1, len(cols) + 1):
        ps.cell(1, c).font = head
        ps.cell(1, c).alignment = Alignment(wrap_text=True, vertical='top')

    n = 0
    for m in data['matches']:
        vid = m['variant_id']
        s = sot.get(vid, {})
        price = s.get('price') or m['price']
        cost = s.get('cost') or m['cost_price']
        v = verdicts.get(str(vid), {})
        verdict = v.get('verdict', 'unchecked') if m.get('rival_name') else ''
        rival = float(m['rival_price']) if m.get('rival_name') and verdict == 'same' else None
        ps.append([m['brand'], m['product_name'], m['variant_name'], m['sku'], m['barcode'], m['categories'],
                   'yes' if m['stock_status'] == 'in_stock' else 'no', cost, price, None,
                   m.get('rival_name', ''), float(m['rival_price']) if m.get('rival_name') else None,
                   verdict, v.get('note', '')])
        r = ps.max_row
        ps[f'J{r}'] = f'=IF(AND(I{r}>0,H{r}>0),(I{r}-H{r})/I{r},"")'
        ps[f'O{r}'] = f'=IF(H{r}>0,CEILING(H{r}/(1-{COMM}-{MINM}),{RND}),"")'
        if rival:
            ps[f'P{r}'] = f'=MAX(FLOOR(L{r}*(1-{UNDER}),{RND}),N(O{r}))'
            ps[f'Q{r}'] = f'=IF(FLOOR(L{r}*(1-{UNDER}),{RND})>=N(O{r}),"under Zoovet","floor: Zoovet too cheap for our margin")'
        else:
            ps[f'P{r}'] = f'=MAX(CEILING(I{r}*(1+{UPL}),{RND}),N(O{r}))'
            ps[f'Q{r}'] = f'=IF(CEILING(I{r}*(1+{UPL}),{RND})>=N(O{r}),"Siruk price + uplift","floor: margin")'
        ps[f'R{r}'] = f'=IF(H{r}>0,P{r}*(1-{COMM})-H{r},"")'
        ps[f'S{r}'] = f'=IF(H{r}>0,R{r}/P{r},"")'
        ps[f'T{r}'] = f'=IF(N(L{r})>0,P{r}/L{r}-1,"")'
        ps[f'U{r}'] = f'=IF(I{r}>0,P{r}/I{r}-1,"")'
        n += 1

    last = ps.max_row
    for col in 'HILOPR':
        for c in ps[f'{col}2:{col}{last}']:
            c[0].number_format = '#,##0'
    for col in 'JSTU':
        for c in ps[f'{col}2:{col}{last}']:
            c[0].number_format = '0.0%'
    widths = dict(A=14, B=40, C=26, D=12, E=15, F=22, G=8, H=10, I=10, J=9, K=52, L=11, M=11, N=34,
                  O=10, P=12, Q=22, R=12, S=9, T=9, U=9)
    for k, w in widths.items():
        ps.column_dimensions[k].width = w
    ps.freeze_panes = 'C2'
    ps.row_dimensions[1].height = 45
    tab = Table(displayName='Prices', ref=f'A1:{get_column_letter(len(cols))}{last}')
    tab.tableStyleInfo = TableStyleInfo(name='TableStyleLight9', showRowStripes=True)
    ps.add_table(tab)
    green, red = PatternFill('solid', fgColor='E2F0D9'), PatternFill('solid', fgColor='F8CBAD')
    ps.conditional_formatting.add(f'P2:P{last}', FormulaRule(formula=[f'LEFT($Q2,5)="floor"'], fill=red))
    ps.conditional_formatting.add(f'P2:P{last}', FormulaRule(formula=['$Q2="under Zoovet"'], fill=green))
    for c in ps[f'P2:P{last}']:
        c[0].font = Font(bold=True)

    zs = wb.create_sheet('Zoovet only')
    zs.append(['Zoovet Yandex item', 'Price (֏)', 'Promo price', 'Weight', 'Zoovet category', 'Brand we also carry'])
    for c in range(1, 7):
        zs.cell(1, c).font = head
    for z in data['rival_unmatched']:
        zs.append([z['name'], float(z['price']), z['promo_price'] or None, z['weight'], ' | '.join(z['categories']), z['brand'] or ''])
    for k, w in dict(A=80, B=10, C=10, D=10, E=40, F=18).items():
        zs.column_dimensions[k].width = w
    zs.freeze_panes = 'A2'
    zs.auto_filter.ref = f'A1:F{zs.max_row}'

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    wb.save(OUT)
    print(f'{n} variants → {OUT}  (verdicts: {len(verdicts)})')


if __name__ == '__main__':
    main()
